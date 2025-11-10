"""
Agent 2: Innovation Scorer - Implementation

Scores Layer 1 innovation signals (patents, papers, GitHub activity).

This agent:
1. Queries innovation metrics from graph (patents, papers, citations)
2. Applies PageRank weighting for importance
3. Uses LLM to calculate final innovation score (0-100)
4. Returns score with reasoning and supporting metrics
"""

from typing import Dict, Any
from neo4j import AsyncDriver
from datetime import datetime, timedelta

from agents.agent_02_innovation.schemas import (
    InnovationInput,
    InnovationOutput,
    InnovationMetrics,
    PatentSummary,
)
from agents.shared.queries import innovation_queries
from agents.shared.openai_client import get_structured_llm
from agents.shared.constants import AGENT_TEMPERATURES


# LLM Prompt for scoring (RECALIBRATED 2025-01-09 for realistic data densities)
INNOVATION_SCORING_PROMPT = """You are an innovation analyst scoring emerging technologies based on Layer 1 innovation signals.

You will be given raw metrics about patent activity, research papers, and community context for a technology.

Your task:
1. Analyze the metrics to determine innovation strength
2. Calculate an innovation score from 0-100 (RECALIBRATED FOR REALISTIC DATA DENSITIES):
   - 0-20: Minimal innovation (0-3 patents, 0-10 papers, minimal citations)
   - 21-40: Low innovation (4-12 patents, 11-30 papers, some citations)
   - 41-60: Moderate innovation (13-30 patents, 31-70 papers, decent citations)
   - 61-80: High innovation (31-60 patents, 71-150 papers, strong citations)
   - 81-100: Breakthrough innovation (60+ patents, 150+ papers, exceptional citations)

   CALIBRATION ANCHOR: Score 50 represents a typical emerging technology with ~15-20 patents
   and ~40-50 papers in 2 years. Most technologies will score 20-60 based on graph data.

3. Consider:
   - Patent count (raw volume - 0-50 is typical range)
   - PageRank-weighted patent count (importance weighting)
   - Citation counts (quality indicator - most have 0-100 citations)
   - Community context (relative activity within graph)
   - Temporal trend (growing/stable/declining)

4. Scoring guidelines:
   - If patent_count = 0 and paper_count < 5: Score 0-15
   - If patent_count 1-5 and paper_count 5-20: Score 15-35
   - If patent_count 6-20 and paper_count 20-60: Score 35-55
   - If patent_count > 20 or paper_count > 60: Score 55-80
   - Reserve 80-100 for exceptional outliers only

5. Provide:
   - innovation_score: 0-100 score
   - reasoning: 2-3 sentences explaining the score
   - confidence: "high", "medium", or "low"

Be objective and data-driven. Most technologies will score 20-60. Scores above 70 should be rare (top 5%).

Technology: {tech_id}

Metrics:
- Patent count (2yr): {patent_count}
- Patent citations: {patent_citations}
- PageRank-weighted patent count: {pagerank_weighted:.1f}
- Avg patent PageRank: {avg_pagerank:.6f}
- Paper count (2yr): {paper_count}
- Paper citations: {paper_citations}
- Community patents: {community_patents}
- Community papers: {community_papers}
- Temporal trend: {trend_summary}

Provide your score and reasoning.
"""


async def get_innovation_metrics(
    driver: AsyncDriver,
    tech_id: str,
    start_date: str = None,
    end_date: str = None,
    community_version: str = "v1"
) -> InnovationMetrics:
    """
    Fetch all innovation metrics for a technology.

    Dates default to current system date (end) and 2 years back (start).

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID to score
        start_date: Start of temporal window
        end_date: End of temporal window
        community_version: Community detection version

    Returns:
        InnovationMetrics with all raw data
    """
    # Calculate dynamic dates if not provided
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        # Look back 2 years for innovation signals
        start_date = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")

    # Query 1: Patent count with PageRank weighting
    patent_data = await innovation_queries.get_patent_count_2yr(
        driver, tech_id, start_date, end_date
    )

    # Query 2: Paper count
    paper_data = await innovation_queries.get_paper_count_2yr(
        driver, tech_id, start_date, end_date
    )

    # Query 3: Community patents (for context)
    community_patent_count = await innovation_queries.get_community_patents(
        driver, tech_id, community_version, start_date, end_date
    )

    # Query 4: Temporal trend
    temporal_trend = await innovation_queries.get_innovation_temporal_trend(
        driver, tech_id
    )

    # Query 5: Top patents by citations (for evidence)
    top_patents = await innovation_queries.get_top_patents_by_citations(
        driver, tech_id, limit=5
    )

    # Query 6: Get community ID from technology node
    community_id_query = f"""
    MATCH (t:Technology {{id: $tech_id}})
    RETURN t.community_{community_version} AS community_id
    """

    async with driver.session() as session:
        result = await session.run(community_id_query, tech_id=tech_id)
        record = await result.single()
        community_id = record["community_id"] if record else None

    # Estimate community paper count (similar logic to patents)
    # For now, we'll estimate it as roughly 2/3 of patent count (typical ratio)
    community_paper_count = int(community_patent_count * 0.67)

    # Convert top patents to PatentSummary objects
    patent_summaries = [
        PatentSummary(
            doc_id=p["doc_id"],
            title=p["title"],
            citations=p["citations"],
            pagerank=p["pagerank"]
        )
        for p in top_patents
    ]

    return InnovationMetrics(
        patent_count_2yr=patent_data.get("patent_count", 0),
        patent_citations=patent_data.get("total_citations", 0),
        patent_pagerank_weighted=patent_data.get("pagerank_weighted_count", 0.0),
        avg_patent_pagerank=patent_data.get("avg_pagerank", 0.0),
        paper_count_2yr=paper_data.get("paper_count", 0),
        paper_citations=paper_data.get("total_citations", 0),
        community_id=community_id,
        community_patent_count=community_patent_count,
        community_paper_count=community_paper_count,
        temporal_trend=temporal_trend,
        top_patents=patent_summaries,
    )


