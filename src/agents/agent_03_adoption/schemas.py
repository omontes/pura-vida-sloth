"""
Pydantic schemas for Agent 3: Adoption Scorer

Defines input/output data structures for Layer 2 adoption scoring.
"""

from typing import Dict, Optional, List
from pydantic import BaseModel, Field


class ContractSummary(BaseModel):
    """Summary of a single government contract for evidence."""
    doc_id: str = Field(description="Contract document ID")
    title: str = Field(description="Contract title")
    value: float = Field(description="Contract value in USD")
    agency: str = Field(description="Government agency")


class AdoptionInput(BaseModel):
    """
    Input for Adoption Scorer agent.

    Takes a single technology ID and optional temporal window overrides.
    """

    tech_id: str = Field(
        description="Technology ID to score"
    )
    start_date: Optional[str] = Field(
        default="2023-07-01",
        description="Start date for temporal window (YYYY-MM-DD)"
    )
    end_date: Optional[str] = Field(
        default="2025-01-01",
        description="End date for temporal window (YYYY-MM-DD)"
    )


class AdoptionMetrics(BaseModel):
    """
    Raw metrics extracted from graph for adoption scoring.

    These metrics are used by the LLM to calculate the final score.
    """

    # Government contract metrics
    gov_contract_count_1yr: int = Field(
        description="Number of government contracts in last year"
    )
    gov_contract_total_value: float = Field(
        description="Total value of government contracts (USD)"
    )
    gov_contract_avg_value: float = Field(
        description="Average contract value (USD)"
    )

    # Regulatory metrics
    regulatory_approval_count: int = Field(
        description="Number of regulatory approvals/certifications"
    )

    # Company development metrics
    companies_developing: int = Field(
        description="Number of companies developing this technology"
    )
    top_companies: List[str] = Field(
        default_factory=list,
        description="Top companies by document count"
    )

    # Top contracts (for evidence)
    top_contracts: List[ContractSummary] = Field(
        default_factory=list,
        description="Top 5 contracts by value"
    )


class AdoptionOutput(BaseModel):
    """
    Output from Adoption Scorer agent.

    Contains score, reasoning, and supporting metrics.
    """

    tech_id: str = Field(
        description="Technology ID that was scored"
    )
    adoption_score: float = Field(
        description="Adoption score (0-100)",
        ge=0.0,
        le=100.0
    )
    reasoning: str = Field(
        description="LLM reasoning for the score (2-3 sentences)"
    )
    key_metrics: AdoptionMetrics = Field(
        description="Raw metrics used for scoring"
    )
    confidence: str = Field(
        description="Confidence level: 'high', 'medium', 'low'"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "tech_id": "evtol",
                "adoption_score": 68.0,
                "reasoning": "Strong government validation with $42M in contracts across 5 agencies. 12 companies actively developing, with 3 regulatory approvals granted. Market formation stage is well underway.",
                "key_metrics": {
                    "gov_contract_count_1yr": 7,
                    "gov_contract_total_value": 42000000.0,
                    "gov_contract_avg_value": 6000000.0,
                    "regulatory_approval_count": 3,
                    "companies_developing": 12,
                    "top_companies": ["JOBY", "ACHR", "LILM"],
                    "top_contracts": []
                },
                "confidence": "high"
            }
        }
