"""
Pydantic schemas for Agent 4: Narrative Scorer

Defines input/output data structures for Layer 4 narrative scoring.
"""

from typing import Dict, Optional, List
from pydantic import BaseModel, Field


class ArticleSummary(BaseModel):
    """Summary of a single news article for evidence."""
    doc_id: str = Field(description="Article document ID")
    title: str = Field(description="Article title")
    outlet: str = Field(description="News outlet")
    sentiment: float = Field(description="Sentiment score (-1 to 1)")


class NarrativeInput(BaseModel):
    """
    Input for Narrative Scorer agent.

    Takes a single technology ID and optional temporal window overrides.
    """

    tech_id: str = Field(
        description="Technology ID to score"
    )
    start_date: Optional[str] = Field(
        default=None,
        description="Start date for temporal window (YYYY-MM-DD), defaults to 6 months ago"
    )
    end_date: Optional[str] = Field(
        default=None,
        description="End date for temporal window (YYYY-MM-DD), defaults to today"
    )


class NarrativeMetrics(BaseModel):
    """
    Raw metrics extracted from graph for narrative scoring.

    These metrics are used by the LLM to calculate the final score.
    """

    # News volume metrics
    news_count_3mo: int = Field(
        description="Number of news articles in last 3 months"
    )

    # Outlet tier breakdown
    tier1_count: int = Field(
        default=0,
        description="Number of tier 1 outlet articles (WSJ, NYT, etc.)"
    )
    tier2_count: int = Field(
        default=0,
        description="Number of tier 2 outlet articles"
    )
    tier3_count: int = Field(
        default=0,
        description="Number of tier 3 outlet articles"
    )

    # Sentiment metrics
    avg_sentiment: float = Field(
        description="Average sentiment score (-1 to 1)"
    )
    sentiment_trend: str = Field(
        default="neutral",
        description="Sentiment trend: 'positive', 'neutral', or 'negative'"
    )

    # Top articles (for evidence)
    top_articles: List[ArticleSummary] = Field(
        default_factory=list,
        description="Top 5 articles by prominence"
    )

    # Tavily real-time search metrics (supplemental)
    news_count_recent_30d: int = Field(
        default=0,
        description="Recent news count from Tavily (last 30 days)"
    )
    freshness_score: float = Field(
        default=0.0,
        description="Narrative freshness/acceleration score (recent vs historical)"
    )
    tavily_headlines: List[str] = Field(
        default_factory=list,
        description="Top headlines from Tavily real-time search"
    )


class NarrativeOutput(BaseModel):
    """
    Output from Narrative Scorer agent.

    Contains score, reasoning, and supporting metrics.
    """

    tech_id: str = Field(
        description="Technology ID that was scored"
    )
    narrative_score: float = Field(
        description="Narrative score (0-100)",
        ge=0.0,
        le=100.0
    )
    reasoning: str = Field(
        description="LLM reasoning for the score (2-3 sentences)"
    )
    key_metrics: NarrativeMetrics = Field(
        description="Raw metrics used for scoring"
    )
    confidence: str = Field(
        description="Confidence level: 'high', 'medium', 'low'"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "tech_id": "evtol",
                "narrative_score": 75.0,
                "reasoning": "High media coverage with 45 articles in last 3 months, including 8 tier-1 outlets. Sentiment is strongly positive (0.65), indicating favorable public perception and media saturation.",
                "key_metrics": {
                    "news_count_3mo": 45,
                    "tier1_count": 8,
                    "tier2_count": 22,
                    "tier3_count": 15,
                    "avg_sentiment": 0.65,
                    "sentiment_trend": "positive",
                    "top_articles": []
                },
                "confidence": "high"
            }
        }
