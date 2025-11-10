"""Agent 10: Chart Generator - Formats data for D3.js hype cycle visualization."""

from typing import Dict, Any, List

def format_technology_for_chart(state: Dict[str, Any]) -> Dict[str, Any]:
    """Format single technology for chart JSON."""
    return {
        "id": state["tech_id"],
        "name": state.get("tech_name", state["tech_id"].replace("_", " ").title()),
        "x": state.get("x_position", 50),
        "y": state.get("y_position", 50),
        "phase": state.get("hype_cycle_phase", "unknown"),
        "scores": {
            "innovation": state.get("innovation_score", 0),
            "adoption": state.get("adoption_score", 0),
            "narrative": state.get("narrative_score", 0),
            "risk": state.get("risk_score", 0),
            "hype": state.get("hype_score", 0),
            "weighted": state.get("weighted_score", 0),
        },
        "summary": state.get("executive_summary", ""),
        "insight": state.get("key_insight", ""),
        "recommendation": state.get("recommendation", ""),
    }

async def chart_generator_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate chart-ready data structure."""
    chart_data = format_technology_for_chart(state)

    return {
        "tech_id": state["tech_id"],
        "chart_data": chart_data,
    }

def generate_full_chart(technologies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate complete hype cycle chart JSON for multiple technologies."""
    return {
        "chart_type": "hype_cycle",
        "generated_at": "2025-01-01T00:00:00Z",
        "technologies": technologies,
        "metadata": {
            "total_count": len(technologies),
            "phases": {
                "innovation_trigger": len([t for t in technologies if t.get("phase") == "innovation_trigger"]),
                "peak": len([t for t in technologies if t.get("phase") == "peak"]),
                "trough": len([t for t in technologies if t.get("phase") == "trough"]),
                "slope": len([t for t in technologies if t.get("phase") == "slope"]),
                "plateau": len([t for t in technologies if t.get("phase") == "plateau"]),
            }
        }
    }
