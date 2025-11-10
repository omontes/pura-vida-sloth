"""Agent 11: Evidence Compiler - Collects supporting evidence for scores."""

from typing import Dict, Any, List

async def evidence_compiler_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Compile evidence from all scoring layers."""

    evidence = {
        "tech_id": state["tech_id"],
        "innovation_evidence": {
            "metrics": state.get("innovation_metrics", {}),
            "reasoning": state.get("innovation_reasoning", ""),
        },
        "adoption_evidence": {
            "metrics": state.get("adoption_metrics", {}),
            "reasoning": state.get("adoption_reasoning", ""),
        },
        "narrative_evidence": {
            "metrics": state.get("narrative_metrics", {}),
            "reasoning": state.get("narrative_reasoning", ""),
        },
        "risk_evidence": {
            "metrics": state.get("risk_metrics", {}),
            "reasoning": state.get("risk_reasoning", ""),
        },
        "hype_analysis": {
            "score": state.get("hype_score", 0),
            "reasoning": state.get("hype_reasoning", ""),
            "divergence": state.get("layer_divergence", 0),
        },
        "phase_analysis": {
            "phase": state.get("hype_cycle_phase", "unknown"),
            "reasoning": state.get("phase_reasoning", ""),
        },
    }

    return {
        "tech_id": state["tech_id"],
        "evidence": evidence,
    }
