"""
Batch Processing Script: Parse All Patents with Concurrent Execution

This script:
1. Loads patents from dataset
2. Processes patents concurrently using ThreadPoolExecutor
3. Assigns quality scores + extracts knowledge graphs for relevant patents
4. Saves results:
   - quality_patents.json: Only patents with score >= 0.85
   - all_patents_scored.json: Complete dataset with scores (audit trail)
   - processing_errors.json: Patents that failed to parse

Usage:
    # Test with first 10 patents
    python batch_process_patents.py --limit 10

    # Process all patents
    python batch_process_patents.py

    # Custom config and output
    python batch_process_patents.py --config configs/evtol_config.json --output data/eVTOL/lens_patents
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

from parsers.patents.patents_parser import (
    PatentTechnologyParser,
    load_patents_from_file,
    load_industry_config
)
from parsers.patents.checkpoint_manager_patents import (
    PatentCheckpointManager,
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


def safe_parse(
    parser: PatentTechnologyParser,
    patent: Dict[str, Any],
    retries: int = 0,
    max_retries: int = 2,
    backoff_base_sec: int = 2
) -> Tuple[bool, Dict[str, Any]]:
    """
    Parse a single patent with retry logic and exponential backoff.

    Args:
        parser: Initialized PatentTechnologyParser
        patent: Patent data dictionary
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
                result = parser.parse_patent(patent)

            return True, result

        except Exception as e:
            attempt += 1
            if attempt > max_retries:
                return False, {
                    "lens_id": patent.get("lens_id", "unknown"),
                    "title": patent.get("title", "Unknown"),
                    "error": f"{type(e).__name__}: {str(e)}",
                    "traceback": traceback.format_exc()
                }
            # Exponential backoff
            sleep(backoff_base_sec ** (attempt - 1))


