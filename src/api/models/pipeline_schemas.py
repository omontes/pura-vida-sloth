"""
Pipeline API Schemas - Pydantic models for multi-agent pipeline execution.

Defines request/response schemas for the WebSocket-based pipeline runner.
"""

from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class PipelineConfig(BaseModel):
    """Configuration for pipeline execution."""

    tech_count: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Number of technologies to analyze"
    )

    community_version: Literal["v0", "v1", "v2"] = Field(
        default="v1",
        description="Community version for tech discovery"
    )

    enable_tavily: bool = Field(
        default=True,
        description="Enable Tavily real-time search for current signals"
    )

    min_docs: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Minimum document count per technology"
    )

    verbosity: Literal["normal", "verbose", "debug"] = Field(
        default="normal",
        description="Logging verbosity level"
    )


class PipelineEvent(BaseModel):
    """Base schema for pipeline events streamed via WebSocket."""

    type: str = Field(..., description="Event type identifier")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    message: Optional[str] = Field(None, description="Human-readable message")


class PipelineStartEvent(PipelineEvent):
    """Event emitted when pipeline execution begins."""

    type: Literal["pipeline_start"] = "pipeline_start"
    config: PipelineConfig


class AgentStartEvent(PipelineEvent):
    """Event emitted when an agent begins processing."""

    type: Literal["agent_start"] = "agent_start"
    agent_name: str = Field(..., description="Name of the agent (e.g., 'innovation_scorer')")
    tech_id: Optional[str] = Field(None, description="Technology being processed")
    tech_name: Optional[str] = Field(None, description="Technology display name")


class AgentCompleteEvent(PipelineEvent):
    """Event emitted when an agent completes processing."""

    type: Literal["agent_complete"] = "agent_complete"
    agent_name: str
    tech_id: Optional[str] = None
    duration_seconds: Optional[float] = None


class TechCompleteEvent(PipelineEvent):
    """Event emitted when a technology completes all agent processing."""

    type: Literal["tech_complete"] = "tech_complete"
    tech_id: str
    tech_name: str
    progress: int = Field(..., description="Number of technologies completed")
    total: int = Field(..., description="Total technologies to process")
    phase: Optional[str] = Field(None, description="Detected hype cycle phase")


class PipelineProgressEvent(PipelineEvent):
    """Event emitted for general progress updates."""

    type: Literal["pipeline_progress"] = "pipeline_progress"
    progress: int = Field(..., ge=0, le=100, description="Overall progress percentage")
    current_tech: Optional[str] = None
    current_agent: Optional[str] = None


class PipelineCompleteEvent(PipelineEvent):
    """Event emitted when pipeline execution completes successfully."""

    type: Literal["pipeline_complete"] = "pipeline_complete"
    chart_data: Dict[str, Any] = Field(..., description="Complete hype cycle chart JSON")
    tech_count: int = Field(..., description="Number of technologies analyzed")
    duration_seconds: float = Field(..., description="Total execution time")
    output_file: str = Field(..., description="Path to saved chart file")
    run_id: Optional[str] = Field(None, description="Unique run identifier for history tracking")


class PipelineErrorEvent(PipelineEvent):
    """Event emitted when an error occurs during pipeline execution."""

    type: Literal["pipeline_error"] = "pipeline_error"
    error: str = Field(..., description="Error message")
    tech_id: Optional[str] = Field(None, description="Technology being processed when error occurred")
    agent_name: Optional[str] = Field(None, description="Agent where error occurred")
    recoverable: bool = Field(default=False, description="Whether pipeline can continue")


class PipelineLogEvent(PipelineEvent):
    """Event emitted for log messages during pipeline execution."""

    type: Literal["pipeline_log"] = "pipeline_log"
    level: Literal["debug", "info", "warning", "error"] = "info"
    message: str


class PipelineStatusResponse(BaseModel):
    """Response schema for pipeline status queries."""

    is_running: bool
    current_tech_count: Optional[int] = None
    progress_percent: Optional[int] = None
    started_at: Optional[str] = None
    estimated_completion: Optional[str] = None
