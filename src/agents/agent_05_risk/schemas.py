"""
Pydantic schemas for Agent 5: Risk Scorer

Defines input/output data structures for Layer 3 risk scoring.
"""

from typing import Optional
from pydantic import BaseModel, Field


class RiskInput(BaseModel):
    """Input for Risk Scorer agent."""
    tech_id: str = Field(description="Technology ID to score")
    start_date: Optional[str] = Field(default="2024-07-01", description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default="2025-01-01", description="End date (YYYY-MM-DD)")


class RiskMetrics(BaseModel):
    """Raw metrics for risk scoring."""
    sec_risk_mentions_6mo: int = Field(description="SEC risk mentions in last 6 months")
    institutional_holdings_pct: float = Field(description="% of shares held by institutions")
    insider_buy_count: int = Field(default=0, description="Insider buy transactions")
    insider_sell_count: int = Field(default=0, description="Insider sell transactions")
    insider_net_position: str = Field(default="neutral", description="'bullish', 'neutral', or 'bearish'")


class RiskOutput(BaseModel):
    """Output from Risk Scorer agent."""
    tech_id: str = Field(description="Technology ID")
    risk_score: float = Field(description="Risk score (0-100)", ge=0.0, le=100.0)
    reasoning: str = Field(description="LLM reasoning (2-3 sentences)")
    key_metrics: RiskMetrics = Field(description="Raw metrics")
    confidence: str = Field(description="'high', 'medium', or 'low'")
