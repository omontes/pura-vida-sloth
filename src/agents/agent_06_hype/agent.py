"""Agent 6: Hype Scorer - Calculates hype from layer score divergence."""

from typing import Dict, Any
from pydantic import BaseModel, Field

class HypeOutput(BaseModel):
    tech_id: str
    hype_score: float = Field(ge=0.0, le=100.0)
    reasoning: str
    layer_divergence: float = Field(description="Std dev of layer scores")
    confidence: str

def calculate_hype_score(innovation: float, adoption: float, narrative: float, risk: float) -> tuple[float, float, str]:
    """
    Calculate hype score from layer divergence.

    High hype = High narrative + Low innovation/adoption (all talk, no substance)
    Low hype = Balanced scores across layers
    """
    import statistics

    # Calculate divergence (standard deviation)
    scores = [innovation, adoption, narrative, risk]
    avg_score = sum(scores) / len(scores)
    divergence = statistics.stdev(scores) if len(scores) > 1 else 0

    # Hype indicators
    narrative_premium = narrative - avg_score  # How much narrative exceeds average
    substance_deficit = avg_score - ((innovation + adoption) / 2)  # Gap between narrative and reality

    # Hype score: High when narrative >> fundamentals
    if narrative > 60 and (innovation < 40 or adoption < 40):
        hype_score = min(100, 50 + (narrative_premium * 2) + (substance_deficit * 1.5))
        reasoning = f"High hype: Strong narrative ({narrative:.0f}) exceeds fundamentals (innov={innovation:.0f}, adopt={adoption:.0f})"
    elif divergence < 15:
        hype_score = max(0, 50 - divergence * 2)
        reasoning = f"Low hype: Balanced scores across layers (divergence={divergence:.1f})"
    else:
        hype_score = 50 + (divergence - 15) * 1.5
        reasoning = f"Moderate hype: Mixed signals across layers (divergence={divergence:.1f})"

    return hype_score, divergence, reasoning

async def hype_scorer_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    tech_id = state["tech_id"]
    innovation = state.get("innovation_score", 50.0)
    adoption = state.get("adoption_score", 50.0)
    narrative = state.get("narrative_score", 50.0)
    risk = state.get("risk_score", 50.0)

    hype_score, divergence, reasoning = calculate_hype_score(innovation, adoption, narrative, risk)

    confidence = "high" if divergence > 20 or abs(narrative - innovation) > 30 else "medium"

    return {
        "tech_id": tech_id,
        "hype_score": hype_score,
        "hype_reasoning": reasoning,
        "layer_divergence": divergence,
        "hype_confidence": confidence,
    }
