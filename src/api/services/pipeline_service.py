"""
Pipeline Service - Wrapper for LangGraph orchestrator with WebSocket streaming.

Provides real-time progress updates during multi-agent pipeline execution.
"""

import asyncio
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, List

from src.agents.langgraph_orchestrator import generate_hype_cycle_chart
from src.agents.shared.logger import AgentLogger, LogLevel
from src.api.models.pipeline_schemas import (
    PipelineConfig,
    AgentStartEvent,
    AgentCompleteEvent,
    TechCompleteEvent,
    PipelineCompleteEvent,
    PipelineErrorEvent,
    PipelineLogEvent,
    PipelineProgressEvent,
    PipelineStartEvent,
)
from src.api.services.run_history_service import RunHistoryService
from src.graph.neo4j_client import Neo4jClient


class StreamingLogger(AgentLogger):
    """Custom logger that streams events to WebSocket."""

    def __init__(
        self,
        level: LogLevel,
        event_callback: Callable[[Dict[str, Any]], None],
        total_techs: int = 0
    ):
        """
        Initialize streaming logger.

        Args:
            level: Log verbosity level
            event_callback: Async callback to send events
            total_techs: Total number of technologies to process
        """
        super().__init__(level=level, log_file=None)
        self.event_callback = event_callback
        self.total_techs = total_techs
        self.completed_techs = 0
        self.current_tech_id = None
        self.current_tech_name = None

    def _send_event(self, event: Dict[str, Any]):
        """Send event via callback."""
        try:
            self.event_callback(event)
        except Exception as e:
            print(f"[ERROR] Failed to send event: {e}")

    def log_pipeline_start(self, tech_count: int, enable_tavily: bool, **kwargs):
        """Override to emit WebSocket event."""
        super().log_pipeline_start(tech_count, enable_tavily, **kwargs)

        event = PipelineStartEvent(
            timestamp=datetime.utcnow().isoformat(),
            message=f"Starting analysis of {tech_count} technologies",
            config=PipelineConfig(
                tech_count=tech_count,
                enable_tavily=enable_tavily,
                community_version=kwargs.get("community_version", "v1"),
                min_docs=kwargs.get("min_document_count", 5),
                verbosity="normal"
            )
        )
        self._send_event(event.model_dump())

    def log_agent_start(self, agent_name: str, tech_id: str, inputs: Optional[Dict[str, Any]] = None):
        """Override to emit WebSocket event."""
        super().log_agent_start(agent_name, tech_id, inputs)

        # Track current tech
        self.current_tech_id = tech_id
        if inputs and "tech_name" in inputs:
            self.current_tech_name = inputs["tech_name"]

        event = AgentStartEvent(
            timestamp=datetime.utcnow().isoformat(),
            message=f"Agent {agent_name} started processing {tech_id}",
            agent_name=agent_name,
            tech_id=tech_id,
            tech_name=self.current_tech_name
        )
        self._send_event(event.model_dump())

        # Emit progress update
        if self.total_techs > 0:
            progress_pct = int((self.completed_techs / self.total_techs) * 100)
            progress_event = PipelineProgressEvent(
                timestamp=datetime.utcnow().isoformat(),
                message=f"Processing {self.completed_techs + 1}/{self.total_techs}",
                progress=progress_pct,
                current_tech=tech_id,
                current_agent=agent_name
            )
            self._send_event(progress_event.model_dump())

    def log_agent_output(self, agent_name: str, tech_id: str, outputs: Dict[str, Any]):
        """Override to emit WebSocket event."""
        super().log_agent_output(agent_name, tech_id, outputs)

        event = AgentCompleteEvent(
            timestamp=datetime.utcnow().isoformat(),
            message=f"Agent {agent_name} completed {tech_id}",
            agent_name=agent_name,
            tech_id=tech_id
        )
        self._send_event(event.model_dump())

    def log_technology_complete(self, tech_id: str, final_state: Dict[str, Any]):
        """Override to emit WebSocket event."""
        super().log_technology_complete(tech_id, final_state)

        self.completed_techs += 1

        event = TechCompleteEvent(
            timestamp=datetime.utcnow().isoformat(),
            message=f"Completed analysis of {tech_id}",
            tech_id=tech_id,
            tech_name=final_state.get("tech_name", tech_id),
            progress=self.completed_techs,
            total=self.total_techs,
            phase=final_state.get("hype_cycle_phase")
        )
        self._send_event(event.model_dump())

    def log_pipeline_complete(self, tech_count: int, duration_seconds: float):
        """Override to emit WebSocket event."""
        super().log_pipeline_complete(tech_count, duration_seconds)

        # Note: final completion event sent by run_pipeline()

    def log_error(self, message: str, tech_id: Optional[str] = None, agent_name: Optional[str] = None):
        """Log error and emit WebSocket event."""
        event = PipelineErrorEvent(
            timestamp=datetime.utcnow().isoformat(),
            message=message,
            error=message,
            tech_id=tech_id,
            agent_name=agent_name,
            recoverable=False
        )
        self._send_event(event.model_dump())

        # Also add to structured logs
        self._append_log({
            "timestamp": datetime.utcnow().isoformat(),
            "event": "error",
            "message": message,
            "tech_id": tech_id,
            "agent_name": agent_name
        })

    def log_info(self, message: str):
        """Log info message."""
        event = PipelineLogEvent(
            timestamp=datetime.utcnow().isoformat(),
            level="info",
            message=message
        )
        self._send_event(event.model_dump())

    def _append_log(self, log_entry: Dict[str, Any]):
        """Override to emit all log entries as WebSocket events."""
        super()._append_log(log_entry)

        # Convert log entry to PipelineLogEvent
        event_type = log_entry.get("event", "unknown")

        # Emit appropriate WebSocket event based on log type
        if event_type in ["agent_start", "agent_output", "tech_complete", "pipeline_start", "pipeline_complete"]:
            # These are already handled by their specific override methods
            pass
        else:
            # Emit as general log event
            message = log_entry.get("message", f"{event_type}: {log_entry.get('tech_id', 'N/A')}")
            level = "debug" if event_type == "llm_call" else "info"

            event = PipelineLogEvent(
                timestamp=log_entry.get("timestamp", datetime.utcnow().isoformat()),
                level=level,
                message=message
            )
            self._send_event(event.model_dump())


