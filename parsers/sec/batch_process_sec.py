"""
Batch Processing Script: Parse All SEC Filings with Concurrent Execution

This script:
1. Discovers SEC filing TXT files from directories
2. Filters by filing type (10-K, 10-Q, 8-K, S-1)
3. Processes filings concurrently using ThreadPoolExecutor
4. Extracts knowledge graphs and scores for relevant filings
5. Saves results with checkpoint system

Usage:
    # Test with first 4 files (1 per type)
    python batch_process_sec.py --limit 4

    # Process all high-value filings (10-K, 10-Q, 8-K, S-1)
    python batch_process_sec.py

    # Custom config and output
    python batch_process_sec.py --config configs/evtol_config.json --input data/eVTOL/sec_filings/txt --output data/eVTOL/sec_filings
"""

import os
import sys
import json
import time
import datetime
import traceback
import argparse
from pathlib import Path
from time import sleep
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import islice
from typing import List, Dict, Any, Optional, Tuple
from tqdm import tqdm

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from parsers.sec.sec_parser import SECFilingParser, load_industry_config
from parsers.sec.checkpoint_manager import (
    ScholarlyCheckpointManager,
    save_checkpoint_files,
    merge_checkpoints
)


def chunked(it, size):
    """Partition an iterable into chunks (lists) of 'size' elements."""
    it = iter(it)
    while True:
        batch = list(islice(it, size))
        if not batch:
            break
        yield batch


