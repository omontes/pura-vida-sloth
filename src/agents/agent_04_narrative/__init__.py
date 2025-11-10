"""
Agent 4: Narrative Scorer

Scores Layer 4 narrative signals (news sentiment, media coverage, outlet tiers).
Uses LLM reasoning with temperature=0.3 for narrative interpretation.

Complexity: Medium (multiple graph queries + LLM scoring)
"""

from src.agents.agent_04_narrative.agent import narrative_scorer_agent, score_narrative
from src.agents.agent_04_narrative.schemas import (
    NarrativeInput,
    NarrativeOutput,
    NarrativeMetrics,
)

__all__ = [
    "narrative_scorer_agent",
    "score_narrative",
    "NarrativeInput",
    "NarrativeOutput",
    "NarrativeMetrics",
]