async def run_pipeline(
    config: PipelineConfig,
    event_callback: Callable[[Dict[str, Any]], None]
) -> Dict[str, Any]:
    """
    Execute multi-agent pipeline with real-time event streaming.

    Args:
        config: Pipeline configuration
        event_callback: Callback to send events to WebSocket

    Returns:
        Complete hype cycle chart JSON

    Raises:
        Exception: If pipeline execution fails
    """
    import time

    # Initialize run history service
    run_history = RunHistoryService()

    # Generate unique run ID
    run_id = run_history.generate_run_id(
        tech_count=config.tech_count,
        community_version=config.community_version
    )

    # Map verbosity to LogLevel
    verbosity_map = {
        "normal": LogLevel.NORMAL,
        "verbose": LogLevel.VERBOSE,
        "debug": LogLevel.DEBUG
    }
    log_level = verbosity_map.get(config.verbosity, LogLevel.NORMAL)

    # Create streaming logger
    logger = StreamingLogger(
        level=log_level,
        event_callback=event_callback,
        total_techs=config.tech_count
    )

    # Connect to Neo4j
    client = Neo4jClient()
    await client.connect()

    try:
        start_time = time.time()

        # Log start
        logger.log_info(f"Starting pipeline run {run_id}...")
        logger.log_info(f"Connecting to Neo4j database...")

        # Execute pipeline
        chart = await generate_hype_cycle_chart(
            driver=client.driver,
            limit=config.tech_count,
            logger=logger,
            enable_tavily=config.enable_tavily,
            community_version=config.community_version,
            min_document_count=config.min_docs
        )

        duration = time.time() - start_time

        # Save outputs to temporary directory first
        output_dir = Path("src/agents/outputs")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save original chart
        chart_file = output_dir / "hype_cycle_chart.json"
        with open(chart_file, "w") as f:
            json.dump(chart, f, indent=2)

        # Generate normalized chart (top 5 per phase)
        normalized_file = output_dir / "hype_cycle_chart_normalized.json"
        try:
            from src.agents.chart_normalization_ranked import normalize_chart
            normalized_chart = await normalize_chart(
                input_file=str(chart_file),
                output_file=str(normalized_file),
                top_n=5
            )
            logger.log_info(f"Generated normalized chart with top 5 per phase")
        except Exception as e:
            logger.log_info(f"Normalization skipped: {str(e)}")
            normalized_chart = chart  # Use original if normalization fails

        # Save to run history
        run_dir = run_history.save_run(
            run_id=run_id,
            chart_data=normalized_chart,
            config=config.model_dump(),
            duration_seconds=duration,
            original_chart=chart
        )
        logger.log_info(f"Saved run to history: {run_id}")

        # Copy normalized chart to frontend public folder (for backwards compatibility)
        frontend_data_dir = Path("frontend/public/data")
        frontend_data_dir.mkdir(parents=True, exist_ok=True)
        frontend_chart_file = frontend_data_dir / "hype_cycle_chart.json"

        shutil.copy(normalized_file, frontend_chart_file)
        logger.log_info(f"Updated frontend chart at {frontend_chart_file}")

        # Send completion event (include run_id)
        completion_event = PipelineCompleteEvent(
            timestamp=datetime.utcnow().isoformat(),
            message=f"Pipeline completed successfully",
            chart_data=normalized_chart,
            tech_count=len(chart.get("technologies", [])),
            duration_seconds=duration,
            output_file=str(frontend_chart_file),
            run_id=run_id  # Include run_id for frontend
        )
        event_callback(completion_event.model_dump())

        return normalized_chart

    except Exception as e:
        # Log error
        logger.log_error(str(e))

        # Re-raise for WebSocket error handling
        raise

    finally:
        await client.close()


async def get_last_generated_chart() -> Optional[Dict[str, Any]]:
    """
    Get the last generated chart from the frontend data folder.

    Returns:
        Chart data or None if not found
    """
    frontend_chart_file = Path("frontend/public/data/hype_cycle_chart.json")

    if not frontend_chart_file.exists():
        return None

    try:
        with open(frontend_chart_file, "r") as f:
            chart_data = json.load(f)

        # Add file modification time as generated_at if missing
        if "generated_at" not in chart_data:
            mtime = frontend_chart_file.stat().st_mtime
            chart_data["generated_at"] = datetime.fromtimestamp(mtime).isoformat()

        return chart_data

    except Exception as e:
        print(f"[ERROR] Failed to load chart: {e}")
        return None