def batch_process_patents(
    config_path: str = "configs/evtol_config.json",
    patents_file: str = "data/eVTOL/lens_patents/patents.json",
    output_dir: str = "data/eVTOL/lens_patents",
    limit: Optional[int] = None,
    start_index: int = 0,
    max_workers: int = 4,
    subbatch_size: int = 8,
    max_retries: int = 2,
    quality_threshold: float = 0.85,
    checkpoint_interval: int = 100,
    resume: bool = True
):
    """
    Batch process patents with concurrent execution and checkpointing.

    Args:
        config_path: Path to industry config JSON
        patents_file: Path to patents dataset JSON
        output_dir: Directory to save output files
        limit: Maximum number of patents to process (None = all)
        start_index: Index to start from (default: 0)
        max_workers: Number of concurrent workers
        subbatch_size: Patents per sub-batch (wave)
        max_retries: Retry attempts per patent
        quality_threshold: Minimum score for quality (default: 0.85)
        checkpoint_interval: Save checkpoint every N patents (default: 100)
        resume: Resume from existing checkpoints if True (default: True)
    """

    print("=" * 80)
    print("PATENTS BATCH PROCESSING")
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

    print(f"  Industry: {industry}")
    print(f"  Keywords: {len(industry_keywords)} core keywords")

    # Initialize parser
    print(f"\n[2/6] Initializing PatentTechnologyParser")
    parser = PatentTechnologyParser(
        openai_api_key=api_key,
        config_path="configs/eVTOL_graph_relations.json",
        model_name="gpt-4o-mini",
        temperature=0.0
    )
    print(f"  Model: gpt-4o-mini")
    print(f"  Quality Threshold: {quality_threshold}")
    print(f"  Max Workers: {max_workers}")
    print(f"  Sub-batch Size: {subbatch_size}")

    # Load patents
    print(f"\n[3/6] Loading patents: {patents_file}")
    all_patents = load_patents_from_file(patents_file, limit=None)
    print(f"  Total patents in dataset: {len(all_patents)}")

    # Select patents to process
    if limit:
        patents_to_process = all_patents[start_index:start_index + limit]
        print(f"  Processing: {len(patents_to_process)} patents (index {start_index} to {start_index + limit - 1})")
    else:
        patents_to_process = all_patents[start_index:]
        print(f"  Processing: {len(patents_to_process)} patents (from index {start_index})")

    if not patents_to_process:
        print("\n  ERROR: No patents to process!")
        return

    # Prepare inputs
    print(f"\n[4/6] Preparing inputs...")
    inputs: List[Dict[str, Any]] = []
    for idx, patent in enumerate(patents_to_process, start_index):
        inputs.append({
            "index": idx,
            "patent": patent
        })
    print(f"  Prepared {len(inputs)} patent inputs")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(f"{output_dir}/batch_processing", exist_ok=True)

    # Create checkpoint directory
    checkpoint_dir = os.path.join(output_dir, "batch_processing", "checkpoints")
    os.makedirs(checkpoint_dir, exist_ok=True)

    # Initialize checkpoint manager
    checkpoint_file = os.path.join(output_dir, "batch_processing", ".checkpoint_patents_batch.json")
    checkpoint_mgr = PatentCheckpointManager(checkpoint_file)

    print(f"\n[CHECKPOINT] Checkpoint system active")
    print(f"  Checkpoint interval: Every {checkpoint_interval} patents")
    print(f"  Checkpoint directory: {checkpoint_dir}")

    # Filter already-completed patents if resume is enabled
    if resume and checkpoint_mgr.get_completed_count() > 0:
        print(f"  Resume mode: Skipping {checkpoint_mgr.get_completed_count()} already-processed patents")
        completed_indices = checkpoint_mgr.get_completed_indices()
        inputs = [item for item in inputs if item["index"] not in completed_indices]
        print(f"  Remaining to process: {len(inputs)} patents")

    if not inputs:
        print("\n  All patents already processed! Merging existing checkpoints...")
        # Just merge and return
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        range_str = f"{start_index}_{start_index + len(patents_to_process) - 1}" if limit else "all"
        OUT_ALL = os.path.join(output_dir, "batch_processing", f"all_patents_scored_{range_str}_{timestamp}.json")
        OUT_QUALITY = os.path.join(output_dir, f"quality_{industry.lower()}_patents.json")
        merge_checkpoints(checkpoint_dir, OUT_ALL, OUT_QUALITY)
        print(f"\n  Checkpoint merge complete!")
        return

    # Output files
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    range_str = f"{start_index}_{start_index + len(patents_to_process) - 1}" if limit else "all"

    OUT_ALL = os.path.join(output_dir, "batch_processing", f"all_patents_scored_{range_str}_{timestamp}.json")
    OUT_QUALITY = os.path.join(output_dir, f"quality_{industry.lower()}_patents.json")
    OUT_ERR = os.path.join(output_dir, "batch_processing", f"processing_errors_{range_str}_{timestamp}.json")

    print(f"\n  Output files:")
    print(f"    All scores: {OUT_ALL}")
    print(f"    Quality: {OUT_QUALITY}")
    print(f"    Errors: {OUT_ERR}")

    # Process in concurrent sub-batches
    print(f"\n[5/6] Processing patents in concurrent sub-batches...")
    print("-" * 80)

    results: List[Optional[Dict[str, Any]]] = [None] * len(inputs)
    error_patents: List[Dict[str, Any]] = []

    t0_global = time.perf_counter()
    total_items = len(inputs)

    # Track checkpoint batch
    checkpoint_batch_results = []
    checkpoint_batch_indices = []  # Track actual indices of patents in batch

    with tqdm(total=total_items, desc="Parsing patents", unit="patent") as pbar:
        base = 0
        for sub in chunked(inputs, subbatch_size):
            # Execute this sub-batch concurrently
            futures = {}
            t_subbatch = time.perf_counter()

            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                for j, item in enumerate(sub):
                    idx_global = base + j
                    futures[ex.submit(safe_parse, parser, item["patent"], 0, max_retries)] = (idx_global, item)

                for future in as_completed(futures):
                    idx_global, item = futures[future]
                    try:
                        ok, data = future.result()
                        if ok:
                            results[idx_global] = data
                            checkpoint_batch_results.append(data)
                            checkpoint_batch_indices.append(item["index"])  # Track actual index

                            # Save checkpoint immediately when interval is reached
                            if len(checkpoint_batch_results) >= checkpoint_interval:
                                # Use min and max of actual indices for filename
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

                                # Mark patents as completed (use actual indices)
                                checkpoint_mgr.mark_batch_completed(checkpoint_batch_indices)

                                # Reset checkpoint batch
                                checkpoint_batch_results = []
                                checkpoint_batch_indices = []
                        else:
                            error_patents.append(data)
                    except Exception as e:
                        # Unexpected error getting future result
                        error_patents.append({
                            "lens_id": item["patent"].get("lens_id", "unknown"),
                            "title": item["patent"].get("title", "Unknown"),
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

            # Save any remaining patents in checkpoint batch at end of processing
            if done == total_items and checkpoint_batch_results and checkpoint_batch_indices:
                # Use min and max of actual indices for filename
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

                # Mark patents as completed (use actual indices)
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
    merge_stats = merge_checkpoints(checkpoint_dir, OUT_ALL, OUT_QUALITY)

    # Load merged results for statistics
    with open(OUT_ALL, "r", encoding="utf-8") as f:
        ok_results = json.load(f)

    with open(OUT_QUALITY, "r", encoding="utf-8") as f:
        quality_patents = json.load(f)

    # Calculate statistics
    total_processed = len(ok_results)
    total_quality = len(quality_patents)
    total_errors = len(error_patents)

    print(f"\n  Total processed: {total_processed}")
    print(f"  Quality patents (>= {quality_threshold}): {total_quality} ({total_quality / max(1, total_processed) * 100:.1f}%)")
    print(f"  Errors: {total_errors}")

    print(f"\n  >> Merged and saved all scored patents: {OUT_ALL}")
    print(f"  >> Merged and saved quality patents: {OUT_QUALITY}")

    # Save errors
    if error_patents:
        with open(OUT_ERR, "w", encoding="utf-8") as f:
            json.dump(error_patents, f, indent=2, ensure_ascii=False)
        print(f"  >> Saved error log: {OUT_ERR}")

    # Summary statistics
    if quality_patents:
        avg_quality = sum(
            r.get("document", {}).get("quality_score", 0)
            for r in quality_patents
        ) / len(quality_patents)

        print(f"\n  Quality Patents Statistics:")
        print(f"    Average quality score: {avg_quality:.2f}/1.0")

    # Cost estimate
    # Rough estimate: ~4,000 tokens per patent average
    estimated_tokens = total_processed * 4000
    estimated_cost = (estimated_tokens / 1_000_000) * 0.30  # Rough average of input/output pricing
    print(f"\n  Estimated cost: ${estimated_cost:.2f} USD")

    print("\n" + "=" * 80)
    print("BATCH PROCESSING COMPLETE")
    print("=" * 80 + "\n")

    return {
        "total_processed": total_processed,
        "total_quality": total_quality,
        "total_errors": total_errors,
        "output_files": {
            "all_scored": OUT_ALL,
            "quality": OUT_QUALITY,
            "errors": OUT_ERR
        }
    }


def main():
    """Command-line interface for batch processing."""

    parser = argparse.ArgumentParser(
        description="Batch process patents for quality scoring and knowledge graph extraction"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="configs/evtol_config.json",
        help="Path to industry config JSON (default: configs/evtol_config.json)"
    )

    parser.add_argument(
        "--patents",
        type=str,
        default="data/eVTOL/lens_patents/patents.json",
        help="Path to patents dataset JSON (default: data/eVTOL/lens_patents/patents.json)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="data/eVTOL/lens_patents",
        help="Output directory (default: data/eVTOL/lens_patents)"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of patents to process (default: None = all)"
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
        default=4,
        help="Number of concurrent workers (default: 4)"
    )

    parser.add_argument(
        "--subbatch",
        type=int,
        default=8,
        help="Patents per sub-batch (default: 8)"
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
        default=100,
        help="Save checkpoint every N patents (default: 100)"
    )

    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable resume from existing checkpoints (default: resume enabled)"
    )

    args = parser.parse_args()

    # Run batch processing
    batch_process_patents(
        config_path=args.config,
        patents_file=args.patents,
        output_dir=args.output,
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
