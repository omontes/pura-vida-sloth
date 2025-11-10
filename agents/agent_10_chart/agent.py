"""Agent 10: Chart Generator - Formats data per HYPE_CYCLE.md spec for D3.js."""

from typing import Dict, Any, List
from datetime import datetime

def format_technology_for_chart(state: Dict[str, Any]) -> Dict[str, Any]:
    """Format single technology for chart JSON per HYPE_CYCLE.md spec."""

    # Use display phase name (proper capitalization)
    phase_display = state.get("hype_cycle_phase_display", state.get("hype_cycle_phase", "Slope of Enlightenment"))

    return {
        "id": state["tech_id"],
        "name": state.get("tech_name", state["tech_id"].replace("_", " ").title()),
        "domain": state.get("domain", "Technology"),
        "phase": phase_display,  # Use display name: "Innovation Trigger", etc.
        "phase_position": state.get("phase_position", "mid"),
        "phase_confidence": state.get("phase_confidence", "medium"),
        "chart_x": state.get("chart_x", 2.7),  # 0.0-5.0 scale
        "scores": {
            "innovation": state.get("innovation_score", 0),
            "adoption": state.get("adoption_score", 0),
            "narrative": state.get("narrative_score", 0),
            "risk": state.get("risk_score", 0),
            "hype": state.get("hype_score", 0),
        },
        "summary": state.get("executive_summary", ""),
        "insight": state.get("key_insight", ""),
        "evidence_counts": {
            "patents": state.get("patent_count", 0),
            "papers": state.get("paper_count", 0),
            "github": state.get("github_count", 0),
            "news": state.get("news_count", 0),
            "sec_filings": state.get("sec_filing_count", 0),
            "insider_transactions": state.get("insider_transaction_count", 0),
        }
    }

async def chart_generator_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate chart-ready data structure."""
    chart_data = format_technology_for_chart(state)

    return {
        "tech_id": state["tech_id"],
        "chart_data": chart_data,
    }

def generate_full_chart(technologies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate complete hype cycle chart JSON per HYPE_CYCLE.md spec.

    Args:
        technologies: List of formatted technology dicts

    Returns:
        Complete chart JSON with proper phase names and metadata
    """
    # Count technologies by phase (using display names)
    phase_counts = {
        "innovation_trigger": 0,
        "peak": 0,
        "trough": 0,
        "slope": 0,
        "plateau": 0,
    }

    # Map display names back to counts
    phase_name_to_key = {
        "Innovation Trigger": "innovation_trigger",
        "Peak of Inflated Expectations": "peak",
        "Trough of Disillusionment": "trough",
        "Slope of Enlightenment": "slope",
        "Plateau of Productivity": "plateau",
    }

    for tech in technologies:
        phase_key = phase_name_to_key.get(tech.get("phase", "Slope of Enlightenment"), "slope")
        phase_counts[phase_key] += 1

    return {
        "industry": "Emerging Technologies",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "metadata": {
            "date_from": "2020-01-01",
            "date_to": datetime.utcnow().strftime("%Y-%m-%d"),
            "total_documents": "N/A",
            "total_count": len(technologies),
            "phases": phase_counts
        },
        "technologies": technologies
    }
