"""
Agent 3: Adoption Scorer - Implementation

Scores Layer 2 adoption signals (government contracts, regulations, company activity).

This agent:
1. Queries adoption metrics from graph (contracts, approvals, companies)
2. Uses LLM to calculate final adoption score (0-100)
3. Returns score with reasoning and supporting metrics
"""

from typing import Dict, Any
from neo4j import AsyncDriver

from agents.agent_03_adoption.schemas import (
    AdoptionInput,
    AdoptionOutput,
    AdoptionMetrics,
    ContractSummary,
)
from agents.shared.queries import adoption_queries
from agents.shared.openai_client import get_structured_llm
from agents.shared.constants import AGENT_TEMPERATURES


# LLM Prompt for scoring
ADOPTION_SCORING_PROMPT = """You are a market adoption analyst scoring emerging technologies based on Layer 2 adoption signals.

You will be given raw metrics about government contracts, regulatory approvals, and company development activity.

Your task:
1. Analyze the metrics to determine adoption/commercialization strength
2. Calculate an adoption score from 0-100:
   - 0-20: Pre-commercial (no contracts, no approvals, limited companies)
   - 21-40: Early commercial (few contracts, some development activity)
   - 41-60: Moderate adoption (government validation, multiple companies, some approvals)
   - 61-80: High adoption (strong contract volume/value, many approvals, active ecosystem)
   - 81-100: Widespread adoption (massive contracts, full certification, industry standard)

3. Consider:
   - Government contract count and total value (validation signal)
   - Regulatory approvals (commercialization readiness)
   - Number of companies developing (ecosystem maturity)
   - Contract diversity across agencies (market breadth)

4. Provide:
   - adoption_score: 0-100 score
   - reasoning: 2-3 sentences explaining the score
   - confidence: "high", "medium", or "low"

Be objective and data-driven. Higher contract values and regulatory approvals indicate higher adoption.

Technology: {tech_id}

Metrics:
- Gov contracts (1yr): {contract_count}
- Total contract value: ${contract_value:,.0f}
- Avg contract value: ${avg_contract_value:,.0f}
- Regulatory approvals: {regulatory_approvals}
- Companies developing: {companies_developing}
- Top companies: {top_companies}

Provide your score and reasoning.
"""


async def get_adoption_metrics(
    driver: AsyncDriver,
    tech_id: str,
    start_date: str = "2023-07-01",
    end_date: str = "2025-01-01"
) -> AdoptionMetrics:
    """
    Fetch all adoption metrics for a technology.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID to score
        start_date: Start of temporal window
        end_date: End of temporal window

    Returns:
        AdoptionMetrics with all raw data
    """
    # Query 1: Government contracts (count and value)
    contract_data = await adoption_queries.get_gov_contracts_1yr(
        driver, tech_id, start_date, end_date
    )

    # Query 2: Top contracts by value
    top_contracts_data = await adoption_queries.get_top_contracts_by_value(
        driver, tech_id, limit=5
    )

    # Query 3: Regulatory approvals
    regulatory_data = await adoption_queries.get_regulatory_approvals(
        driver, tech_id
    )

    # Query 4: Companies developing this technology
    companies_data = await adoption_queries.get_companies_developing_tech(
        driver, tech_id, limit=10
    )

    # Extract contract metrics from dict
    contract_count = contract_data.get("count", 0)
    total_value = contract_data.get("total_value", 0.0)
    avg_value = contract_data.get("avg_contract_value", 0.0)

    # Extract regulatory count from dict
    regulatory_count = regulatory_data.get("count", 0)

    # Convert top contracts to ContractSummary objects
    contract_summaries = [
        ContractSummary(
            doc_id=c.get("doc_id", ""),
            title=c.get("title", "Unknown"),
            value=c.get("value", 0.0),
            agency=c.get("agency", "Unknown")
        )
        for c in top_contracts_data[:5]
    ]

    # Extract top companies (tickers)
    top_companies = [c.get("ticker", "") for c in companies_data[:5] if c.get("ticker")]

    return AdoptionMetrics(
        gov_contract_count_1yr=contract_count,
        gov_contract_total_value=total_value,
        gov_contract_avg_value=avg_value,
        regulatory_approval_count=regulatory_count,
        companies_developing=len(companies_data),
        top_companies=top_companies,
        top_contracts=contract_summaries,
    )


