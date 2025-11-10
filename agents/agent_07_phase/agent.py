"""Agent 7: Phase Detector - Determines hype cycle phase."""

from typing import Dict, Any
from pydantic import BaseModel, Field

class PhaseOutput(BaseModel):
    tech_id: str
    phase: str = Field(description="innovation_trigger|peak|trough|slope|plateau")
    reasoning: str
    confidence: str

def detect_hype_cycle_phase(innovation: float, adoption: float, narrative: float, risk: float, hype: float) -> tuple[str, str]:
    """
    Detect hype cycle phase from layer scores.

    Phases:
    1. Innovation Trigger: High innovation, low adoption/narrative
    2. Peak of Inflated Expectations: High narrative, moderate innovation, low adoption
    3. Trough of Disillusionment: Declining narrative, low adoption, moderate innovation
    4. Slope of Enlightenment: Growing adoption, moderate narrative, sustained innovation
    5. Plateau of Productivity: High adoption, balanced scores
    """

    # Phase 1: Innovation Trigger
    if innovation > 50 and adoption < 30 and narrative < 40:
        return "innovation_trigger", f"Early innovation ({innovation:.0f}) with minimal adoption ({adoption:.0f}) and low media coverage ({narrative:.0f})"

    # Phase 2: Peak of Inflated Expectations
    if narrative > 65 and hype > 60 and adoption < 50:
        return "peak", f"Media saturation ({narrative:.0f}) with high hype ({hype:.0f}) but low real adoption ({adoption:.0f})"

    # Phase 3: Trough of Disillusionment
    if narrative < 40 and adoption < 40 and (innovation < 50 or risk > 60):
        return "trough", f"Low narrative ({narrative:.0f}) and adoption ({adoption:.0f}), market correction phase"

    # Phase 4: Slope of Enlightenment
    if adoption > 50 and 40 < narrative < 70 and innovation > 40 and hype < 60:
        return "slope", f"Growing adoption ({adoption:.0f}) with sustained innovation ({innovation:.0f}) and realistic expectations"

    # Phase 5: Plateau of Productivity
    if adoption > 70 and innovation > 50 and 40 < narrative < 70 and risk < 50:
        return "plateau", f"Mature market with high adoption ({adoption:.0f}), sustained innovation ({innovation:.0f}), and stable risk profile"

    # Default: Slope (most common mature phase)
    return "slope", f"Moderate signals across layers (innov={innovation:.0f}, adopt={adoption:.0f}, narr={narrative:.0f})"

async def phase_detector_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    tech_id = state["tech_id"]
    innovation = state.get("innovation_score", 50.0)
    adoption = state.get("adoption_score", 50.0)
    narrative = state.get("narrative_score", 50.0)
    risk = state.get("risk_score", 50.0)
    hype = state.get("hype_score", 50.0)

    phase, reasoning = detect_hype_cycle_phase(innovation, adoption, narrative, risk, hype)

    # Confidence based on score clarity
    if max([innovation, adoption, narrative]) - min([innovation, adoption, narrative]) > 30:
        confidence = "high"
    else:
        confidence = "medium"

    return {
        "tech_id": tech_id,
        "hype_cycle_phase": phase,
        "phase_reasoning": reasoning,
        "phase_confidence": confidence,
    }
