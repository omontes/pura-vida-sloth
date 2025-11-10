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

from typing import Dict, Any, List, TypedDict, Optional
from langgraph.graph import StateGraph, END
from neo4j import AsyncDriver

# Import logger
from agents.shared.logger import AgentLogger, LogLevel

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

    # Configuration options
    enable_tavily: bool  # Enable Tavily real-time search (default: False, slow)
    _logger: AgentLogger  # Logger instance (internal, not serialized)

    # Layer scores (Agents 2-5)
    innovation_score: float
    innovation_reasoning: str
    innovation_metrics: dict
    innovation_confidence: str

    # Document counts for evidence (from innovation)
    patent_count: int
    paper_count: int
    github_count: int

    adoption_score: float
    adoption_reasoning: str
    adoption_metrics: dict
    adoption_confidence: str

    narrative_score: float
    narrative_reasoning: str
    narrative_metrics: dict
    narrative_confidence: str

    # Document counts for evidence
    news_count: int

    risk_score: float
    risk_reasoning: str
    risk_metrics: dict
    risk_confidence: str

    # Document counts for evidence
    sec_filing_count: int
    insider_transaction_count: int

    # Hype analysis (Agent 6)
    hype_score: float
    hype_reasoning: str
    layer_divergence: float
    hype_confidence: str

    # Phase detection (Agent 7)
    hype_cycle_phase: str
    phase_reasoning: str
    phase_confidence: float

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

    # Define agent wrapper functions with logging
    async def run_innovation(state: Dict[str, Any]) -> Dict[str, Any]:
        logger = state.get("_logger", AgentLogger(LogLevel.SILENT))
        logger.log_agent_start("innovation_scorer", state["tech_id"])
        result = await innovation_scorer_agent(state, driver)
        logger.log_agent_output("innovation_scorer", state["tech_id"], result)
        return result

    async def run_adoption(state: Dict[str, Any]) -> Dict[str, Any]:
        logger = state.get("_logger", AgentLogger(LogLevel.SILENT))
        logger.log_agent_start("adoption_scorer", state["tech_id"])
        result = await adoption_scorer_agent(state, driver)
        logger.log_agent_output("adoption_scorer", state["tech_id"], result)
        return result

    async def run_narrative(state: Dict[str, Any]) -> Dict[str, Any]:
        logger = state.get("_logger", AgentLogger(LogLevel.SILENT))
        logger.log_agent_start("narrative_scorer", state["tech_id"])
        result = await narrative_scorer_agent(state, driver)
        logger.log_agent_output("narrative_scorer", state["tech_id"], result)
        return result

    async def run_risk(state: Dict[str, Any]) -> Dict[str, Any]:
        logger = state.get("_logger", AgentLogger(LogLevel.SILENT))
        logger.log_agent_start("risk_scorer", state["tech_id"])
        result = await risk_scorer_agent(state, driver)
        logger.log_agent_output("risk_scorer", state["tech_id"], result)
        return result

    async def run_hype(state: Dict[str, Any]) -> Dict[str, Any]:
        logger = state.get("_logger", AgentLogger(LogLevel.SILENT))
        logger.log_agent_start("hype_scorer", state["tech_id"])
        result = await hype_scorer_agent(state)
        logger.log_agent_output("hype_scorer", state["tech_id"], result)
        return result

    async def run_phase(state: Dict[str, Any]) -> Dict[str, Any]:
        logger = state.get("_logger", AgentLogger(LogLevel.SILENT))
        logger.log_agent_start("phase_detector", state["tech_id"])
        result = await phase_detector_agent(state)
        logger.log_agent_output("phase_detector", state["tech_id"], result)
        return result

    async def run_analyst(state: Dict[str, Any]) -> Dict[str, Any]:
        logger = state.get("_logger", AgentLogger(LogLevel.SILENT))
        logger.log_agent_start("llm_analyst", state["tech_id"])
        result = await llm_analyst_agent(state)
        logger.log_agent_output("llm_analyst", state["tech_id"], result)
        return result

    async def run_ensemble(state: Dict[str, Any]) -> Dict[str, Any]:
        logger = state.get("_logger", AgentLogger(LogLevel.SILENT))
        logger.log_agent_start("ensemble", state["tech_id"])
        result = await ensemble_agent(state)
        logger.log_agent_output("ensemble", state["tech_id"], result)
        return result

    async def run_chart(state: Dict[str, Any]) -> Dict[str, Any]:
        logger = state.get("_logger", AgentLogger(LogLevel.SILENT))
        logger.log_agent_start("chart_generator", state["tech_id"])
        result = await chart_generator_agent(state)
        logger.log_agent_output("chart_generator", state["tech_id"], result)
        return result

    async def run_evidence(state: Dict[str, Any]) -> Dict[str, Any]:
        logger = state.get("_logger", AgentLogger(LogLevel.SILENT))
        logger.log_agent_start("evidence_compiler", state["tech_id"])
        result = await evidence_compiler_agent(state)
        logger.log_agent_output("evidence_compiler", state["tech_id"], result)
        return result

    async def run_validator(state: Dict[str, Any]) -> Dict[str, Any]:
        logger = state.get("_logger", AgentLogger(LogLevel.SILENT))
        logger.log_agent_start("validator", state["tech_id"])
        result = await output_validator_agent(state)
        logger.log_agent_output("validator", state["tech_id"], result)
        return result

    # Add nodes
    workflow.add_node("innovation_scorer", run_innovation)
    workflow.add_node("adoption_scorer", run_adoption)
    workflow.add_node("narrative_scorer", run_narrative)
    workflow.add_node("risk_scorer", run_risk)
    workflow.add_node("hype_scorer", run_hype)
    workflow.add_node("phase_detector", run_phase)
    workflow.add_node("llm_analyst", run_analyst)
    workflow.add_node("ensemble", run_ensemble)
    workflow.add_node("chart_generator", run_chart)
    workflow.add_node("evidence_compiler", run_evidence)
    workflow.add_node("validator", run_validator)

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
    tech_name: str = None,
    logger: Optional[AgentLogger] = None,
    enable_tavily: bool = True
) -> Dict[str, Any]:
    """
    Analyze single technology through full pipeline.

    Args:
        driver: Neo4j driver
        tech_id: Technology ID
        tech_name: Human-readable name (optional)
        logger: Optional logger for verbose output
        enable_tavily: Enable Tavily real-time search (default: True)

    Returns:
        Complete analysis with all scores, positioning, and evidence
    """
    # Create default silent logger if not provided
    if logger is None:
        logger = AgentLogger(level=LogLevel.SILENT)

    graph = build_hype_cycle_graph(driver)

    initial_state = {
        "tech_id": tech_id,
        "tech_name": tech_name or tech_id.replace("_", " ").title(),
        "enable_tavily": enable_tavily,
        "_logger": logger,  # Pass logger via state
    }

    result = await graph.ainvoke(initial_state)

    # Log technology completion
    logger.log_technology_complete(tech_id, result)

    return result


