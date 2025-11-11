"""
Pura Vida Sloth - FastAPI Backend

Main application entry point.

Usage:
    uvicorn src.api.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import get_settings
from .dependencies import close_neo4j_driver
from .routes import health, neo4j_routes, pipeline_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    print("🚀 Starting Pura Vida Sloth API...")
    print("📊 Neo4j connection configured")
    print("🌐 CORS enabled for frontend")

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(neo4j_routes.router)
app.include_router(pipeline_routes.router)


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Pura Vida Sloth API",
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/health",
        "neo4j_health": "/health/neo4j",
        "pipeline": {
            "websocket": "/api/pipeline/ws/run",
            "status": "/api/pipeline/status",
            "last_chart": "/api/pipeline/last-chart",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
