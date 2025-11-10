"""Agent 12: Output Validator - Validates final output structure."""

from typing import Dict, Any

def validate_technology_output(state: Dict[str, Any]) -> tuple[bool, list]:
    """Validate that all required fields are present and valid."""
    errors = []

    # Required fields
    required_fields = [
        "tech_id", "innovation_score", "adoption_score", "narrative_score",
        "risk_score", "hype_score", "hype_cycle_phase", "x_position", "y_position",
        "executive_summary", "key_insight", "recommendation"
    ]

    for field in required_fields:
        if field not in state or state[field] is None:
            errors.append(f"Missing required field: {field}")

    # Validate score ranges
    score_fields = ["innovation_score", "adoption_score", "narrative_score", "risk_score", "hype_score"]
    for field in score_fields:
        if field in state:
            score = state[field]
            if not isinstance(score, (int, float)) or not (0 <= score <= 100):
                errors.append(f"Invalid {field}: {score} (must be 0-100)")

    # Validate positions
    if "x_position" in state:
        x = state["x_position"]
        if not isinstance(x, (int, float)) or not (0 <= x <= 100):
            errors.append(f"Invalid x_position: {x}")

    if "y_position" in state:
        y = state["y_position"]
        if not isinstance(y, (int, float)) or not (0 <= y <= 100):
            errors.append(f"Invalid y_position: {y}")

    # Validate phase
    valid_phases = ["innovation_trigger", "peak", "trough", "slope", "plateau"]
    if "hype_cycle_phase" in state and state["hype_cycle_phase"] not in valid_phases:
        errors.append(f"Invalid phase: {state['hype_cycle_phase']}")

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