def discover_sec_files(
    input_dir: str,
    filing_types: List[str] = None,
    metadata_file: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Discover SEC filing TXT files from directory structure.

    Args:
        input_dir: Root directory containing filing type subdirectories
        filing_types: List of filing types to include (e.g., ["10-K", "10-Q", "8-K", "S-1"])
        metadata_file: Optional path to metadata.json for URL and ticker info

    Returns:
        List of dicts with 'file_path', 'filing_type', 'ticker', 'url'
    """
    if filing_types is None:
        filing_types = ["10-K", "10-Q", "8-K", "S-1"]

    # Load metadata if available
    metadata_lookup = {}
    if metadata_file and os.path.exists(metadata_file):
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
            for filing in metadata.get("filings", []):
                # Key by filename parts
                key = f"{filing.get('ticker')}_{filing.get('filing_type')}_{filing.get('accession')}"
                metadata_lookup[key] = filing

    files = []

    for filing_type in filing_types:
        # Construct subdirectory path
        subdir = os.path.join(input_dir, filing_type)

        if not os.path.exists(subdir):
            print(f"  Warning: Directory not found: {subdir}")
            continue

        # Find all TXT files
        for filename in os.listdir(subdir):
            if not filename.endswith('.txt'):
                continue

            file_path = os.path.join(subdir, filename)

            # Parse filename for ticker and accession
            # Format: {TICKER}_{FILING_TYPE}_{DATE}_{ACCESSION}.txt
            parts = filename.replace('.txt', '').split('_')
            ticker = parts[0] if len(parts) >= 1 else None
            accession = parts[3] if len(parts) >= 4 else None

            # Lookup metadata
            metadata_key = f"{ticker}_{filing_type}_{accession}"
            metadata_record = metadata_lookup.get(metadata_key)

            files.append({
                'file_path': file_path,
                'filing_type': filing_type,
                'ticker': ticker,
                'metadata': metadata_record
            })

    return files


def safe_parse(
    parser: SECFilingParser,
    file_info: Dict[str, Any],
    retries: int = 0,
    max_retries: int = 2,
    backoff_base_sec: int = 2
) -> Tuple[bool, Dict[str, Any]]:
    """
    Parse a single SEC filing with retry logic and exponential backoff.

    Args:
        parser: Initialized SECFilingParser
        file_info: Dict with file_path, filing_type, metadata
        retries: Current retry count
        max_retries: Maximum retry attempts
        backoff_base_sec: Base seconds for exponential backoff

    Returns:
        Tuple of (success: bool, result: dict or error: dict)
    """
    attempt = 0
    while True:
        try:
            # Suppress token usage prints during batch processing
            import io
            import contextlib

            # Capture stdout to suppress print statements
            with contextlib.redirect_stdout(io.StringIO()):
                result = parser.parse_filing(
                    file_path=file_info['file_path'],
                    metadata_record=file_info.get('metadata')
                )

            return True, result

        except Exception as e:
            attempt += 1
            if attempt > max_retries:
                return False, {
                    "file_path": file_info['file_path'],
                    "ticker": file_info.get('ticker', 'unknown'),
                    "filing_type": file_info.get('filing_type', 'unknown'),
                    "error": f"{type(e).__name__}: {str(e)}",
                    "traceback": traceback.format_exc()
                }
            # Exponential backoff
            sleep(backoff_base_sec ** (attempt - 1))


def batch_process_sec_filings(
    config_path: str = "configs/evtol_config.json",
    input_dir: str = "data/eVTOL/sec_filings/txt",
    metadata_file: str = "data/eVTOL/sec_filings/metadata.json",
    output_dir: str = "data/eVTOL/sec_filings",
    filing_types: List[str] = None,
    limit: Optional[int] = None,
    start_index: int = 0,
    max_workers: int = 3,
    subbatch_size: int = 6,
    max_retries: int = 2,
    quality_threshold: float = 0.85,
    checkpoint_interval: int = 50,
    resume: bool = True,
    graph_relations_config: str = "configs/eVTOL_graph_relations.json"
):
    """
    Batch process SEC filings with concurrent execution and checkpointing.

    Args:
        config_path: Path to industry config JSON
        input_dir: Directory containing filing type subdirectories
        metadata_file: Path to metadata.json (optional, for URLs)
        output_dir: Directory to save output files
        filing_types: List of filing types to process (default: ["10-K", "10-Q", "8-K", "S-1"])
        limit: Maximum number of filings to process (None = all)
        start_index: Index to start from (default: 0)
        max_workers: Number of concurrent workers
        subbatch_size: Filings per sub-batch (wave)
        max_retries: Retry attempts per filing
        quality_threshold: Minimum score for relevance (default: 0.85)
        checkpoint_interval: Save checkpoint every N filings (default: 50)
        resume: Resume from existing checkpoints if True (default: True)
        graph_relations_config: Path to graph relations config
    """

    if filing_types is None:
        filing_types = ["10-K", "10-Q", "8-K", "S-1"]

    print("=" * 80)
    print("SEC FILINGS BATCH PROCESSING")
    print("=" * 80)

    # Load API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    # Load industry config
    print(f"\n[1/6] Loading industry config: {config_path}")
    config = load_industry_config(config_path)

    industry = config.get("industry", "Unknown")
    industry_name = config.get("industry_name", "Unknown")
    industry_keywords = config.get("keywords", {}).get("core", [])
    industry_description = f"{industry_name} - {config.get('description', '')}"

    print(f"  Industry: {industry}")
    print(f"  Keywords: {len(industry_keywords)} core keywords")

    # Initialize parser
    print(f"\n[2/6] Initializing SECFilingParser")
    parser = SECFilingParser(
        openai_api_key=api_key,
        config_path=graph_relations_config,
        industry_name=industry,
        industry_keywords=industry_keywords,
        industry_description=industry_description,
        model_name="gpt-4o-mini",
        temperature=0.0
    )
    print(f"  Model: gpt-4o-mini")
    print(f"  Quality Threshold: {quality_threshold}")
    print(f"  Max Workers: {max_workers}")
    print(f"  Sub-batch Size: {subbatch_size}")

    # Discover SEC files
    print(f"\n[3/6] Discovering SEC filings: {input_dir}")
    print(f"  Filing types: {', '.join(filing_types)}")
    all_files = discover_sec_files(input_dir, filing_types, metadata_file)
    print(f"  Total filings found: {len(all_files)}")

    # Select files to process
    if limit:
        files_to_process = all_files[start_index:start_index + limit]
        print(f"  Processing: {len(files_to_process)} filings (index {start_index} to {start_index + limit - 1})")
    else:
        files_to_process = all_files[start_index:]
        print(f"  Processing: {len(files_to_process)} filings (from index {start_index})")

    if not files_to_process:
        print("\n  ERROR: No filings to process!")
        return

    # Prepare inputs
    print(f"\n[4/6] Preparing inputs...")
    inputs: List[Dict[str, Any]] = []
    for idx, file_info in enumerate(files_to_process, start_index):
        inputs.append({
            "index": idx,
            "file_info": file_info
        })
    print(f"  Prepared {len(inputs)} filing inputs")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(f"{output_dir}/batch_processing", exist_ok=True)

    # Create checkpoint directory
    checkpoint_dir = os.path.join(output_dir, "batch_processing", "checkpoints")
    os.makedirs(checkpoint_dir, exist_ok=True)

    # Initialize checkpoint manager
    checkpoint_file = os.path.join(output_dir, "batch_processing", ".checkpoint_sec_batch.json")
    checkpoint_mgr = ScholarlyCheckpointManager(checkpoint_file)

    print(f"\n[CHECKPOINT] Checkpoint system active")
    print(f"  Checkpoint interval: Every {checkpoint_interval} filings")
    print(f"  Checkpoint directory: {checkpoint_dir}")

    # Filter already-completed filings if resume is enabled
    if resume and checkpoint_mgr.get_completed_count() > 0:
        print(f"  Resume mode: Skipping {checkpoint_mgr.get_completed_count()} already-processed filings")
        completed_indices = checkpoint_mgr.get_completed_indices()
        inputs = [item for item in inputs if item["index"] not in completed_indices]
        print(f"  Remaining to process: {len(inputs)} filings")

    if not inputs:
        print("\n  All filings already processed! Merging existing checkpoints...")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        range_str = f"{start_index}_{start_index + len(files_to_process) - 1}" if limit else "all"
        OUT_ALL = os.path.join(output_dir, "batch_processing", f"all_sec_scored_{range_str}_{timestamp}.json")
        OUT_RELEVANT = os.path.join(output_dir, f"relevant_{industry.lower()}_sec_filings.json")
        merge_checkpoints(checkpoint_dir, OUT_ALL, OUT_RELEVANT)
        print(f"\n  Checkpoint merge complete!")
        return

    # Output files
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    range_str = f"{start_index}_{start_index + len(files_to_process) - 1}" if limit else "all"

    OUT_ALL = os.path.join(output_dir, "batch_processing", f"all_sec_scored_{range_str}_{timestamp}.json")
    OUT_RELEVANT = os.path.join(output_dir, f"relevant_{industry.lower()}_sec_filings.json")
    OUT_ERR = os.path.join(output_dir, "batch_processing", f"processing_errors_{range_str}_{timestamp}.json")

    print(f"\n  Output files:")
    print(f"    All scores: {OUT_ALL}")
    print(f"    Relevant: {OUT_RELEVANT}")
    print(f"    Errors: {OUT_ERR}")

    # Process in concurrent sub-batches
    print(f"\n[5/6] Processing filings in concurrent sub-batches...")
    print("-" * 80)

    results: List[Optional[Dict[str, Any]]] = [None] * len(inputs)
    error_filings: List[Dict[str, Any]] = []

    t0_global = time.perf_counter()
    total_items = len(inputs)

    # Track checkpoint batch
    checkpoint_batch_results = []
    checkpoint_batch_indices = []

    with tqdm(total=total_items, desc="Parsing filings", unit="filing") as pbar:
        base = 0
        for sub in chunked(inputs, subbatch_size):
            # Execute this sub-batch concurrently
            futures = {}
            t_subbatch = time.perf_counter()

            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                for j, item in enumerate(sub):
                    idx_global = base + j
                    futures[ex.submit(safe_parse, parser, item["file_info"], 0, max_retries)] = (idx_global, item)

                for future in as_completed(futures):
                    idx_global, item = futures[future]
                    try:
                        ok, data = future.result()
                        if ok:
                            results[idx_global] = data
                            checkpoint_batch_results.append(data)
                            checkpoint_batch_indices.append(item["index"])

                            # Save checkpoint immediately when interval is reached
                            if len(checkpoint_batch_results) >= checkpoint_interval:
                                checkpoint_start_idx = min(checkpoint_batch_indices)
                                checkpoint_end_idx = max(checkpoint_batch_indices)

                                # Save checkpoint files
                                save_checkpoint_files(
                                    results=checkpoint_batch_results,
                                    start_idx=checkpoint_start_idx,
                                    end_idx=checkpoint_end_idx,
                                    checkpoint_dir=checkpoint_dir,
                                    industry=industry,
                                    quality_threshold=quality_threshold
                                )

                                # Mark filings as completed
                                checkpoint_mgr.mark_batch_completed(checkpoint_batch_indices)

                                # Reset checkpoint batch
                                checkpoint_batch_results = []
                                checkpoint_batch_indices = []
                        else:
                            error_filings.append(data)
                    except Exception as e:
                        # Unexpected error getting future result
                        error_filings.append({
                            "file_path": item["file_info"].get("file_path", "unknown"),
                            "ticker": item["file_info"].get("ticker", "unknown"),
                            "filing_type": item["file_info"].get("filing_type", "unknown"),
                            "error": f"FUTURE_FAILURE: {type(e).__name__}: {str(e)}",
                            "traceback": traceback.format_exc()
                        })
                    finally:
                        pbar.update(1)

            # Calculate ETA
            iter_sec = time.perf_counter() - t_subbatch
            done = min(base + len(sub), total_items)
            elapsed = time.perf_counter() - t0_global
            avg = elapsed / max(1, done)
            remaining_sec = avg * (total_items - done)
            eta = datetime.timedelta(seconds=max(0, int(remaining_sec)))

            pbar.set_postfix(batch_s=f"{iter_sec:.1f}", avg_s=f"{avg:.2f}", eta=str(eta))

            base += len(sub)

            # Save any remaining filings in checkpoint batch at end of processing
            if done == total_items and checkpoint_batch_results and checkpoint_batch_indices:
                checkpoint_start_idx = min(checkpoint_batch_indices)
                checkpoint_end_idx = max(checkpoint_batch_indices)

                # Save final checkpoint files
                save_checkpoint_files(
                    results=checkpoint_batch_results,
                    start_idx=checkpoint_start_idx,
                    end_idx=checkpoint_end_idx,
                    checkpoint_dir=checkpoint_dir,
                    industry=industry,
                    quality_threshold=quality_threshold
                )

                # Mark filings as completed
                checkpoint_mgr.mark_batch_completed(checkpoint_batch_indices)

                # Reset checkpoint batch
                checkpoint_batch_results = []
                checkpoint_batch_indices = []

    elapsed_total = time.perf_counter() - t0_global
    print("\n" + "-" * 80)
    print(f"Processing complete in {datetime.timedelta(seconds=int(elapsed_total))}")

    # Merge checkpoints and save final results
    print(f"\n[6/6] Merging checkpoints and saving final results...")

    # Merge all checkpoint files
    merge_stats = merge_checkpoints(checkpoint_dir, OUT_ALL, OUT_RELEVANT)

    # Load merged results for statistics
    with open(OUT_ALL, "r", encoding="utf-8") as f:
        ok_results = json.load(f)

    with open(OUT_RELEVANT, "r", encoding="utf-8") as f:
        relevant_filings = json.load(f)

    # Calculate statistics
    total_processed = len(ok_results)
    total_relevant = len(relevant_filings)
    total_errors = len(error_filings)

    print(f"\n  Total processed: {total_processed}")
    print(f"  Relevant filings (>= {quality_threshold}): {total_relevant} ({total_relevant / max(1, total_processed) * 100:.1f}%)")
    print(f"  Errors: {total_errors}")

    print(f"\n  ✓ Merged and saved all scored filings: {OUT_ALL}")
    print(f"  ✓ Merged and saved relevant filings: {OUT_RELEVANT}")

    # Save errors
    if error_filings:
        with open(OUT_ERR, "w", encoding="utf-8") as f:
            json.dump(error_filings, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Saved error log: {OUT_ERR}")

    # Summary statistics
    if relevant_filings:
        avg_quality = sum(
            r.get("document", {}).get("quality_score", 0)
            for r in relevant_filings
        ) / len(relevant_filings)

        filing_type_counts = {}
        for r in relevant_filings:
            ft = r.get("document", {}).get("filing_type", "unknown")
            filing_type_counts[ft] = filing_type_counts.get(ft, 0) + 1

        print(f"\n  Relevant Filings Statistics:")
        print(f"    Average quality score: {avg_quality:.2f}")
        print(f"    Filing type breakdown:")
        for ft, count in sorted(filing_type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"      - {ft}: {count} filings ({count / total_relevant * 100:.1f}%)")

    # Cost estimate
    # Rough estimate: SEC filings are much larger than papers
    # ~15,000 tokens per filing average (chunking + summarization + extraction)
    estimated_tokens = total_processed * 15000
    estimated_cost = (estimated_tokens / 1_000_000) * 0.30
    print(f"\n  Estimated cost: ${estimated_cost:.2f} USD")

    print("\n" + "=" * 80)
    print("BATCH PROCESSING COMPLETE")
    print("=" * 80 + "\n")

    return {
        "total_processed": total_processed,
        "total_relevant": total_relevant,
        "total_errors": total_errors,
        "output_files": {
            "all_scored": OUT_ALL,
            "relevant": OUT_RELEVANT,
            "errors": OUT_ERR
        }
    }


def main():
    """Command-line interface for batch processing."""

    parser = argparse.ArgumentParser(
        description="Batch process SEC filings for knowledge graph extraction"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="configs/evtol_config.json",
        help="Path to industry config JSON (default: configs/evtol_config.json)"
    )

    parser.add_argument(
        "--input",
        type=str,
        default="data/eVTOL/sec_filings/txt",
        help="Input directory with filing type subdirectories (default: data/eVTOL/sec_filings/txt)"
    )

    parser.add_argument(
        "--metadata",
        type=str,
        default="data/eVTOL/sec_filings/metadata.json",
        help="Path to metadata.json (default: data/eVTOL/sec_filings/metadata.json)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="data/eVTOL/sec_filings",
        help="Output directory (default: data/eVTOL/sec_filings)"
    )

    parser.add_argument(
        "--filing-types",
        type=str,
        default="10-K,10-Q,8-K,S-1",
        help="Comma-separated filing types (default: 10-K,10-Q,8-K,S-1)"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of filings to process (default: None = all)"
    )

    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Starting index (default: 0)"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=3,
        help="Number of concurrent workers (default: 3)"
    )

    parser.add_argument(
        "--subbatch",
        type=int,
        default=6,
        help="Filings per sub-batch (default: 6)"
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Quality threshold (default: 0.85)"
    )

    parser.add_argument(
        "--checkpoint",
        type=int,
        default=50,
        help="Save checkpoint every N filings (default: 50)"
    )

    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable resume from existing checkpoints (default: resume enabled)"
    )

    args = parser.parse_args()

    # Parse filing types
    filing_types = [ft.strip() for ft in args.filing_types.split(',')]

    # Run batch processing
    batch_process_sec_filings(
        config_path=args.config,
        input_dir=args.input,
        metadata_file=args.metadata,
        output_dir=args.output,
        filing_types=filing_types,
        limit=args.limit,
        start_index=args.start,
        max_workers=args.workers,
        subbatch_size=args.subbatch,
        quality_threshold=args.threshold,
        checkpoint_interval=args.checkpoint,
        resume=not args.no_resume
    )


if __name__ == "__main__":
    main()
