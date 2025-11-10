"""
LangGraph Orchestrator - Coordinates 12-agent hype cycle analysis pipeline.

Pipeline Flow:
1. Tech Discovery (Agent 1) → Fan out to all technologies
2. Layer Scoring (Agents 2-5) → Parallel scoring per technology
3. Hype Analysis (Agent 6) → Calculate hype from layer divergence
4. Phase Detection (Agent 7) → Determine hype cycle phase
5. LLM Analysis (Agent 8) → Generate executive summary
6. Ensemble (Agent 9) → Calculate final X/Y positioning
7. Chart Generation (Agent 10) → Format for visualization
8. Evidence Compilation (Agent 11) → Collect supporting data
9. Validation (Agent 12) → Verify output structure
"""

from typing import Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, END
from neo4j import AsyncDriver

# Import all agents
from agents.agent_01_tech_discovery.agent import tech_discovery_agent
from agents.agent_02_innovation.agent import innovation_scorer_agent
from agents.agent_03_adoption.agent import adoption_scorer_agent
from agents.agent_04_narrative.agent import narrative_scorer_agent
from agents.agent_05_risk.agent import risk_scorer_agent
from agents.agent_06_hype.agent import hype_scorer_agent
from agents.agent_07_phase.agent import phase_detector_agent
from agents.agent_08_analyst.agent import llm_analyst_agent
from agents.agent_09_ensemble.agent import ensemble_agent
from agents.agent_10_chart.agent import chart_generator_agent
from agents.agent_11_evidence.agent import evidence_compiler_agent
from agents.agent_12_validator.agent import output_validator_agent


# State schema
class HypeCycleState(TypedDict, total=False):
    """State for single technology analysis."""
    # Tech identification
    tech_id: str
    tech_name: str

    # Layer scores (Agents 2-5)
    innovation_score: float
    innovation_reasoning: str
    innovation_metrics: dict
    innovation_confidence: str

    adoption_score: float
    adoption_reasoning: str
    adoption_metrics: dict
    adoption_confidence: str

    narrative_score: float
    narrative_reasoning: str
    narrative_metrics: dict
    narrative_confidence: str

    risk_score: float
    risk_reasoning: str
    risk_metrics: dict
    risk_confidence: str

    # Hype analysis (Agent 6)
    hype_score: float
    hype_reasoning: str
    layer_divergence: float
    hype_confidence: str

    # Phase detection (Agent 7)
    hype_cycle_phase: str
    phase_reasoning: str
    phase_confidence: str

    # LLM analysis (Agent 8)
    executive_summary: str
    key_insight: str
    recommendation: str

    # Ensemble positioning (Agent 9)
    chart_x: float  # 0.0-5.0 scale per HYPE_CYCLE.md
    chart_y: float  # 0-100 expectations
    phase_position: str  # "early", "mid", "late"
    hype_cycle_phase_display: str  # Display name: "Innovation Trigger", etc.
    weighted_score: float

    # Legacy fields (deprecated but kept for compatibility)
    x_position: float
    y_position: float
    chart_positioning: str

    # Chart data (Agent 10)
    chart_data: dict

    # Evidence (Agent 11)
    evidence: dict

    # Validation (Agent 12)
    validation_status: str
    validation_errors: list


