"""Agent 12: Output Validator - Validates final output per HYPE_CYCLE.md spec."""

from typing import Dict, Any
from agents.shared.hype_cycle_spec import validate_chart_x, PHASE_NAMES

def validate_technology_output(state: Dict[str, Any]) -> tuple[bool, list]:
    """Validate that all required fields are present and valid per HYPE_CYCLE.md."""
    errors = []

    # Required fields
    required_fields = [
        "tech_id", "innovation_score", "adoption_score", "narrative_score",
        "risk_score", "hype_score", "hype_cycle_phase", "chart_x", "phase_position",
        "executive_summary", "key_insight"
    ]

    for field in required_fields:
        if field not in state or state[field] is None:
            errors.append(f"Missing required field: {field}")

    # Validate score ranges (0-100)
    score_fields = ["innovation_score", "adoption_score", "narrative_score", "risk_score", "hype_score"]
    for field in score_fields:
        if field in state:
            score = state[field]
            if not isinstance(score, (int, float)) or not (0 <= score <= 100):
                errors.append(f"Invalid {field}: {score} (must be 0-100)")

    # Validate chart_x (0.0-5.0 scale)
    if "chart_x" in state:
        chart_x = state["chart_x"]
        if not isinstance(chart_x, (int, float)) or not (0.0 <= chart_x <= 5.0):
            errors.append(f"Invalid chart_x: {chart_x} (must be 0.0-5.0)")

        # Validate chart_x matches phase range
        phase_display = state.get("hype_cycle_phase_display")
        if phase_display:
            is_valid, error_msg = validate_chart_x(phase_display, chart_x)
            if not is_valid:
                errors.append(error_msg)

    # Validate phase_position
    if "phase_position" in state:
        phase_pos = state["phase_position"]
        if phase_pos not in ["early", "mid", "late"]:
            errors.append(f"Invalid phase_position: {phase_pos} (must be early/mid/late)")

    # Validate phase_confidence (0.0-1.0 float)
    if "phase_confidence" in state:
        phase_conf = state["phase_confidence"]
        if not isinstance(phase_conf, (int, float)):
            errors.append(f"Invalid phase_confidence type: {type(phase_conf).__name__} (must be numeric float)")
        elif not (0.0 <= phase_conf <= 1.0):
            errors.append(f"Invalid phase_confidence: {phase_conf} (must be 0.0-1.0)")

    # Validate phase name (accept both code and display)
    if "hype_cycle_phase" in state:
        phase_code = state["hype_cycle_phase"]
        valid_phase_codes = ["innovation_trigger", "peak", "trough", "slope", "plateau"]
        if phase_code not in valid_phase_codes:
            errors.append(f"Invalid phase code: {phase_code}")

    is_valid = len(errors) == 0
    return is_valid, errors

async def output_validator_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Validate final output and return status."""
    is_valid, errors = validate_technology_output(state)

    return {
        "tech_id": state["tech_id"],
        "validation_status": "valid" if is_valid else "invalid",
        "validation_errors": errors,
    }
