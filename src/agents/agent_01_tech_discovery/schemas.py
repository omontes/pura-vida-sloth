"""
Pydantic schemas for Agent 1: Tech Discovery

Defines input/output data structures for technology enumeration.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class TechDiscoveryInput(BaseModel):
    """
    Input for Tech Discovery agent.

    Optional filters can be applied to narrow down technologies.
    """

    industry_filter: Optional[str] = Field(
        default=None,
        description="Optional industry filter (e.g., 'Aviation', 'Energy')"
    )
    min_document_count: int = Field(
        default=1,
        description="Minimum number of documents required (default: 1)"
    )
    limit: Optional[int] = Field(
        default=None,
        description="Maximum number of technologies to return (None = all)"
    )


class Technology(BaseModel):
    """
    Technology metadata from graph.

    Contains all information needed for downstream agents to score this technology.
    """

    id: str = Field(
        description="Technology ID (canonical identifier)"
    )
    name: str = Field(
        description="Technology name (human-readable)"
    )
    domain: Optional[str] = Field(
        default=None,
        description="Technology domain/industry (e.g., 'Aviation', 'Energy')"
    )
    aliases: List[str] = Field(
        default_factory=list,
        description="Alternative names for this technology"
    )
    companies: List[str] = Field(
        default_factory=list,
        description="Company tickers developing/using this technology"
    )
    document_count: int = Field(
        description="Total number of documents mentioning this technology"
    )
    doc_type_breakdown: Dict[str, int] = Field(
        default_factory=dict,
        description="Document count by type (e.g., {'patent': 42, 'news': 18})"
    )
    community_id: Optional[int] = Field(
        default=None,
        description="Community ID (v1) this technology belongs to"
    )
    pagerank: Optional[float] = Field(
        default=None,
        description="PageRank score (importance/influence)"
    )


class TechDiscoveryOutput(BaseModel):
    """
    Output from Tech Discovery agent.

    Returns list of technologies with metadata, ready for downstream agents.
    """

    technologies: List[Technology] = Field(
        description="List of discovered technologies"
    )
    total_count: int = Field(
        description="Total number of technologies found"
    )
    filtered_count: int = Field(
        description="Number of technologies after filtering"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "technologies": [
                    {
                        "id": "solid_state_battery",
                        "name": "Solid-State Battery",
                        "domain": "Energy",
                        "aliases": ["solid state battery", "SSB"],
                        "companies": ["QS", "SLDP"],
                        "document_count": 127,
                        "doc_type_breakdown": {
                            "patent": 42,
                            "news": 35,
                            "technical_paper": 28,
                            "sec_filing": 15,
                            "government_contract": 7
                        },
                        "community_id": 23,
                        "pagerank": 0.0045
                    }
                ],
                "total_count": 1755,
                "filtered_count": 1
            }
        }
