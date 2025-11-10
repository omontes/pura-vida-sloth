"""Agent 5: Risk Scorer - Layer 3 financial risk signals."""

from typing import Dict, Any
from neo4j import AsyncDriver
from agents.agent_05_risk.schemas import RiskInput, RiskOutput, RiskMetrics
from agents.shared.queries import risk_queries
from agents.shared.openai_client import get_structured_llm
from agents.shared.constants import AGENT_TEMPERATURES

RISK_SCORING_PROMPT = """Score financial risk (0-100) based on:
- SEC risk mentions (higher = more risk flagged)
- Institutional holdings (lower = less confidence)
- Insider trading (net selling = bearish)

Score ranges:
- 0-20: Low risk (few mentions, high institutional holdings, insider buying)
- 21-40: Moderate-low risk
- 41-60: Moderate risk
- 61-80: High risk (many mentions, low holdings, insider selling)
- 81-100: Extreme risk

Tech: {tech_id}
SEC risk mentions (6mo): {sec_mentions}
Institutional holdings: {inst_holdings:.1f}%
Insider buys: {insider_buys}
Insider sells: {insider_sells}
Insider position: {insider_position}

Provide score and reasoning."""

async def get_risk_metrics(driver: AsyncDriver, tech_id: str, start_date: str, end_date: str) -> RiskMetrics:
    sec_data = await risk_queries.get_sec_risk_mentions_6mo(driver, tech_id, start_date, end_date)
    holdings_data = await risk_queries.get_institutional_holdings(driver, tech_id)
    insider_data = await risk_queries.get_insider_trading_summary(driver, tech_id, start_date, end_date)

    return RiskMetrics(
        sec_risk_mentions_6mo=sec_data.get("count", 0),
        institutional_holdings_pct=holdings_data.get("avg_ownership_pct", 0.0),
        insider_buy_count=insider_data.get("buy_count", 0),
        insider_sell_count=insider_data.get("sell_count", 0),
        insider_net_position=insider_data.get("net_position", "neutral"),
    )

async def risk_scorer_agent(state: Dict[str, Any], driver: AsyncDriver) -> Dict[str, Any]:
    input_data = RiskInput(**state)
    metrics = await get_risk_metrics(driver, input_data.tech_id, input_data.start_date, input_data.end_date)

    prompt = RISK_SCORING_PROMPT.format(
        tech_id=input_data.tech_id,
        sec_mentions=metrics.sec_risk_mentions_6mo,
        inst_holdings=metrics.institutional_holdings_pct,
        insider_buys=metrics.insider_buy_count,
        insider_sells=metrics.insider_sell_count,
        insider_position=metrics.insider_net_position,
    )

    llm = get_structured_llm(output_schema=RiskOutput, model="gpt-4o-mini", temperature=AGENT_TEMPERATURES["agent_05_risk"])
    result = await llm.ainvoke(prompt)

    return {
        "tech_id": input_data.tech_id,
        "risk_score": result.risk_score,
        "risk_reasoning": result.reasoning,
        "risk_metrics": metrics.model_dump(),
        "risk_confidence": result.confidence,
    }

async def score_risk(driver: AsyncDriver, tech_id: str, start_date: str = "2024-07-01", end_date: str = "2025-01-01") -> RiskOutput:
    state = {"tech_id": tech_id, "start_date": start_date, "end_date": end_date}
    result = await risk_scorer_agent(state, driver)
    return RiskOutput(
        tech_id=result["tech_id"],
        risk_score=result["risk_score"],
        reasoning=result["risk_reasoning"],
        key_metrics=RiskMetrics(**result["risk_metrics"]),
        confidence=result["risk_confidence"],
    )
