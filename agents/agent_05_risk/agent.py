"""Agent 5: Risk Scorer - Layer 3 financial risk signals."""

from typing import Dict, Any
from neo4j import AsyncDriver
from datetime import datetime, timedelta
from agents.agent_05_risk.schemas import RiskInput, RiskOutput, RiskMetrics
from agents.shared.queries import risk_queries
from agents.shared.openai_client import get_structured_llm
from agents.shared.constants import AGENT_TEMPERATURES
from agents.shared.logger import AgentLogger, LogLevel

RISK_SCORING_PROMPT = """You are a financial risk analyst scoring emerging technologies based on Layer 3 financial signals.

You will be given raw metrics about SEC risk disclosures, institutional holdings, and insider trading.

Your task:
1. Analyze the metrics to determine financial risk level
2. Calculate a risk score from 0-100 (RECALIBRATED FOR REALISTIC DATA DENSITIES):
   - 0-20: Low risk (0-3 SEC mentions, high holdings >40%, net insider buying)
   - 21-40: Moderate-low risk (4-10 mentions, holdings 20-40%, balanced insider activity)
   - 41-60: Moderate risk (11-25 mentions, holdings 10-20%, mixed insider signals)
   - 61-80: High risk (26-50 mentions, holdings <10%, net insider selling)
   - 81-100: Extreme risk (50+ mentions, minimal holdings, heavy insider selling)

   CALIBRATION ANCHOR: Score 50 represents moderate financial uncertainty with ~15-20 SEC
   risk mentions in 6 months, ~15% institutional holdings, and neutral insider activity.
   Most technologies will score 10-40 based on sparse SEC filing data.

3. Consider:
   - SEC risk mentions (0-30 is typical 6-month range for emerging tech)
   - Institutional holdings (most emerging tech has 0-30% holdings)
   - Insider trading balance (buy vs sell ratio)
   - Net insider position (bullish/neutral/bearish signal)

4. Scoring guidelines:
   - If sec_mentions = 0 and inst_holdings < 5%: Score 10-25 (data scarcity, not confidence)
   - If sec_mentions 1-10 and insider_position = "buying": Score 15-35
   - If sec_mentions 10-25 and insider_position = "neutral": Score 35-55
   - If sec_mentions > 25 or insider_position = "selling": Score 55-75
   - Reserve 75-100 for severe financial distress signals

5. Provide:
   - risk_score: 0-100 score
   - reasoning: 2-3 sentences explaining the score
   - confidence: "high", "medium", or "low"

Be objective and data-driven. Most technologies will score 10-40. Absence of data ≠ low risk.

Technology: {tech_id}

Metrics:
- SEC risk mentions (6mo): {sec_mentions}
- Institutional holdings: {inst_holdings:.1f}%
- Insider buys: {insider_buys}
- Insider sells: {insider_sells}
- Insider net position: {insider_position}

Provide your score and reasoning.
"""

async def get_risk_metrics(driver: AsyncDriver, tech_id: str, start_date: str = None, end_date: str = None) -> RiskMetrics:
    # Calculate dynamic dates if not provided
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        # Look back 6 months for risk signals
        start_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")

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

    # Get logger from state
    logger = state.get("_logger", AgentLogger(LogLevel.SILENT))

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

    # Log LLM call in debug mode
    logger.log_llm_call(
        agent_name="risk_scorer",
        prompt=prompt,
        response=result,
        model="gpt-4o-mini",
        tech_id=input_data.tech_id
    )

    return {
        "tech_id": input_data.tech_id,
        "risk_score": result.risk_score,
        "risk_reasoning": result.reasoning,
        "risk_metrics": metrics.model_dump(),
        "risk_confidence": result.confidence,
        # Document counts for evidence (set to 0 - not implemented yet)
        "sec_filing_count": 0,
        "insider_transaction_count": 0,
    }

async def score_risk(driver: AsyncDriver, tech_id: str, start_date: str = None, end_date: str = None) -> RiskOutput:
    state = {"tech_id": tech_id, "start_date": start_date, "end_date": end_date}
    result = await risk_scorer_agent(state, driver)
    return RiskOutput(
        tech_id=result["tech_id"],
        risk_score=result["risk_score"],
        reasoning=result["risk_reasoning"],
        key_metrics=RiskMetrics(**result["risk_metrics"]),
        confidence=result["risk_confidence"],
    )