async def analyze_multiple_technologies(
    driver: AsyncDriver,
    tech_ids: List[str],
    max_concurrent: int = 20,
    logger: Optional[AgentLogger] = None,
    enable_tavily: bool = True
) -> List[Dict[str, Any]]:
    """
    Analyze multiple technologies in parallel with concurrency limit.

    Args:
        driver: Neo4j driver
        tech_ids: List of technology IDs
        max_concurrent: Maximum number of concurrent analyses (default: 20)
                       Prevents Neo4j connection pool exhaustion
        logger: Optional logger for verbose output
        enable_tavily: Enable Tavily real-time search (default: True)

    Returns:
        List of complete analyses
    """
    import asyncio

    # Create default silent logger if not provided
    if logger is None:
        logger = AgentLogger(level=LogLevel.SILENT)

    # Semaphore to limit concurrent database connections
    semaphore = asyncio.Semaphore(max_concurrent)

    async def analyze_with_limit(tech_id: str) -> Dict[str, Any]:
        """Analyze single technology with semaphore."""
        async with semaphore:
            return await analyze_single_technology(
                driver, tech_id, logger=logger, enable_tavily=enable_tavily
            )

    if logger.level.value >= LogLevel.NORMAL.value:
        print(f"\n[ORCHESTRATOR] Analyzing {len(tech_ids)} technologies (max {max_concurrent} concurrent)")

    tasks = [analyze_with_limit(tech_id) for tech_id in tech_ids]
    results = await asyncio.gather(*tasks)
    return results


async def generate_hype_cycle_chart(
    driver: AsyncDriver,
    limit: int = None,
    industry_filter: str = None,
    logger: Optional[AgentLogger] = None,
    enable_tavily: bool = True,
    community_version: str = "v1",
    min_document_count: int = 5
) -> Dict[str, Any]:
    """
    Generate complete hype cycle chart for all technologies.

    Args:
        driver: Neo4j driver
        limit: Maximum technologies to analyze
        industry_filter: Optional industry filter
        logger: Optional logger for verbose output
        enable_tavily: Enable Tavily real-time search (default: True)
        community_version: Community version to use (v0, v1, v2)
        min_document_count: Minimum documents required per technology

    Returns:
        Complete chart JSON ready for D3.js visualization
    """
    # Create default silent logger if not provided
    if logger is None:
        logger = AgentLogger(level=LogLevel.SILENT)

    # Log pipeline start
    logger.log_pipeline_start(
        tech_count=limit or "all",
        enable_tavily=enable_tavily,
        community_version=community_version,
        min_document_count=min_document_count
    )

    # Step 1: Discover technologies using ADAPTIVE community-based stratified sampling
    from agents.agent_01_tech_discovery.agent import discover_technologies_with_community_sampling

    tech_discovery = await discover_technologies_with_community_sampling(
        driver=driver,
        version=community_version,
        total_limit=limit,
        early_pct=0.20,  # Target 20% from early-stage communities (Innovation Trigger)
        mid_pct=0.40,    # Target 40% from mid-stage communities (Slope)
        late_pct=0.20,   # Target 20% from late-stage communities (Plateau)
        hype_pct=0.20,   # Target 20% from hype-stage communities (Peak)
        min_document_count=min_document_count
    )

    tech_ids = [t.id for t in tech_discovery.technologies]

    if logger.level.value >= LogLevel.NORMAL.value:
        print(f"Analyzing {len(tech_ids)} technologies...")

    # Step 2: Analyze all technologies
    import time
    start_time = time.time()

    results = await analyze_multiple_technologies(
        driver, tech_ids, logger=logger, enable_tavily=enable_tavily
    )

    duration = time.time() - start_time

    # Step 3: Generate chart JSON
    from agents.agent_10_chart.agent import generate_full_chart

    chart_data_list = [r.get("chart_data", {}) for r in results if r.get("validation_status") == "valid"]

    final_chart = generate_full_chart(chart_data_list)

    # Log pipeline completion
    logger.log_pipeline_complete(tech_count=len(tech_ids), duration_seconds=duration)

    return final_chart
