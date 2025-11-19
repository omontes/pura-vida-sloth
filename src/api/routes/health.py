"""
Health Check Routes

GET /health - Check API status
GET /health/neo4j - Check Neo4j connection
"""

from fastapi import APIRouter, Depends, HTTPException
from neo4j import AsyncDriver
from ..dependencies import get_neo4j_driver

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """API health check"""
    return {
        "status": "healthy",
        "service": "Pura Vida Sloth API",
        "version": "1.0.0"
    }


@router.head("/health")
async def health_check_head():
    """Health check for HEAD requests (used by monitoring services like UptimeRobot)"""
    return {}


@router.get("/health/neo4j")
async def neo4j_health_check(driver: AsyncDriver = Depends(get_neo4j_driver)):
    """Check Neo4j connection"""
    try:
        async with driver.session() as session:
            result = await session.run("RETURN 1 as test")
            record = await result.single()
            if record and record.get("test") == 1:
                return {
                    "status": "healthy",
                    "neo4j": "connected"
                }
            raise Exception("Unexpected result")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neo4j connection failed: {str(e)}")


@router.head("/health/neo4j")
async def neo4j_health_check_head(driver: AsyncDriver = Depends(get_neo4j_driver)):
    """Check Neo4j connection for HEAD requests (used by monitoring services like UptimeRobot)"""
    try:
        async with driver.session() as session:
            result = await session.run("RETURN 1 as test")
            record = await result.single()
            if record and record.get("test") == 1:
                return {}
            raise Exception("Unexpected result")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neo4j connection failed: {str(e)}")
