"""Agent 7: Phase Detector - Determines hype cycle phase."""

from typing import Dict, Any
from pydantic import BaseModel, Field

class PhaseOutput(BaseModel):
    tech_id: str
    phase: str = Field(description="innovation_trigger|peak|trough|slope|plateau")
    reasoning: str
    confidence: float = Field(description="Confidence score 0.0-1.0")

def detect_hype_cycle_phase(innovation: float, adoption: float, narrative: float, risk: float, hype: float) -> tuple[str, str]:
    """
    Detect hype cycle phase from layer scores.

    RECALIBRATED THRESHOLDS (2025-01-10 v4):
    - Fixed freshness calculation bug (was returning raw count instead of 1.0 for zero baseline)
    - Relaxed Innovation Trigger: adoption 10→15, narrative 25→35
    - Relaxed Plateau: adoption 30→25, innovation 20→15, risk 35→40

    Previous issue: 82% Peak clustering due to freshness bug + too-strict Innovation/Plateau thresholds.

    Phases:
    1. Innovation Trigger: High innovation, low adoption/narrative
    2. Peak of Inflated Expectations: High narrative AND hype, low adoption
    3. Trough of Disillusionment: Low scores with 2/4 criteria
    4. Slope of Enlightenment: Moderate growth across metrics
    5. Plateau of Productivity: Moderate-to-high adoption, sustained innovation
    """

    # Phase 1: Innovation Trigger (RECALIBRATED v6 for min_doc_count=5)
    # Early innovation with minimal adoption and low-to-moderate media coverage
    # Adjusted for min_doc=5: innovation 20-35, adoption 10-25, narrative 25-45
    if innovation > 20 and adoption < 25 and narrative < 45:
        return "innovation_trigger", f"Early innovation ({innovation:.0f}) with minimal adoption ({adoption:.0f}) and low media coverage ({narrative:.0f})"

    # Phase 2: Peak of Inflated Expectations (TIGHTENED: 20→45, OR→AND, 25→40)
    # Require BOTH high narrative AND high hype (not just one), with low adoption
    # This filters out Tavily noise and captures true media saturation
    if narrative > 45 and hype > 40 and adoption < 25:
        return "peak", f"Media saturation ({narrative:.0f}) with high hype ({hype:.0f}) but limited adoption ({adoption:.0f})"

    # Phase 5: Plateau of Productivity (RECALIBRATED v6 for realistic late-stage thresholds)
    # Check BEFORE Slope to capture mature technologies with high adoption
    # Relaxed narrative threshold to allow media coverage for commercialized tech
    if adoption > 30 and innovation > 18 and narrative < 75 and risk < 45:
        return "plateau", f"Mature market with high adoption ({adoption:.0f}), sustained innovation ({innovation:.0f}), and stable risk profile"

    # Phase 4: Slope of Enlightenment (ADJUSTED: 10→20 for narrative baseline shift)
    # Moderate adoption with balanced metrics (accounts for Tavily baseline)
    if adoption > 20 and innovation > 12 and narrative > 20 and hype < 50:
        return "slope", f"Growing adoption ({adoption:.0f}) with sustained innovation ({innovation:.0f}) and realistic expectations"

    # Phase 3: Trough of Disillusionment (RECALIBRATED v5 for sparse data + min_doc_count=5)
    # Two-tier detection: "dead" technologies vs underperforming technologies

    # Tier 1: Truly dead technologies (minimal activity across ALL layers)
    if innovation < 5 and adoption < 5 and narrative < 20:
        return "trough", f"Minimal activity across all layers: innovation ({innovation:.0f}), adoption ({adoption:.0f}), narrative ({narrative:.0f})"

    # Tier 2: Underperforming technologies (require 3+ weak signals, not just 2)
    # Adjusted thresholds for min_document_count=5 baseline
    low_count = sum([
        narrative < 35,     # Below Tavily baseline + minimal organic coverage
        adoption < 18,      # Significantly below moderate adoption
        innovation < 18,    # Minimal R&D activity
        hype < 28           # Low media buzz
    ])
    if low_count >= 3:      # Require 3+ criteria (not 2) to avoid over-classification
        return "trough", f"Multiple underperforming metrics (3+ low scores): narrative ({narrative:.0f}), adoption ({adoption:.0f}), innovation ({innovation:.0f})"

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

    # Confidence based on score clarity (numeric 0.0-1.0)
    # Higher spread = clearer signal differentiation = higher confidence
    spread = max([innovation, adoption, narrative]) - min([innovation, adoption, narrative])
    if spread > 30:
        confidence = 0.85  # High confidence: clear signal differentiation
    elif spread > 15:
        confidence = 0.65  # Medium confidence: moderate clarity
    else:
        confidence = 0.45  # Low confidence: conflicting/unclear signals

    return {
        "tech_id": tech_id,
        "hype_cycle_phase": phase,
        "phase_reasoning": reasoning,
        "phase_confidence": confidence,
    }
