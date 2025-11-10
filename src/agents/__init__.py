"""
Multi-Agent Hype Cycle Analysis System (Phases 4+5)

This package contains the LangGraph-based multi-agent orchestrator and all 12 specialized agents
that perform technology lifecycle analysis using 4-layer intelligence framework.

Agents:
- agent_01_tech_discovery: Discovers technologies from graph communities
- agent_02_innovation: Scores Layer 1 (patents, papers, GitHub)
- agent_03_adoption: Scores Layer 2 (contracts, revenue, partnerships)
- agent_04_narrative: Scores Layer 4 (media coverage, sentiment)
- agent_05_risk: Scores Layer 3 (SEC filings, insider trading)
- agent_06_hype: Calculates overall hype score from 4 layers
- agent_07_phase: Detects Gartner Hype Cycle phase
- agent_08_analyst: Generates executive summary narrative
- agent_09_ensemble: Calculates chart positioning (X/Y coordinates)
- agent_10_chart: Generates final chart data structure
- agent_11_evidence: Compiles supporting evidence documents
- agent_12_validator: Validates output quality

Orchestrator:
- langgraph_orchestrator: LangGraph state machine coordinating all agents

Shared:
- shared.queries: Neo4j query modules for each agent
- shared.openai_client: Structured LLM client
- shared.logger: Verbose logging system
- shared.constants: Shared configuration
"""

__version__ = "0.1.0"

# Lazy imports to avoid circular dependencies
__all__ = [
    "langgraph_orchestrator",
    "analyze_single_technology",
    "analyze_multiple_technologies",
]
