"""
Dependency Injection

Provides Neo4j driver as FastAPI dependency.
"""

from neo4j import AsyncGraphDatabase, AsyncDriver
from .config import get_settings
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# Global driver instance
_driver: AsyncDriver | None = None


async def get_neo4j_driver() -> AsyncDriver:
    """
    Get Neo4j async driver instance (singleton).

    Returns driver that can execute Cypher queries.
    """
    global _driver

    if _driver is None:
        settings = get_settings()
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password),
        )

    return _driver


async def close_neo4j_driver():
    """Close Neo4j driver on shutdown"""
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None


@asynccontextmanager
async def neo4j_session_context(driver: AsyncDriver) -> AsyncGenerator:
    """
    Async context manager for Neo4j sessions.

    Usage:
        async with neo4j_session_context(driver) as session:
            result = await session.run("MATCH (n) RETURN n")
    """
    settings = get_settings()
    async with driver.session(database=settings.neo4j_database) as session:
        yield session
