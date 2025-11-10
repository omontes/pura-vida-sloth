"""
Pydantic schemas for Agent 2: Innovation Scorer

Defines input/output data structures for Layer 1 innovation scoring.
"""

from typing import Dict, Optional, List, Any
from pydantic import BaseModel, Field


class PatentSummary(BaseModel):
    """Summary of a single patent for evidence."""
    doc_id: str = Field(description="Patent document ID")
    title: str = Field(description="Patent title")
    citations: int = Field(description="Number of citations received")
    pagerank: float = Field(description="PageRank score")


class InnovationInput(BaseModel):
    """
    Input for Innovation Scorer agent.

    Takes a single technology ID and optional temporal window overrides.
    """

    tech_id: str = Field(
        description="Technology ID to score"
    )
    start_date: Optional[str] = Field(
        default="2023-01-01",
        description="Start date for temporal window (YYYY-MM-DD)"
    )
    end_date: Optional[str] = Field(
        default="2025-01-01",
        description="End date for temporal window (YYYY-MM-DD)"
    )
    community_version: str = Field(
        default="v1",
        description="Community detection version to use (v0-v5)"
    )


class InnovationMetrics(BaseModel):
    """
    Raw metrics extracted from graph for innovation scoring.

    These metrics are used by the LLM to calculate the final score.
    """

    # Patent metrics
    patent_count_2yr: int = Field(
        description="Number of patents filed in last 2 years"
    )
    patent_citations: int = Field(
        description="Total citations received by patents"
    )
    patent_pagerank_weighted: float = Field(
        description="PageRank-weighted patent count (importance weighting)"
    )
    avg_patent_pagerank: float = Field(
        description="Average PageRank score of patents"
    )

    # Paper metrics
    paper_count_2yr: int = Field(
        description="Number of research papers published in last 2 years"
    )
    paper_citations: int = Field(
        description="Total citations received by papers"
    )

    # Community context
    community_id: Optional[int] = Field(
        default=None,
        description="Community ID this technology belongs to"
    )
    community_patent_count: int = Field(
        default=0,
        description="Total patents in technology's community"
    )
    community_paper_count: int = Field(
        default=0,
        description="Total papers in technology's community"
    )

    # Temporal trend
    temporal_trend: str = Field(
        default="stable",
        description="Innovation trend: 'growing', 'stable', or 'declining'"
    )

    # Top patents (for evidence)
    top_patents: List[PatentSummary] = Field(
        default_factory=list,
        description="Top 5 patents by citations"
    )


class InnovationOutput(BaseModel):
    """
    Output from Innovation Scorer agent.

    Contains score, reasoning, and supporting metrics.
    """

    tech_id: str = Field(
        description="Technology ID that was scored"
    )
    innovation_score: float = Field(
        description="Innovation score (0-100)",
        ge=0.0,
        le=100.0
    )
    reasoning: str = Field(
        description="LLM reasoning for the score (2-3 sentences)"
    )
    key_metrics: InnovationMetrics = Field(
        description="Raw metrics used for scoring"
    )
    confidence: str = Field(
        description="Confidence level: 'high', 'medium', 'low'"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "tech_id": "solid_state_battery",
                "innovation_score": 72.5,
                "reasoning": "Strong patent activity with 42 filings in last 2 years, heavily weighted by PageRank (avg 0.0045). Community shows 127 total patents. Temporal trend shows acceleration in Q3 2024.",
                "key_metrics": {
                    "patent_count_2yr": 42,
                    "patent_citations": 156,
                    "patent_pagerank_weighted": 58.3,
                    "avg_patent_pagerank": 0.0045,
                    "paper_count_2yr": 28,
                    "paper_citations": 89,
                    "community_id": 23,
                    "community_patent_count": 127,
                    "community_paper_count": 85,
                    "temporal_trend": "growing",
                    "top_patents": []
                },
                "confidence": "high"
            }
        }
