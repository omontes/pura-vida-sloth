"""
Configuration management for Canopy Intelligence.

This module centralizes all configuration settings including feature flags,
environment variables, and application constants.
"""

import os
from typing import Optional


# ============================================================================
# Feature Flags
# ============================================================================

# Controls whether the multi-agent pipeline execution endpoints are enabled
# When False, only read-only endpoints are available (no OpenAI costs)
# Set to "true" in development, "false" in production demo
ENABLE_PIPELINE_EXECUTION = os.getenv("ENABLE_PIPELINE_EXECUTION", "false").lower() == "true"


# ============================================================================
# Neo4j Configuration
# ============================================================================

NEO4J_URI: Optional[str] = os.getenv("NEO4J_URI")
NEO4J_USERNAME: str = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD: Optional[str] = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE: str = os.getenv("NEO4J_DATABASE", "neo4j")


# ============================================================================
# API Keys (Only needed when ENABLE_PIPELINE_EXECUTION=true)
# ============================================================================

OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY: Optional[str] = os.getenv("TAVILY_API_KEY")
LENS_API_TOKEN: Optional[str] = os.getenv("LENS_API_TOKEN")
GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN")


# ============================================================================
# Application Settings
# ============================================================================

# Python environment detection
PYTHON_UNBUFFERED: str = os.getenv("PYTHONUNBUFFERED", "1")

# Deployment environment
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION: bool = ENVIRONMENT == "production"


# ============================================================================
# Validation
# ============================================================================

def validate_config() -> None:
    """
    Validate required configuration settings.

    Raises:
        ValueError: If required settings are missing or invalid.
    """
    # Neo4j is always required (for graph visualization)
    if not NEO4J_URI:
        raise ValueError("NEO4J_URI environment variable is required")

    if not NEO4J_PASSWORD:
        raise ValueError("NEO4J_PASSWORD environment variable is required")

    # OpenAI is only required if pipeline execution is enabled
    if ENABLE_PIPELINE_EXECUTION and not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY is required when ENABLE_PIPELINE_EXECUTION=true"
        )


def get_config_summary() -> dict:
    """
    Get a summary of current configuration (safe for logging).

    Returns:
        dict: Configuration summary with sensitive values masked.
    """
    return {
        "environment": ENVIRONMENT,
        "is_production": IS_PRODUCTION,
        "pipeline_execution_enabled": ENABLE_PIPELINE_EXECUTION,
        "neo4j_connected": bool(NEO4J_URI and NEO4J_PASSWORD),
        "openai_configured": bool(OPENAI_API_KEY),
        "tavily_configured": bool(TAVILY_API_KEY),
        "lens_configured": bool(LENS_API_TOKEN),
        "github_configured": bool(GITHUB_TOKEN),
    }
