"""
Agent 3: Adoption Scorer

Scores Layer 2 adoption signals (government contracts, regulations, company activity).
Uses LLM reasoning to calculate adoption score.

Complexity: Medium (multiple graph queries + LLM scoring)
"""

from src.agents.agent_03_adoption.agent import adoption_scorer_agent, score_adoption
from src.agents.agent_03_adoption.schemas import (
    AdoptionInput,
    AdoptionOutput,
    AdoptionMetrics,
)

__all__ = [
    "adoption_scorer_agent",
    "score_adoption",
    "AdoptionInput",
    "AdoptionOutput",
    "AdoptionMetrics",
]
