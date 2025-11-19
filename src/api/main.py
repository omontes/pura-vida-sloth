"""
Canopy Intelligence - FastAPI Backend

Main application entry point for the multi-source intelligence platform.

Usage:
    uvicorn src.api.main:app --reload --port 8000

Environment Variables:
    ENABLE_PIPELINE_EXECUTION: Set to 'true' to enable agent execution (default: 'false')
    See .env.example for full list of required variables
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import get_settings
from .dependencies import close_neo4j_driver
from .routes import health, neo4j_routes, pipeline_routes
from .routes import pipeline_read_only_routes

# Import feature flags from core config
from src.core.config import ENABLE_PIPELINE_EXECUTION, get_config_summary


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    print("🚀 Starting Canopy Intelligence API...")
    print("📊 Neo4j connection configured")
    print("🌐 CORS enabled for frontend")

    # Display configuration summary
    config = get_config_summary()
    print(f"⚙️  Configuration:")
    print(f"   - Environment: {config['environment']}")
    print(f"   - Pipeline execution: {'✅ ENABLED' if config['pipeline_execution_enabled'] else '❌ DISABLED (demo mode)'}")
    print(f"   - Neo4j connected: {'✅' if config['neo4j_connected'] else '❌'}")

    if ENABLE_PIPELINE_EXECUTION:
        print("   🤖 Multi-agent system ACTIVE (OpenAI costs apply)")
    else:
        print("   📖 Read-only mode (zero costs, pre-generated data)")

    yield

    # Shutdown
    print("🛑 Shutting down...")
    await close_neo4j_driver()
    print("✅ Neo4j driver closed")


# Create FastAPI app
settings = get_settings()
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    lifespan=lifespan,
)

# Configure CORS for frontend
# Note: FastAPI's CORSMiddleware doesn't support wildcard domains in allow_origins list
# so we handle Vercel preview deployments by allowing all vercel.app subdomains
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "DELETE"],
    allow_headers=["*"],
    allow_origin_regex=r"https://.*\.vercel\.app",  # Allow all Vercel preview deployments
)

# Include routers - Always enabled
app.include_router(health.router)
app.include_router(neo4j_routes.router)

# Include pipeline routers conditionally based on feature flag
if ENABLE_PIPELINE_EXECUTION:
    # Full pipeline routes including WebSocket execution (costs OpenAI credits)
    app.include_router(pipeline_routes.router)
    print("   ⚡ Pipeline execution routes ENABLED")
else:
    # Read-only pipeline routes (zero cost, safe for demo)
    app.include_router(pipeline_read_only_routes.router)
    print("   🔒 Pipeline execution routes DISABLED (read-only mode)")


@app.get("/")
async def root():
    """API root endpoint with available routes"""
    response = {
        "message": "Canopy Intelligence API",
        "description": "Multi-Source Intelligence Platform for Strategic Technology Market Research",
        "version": settings.api_version,
        "mode": "full" if ENABLE_PIPELINE_EXECUTION else "demo (read-only)",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "neo4j_health": "/health/neo4j",
            "neo4j_graph": "/api/neo4j/subgraph",
            "pipeline": {
                "status": "/api/pipeline/status",
                "last_chart": "/api/pipeline/last-chart",
                "runs": "/api/pipeline/runs",
            },
        },
    }

    # Add execution endpoints only if enabled
    if ENABLE_PIPELINE_EXECUTION:
        response["endpoints"]["pipeline"]["websocket"] = "/api/pipeline/ws/run"
        response["endpoints"]["pipeline"]["cancel"] = "/api/pipeline/cancel"
    else:
        response["demo_mode_info"] = "/api/pipeline/execution-disabled"

    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
