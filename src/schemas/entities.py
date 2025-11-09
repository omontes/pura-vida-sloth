"""
Pydantic schemas for Technology and Company entity nodes.

These schemas validate entity data before writing to Neo4j.
Based on SCHEMA_V2_COMPLETE.md specification.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Technology(BaseModel):
    """
    Technology node schema.

    Represents an emerging technology tracked in the system.
    NO SCORES stored (Pure GraphRAG principle).
    """

    id: str = Field(..., description="Canonical technology identifier (e.g., 'evtol')")
    name: str = Field(..., description="Full technology name")
    domain: str = Field(..., description="Technology domain (e.g., 'Aviation', 'Energy')")
    description: Optional[str] = Field(None, description="Technology description")
    aliases: list[str] = Field(default_factory=list, description="Alternative names")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "evtol",
                "name": "Electric Vertical Takeoff and Landing",
                "domain": "Aviation",
                "description": "Aircraft that use electric power to hover, take off, and land vertically",
                "aliases": ["eVTOL", "electric VTOL", "electric vertical takeoff"],
                "updated_at": "2025-01-15T10:30:00Z"
            }
        }


class Company(BaseModel):
    """
    Company node schema.

    Represents a company involved in emerging technology markets.
    NO SCORES stored (Pure GraphRAG principle).
    """

    id: str = Field(..., description="Canonical company identifier (e.g., 'joby')")
    name: str = Field(..., description="Company legal name")
    aliases: list[str] = Field(default_factory=list, description="Alternative names, trading names")
    ticker: Optional[str] = Field(None, description="Stock ticker symbol if publicly traded")
    kind: Optional[str] = Field(None, description="Company type (e.g., 'oem', 'supplier', 'operator')")
    sector: Optional[str] = Field(None, description="Industry sector")
    country: Optional[str] = Field(None, description="Country of incorporation (ISO 2-letter code)")
    description: Optional[str] = Field(None, description="Company description")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "joby",
                "name": "Joby Aviation",
                "aliases": ["Joby", "JOBY", "Joby Aero Inc."],
                "ticker": "JOBY",
                "kind": "oem",
                "sector": "Aviation",
                "country": "US",
                "description": "Electric vertical takeoff and landing aircraft manufacturer",
                "updated_at": "2025-01-15T10:30:00Z"
            }
        }