def build_hype_cycle_graph(driver: AsyncDriver) -> StateGraph:
    """
    Build LangGraph for hype cycle analysis.

    Sequential flow for single technology:
    Tech Discovery → Layer Scoring (parallel) → Hype → Phase → Analyst → Ensemble → Chart → Evidence → Validation
    """

    # Create graph
    workflow = StateGraph(HypeCycleState)

    # Define agent wrapper functions
    async def run_innovation(state: Dict[str, Any]) -> Dict[str, Any]:
        return await innovation_scorer_agent(state, driver)

    async def run_adoption(state: Dict[str, Any]) -> Dict[str, Any]:
        return await adoption_scorer_agent(state, driver)

    async def run_narrative(state: Dict[str, Any]) -> Dict[str, Any]:
        return await narrative_scorer_agent(state, driver)

    async def run_risk(state: Dict[str, Any]) -> Dict[str, Any]:
        return await risk_scorer_agent(state, driver)

    # Add nodes
    workflow.add_node("innovation_scorer", run_innovation)
    workflow.add_node("adoption_scorer", run_adoption)
    workflow.add_node("narrative_scorer", run_narrative)
    workflow.add_node("risk_scorer", run_risk)
    workflow.add_node("hype_scorer", hype_scorer_agent)
    workflow.add_node("phase_detector", phase_detector_agent)
    workflow.add_node("llm_analyst", llm_analyst_agent)
    workflow.add_node("ensemble", ensemble_agent)
    workflow.add_node("chart_generator", chart_generator_agent)
    workflow.add_node("evidence_compiler", evidence_compiler_agent)
    workflow.add_node("validator", output_validator_agent)

    # Define edges (sequential flow)
    workflow.set_entry_point("innovation_scorer")
    workflow.add_edge("innovation_scorer", "adoption_scorer")
    workflow.add_edge("adoption_scorer", "narrative_scorer")
    workflow.add_edge("narrative_scorer", "risk_scorer")
    workflow.add_edge("risk_scorer", "hype_scorer")
    workflow.add_edge("hype_scorer", "phase_detector")
    workflow.add_edge("phase_detector", "llm_analyst")
    workflow.add_edge("llm_analyst", "ensemble")
    workflow.add_edge("ensemble", "chart_generator")
    workflow.add_edge("chart_generator", "evidence_compiler")
    workflow.add_edge("evidence_compiler", "validator")
    workflow.add_edge("validator", END)

    return workflow.compile()


async def analyze_single_technology(
    driver: AsyncDriver,
    tech_id: str,
    tech_name: str = None
) -> Dict[str, Any]:
    """
    Analyze single technology through full pipeline.

    Args:
        driver: Neo4j driver
        tech_id: Technology ID
        tech_name: Human-readable name (optional)

    Returns:
        Complete analysis with all scores, positioning, and evidence
    """
    graph = build_hype_cycle_graph(driver)

    initial_state = {
        "tech_id": tech_id,
        "tech_name": tech_name or tech_id.replace("_", " ").title(),
    }

    result = await graph.ainvoke(initial_state)
    return result


async def analyze_multiple_technologies(
    driver: AsyncDriver,
    tech_ids: List[str]
) -> List[Dict[str, Any]]:
    """
    Analyze multiple technologies in parallel.

    Args:
        driver: Neo4j driver
        tech_ids: List of technology IDs

    Returns:
        List of complete analyses
    """
    import asyncio

    tasks = [
        analyze_single_technology(driver, tech_id)
        for tech_id in tech_ids
    ]

    results = await asyncio.gather(*tasks)
    return results


async def generate_hype_cycle_chart(
    driver: AsyncDriver,
    limit: int = None,
    industry_filter: str = None
) -> Dict[str, Any]:
    """
    Generate complete hype cycle chart for all technologies.

    Args:
        driver: Neo4j driver
        limit: Maximum technologies to analyze
        industry_filter: Optional industry filter

    Returns:
        Complete chart JSON ready for D3.js visualization
    """
    # Step 1: Discover technologies using ADAPTIVE community-based stratified sampling
    from agents.agent_01_tech_discovery.agent import discover_technologies_with_community_sampling

    tech_discovery = await discover_technologies_with_community_sampling(
        driver=driver,
        version="v1",
        total_limit=limit,
        early_pct=0.20,  # Target 20% from early-stage communities (Innovation Trigger)
        mid_pct=0.40,    # Target 40% from mid-stage communities (Slope)
        late_pct=0.20,   # Target 20% from late-stage communities (Plateau)
        hype_pct=0.20,   # Target 20% from hype-stage communities (Peak)
        min_document_count=1
    )

    tech_ids = [t.id for t in tech_discovery.technologies]

    print(f"Analyzing {len(tech_ids)} technologies...")

    # Step 2: Analyze all technologies
    results = await analyze_multiple_technologies(driver, tech_ids)

    # Step 3: Generate chart JSON
    from agents.agent_10_chart.agent import generate_full_chart

    chart_data_list = [r.get("chart_data", {}) for r in results if r.get("validation_status") == "valid"]

    final_chart = generate_full_chart(chart_data_list)

    return final_chart
