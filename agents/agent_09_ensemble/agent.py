"""Agent 9: Ensemble - Calculates final X/Y positioning on hype cycle."""

from typing import Dict, Any
from pydantic import BaseModel, Field
from agents.shared.constants import LAYER_WEIGHTS

class EnsembleOutput(BaseModel):
    tech_id: str
    x_position: float = Field(description="X-axis: maturity (0-100)", ge=0, le=100)
    y_position: float = Field(description="Y-axis: expectations (0-100)", ge=0, le=100)
    weighted_score: float = Field(description="Overall weighted score")
    positioning: str = Field(description="Chart quadrant/description")

def calculate_hype_cycle_position(
    innovation: float,
    adoption: float,
    narrative: float,
    risk: float,
    phase: str
) -> tuple[float, float, float, str]:
    """
    Calculate X/Y position on hype cycle chart.

    X-axis (Maturity/Time):
    - Driven by Innovation + Adoption (real progress)
    - innovation_trigger: 0-20
    - peak: 20-40
    - trough: 40-60
    - slope: 60-80
    - plateau: 80-100

    Y-axis (Expectations/Visibility):
    - Driven by Narrative + Hype
    - Low: 0-30 (trough)
    - Medium: 30-70 (trigger, slope, plateau)
    - High: 70-100 (peak)
    """

    # Calculate weighted overall score
    weighted_score = (
        innovation * LAYER_WEIGHTS["innovation"] +
        adoption * LAYER_WEIGHTS["adoption"] +
        narrative * LAYER_WEIGHTS["narrative"] +
        (100 - risk) * LAYER_WEIGHTS["risk"]  # Invert risk (lower risk = better)
    )

    # X-axis: Maturity (innovation + adoption weighted)
    maturity = (innovation * 0.4 + adoption * 0.6)  # Adoption weighs more for maturity

    # Y-axis: Expectations (narrative dominates)
    expectations = narrative * 0.7 + (innovation * 0.3)

    # Adjust based on detected phase
    phase_adjustments = {
        "innovation_trigger": (15, 40),
        "peak": (35, 85),
        "trough": (55, 25),
        "slope": (70, 55),
        "plateau": (85, 60),
    }

    if phase in phase_adjustments:
        target_x, target_y = phase_adjustments[phase]
        # Blend calculated position with phase target (70% calculated, 30% phase)
        x_position = maturity * 0.7 + target_x * 0.3
        y_position = expectations * 0.7 + target_y * 0.3
    else:
        x_position = maturity
        y_position = expectations

    # Determine positioning description
    if y_position > 70:
        positioning = "Peak of Inflated Expectations"
    elif y_position < 35:
        positioning = "Trough of Disillusionment"
    elif x_position > 75:
        positioning = "Plateau of Productivity"
    elif x_position > 55:
        positioning = "Slope of Enlightenment"
    else:
        positioning = "Innovation Trigger"

    return x_position, y_position, weighted_score, positioning

async def ensemble_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    tech_id = state["tech_id"]
    innovation = state.get("innovation_score", 50.0)
    adoption = state.get("adoption_score", 50.0)
    narrative = state.get("narrative_score", 50.0)
    risk = state.get("risk_score", 50.0)
    phase = state.get("hype_cycle_phase", "slope")

    x_pos, y_pos, weighted, positioning = calculate_hype_cycle_position(
        innovation, adoption, narrative, risk, phase
    )

    return {
        "tech_id": tech_id,
        "x_position": round(x_pos, 2),
        "y_position": round(y_pos, 2),
        "weighted_score": round(weighted, 2),
        "chart_positioning": positioning,
    }
