"""
Hype Cycle Chart Specification Constants

Defines the exact phase names, ranges, and calculations per docs/HYPE_CYCLE.md
"""

from typing import Dict, Tuple

# Phase name mappings: internal code name -> display name
PHASE_NAMES = {
    "innovation_trigger": "Innovation Trigger",
    "peak": "Peak of Inflated Expectations",
    "trough": "Trough of Disillusionment",
    "slope": "Slope of Enlightenment",
    "plateau": "Plateau of Productivity",
}

# Reverse mapping: display name -> internal code name
PHASE_CODES = {v: k for k, v in PHASE_NAMES.items()}

# Chart X-axis ranges for each phase (0.0 to 5.0 scale)
# Format: (min_x, max_x)
PHASE_RANGES: Dict[str, Tuple[float, float]] = {
    "Innovation Trigger": (0.0, 0.7),
    "Peak of Inflated Expectations": (0.7, 1.4),
    "Trough of Disillusionment": (1.4, 2.7),
    "Slope of Enlightenment": (2.7, 4.2),
    "Plateau of Productivity": (4.2, 5.0),
}

# Phase position multipliers
PHASE_POSITION_MULTIPLIERS = {
    "early": 0.25,
    "mid": 0.50,
    "late": 0.75,
}


def calculate_chart_x(phase: str, phase_position: str) -> float:
    """
    Calculate chart_x value based on phase and position within phase.

    Args:
        phase: Display phase name (e.g., "Innovation Trigger")
        phase_position: Position within phase ("early", "mid", "late")

    Returns:
        chart_x value (0.0 to 5.0)

    Example:
        >>> calculate_chart_x("Innovation Trigger", "mid")
        0.35
        >>> calculate_chart_x("Slope of Enlightenment", "late")
        3.825
    """
    if phase not in PHASE_RANGES:
        raise ValueError(f"Invalid phase: {phase}")

    if phase_position not in PHASE_POSITION_MULTIPLIERS:
        raise ValueError(f"Invalid phase_position: {phase_position}")

    min_x, max_x = PHASE_RANGES[phase]
    width = max_x - min_x
    multiplier = PHASE_POSITION_MULTIPLIERS[phase_position]

    return min_x + (width * multiplier)


def determine_phase_position(
    innovation: float,
    adoption: float,
    narrative: float,
    risk: float,
    phase: str
) -> str:
    """
    Determine position within phase based on layer scores.

    Higher scores indicate later position in phase.

    Args:
        innovation: Innovation score (0-100)
        adoption: Adoption score (0-100)
        narrative: Narrative score (0-100)
        risk: Risk score (0-100)
        phase: Display phase name

    Returns:
        "early", "mid", or "late"
    """
    # Calculate weighted maturity score
    maturity = (innovation * 0.3 + adoption * 0.4 + (100 - risk) * 0.3)

    # Determine position based on maturity
    if maturity < 40:
        return "early"
    elif maturity < 70:
        return "mid"
    else:
        return "late"


def validate_chart_x(phase: str, chart_x: float, tolerance: float = 0.05) -> Tuple[bool, str]:
    """
    Validate that chart_x is within correct range for phase.

    Args:
        phase: Display phase name
        chart_x: Chart X coordinate
        tolerance: Floating point tolerance for validation

    Returns:
        (is_valid, error_message)
    """
    if phase not in PHASE_RANGES:
        return False, f"Invalid phase: {phase}"

    min_x, max_x = PHASE_RANGES[phase]

    # Allow slight tolerance for floating point errors
    if chart_x < min_x - tolerance or chart_x > max_x + tolerance:
        return False, f"chart_x {chart_x:.3f} not in range [{min_x}, {max_x}] for {phase}"

    return True, ""


# Quick reference table for chart_x values
CHART_X_REFERENCE = {
    "Innovation Trigger": {
        "early": 0.175,
        "mid": 0.35,
        "late": 0.525,
    },
    "Peak of Inflated Expectations": {
        "early": 0.875,
        "mid": 1.05,
        "late": 1.225,
    },
    "Trough of Disillusionment": {
        "early": 1.725,
        "mid": 2.05,
        "late": 2.375,
    },
    "Slope of Enlightenment": {
        "early": 3.075,
        "mid": 3.45,
        "late": 3.825,
    },
    "Plateau of Productivity": {
        "early": 4.4,
        "mid": 4.6,
        "late": 4.8,
    },
}
