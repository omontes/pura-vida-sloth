"""
Merge scholarly papers checkpoint files into final output files.

Creates two output files in the same folder:
1. all_papers_500.json - All processed papers
2. relevant_papers_quality_0.85.json - Papers with quality_score >= 0.85
"""

import json
import os
from pathlib import Path


def load_checkpoint_files(checkpoint_dir: str) -> dict:
    """Load all checkpoint files from directory."""
    if not os.path.exists(checkpoint_dir):
        print(f"ERROR: Checkpoint directory not found: {checkpoint_dir}")
        return {"all_results": [], "relevant_results": []}

    # Find all checkpoint files (exclude relevant checkpoints for now)
    checkpoint_files = sorted([
        f for f in os.listdir(checkpoint_dir)
        if f.startswith("checkpoint_") and f.endswith(".json") and "relevant" not in f
    ])

    print(f"Found {len(checkpoint_files)} checkpoint files")

    # Load all results
    all_results = []
    for filename in checkpoint_files:
        filepath = os.path.join(checkpoint_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                batch = json.load(f)
                all_results.extend(batch)
                print(f"  Loaded {len(batch)} papers from {filename}")
        except Exception as e:
            print(f"  Warning: Could not load {filename}: {e}")

    return all_results


def deduplicate_by_doc_id(results: list) -> list:
    """Deduplicate results by doc_id."""
    seen = set()
    deduped = []

    for result in results:
        doc_id = result.get("document", {}).get("doc_id", "")
        if doc_id and doc_id not in seen:
            seen.add(doc_id)
            deduped.append(result)

    return deduped


def filter_by_quality(results: list, threshold: float = 0.85) -> list:
    """Filter results by quality score."""
    return [
        r for r in results
        if r.get("document", {}).get("quality_score", 0.0) >= threshold
    ]


def analyze_quality_distribution(results: list) -> dict:
    """Analyze quality score distribution."""
    scores = [r.get("document", {}).get("quality_score", 0.0) for r in results]

    return {
        "total": len(scores),
        "min": min(scores) if scores else 0,
        "max": max(scores) if scores else 0,
        "avg": sum(scores) / len(scores) if scores else 0,
        "quality_count": len([s for s in scores if s >= 0.85]),
        "quality_percent": (len([s for s in scores if s >= 0.85]) / len(scores) * 100) if scores else 0
    }


def main():
    print("=" * 80)
    print("MERGING SCHOLARLY PAPERS CHECKPOINT FILES")
    print("=" * 80 + "\n")

    # Paths
    checkpoint_dir = "data/eVTOL/lens_scholarly/batch_processing/checkpoints"
    output_dir = "data/eVTOL/lens_scholarly/batch_processing"

    output_all = os.path.join(output_dir, "all_papers_500.json")
    output_relevant = os.path.join(output_dir, "relevant_papers_quality_0.85.json")

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Load checkpoint files
    print("[1/5] Loading checkpoint files...")
    all_results = load_checkpoint_files(checkpoint_dir)
    print(f"  Total papers loaded: {len(all_results)}")

    # Deduplicate
    print("\n[2/5] Deduplicating by doc_id...")
    deduped_all = deduplicate_by_doc_id(all_results)
    duplicates_removed = len(all_results) - len(deduped_all)
    print(f"  Unique papers: {len(deduped_all)}")
    print(f"  Duplicates removed: {duplicates_removed}")

    # Filter by quality
    print("\n[3/5] Filtering by quality score >= 0.85...")
    relevant_papers = filter_by_quality(deduped_all, threshold=0.85)
    print(f"  Relevant papers: {len(relevant_papers)}")
    print(f"  Filtered out: {len(deduped_all) - len(relevant_papers)}")

    # Analyze quality distribution
    print("\n[4/5] Analyzing quality score distribution...")
    stats = analyze_quality_distribution(deduped_all)
    print(f"  Total papers: {stats['total']}")
    print(f"  Quality score range: {stats['min']:.2f} - {stats['max']:.2f}")
    print(f"  Average quality score: {stats['avg']:.2f}")
    print(f"  Papers >= 0.85: {stats['quality_count']} ({stats['quality_percent']:.1f}%)")

    # Save files
    print("\n[5/5] Saving output files...")

    # Save all papers
    with open(output_all, "w", encoding="utf-8") as f:
        json.dump(deduped_all, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Saved all papers: {output_all}")

    # Save relevant papers
    with open(output_relevant, "w", encoding="utf-8") as f:
        json.dump(relevant_papers, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Saved relevant papers: {output_relevant}")

    # Final summary
    print("\n" + "=" * 80)
    print("MERGE COMPLETE")
    print("=" * 80)
    print(f"\nOutput files created in: {output_dir}")
    print(f"  1. all_papers_500.json ({len(deduped_all)} papers)")
    print(f"  2. relevant_papers_quality_0.85.json ({len(relevant_papers)} papers)")
    print()


if __name__ == "__main__":
    main()
