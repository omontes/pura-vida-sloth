"""
Checkpoint Manager for Scholarly Parser Batch Processing

Tracks processing progress and enables resume capability after crashes.
Saves checkpoint state every N papers to prevent data loss.
"""

import json
import os
from typing import Set, Optional
from pathlib import Path


class ScholarlyCheckpointManager:
    """
    Manages checkpoint state for batch processing of scholarly papers.

    Tracks which papers have been successfully processed to enable:
    - Resume after crashes
    - Skipping already-processed papers
    - Progress persistence across sessions
    """

    def __init__(self, checkpoint_file: str = ".checkpoint_scholarly_batch.json"):
        """
        Initialize checkpoint manager.

        Args:
            checkpoint_file: Path to checkpoint state file
        """
        self.checkpoint_file = checkpoint_file
        self.completed_indices: Set[int] = set()
        self.load()

    def load(self) -> None:
        """Load checkpoint state from disk if exists."""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.completed_indices = set(data.get("completed_indices", []))
                print(f"  Loaded checkpoint: {len(self.completed_indices)} papers already processed")
            except Exception as e:
                print(f"  Warning: Could not load checkpoint file: {e}")
                self.completed_indices = set()
        else:
            self.completed_indices = set()

    def save(self) -> None:
        """Save checkpoint state to disk."""
        try:
            data = {
                "completed_indices": sorted(list(self.completed_indices))
            }
            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"  Warning: Could not save checkpoint file: {e}")

    def is_completed(self, index: int) -> bool:
        """Check if paper at index has been processed."""
        return index in self.completed_indices

    def mark_completed(self, index: int) -> None:
        """Mark paper at index as completed."""
        self.completed_indices.add(index)

    def mark_batch_completed(self, indices: list) -> None:
        """Mark multiple papers as completed."""
        self.completed_indices.update(indices)
        self.save()

    def get_completed_indices(self) -> Set[int]:
        """Get set of all completed paper indices."""
        return self.completed_indices.copy()

    def get_completed_count(self) -> int:
        """Get count of completed papers."""
        return len(self.completed_indices)

    def clear(self) -> None:
        """Clear checkpoint state (reset)."""
        self.completed_indices = set()
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
        print(f"  Checkpoint cleared")

    def __repr__(self) -> str:
        return f"<ScholarlyCheckpointManager: {len(self.completed_indices)} completed>"


def save_checkpoint_files(
    results: list,
    start_idx: int,
    end_idx: int,
    checkpoint_dir: str,
    industry: str,
    relevance_threshold: float = 8.0
) -> tuple:
    """
    Save checkpoint files for a batch of results.

    Args:
        results: List of parsed paper results
        start_idx: Starting index of this batch
        end_idx: Ending index of this batch
        checkpoint_dir: Directory to save checkpoint files
        industry: Industry name (for filenames)
        relevance_threshold: Threshold for relevance filtering

    Returns:
        Tuple of (checkpoint_all_path, checkpoint_relevant_path)
    """
    os.makedirs(checkpoint_dir, exist_ok=True)

    # Format indices with leading zeros for sorting
    start_str = f"{start_idx:04d}"
    end_str = f"{end_idx:04d}"

    # Save all results
    checkpoint_all = os.path.join(checkpoint_dir, f"checkpoint_{start_str}-{end_str}.json")
    with open(checkpoint_all, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Save relevant results only
    relevant_results = [
        r for r in results
        if r.get("relevance_assessment", {}).get("is_relevant", False)
    ]

    checkpoint_relevant = os.path.join(checkpoint_dir, f"checkpoint_relevant_{start_str}-{end_str}.json")
    with open(checkpoint_relevant, "w", encoding="utf-8") as f:
        json.dump(relevant_results, f, indent=2, ensure_ascii=False)

    return checkpoint_all, checkpoint_relevant


def load_existing_checkpoints(checkpoint_dir: str) -> dict:
    """
    Load all existing checkpoint files from directory.

    Args:
        checkpoint_dir: Directory containing checkpoint files

    Returns:
        Dictionary with keys 'all_results' and 'relevant_results'
    """
    if not os.path.exists(checkpoint_dir):
        return {"all_results": [], "relevant_results": []}

    # Find all checkpoint files
    checkpoint_files = sorted([
        f for f in os.listdir(checkpoint_dir)
        if f.startswith("checkpoint_") and f.endswith(".json") and "relevant" not in f
    ])

    relevant_checkpoint_files = sorted([
        f for f in os.listdir(checkpoint_dir)
        if f.startswith("checkpoint_relevant_") and f.endswith(".json")
    ])

    # Load all results
    all_results = []
    for filename in checkpoint_files:
        filepath = os.path.join(checkpoint_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                batch = json.load(f)
                all_results.extend(batch)
        except Exception as e:
            print(f"  Warning: Could not load checkpoint {filename}: {e}")

    # Load relevant results
    relevant_results = []
    for filename in relevant_checkpoint_files:
        filepath = os.path.join(checkpoint_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                batch = json.load(f)
                relevant_results.extend(batch)
        except Exception as e:
            print(f"  Warning: Could not load checkpoint {filename}: {e}")

    return {
        "all_results": all_results,
        "relevant_results": relevant_results
    }


def merge_checkpoints(checkpoint_dir: str, output_all: str, output_relevant: str) -> dict:
    """
    Merge all checkpoint files into final output files.

    Args:
        checkpoint_dir: Directory containing checkpoint files
        output_all: Path for merged all results file
        output_relevant: Path for merged relevant results file

    Returns:
        Dictionary with statistics
    """
    print(f"\n  Merging checkpoint files...")

    data = load_existing_checkpoints(checkpoint_dir)
    all_results = data["all_results"]
    relevant_results = data["relevant_results"]

    # Deduplicate by lens_id (in case of overlapping checkpoints)
    seen_all = set()
    deduped_all = []
    for result in all_results:
        lens_id = result.get("paper_metadata", {}).get("lens_id", "")
        if lens_id and lens_id not in seen_all:
            seen_all.add(lens_id)
            deduped_all.append(result)

    seen_relevant = set()
    deduped_relevant = []
    for result in relevant_results:
        lens_id = result.get("paper_metadata", {}).get("lens_id", "")
        if lens_id and lens_id not in seen_relevant:
            seen_relevant.add(lens_id)
            deduped_relevant.append(result)

    # Save merged files
    with open(output_all, "w", encoding="utf-8") as f:
        json.dump(deduped_all, f, indent=2, ensure_ascii=False)

    with open(output_relevant, "w", encoding="utf-8") as f:
        json.dump(deduped_relevant, f, indent=2, ensure_ascii=False)

    print(f"    All results: {len(deduped_all)} papers")
    print(f"    Relevant results: {len(deduped_relevant)} papers")
    print(f"    Duplicates removed: {len(all_results) - len(deduped_all)}")

    return {
        "total_all": len(deduped_all),
        "total_relevant": len(deduped_relevant),
        "duplicates_removed": len(all_results) - len(deduped_all)
    }
