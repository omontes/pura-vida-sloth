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

    RECALIBRATED THRESHOLDS (2025-01-10 v3): Adjusted for Tavily-enhanced narrative scores.
    Tavily adds +20-30 points to narrative baseline, causing 96% Peak clustering with old thresholds.
    New calibration accounts for Tavily-boosted distribution while maintaining phase diversity.

    Phases:
    1. Innovation Trigger: High innovation, low adoption/narrative
    2. Peak of Inflated Expectations: High narrative AND hype, low adoption
    3. Trough of Disillusionment: Low scores with 2/4 criteria
    4. Slope of Enlightenment: Moderate growth across metrics
    5. Plateau of Productivity: High adoption, sustained innovation
    """

    # Phase 1: Innovation Trigger (TIGHTENED: 12→25 to account for Tavily noise)
    # Early innovation with truly minimal media coverage (harder to achieve with Tavily)
    if innovation > 15 and adoption < 10 and narrative < 25:
        return "innovation_trigger", f"Early innovation ({innovation:.0f}) with minimal adoption ({adoption:.0f}) and low media coverage ({narrative:.0f})"

    # Phase 2: Peak of Inflated Expectations (TIGHTENED: 20→45, OR→AND, 25→40)
    # Require BOTH high narrative AND high hype (not just one), with low adoption
    # This filters out Tavily noise and captures true media saturation
    if narrative > 45 and hype > 40 and adoption < 25:
        return "peak", f"Media saturation ({narrative:.0f}) with high hype ({hype:.0f}) but limited adoption ({adoption:.0f})"

    # Phase 5: Plateau of Productivity (KEEP: works well)
    # Check BEFORE Slope to capture mature technologies
    if adoption > 30 and innovation > 20 and narrative < 60 and risk < 35:
        return "plateau", f"Mature market with high adoption ({adoption:.0f}), sustained innovation ({innovation:.0f}), and stable risk profile"

    # Phase 4: Slope of Enlightenment (ADJUSTED: 10→20 for narrative baseline shift)
    # Moderate adoption with balanced metrics (accounts for Tavily baseline)
    if adoption > 20 and innovation > 12 and narrative > 20 and hype < 50:
        return "slope", f"Growing adoption ({adoption:.0f}) with sustained innovation ({innovation:.0f}) and realistic expectations"

    # Phase 3: Trough of Disillusionment (TIGHTENED: 15→25, 20→30)
    # Technologies with multiple weak signals (adjusted for Tavily baseline)
    low_count = sum([
        narrative < 30,
        adoption < 20,
        innovation < 20,
        hype < 30
    ])
    if low_count >= 2:
        return "trough", f"Multiple underperforming metrics (2+ low scores): narrative ({narrative:.0f}), adoption ({adoption:.0f}), innovation ({innovation:.0f})"

    # Default: Slope (for mixed signals that don't fit anywhere)
    return "slope", f"Mixed signals across layers (innov={innovation:.0f}, adopt={adoption:.0f}, narr={narrative:.0f})"

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
