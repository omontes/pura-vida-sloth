"""Agent 9: Ensemble - Calculates chart positioning per HYPE_CYCLE.md spec."""

from typing import Dict, Any
from pydantic import BaseModel, Field
from agents.shared.constants import LAYER_WEIGHTS
from agents.shared.hype_cycle_spec import (
    PHASE_NAMES,
    calculate_chart_x,
    determine_phase_position,
)

class EnsembleOutput(BaseModel):
    tech_id: str
    chart_x: float = Field(description="X-axis: maturity (0.0-5.0)", ge=0, le=5.0)
    chart_y: float = Field(description="Y-axis: expectations (0-100)", ge=0, le=100)
    phase_position: str = Field(description="Position in phase: early|mid|late")
    weighted_score: float = Field(description="Overall weighted score")

def calculate_hype_cycle_position(
    innovation: float,
    adoption: float,
    narrative: float,
    risk: float,
    phase_code: str
) -> tuple[float, float, str, float]:
    """
    Calculate chart position on hype cycle per HYPE_CYCLE.md spec.

    Args:
        innovation: Innovation score (0-100)
        adoption: Adoption score (0-100)
        narrative: Narrative score (0-100)
        risk: Risk score (0-100)
        phase_code: Phase code (innovation_trigger, peak, trough, slope, plateau)

    Returns:
        (chart_x, chart_y, phase_position, weighted_score)

    Chart X-axis (0.0 to 5.0):
    - Innovation Trigger: 0.0 - 0.7
    - Peak of Inflated Expectations: 0.7 - 1.4
    - Trough of Disillusionment: 1.4 - 2.7
    - Slope of Enlightenment: 2.7 - 4.2
    - Plateau of Productivity: 4.2 - 5.0

    Chart Y-axis (0-100): Expectations/Visibility
    - Driven by narrative + hype signals
    """
    # Convert phase code to display name
    phase_display = PHASE_NAMES.get(phase_code, "Slope of Enlightenment")

    # Calculate weighted overall score
    weighted_score = (
        innovation * LAYER_WEIGHTS["innovation"] +
        adoption * LAYER_WEIGHTS["adoption"] +
        narrative * LAYER_WEIGHTS["narrative"] +
        (100 - risk) * LAYER_WEIGHTS["risk"]  # Invert risk (lower risk = better)
    )

    # Determine position within phase (early/mid/late)
    phase_position = determine_phase_position(
        innovation, adoption, narrative, risk, phase_display
    )

    # Calculate chart_x using spec formula
    chart_x = calculate_chart_x(phase_display, phase_position)

    # Calculate chart_y: Expectations (narrative dominates, 0-100 scale)
    # Higher narrative = higher expectations
    chart_y = narrative * 0.7 + (innovation * 0.2) + (adoption * 0.1)

    # Apply phase-specific Y adjustments for realism
    phase_y_adjustments = {
        "Innovation Trigger": 0.8,        # Lower expectations, early tech
        "Peak of Inflated Expectations": 1.3,  # Inflated expectations
        "Trough of Disillusionment": 0.5,      # Crashed expectations
        "Slope of Enlightenment": 0.9,         # Recovering expectations
        "Plateau of Productivity": 0.85,       # Stable, realistic expectations
    }

    y_multiplier = phase_y_adjustments.get(phase_display, 1.0)
    chart_y = min(100, chart_y * y_multiplier)

    return chart_x, chart_y, phase_position, weighted_score

async def ensemble_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    tech_id = state["tech_id"]
    innovation = state.get("innovation_score", 50.0)
    adoption = state.get("adoption_score", 50.0)
    narrative = state.get("narrative_score", 50.0)
    risk = state.get("risk_score", 50.0)
    phase_code = state.get("hype_cycle_phase", "slope")

    chart_x, chart_y, phase_position, weighted = calculate_hype_cycle_position(
        innovation, adoption, narrative, risk, phase_code
    )

    # Convert phase code to display name for output
    phase_display = PHASE_NAMES.get(phase_code, "Slope of Enlightenment")

    return {
        "tech_id": tech_id,
        "chart_x": round(chart_x, 3),
        "chart_y": round(chart_y, 2),
        "phase_position": phase_position,
        "hype_cycle_phase_display": phase_display,  # Display name for output
        "weighted_score": round(weighted, 2),
    }
