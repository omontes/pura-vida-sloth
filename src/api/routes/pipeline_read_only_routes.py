"""
Pipeline Read-Only Routes - Safe endpoints for demo mode.

These routes provide access to pipeline data and run history WITHOUT
executing the multi-agent system (zero OpenAI costs).

Used when ENABLE_PIPELINE_EXECUTION=false for production demos.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.api.models.pipeline_schemas import PipelineStatusResponse
from src.api.services.pipeline_service import get_last_generated_chart
from src.api.services.run_history_service import RunHistoryService


router = APIRouter(prefix="/api/pipeline", tags=["pipeline-readonly"])

# Track pipeline state (read-only in demo mode)
_pipeline_state = {
    "is_running": False,
    "current_config": None,
    "started_at": None,
}


@router.get("/status", response_model=PipelineStatusResponse)
async def get_pipeline_status():
    """
    Get current pipeline execution status.

    In demo mode, this will always return is_running=False.

    Returns:
        Pipeline status including whether it's running and progress
    """
    return PipelineStatusResponse(
        is_running=_pipeline_state["is_running"],
        current_tech_count=_pipeline_state["current_config"].get("tech_count") if _pipeline_state["current_config"] else None,
        started_at=_pipeline_state["started_at"]
    )


@router.get("/last-chart")
async def get_last_chart():
    """
    Get the last generated chart from the frontend data folder.

    This reads pre-generated analysis results from:
    - frontend/public/data/hype_cycle_chart.json

    Returns:
        Chart JSON or 404 if not found
    """
    chart = await get_last_generated_chart()

    if chart is None:
        raise HTTPException(
            status_code=404,
            detail="No chart found. Chart data should be pre-generated in demo mode."
        )

    return JSONResponse(content=chart)


# ========================================
# Run History Endpoints (Read-Only)
# ========================================

@router.get("/runs")
async def list_pipeline_runs(limit: int = 20):
    """
    List all pipeline runs (newest first).

    Provides access to historical analysis results without running new pipelines.

    Args:
        limit: Maximum number of runs to return (default: 20)

    Returns:
        List of run metadata dictionaries with run_id, created_at, config, etc.
    """
    run_history = RunHistoryService()
    runs = run_history.list_runs(limit=limit)
    return JSONResponse(content={"runs": runs, "count": len(runs)})


@router.get("/runs/{run_id}")
async def get_pipeline_run(run_id: str):
    """
    Get complete data for a specific pipeline run.

    Allows viewing historical analysis results.

    Args:
        run_id: Unique run identifier (format: YYYY-MM-DD_HH-MM-SS_{tech_count}tech_{version})

    Returns:
        Run data including chart_data, metadata, and original_chart

    Raises:
        404: Run not found
    """
    run_history = RunHistoryService()
    run_data = run_history.get_run(run_id)

    if run_data is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    return JSONResponse(content=run_data)


@router.get("/execution-disabled")
async def execution_disabled_info():
    """
    Informational endpoint explaining why pipeline execution is disabled.

    Returns:
        Message explaining demo mode and how to enable full features.
    """
    return JSONResponse(
        content={
            "message": "Pipeline execution is disabled in demo mode",
            "reason": "This deployment is configured for read-only access to avoid OpenAI API costs",
            "available_features": [
                "View pre-generated Hype Cycle Chart",
                "Explore interactive Neo4j graph visualization",
                "Browse historical pipeline runs",
                "Access run metadata and analysis results"
            ],
            "to_enable_full_features": [
                "Clone the repository and run locally",
                "Set ENABLE_PIPELINE_EXECUTION=true in your .env file",
                "Add your OpenAI API key and other credentials",
                "Run the full multi-agent analysis pipeline"
            ],
            "documentation": "https://github.com/[your-username]/pura-vida-sloth#readme"
        }
    )
