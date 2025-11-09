"""
Configuration Management

Loads settings from environment variables.
Required .env variables:
- NEO4J_URI
- NEO4J_USERNAME
- NEO4J_PASSWORD
- NEO4J_DATABASE
"""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment"""

    # Neo4j Connection
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_username: str = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "password")
    neo4j_database: str = os.getenv("NEO4J_DATABASE", "neo4j")

    # API Settings
    api_title: str = "Pura Vida Sloth API"
    api_version: str = "1.0.0"
    api_description: str = "Strategic Technology Market Research - Neo4j GraphRAG API"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields in .env (used by other parts of app)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
