"""Agent 8: LLM Analyst - Generates executive narrative summary."""

from typing import Dict, Any
from pydantic import BaseModel, Field
from src.agents.shared.openai_client import get_structured_llm
from src.agents.shared.constants import AGENT_TEMPERATURES
from src.agents.shared.logger import AgentLogger, LogLevel

class AnalystOutput(BaseModel):
    tech_id: str
    executive_summary: str = Field(description="3-4 sentence summary for executives")
    key_insight: str = Field(description="Single most important insight")
    recommendation: str = Field(description="Strategic recommendation")

ANALYST_PROMPT = """You are a strategic technology analyst writing an executive briefing.

Technology: {tech_id}

Layer Scores:
- Innovation (patents/papers): {innovation:.0f}/100
- Adoption (contracts/revenue): {adoption:.0f}/100
- Narrative (media coverage): {narrative:.0f}/100
- Risk (financial signals): {risk:.0f}/100

Hype Analysis:
- Hype Score: {hype:.0f}/100
- Phase: {phase}
- Layer Divergence: {divergence:.1f}

Provide:
1. executive_summary: 3-4 sentences explaining technology position and market dynamics
2. key_insight: Single most important takeaway for decision makers
3. recommendation: Strategic action (invest/monitor/avoid) with brief justification

Be direct and actionable. Focus on the "so what" for executives."""

async def llm_analyst_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    # Get logger from state
    logger = state.get("_logger", AgentLogger(LogLevel.SILENT))

    prompt = ANALYST_PROMPT.format(
        tech_id=state["tech_id"],
        innovation=state.get("innovation_score", 50),
        adoption=state.get("adoption_score", 50),
        narrative=state.get("narrative_score", 50),
        risk=state.get("risk_score", 50),
        hype=state.get("hype_score", 50),
        phase=state.get("hype_cycle_phase", "unknown"),
        divergence=state.get("layer_divergence", 0),
    )

    llm = get_structured_llm(
        output_schema=AnalystOutput,
        model="gpt-4o-mini",
        temperature=AGENT_TEMPERATURES["agent_08_analyst"],
    )

    result = await llm.ainvoke(prompt)

    # Log LLM call in debug mode
    logger.log_llm_call(
        agent_name="llm_analyst",
        prompt=prompt,
        response=result,
        model="gpt-4o-mini",
        tech_id=state["tech_id"]
    )

    return {
        "tech_id": state["tech_id"],
        "executive_summary": result.executive_summary,
        "key_insight": result.key_insight,
        "recommendation": result.recommendation,
    }
