"""
Pipeline Routes - WebSocket endpoints for multi-agent pipeline execution.

Provides real-time progress streaming and pipeline control.
"""

import asyncio
import json
from typing import Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse

from src.api.models.pipeline_schemas import PipelineConfig, PipelineStatusResponse
from src.api.services.pipeline_service import run_pipeline, get_last_generated_chart
from src.api.services.run_history_service import RunHistoryService


router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

# Track running pipeline (simple in-memory state, single-runner model)
_pipeline_state = {
    "is_running": False,
    "current_config": None,
    "started_at": None,
}


@router.websocket("/ws/run")
async def run_pipeline_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for running multi-agent pipeline with real-time updates.

    Protocol:
    1. Client connects and sends PipelineConfig as JSON
    2. Server validates config and starts pipeline
    3. Server streams progress events (pipeline_start, agent_start, tech_complete, etc.)
    4. Server sends pipeline_complete with full chart JSON
    5. Connection closes

    Events:
    - pipeline_start: Pipeline execution begins
    - agent_start: Agent begins processing technology
    - agent_complete: Agent completes processing
    - tech_complete: Technology completes all agents
    - pipeline_progress: General progress updates
    - pipeline_log: Info/debug messages
    - pipeline_complete: Pipeline finishes successfully
    - pipeline_error: Error occurred
    """
    await websocket.accept()

    try:
        # Check if pipeline already running
        if _pipeline_state["is_running"]:
            error_msg = {
                "type": "pipeline_error",
                "error": "Pipeline already running. Please wait for current execution to complete.",
                "recoverable": False
            }
            await websocket.send_json(error_msg)
            await websocket.close()
            return

        # Receive configuration from client
        config_data = await websocket.receive_json()

        # Validate and parse config
        try:
            config = PipelineConfig(**config_data)
        except Exception as e:
            error_msg = {
                "type": "pipeline_error",
                "error": f"Invalid configuration: {str(e)}",
                "recoverable": False
            }
            await websocket.send_json(error_msg)
            await websocket.close()
            return

        # Mark pipeline as running
        _pipeline_state["is_running"] = True
        _pipeline_state["current_config"] = config.model_dump()

        from datetime import datetime
        _pipeline_state["started_at"] = datetime.utcnow().isoformat()

        # Event callback to send to WebSocket
        async def send_event(event: Dict[str, Any]):
            """Send event to WebSocket client."""
            try:
                await websocket.send_json(event)
            except Exception as e:
                print(f"[ERROR] Failed to send WebSocket event: {e}")

        # Wrap sync callback for async context
        event_queue = asyncio.Queue()

        def sync_callback(event: Dict[str, Any]):
            """Sync callback that queues events."""
            asyncio.create_task(event_queue.put(event))

        # Start event sender task
        async def event_sender():
            """Send queued events to WebSocket."""
            while True:
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
                    await send_event(event)
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    continue
                except Exception as e:
                    print(f"[ERROR] Event sender error: {e}")
                    break

        sender_task = asyncio.create_task(event_sender())

        try:
            # Run pipeline
            chart = await run_pipeline(config, sync_callback)

            # Pipeline completed successfully (completion event sent by service)

        except Exception as e:
            # Send error event
            error_event = {
                "type": "pipeline_error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": f"Pipeline failed: {str(e)}",
                "recoverable": False
            }
            await send_event(error_event)

        finally:
            # Mark pipeline as not running
            _pipeline_state["is_running"] = False
            _pipeline_state["current_config"] = None
            _pipeline_state["started_at"] = None

            # Cancel sender task
            sender_task.cancel()
            try:
                await sender_task
            except asyncio.CancelledError:
                pass

            # Close WebSocket
            await websocket.close()

    except WebSocketDisconnect:
        print("[INFO] Client disconnected from pipeline WebSocket")
        _pipeline_state["is_running"] = False
        _pipeline_state["current_config"] = None
        _pipeline_state["started_at"] = None

    except Exception as e:
        print(f"[ERROR] WebSocket error: {e}")
        _pipeline_state["is_running"] = False
        _pipeline_state["current_config"] = None
        _pipeline_state["started_at"] = None

        try:
            await websocket.close()
        except:
            pass


@router.get("/status", response_model=PipelineStatusResponse)
async def get_pipeline_status():
    """
    Get current pipeline execution status.

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

    Returns:
        Chart JSON or 404 if not found
    """
    chart = await get_last_generated_chart()

    if chart is None:
        raise HTTPException(status_code=404, detail="No chart found. Please run the pipeline first.")

    return JSONResponse(content=chart)


@router.post("/cancel")
async def cancel_pipeline():
    """
    Cancel currently running pipeline.

    Note: Current implementation doesn't support graceful cancellation.
    This endpoint is reserved for future use.
    """
    if not _pipeline_state["is_running"]:
        raise HTTPException(status_code=400, detail="No pipeline currently running")

    # TODO: Implement graceful cancellation
    # For now, just reset state (pipeline will continue until completion)
    return {"message": "Cancellation requested (not yet implemented)"}


# ========================================
# Run History Endpoints
# ========================================

@router.get("/runs")
async def list_pipeline_runs(limit: int = 20):
    """
    List all pipeline runs (newest first).

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


@router.delete("/runs/{run_id}")
async def delete_pipeline_run(run_id: str):
    """
    Delete a pipeline run and all its files.

    Args:
        run_id: Unique run identifier

    Returns:
        Success message

    Raises:
        404: Run not found
        500: Delete failed
    """
    run_history = RunHistoryService()
    success = run_history.delete_run(run_id)

    if not success:
        # Check if run exists
        run_data = run_history.get_run(run_id)
        if run_data is None:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to delete run '{run_id}'")

    return JSONResponse(content={"message": f"Run '{run_id}' deleted successfully"})
