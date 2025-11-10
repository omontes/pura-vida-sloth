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

    RECALIBRATED THRESHOLDS (2025-01-09): Lowered by 50-70% to match observed score distributions
    from 500-technology analysis. Scores compress to 0-41 range due to sparse graph data and
    conservative LLM prompts.

    Phases:
    1. Innovation Trigger: High innovation, low adoption/narrative
    2. Peak of Inflated Expectations: High narrative, moderate innovation, low adoption
    3. Trough of Disillusionment: ALL low scores (moved to end to prevent catch-all)
    4. Slope of Enlightenment: Growing adoption, moderate narrative, sustained innovation
    5. Plateau of Productivity: High adoption, balanced scores
    """

    # Phase 1: Innovation Trigger (RECALIBRATED: 50→20, 30→15, 40→15)
    if innovation > 20 and adoption < 15 and narrative < 15:
        return "innovation_trigger", f"Early innovation ({innovation:.0f}) with minimal adoption ({adoption:.0f}) and low media coverage ({narrative:.0f})"

    # Phase 2: Peak of Inflated Expectations (RECALIBRATED: 65→30, 60→40, 50→25)
    if narrative > 30 and hype > 40 and adoption < 25:
        return "peak", f"Media saturation ({narrative:.0f}) with high hype ({hype:.0f}) but low real adoption ({adoption:.0f})"

    # Phase 4: Slope of Enlightenment (RECALIBRATED: 50→25, 40-70→15-40, 40→15, 60→45)
    # MOVED BEFORE TROUGH to prevent catch-all behavior
    if adoption > 25 and 15 < narrative < 40 and innovation > 15 and hype < 45:
        return "slope", f"Growing adoption ({adoption:.0f}) with sustained innovation ({innovation:.0f}) and realistic expectations"

    # Phase 5: Plateau of Productivity (RECALIBRATED: 70→40, 50→25, 40-70→15-40, 50→30)
    if adoption > 40 and innovation > 25 and 15 < narrative < 40 and risk < 30:
        return "plateau", f"Mature market with high adoption ({adoption:.0f}), sustained innovation ({innovation:.0f}), and stable risk profile"

    # Phase 3: Trough of Disillusionment (RECALIBRATED: <40→<15, TIGHTENED: requires ALL low, not OR)
    # MOVED TO END to act as fallback for truly underperforming technologies only
    if narrative < 15 and adoption < 15 and innovation < 15 and risk < 20:
        return "trough", f"All metrics underperforming: narrative ({narrative:.0f}), adoption ({adoption:.0f}), innovation ({innovation:.0f})"

    # Default: Slope (catches edge cases with mixed signals)
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