async def adoption_scorer_agent(
    state: Dict[str, Any],
    driver: AsyncDriver
) -> Dict[str, Any]:
    """
    Adoption Scorer Agent - Main entry point.

    This agent scores Layer 2 adoption signals for a single technology.

    Args:
        state: LangGraph state dict with tech_id
        driver: Neo4j async driver

    Returns:
        Updated state with adoption_score and metrics

    State Updates:
        - adoption_score: float (0-100)
        - adoption_reasoning: str
        - adoption_metrics: dict
        - adoption_confidence: str

    Example:
        >>> state = {"tech_id": "evtol"}
        >>> result = await adoption_scorer_agent(state, driver)
        >>> result["adoption_score"]
        68.0
    """
    # Parse input
    input_data = AdoptionInput(**state)

    # Fetch metrics
    metrics = await get_adoption_metrics(
        driver=driver,
        tech_id=input_data.tech_id,
        start_date=input_data.start_date,
        end_date=input_data.end_date,
    )

    # Build prompt
    prompt = ADOPTION_SCORING_PROMPT.format(
        tech_id=input_data.tech_id,
        contract_count=metrics.gov_contract_count_1yr,
        contract_value=metrics.gov_contract_total_value,
        avg_contract_value=metrics.gov_contract_avg_value,
        regulatory_approvals=metrics.regulatory_approval_count,
        companies_developing=metrics.companies_developing,
        top_companies=", ".join(metrics.top_companies) if metrics.top_companies else "None",
    )

    # Get structured LLM with temperature from constants
    llm = get_structured_llm(
        output_schema=AdoptionOutput,
        model="gpt-4o-mini",
        temperature=AGENT_TEMPERATURES["agent_03_adoption"],
    )

    # Score with LLM
    result = await llm.ainvoke(prompt)

    # Validate output
    output = AdoptionOutput(
        tech_id=input_data.tech_id,
        adoption_score=result.adoption_score,
        reasoning=result.reasoning,
        key_metrics=metrics,
        confidence=result.confidence,
    )

    # Return state update (for LangGraph compatibility)
    return {
        "tech_id": input_data.tech_id,
        "adoption_score": output.adoption_score,
        "adoption_reasoning": output.reasoning,
        "adoption_metrics": metrics.model_dump(),
        "adoption_confidence": output.confidence,
    }


# Standalone function for testing (non-LangGraph)
async def score_adoption(
    driver: AsyncDriver,
    tech_id: str,
    start_date: str = "2023-07-01",
    end_date: str = "2025-01-01"
) -> AdoptionOutput:
    """
    Standalone function for scoring adoption (testing/debugging).

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID to score
        start_date: Start of temporal window
        end_date: End of temporal window

    Returns:
        AdoptionOutput with score and metrics

    Example:
        >>> from src.graph.neo4j_client import Neo4jClient
        >>> client = Neo4jClient()
        >>> await client.connect()
        >>> output = await score_adoption(client.driver, "evtol")
        >>> output.adoption_score
        68.0
    """
    state = {
        "tech_id": tech_id,
        "start_date": start_date,
        "end_date": end_date,
    }

    result = await adoption_scorer_agent(state, driver)

    return AdoptionOutput(
        tech_id=result["tech_id"],
        adoption_score=result["adoption_score"],
        reasoning=result["adoption_reasoning"],
        key_metrics=AdoptionMetrics(**result["adoption_metrics"]),
        confidence=result["adoption_confidence"],
    )