async def innovation_scorer_agent(
    state: Dict[str, Any],
    driver: AsyncDriver
) -> Dict[str, Any]:
    """
    Innovation Scorer Agent - Main entry point.

    This agent scores Layer 1 innovation signals for a single technology.

    Args:
        state: LangGraph state dict with tech_id
        driver: Neo4j async driver

    Returns:
        Updated state with innovation_score and metrics

    State Updates:
        - innovation_score: float (0-100)
        - innovation_reasoning: str
        - innovation_metrics: dict
        - innovation_confidence: str

    Example:
        >>> state = {"tech_id": "solid_state_battery"}
        >>> result = await innovation_scorer_agent(state, driver)
        >>> result["innovation_score"]
        72.5
    """
    # Parse input
    input_data = InnovationInput(**state)

    # Fetch metrics
    metrics = await get_innovation_metrics(
        driver=driver,
        tech_id=input_data.tech_id,
        start_date=input_data.start_date,
        end_date=input_data.end_date,
        community_version=input_data.community_version,
    )

    # Get temporal trend (string: growing/stable/declining)
    trend_summary = metrics.temporal_trend

    # Build prompt
    prompt = INNOVATION_SCORING_PROMPT.format(
        tech_id=input_data.tech_id,
        patent_count=metrics.patent_count_2yr,
        patent_citations=metrics.patent_citations,
        pagerank_weighted=metrics.patent_pagerank_weighted,
        avg_pagerank=metrics.avg_patent_pagerank,
        paper_count=metrics.paper_count_2yr,
        paper_citations=metrics.paper_citations,
        community_patents=metrics.community_patent_count,
        community_papers=metrics.community_paper_count,
        trend_summary=trend_summary,
    )

    # Get structured LLM with temperature from constants
    llm = get_structured_llm(
        output_schema=InnovationOutput,
        model="gpt-4o-mini",
        temperature=AGENT_TEMPERATURES["agent_02_innovation"],
    )

    # Score with LLM
    result = await llm.ainvoke(prompt)

    # Validate output
    output = InnovationOutput(
        tech_id=input_data.tech_id,
        innovation_score=result.innovation_score,
        reasoning=result.reasoning,
        key_metrics=metrics,
        confidence=result.confidence,
    )

    # Return state update (for LangGraph compatibility)
    return {
        "tech_id": input_data.tech_id,
        "innovation_score": output.innovation_score,
        "innovation_reasoning": output.reasoning,
        "innovation_metrics": metrics.model_dump(),
        "innovation_confidence": output.confidence,
    }


# Standalone function for testing (non-LangGraph)
async def score_innovation(
    driver: AsyncDriver,
    tech_id: str,
    start_date: str = None,
    end_date: str = None,
    community_version: str = "v1"
) -> InnovationOutput:
    """
    Standalone function for scoring innovation (testing/debugging).

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID to score
        start_date: Start of temporal window
        end_date: End of temporal window
        community_version: Community detection version

    Returns:
        InnovationOutput with score and metrics

    Example:
        >>> from src.graph.neo4j_client import Neo4jClient
        >>> client = Neo4jClient()
        >>> await client.connect()
        >>> output = await score_innovation(client.driver, "solid_state_battery")
        >>> output.innovation_score
        72.5
    """
    state = {
        "tech_id": tech_id,
        "start_date": start_date,
        "end_date": end_date,
        "community_version": community_version,
    }

    result = await innovation_scorer_agent(state, driver)

    return InnovationOutput(
        tech_id=result["tech_id"],
        innovation_score=result["innovation_score"],
        reasoning=result["innovation_reasoning"],
        key_metrics=InnovationMetrics(**result["innovation_metrics"]),
        confidence=result["innovation_confidence"],
    )
