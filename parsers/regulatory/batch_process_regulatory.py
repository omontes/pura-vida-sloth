"""
Batch Processor for Regulatory Documents
Author: Pura Vida Sloth Intelligence System

Processes Federal Register regulatory documents with:
- Checkpoint/resume capability
- Concurrent processing with ThreadPoolExecutor
- Quality threshold filtering (0.85+)
- Progress tracking and error handling
"""

import os
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Load environment
load_dotenv()

from parsers.regulatory.regulatory_parser import RegulatoryDocumentParser, load_industry_config
from parsers.scholarly.checkpoint_manager import ScholarlyCheckpointManager


def discover_markdown_files(markdown_dir: str) -> List[str]:
    """
    Discover all markdown files in the directory.

    Args:
        markdown_dir: Directory containing .md files

    Returns:
        List of absolute file paths
    """
    md_path = Path(markdown_dir)
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown directory not found: {markdown_dir}")

    md_files = list(md_path.glob("*.md"))
    md_files.sort()  # Sort for deterministic processing

    return [str(f) for f in md_files]


def prepare_inputs(
    md_files: List[str],
    start_index: int = 0,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Prepare input list for batch processing.

    Args:
        md_files: List of markdown file paths
        start_index: Starting index for processing
        limit: Maximum number to process (None = all)

    Returns:
        List of input dicts with index, file_path
    """
    inputs = []

    end_index = min(len(md_files), start_index + limit) if limit else len(md_files)

    for idx in range(start_index, end_index):
        inputs.append({
            "index": idx,
            "file_path": md_files[idx]
        })

    return inputs


def process_single_document(
    parser: RegulatoryDocumentParser,
    file_path: str,
    index: int
) -> Dict[str, Any]:
    """
    Process a single regulatory document.

    Args:
        parser: RegulatoryDocumentParser instance
        file_path: Path to markdown file
        index: Document index

    Returns:
        Parsed result dict
    """
    filename = os.path.basename(file_path)

    try:
        print(f"\n[{index}] Processing: {filename}")

        result = parser.parse_document(file_path)

        quality_score = result.get("document", {}).get("quality_score", 0.0)
        print(f"  [OK] Quality Score: {quality_score:.2f}")

        return result

    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        raise


def process_batch_concurrent(
    parser: RegulatoryDocumentParser,
    inputs: List[Dict[str, Any]],
    max_workers: int = 3
) -> List[Dict[str, Any]]:
    """
    Process documents concurrently with ThreadPoolExecutor.

    Args:
        parser: RegulatoryDocumentParser instance
        inputs: List of input dicts
        max_workers: Number of concurrent workers

    Returns:
        List of parsed results (in original order)
    """
    # Use dict to store results by index (fixes race condition)
    results_dict = {}
    errors = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_input = {
            executor.submit(
                process_single_document,
                parser,
                inp["file_path"],
                inp["index"]
            ): inp for inp in inputs
        }

        # Collect results
        for future in as_completed(future_to_input):
            inp = future_to_input[future]
            idx = inp["index"]

            try:
                result = future.result()
                results_dict[idx] = result
            except Exception as e:
                error_record = {
                    "index": idx,
                    "file_path": inp["file_path"],
                    "error": str(e)
                }
                errors.append(error_record)
                print(f"  [ERROR] Document {idx}: {e}")

    # Convert dict to sorted list (preserve original order)
    results = [results_dict[inp["index"]] for inp in inputs if inp["index"] in results_dict]

    return results, errors


def save_checkpoint(
    results: List[Dict[str, Any]],
    checkpoint_dir: str,
    start_idx: int,
    end_idx: int,
    quality_threshold: float = 0.85
):
    """
    Save checkpoint files (all results + relevant only).

    Args:
        results: List of parsed documents
        checkpoint_dir: Directory to save checkpoints
        start_idx: Starting index
        end_idx: Ending index
        quality_threshold: Minimum quality score for relevance
    """
    os.makedirs(checkpoint_dir, exist_ok=True)

    # Save all results
    all_checkpoint_path = os.path.join(
        checkpoint_dir,
        f"checkpoint_{start_idx:04d}-{end_idx:04d}.json"
    )
    with open(all_checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n[CHECKPOINT] Saved all results: {all_checkpoint_path}")

    # Save relevant only (quality >= threshold)
    relevant = [r for r in results if r.get("document", {}).get("quality_score", 0) >= quality_threshold]

    if relevant:
        relevant_checkpoint_path = os.path.join(
            checkpoint_dir,
            f"checkpoint_relevant_{start_idx:04d}-{end_idx:04d}.json"
        )
        with open(relevant_checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(relevant, f, indent=2, ensure_ascii=False)

        print(f"[CHECKPOINT] Saved relevant results ({len(relevant)}): {relevant_checkpoint_path}")


def merge_checkpoints(
    checkpoint_dir: str,
    output_dir: str,
    start_idx: int,
    end_idx: int,
    quality_threshold: float = 0.85
):
    """
    Merge all checkpoint files into final outputs.

    Args:
        checkpoint_dir: Directory containing checkpoint files
        output_dir: Output directory for merged files
        start_idx: Starting index
        end_idx: Ending index
        quality_threshold: Quality threshold for relevance filtering
    """
    checkpoint_path = Path(checkpoint_dir)

    # Collect all checkpoint files
    all_checkpoints = sorted(checkpoint_path.glob("checkpoint_[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9].json"))

    if not all_checkpoints:
        print("\n[WARNING] No checkpoint files found to merge")
        return

    print(f"\n[6/6] Merging {len(all_checkpoints)} checkpoint files...")

    # Merge all results
    all_results = []
    for cp_file in all_checkpoints:
        with open(cp_file, "r", encoding="utf-8") as f:
            results = json.load(f)
            all_results.extend(results)

    # Deduplicate by doc_id
    seen_ids = set()
    deduplicated = []
    for result in all_results:
        doc_id = result.get("document", {}).get("doc_id")
        if doc_id and doc_id not in seen_ids:
            deduplicated.append(result)
            seen_ids.add(doc_id)

    print(f"  Total documents: {len(deduplicated)} (after deduplication)")

    # Save merged all results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    range_str = f"{start_idx}_{end_idx}" if end_idx < 999999 else "all"

    all_output_path = os.path.join(
        output_dir,
        f"all_regulatory_scored_{range_str}_{timestamp}.json"
    )
    with open(all_output_path, "w", encoding="utf-8") as f:
        json.dump(deduplicated, f, indent=2, ensure_ascii=False)

    print(f"  Saved all results: {all_output_path}")

    # Filter and save relevant results
    relevant = [r for r in deduplicated if r.get("document", {}).get("quality_score", 0) >= quality_threshold]

    print(f"  Relevant documents (quality >= {quality_threshold}): {len(relevant)}")

    relevant_output_path = os.path.join(
        os.path.dirname(output_dir),
        "relevant_evtol_regulatory_docs.json"
    )
    with open(relevant_output_path, "w", encoding="utf-8") as f:
        json.dump(relevant, f, indent=2, ensure_ascii=False)

    print(f"  Saved relevant results: {relevant_output_path}")

    # Print quality distribution
    quality_scores = [r.get("document", {}).get("quality_score", 0) for r in deduplicated]
    if quality_scores:
        avg_quality = sum(quality_scores) / len(quality_scores)
        print(f"\n  Quality Statistics:")
        print(f"    Average: {avg_quality:.2f}")
        print(f"    Min: {min(quality_scores):.2f}")
        print(f"    Max: {max(quality_scores):.2f}")


def main():
    parser_args = argparse.ArgumentParser(description="Batch process regulatory documents")

    parser_args.add_argument("--config", default="configs/evtol_config.json", help="Industry config file")
    parser_args.add_argument("--input", default="data/eVTOL/regulatory_docs/ade_parsed_results/markdown", help="Input markdown directory")
    parser_args.add_argument("--output", default="data/eVTOL/regulatory_docs", help="Output directory")
    parser_args.add_argument("--start", type=int, default=0, help="Starting index")
    parser_args.add_argument("--limit", type=int, default=None, help="Max documents to process (None = all)")
    parser_args.add_argument("--workers", type=int, default=3, help="Number of concurrent workers")
    parser_args.add_argument("--threshold", type=float, default=0.85, help="Quality threshold for relevance filtering")
    parser_args.add_argument("--checkpoint", type=int, default=10, help="Save checkpoint every N documents")
    parser_args.add_argument("--no-resume", action="store_true", help="Disable resume from checkpoint")

    args = parser_args.parse_args()

    print("="*80)
    print("REGULATORY DOCUMENTS BATCH PROCESSING")
    print("="*80)

    # [1/6] Load industry config
    print(f"\n[1/6] Loading industry config: {args.config}")
    config = load_industry_config(args.config)
    print(f"  Industry: {config.get('industry')}")
    print(f"  Keywords: {len(config.get('keywords', {}).get('core', []))} core keywords")

    # [2/6] Initialize parser
    print(f"\n[2/6] Initializing RegulatoryDocumentParser")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    parser = RegulatoryDocumentParser(
        openai_api_key=api_key,
        config_path="configs/eVTOL_graph_relations.json",
        industry_name=config.get("industry"),
        model_name="gpt-4o-mini",
        temperature=0.0
    )
    print(f"  Model: gpt-4o-mini")
    print(f"  Quality Threshold: {args.threshold}")
    print(f"  Max Workers: {args.workers}")

    # [3/6] Discover markdown files
    print(f"\n[3/6] Discovering regulatory documents: {args.input}")
    md_files = discover_markdown_files(args.input)
    print(f"  Total markdown files found: {len(md_files)}")

    # [4/6] Prepare inputs
    print(f"\n[4/6] Preparing inputs...")
    inputs = prepare_inputs(md_files, start_index=args.start, limit=args.limit)
    print(f"  Prepared {len(inputs)} document inputs")

    # Setup checkpoint manager
    checkpoint_dir = os.path.join(args.output, "batch_processing", "checkpoints")
    checkpoint_file = os.path.join(checkpoint_dir, ".checkpoint_regulatory_batch.json")

    checkpoint_mgr = ScholarlyCheckpointManager(checkpoint_file)

    resume = not args.no_resume
    if resume and checkpoint_mgr.get_completed_count() > 0:
        print(f"  Resume mode: Skipping {checkpoint_mgr.get_completed_count()} already-processed documents")
        completed_indices = checkpoint_mgr.get_completed_indices()
        inputs = [item for item in inputs if item["index"] not in completed_indices]

    print(f"  Remaining to process: {len(inputs)} documents")

    print(f"\n[CHECKPOINT] Checkpoint system active")
    print(f"  Checkpoint interval: Every {args.checkpoint} documents")
    print(f"  Checkpoint directory: {checkpoint_dir}")

    # Determine output range
    if inputs:
        start_idx = inputs[0]["index"]
        end_idx = inputs[-1]["index"]
    else:
        print("\n[DONE] All documents already processed!")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    range_str = f"{start_idx}_{end_idx}" if args.limit else "all"

    print(f"\n  Output files:")
    print(f"    All scores: {args.output}/batch_processing/all_regulatory_scored_{range_str}_{timestamp}.json")
    print(f"    Relevant: {args.output}/relevant_evtol_regulatory_docs.json")
    print(f"    Errors: {args.output}/batch_processing/processing_errors_{range_str}_{timestamp}.json")

    # [5/6] Process documents in batches
    print(f"\n[5/6] Processing documents...")
    print("-"*80)

    all_results = []
    all_errors = []

    for batch_start in range(0, len(inputs), args.checkpoint):
        batch_end = min(batch_start + args.checkpoint, len(inputs))
        batch_inputs = inputs[batch_start:batch_end]

        print(f"\n[BATCH] Processing documents {batch_start}-{batch_end-1}")

        batch_results, batch_errors = process_batch_concurrent(
            parser,
            batch_inputs,
            max_workers=args.workers
        )

        all_results.extend(batch_results)
        all_errors.extend(batch_errors)

        # Update checkpoint manager
        for inp in batch_inputs:
            checkpoint_mgr.mark_completed(inp["index"])
        checkpoint_mgr.save()

        # Save checkpoint files
        if batch_results:
            batch_start_idx = batch_inputs[0]["index"]
            batch_end_idx = batch_inputs[-1]["index"]

            save_checkpoint(
                batch_results,
                checkpoint_dir,
                batch_start_idx,
                batch_end_idx,
                args.threshold
            )

    print(f"\n{'='*80}")
    print(f"PROCESSING COMPLETE")
    print(f"{'='*80}")
    print(f"  Successfully processed: {len(all_results)}/{len(inputs)}")
    print(f"  Errors: {len(all_errors)}/{len(inputs)}")

    # Save errors
    if all_errors:
        errors_path = os.path.join(
            args.output,
            "batch_processing",
            f"processing_errors_{range_str}_{timestamp}.json"
        )
        with open(errors_path, "w", encoding="utf-8") as f:
            json.dump(all_errors, f, indent=2, ensure_ascii=False)
        print(f"  Errors saved: {errors_path}")

    # [6/6] Merge checkpoints
    merge_checkpoints(
        checkpoint_dir,
        os.path.join(args.output, "batch_processing"),
        start_idx,
        end_idx,
        args.threshold
    )

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()
