"""
Run History Service - Manages pipeline execution history.

Provides functionality to save, list, retrieve, and delete pipeline runs.
Each run is stored in a timestamped directory with complete outputs.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class RunHistoryService:
    """Service for managing pipeline run history."""

    def __init__(self, history_dir: str = "src/agents/run_history"):
        """
        Initialize run history service.

        Args:
            history_dir: Directory to store run history
        """
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def generate_run_id(
        self,
        tech_count: int,
        community_version: str = "v1",
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Generate unique run ID.

        Format: YYYY-MM-DD_HH-MM-SS_{tech_count}tech_{version}
        Example: 2025-01-10_14-30-45_10tech_v1

        Args:
            tech_count: Number of technologies analyzed
            community_version: Community detection version
            timestamp: Optional timestamp (defaults to now)

        Returns:
            Unique run ID string
        """
        if timestamp is None:
            timestamp = datetime.now()

        date_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        return f"{date_str}_{tech_count}tech_{community_version}"

    def save_run(
        self,
        run_id: str,
        chart_data: Dict[str, Any],
        config: Dict[str, Any],
        duration_seconds: float,
        original_chart: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Save pipeline run to history.

        Creates directory structure:
        run_history/{run_id}/
            ├── hype_cycle_chart.json          (normalized chart)
            ├── hype_cycle_chart_full.json     (original chart, if provided)
            └── metadata.json                  (run metadata)

        Args:
            run_id: Unique run identifier
            chart_data: Normalized hype cycle chart data
            config: Pipeline configuration
            duration_seconds: Execution duration
            original_chart: Optional original (non-normalized) chart

        Returns:
            Path to run directory
        """
        run_dir = self.history_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Save normalized chart
        chart_file = run_dir / "hype_cycle_chart.json"
        with open(chart_file, "w") as f:
            json.dump(chart_data, f, indent=2)

        # Save original chart if provided
        if original_chart:
            original_file = run_dir / "hype_cycle_chart_full.json"
            with open(original_file, "w") as f:
                json.dump(original_chart, f, indent=2)

        # Save metadata
        metadata = {
            "run_id": run_id,
            "created_at": datetime.now().isoformat(),
            "config": config,
            "duration_seconds": duration_seconds,
            "tech_count": len(chart_data.get("technologies", [])),
            "phases": list(chart_data.get("metadata", {}).get("phases", {}).keys())
        }

        metadata_file = run_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        return run_dir

    def list_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        List all pipeline runs (newest first).

        Args:
            limit: Maximum number of runs to return

        Returns:
            List of run metadata dictionaries
        """
        runs = []

        # Find all run directories
        if not self.history_dir.exists():
            return []

        for run_dir in self.history_dir.iterdir():
            if not run_dir.is_dir():
                continue

            metadata_file = run_dir / "metadata.json"
            if not metadata_file.exists():
                continue

            try:
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                runs.append(metadata)
            except Exception as e:
                print(f"[WARNING] Failed to load metadata for {run_dir.name}: {e}")
                continue

        # Sort by created_at (newest first)
        runs.sort(key=lambda r: r.get("created_at", ""), reverse=True)

        return runs[:limit]

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete data for a specific run.

        Args:
            run_id: Run identifier

        Returns:
            Dictionary with chart_data, metadata, and original_chart (if exists)
            None if run not found
        """
        run_dir = self.history_dir / run_id

        if not run_dir.exists():
            return None

        try:
            # Load normalized chart
            chart_file = run_dir / "hype_cycle_chart.json"
            with open(chart_file, "r") as f:
                chart_data = json.load(f)

            # Load metadata
            metadata_file = run_dir / "metadata.json"
            with open(metadata_file, "r") as f:
                metadata = json.load(f)

            # Load original chart if exists
            original_chart = None
            original_file = run_dir / "hype_cycle_chart_full.json"
            if original_file.exists():
                with open(original_file, "r") as f:
                    original_chart = json.load(f)

            return {
                "run_id": run_id,
                "chart_data": chart_data,
                "metadata": metadata,
                "original_chart": original_chart
            }

        except Exception as e:
            print(f"[ERROR] Failed to load run {run_id}: {e}")
            return None

    def delete_run(self, run_id: str) -> bool:
        """
        Delete a pipeline run.

        Args:
            run_id: Run identifier

        Returns:
            True if deleted successfully, False otherwise
        """
        run_dir = self.history_dir / run_id

        if not run_dir.exists():
            return False

        try:
            shutil.rmtree(run_dir)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to delete run {run_id}: {e}")
            return False

    def get_latest_run(self) -> Optional[Dict[str, Any]]:
        """
        Get the most recent pipeline run.

        Returns:
            Run data or None if no runs exist
        """
        runs = self.list_runs(limit=1)
        if not runs:
            return None

        run_id = runs[0]["run_id"]
        return self.get_run(run_id)
