"""
Agent 4: Narrative Scorer - Implementation

Scores Layer 4 narrative signals (news sentiment, media coverage, outlet tiers).

This agent:
1. Queries narrative metrics from graph (news volume, sentiment, outlet quality)
2. Uses LLM to calculate final narrative score (0-100)
3. Returns score with reasoning and supporting metrics
"""

from typing import Dict, Any
from neo4j import AsyncDriver
from datetime import datetime, timedelta

from agents.agent_04_narrative.schemas import (
    NarrativeInput,
    NarrativeOutput,
    NarrativeMetrics,
    ArticleSummary,
)
from agents.shared.queries import narrative_queries
from agents.shared.openai_client import get_structured_llm
from agents.shared.constants import AGENT_TEMPERATURES


# LLM Prompt for scoring (RECALIBRATED 2025-01-10 - removed conservative anchoring)
NARRATIVE_SCORING_PROMPT = """You are a narrative analyst scoring emerging technologies based on Layer 4 narrative signals.

You will be given raw metrics about news coverage, media outlet quality, and sentiment.

Your task:
1. Analyze the metrics to determine narrative strength and media saturation
2. Calculate a narrative score from 0-100 using the full range:
   - 0-20: Minimal coverage (0-5 articles, no tier-1 outlets, neutral sentiment)
   - 21-40: Low coverage (6-20 articles, 1-3 tier-2 outlets, mixed sentiment)
   - 41-60: Moderate coverage (21-50 articles, some tier-2, positive trend)
   - 61-80: High coverage (51-120 articles, multiple tier-1, strong positive sentiment)
   - 81-100: Media saturation (120+ articles, dominant tier-1, overwhelmingly positive)

3. Consider:
   - News volume (article count in 3-month window)
   - Outlet tier distribution (tier 1 = Industry Authority/Financial Authority)
   - Average sentiment (-1.0 to +1.0 scale)
   - Sentiment trend (improving/stable/deteriorating)

4. Scoring guidelines - use the full scale based on data:
   - If news_count = 0: Score 0-10
   - If news_count 1-10 and tier1_count = 0: Score 10-25
   - If news_count 10-30 and tier1_count < 3: Score 25-45
   - If news_count 30-80 or tier1_count >= 3: Score 45-70
   - If news_count > 80 or tier1_count >= 6: Score 70-95

5. Provide:
   - narrative_score: 0-100 score
   - reasoning: 2-3 sentences explaining the score
   - confidence: "high", "medium", or "low"

Be objective and data-driven. Use the full 0-100 scale based on the actual metrics.

NOTE: Very high scores (>70) often indicate market peak/hype saturation (contrarian signal).

Technology: {tech_id}

Metrics:
- News articles (3mo): {news_count}
- Tier 1 outlets: {tier1_count}
- Tier 2 outlets: {tier2_count}
- Tier 3 outlets: {tier3_count}
- Avg sentiment: {avg_sentiment:.2f}
- Sentiment trend: {sentiment_trend}

Provide your score and reasoning.
"""


async def get_narrative_metrics(
    driver: AsyncDriver,
    tech_id: str,
    start_date: str = None,
    end_date: str = None
) -> NarrativeMetrics:
    """
    Fetch all narrative metrics for a technology.

    Dates default to current system date (end) and 6 months back (start).

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID to score
        start_date: Start of temporal window
        end_date: End of temporal window

    Returns:
        NarrativeMetrics with all raw data
    """
    # Calculate dynamic dates if not provided
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        # Look back 6 months for narrative signals
        start_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")

    # Query 1: News count (3 months)
    news_data = await narrative_queries.get_news_count_3mo(
        driver, tech_id, start_date, end_date
    )

    # Query 2: Outlet tier breakdown
    tier_data = await narrative_queries.get_outlet_tier_breakdown(
        driver, tech_id, start_date, end_date
    )

    # Query 3: Top articles by prominence
    top_articles_data = await narrative_queries.get_top_articles_by_prominence(
        driver, tech_id, limit=5
    )

    # Query 4: Sentiment temporal trend
    sentiment_data = await narrative_queries.get_sentiment_temporal_trend(
        driver, tech_id
    )

    # Extract news count from dict
    news_count = news_data.get("article_count", 0)
    avg_sentiment = news_data.get("avg_sentiment", 0.0)

    # Extract tier breakdown from dict (tier_data IS the breakdown)
    tier1_count = tier_data.get("Industry Authority", 0)
    tier2_count = tier_data.get("Financial Authority", 0)
    tier3_count = tier_data.get("Mainstream", 0)

    # Determine sentiment trend from temporal data
    recent_avg = sentiment_data.get("recent_avg", 0.0)
    if recent_avg > 0.3:
        sentiment_trend = "positive"
    elif recent_avg < -0.3:
        sentiment_trend = "negative"
    else:
        sentiment_trend = "neutral"

    # Convert top articles to ArticleSummary objects
    article_summaries = [
        ArticleSummary(
            doc_id=a.get("doc_id", ""),
            title=a.get("title", "Unknown"),
            outlet=a.get("outlet", "Unknown"),
            sentiment=a.get("sentiment", 0.0)
        )
        for a in top_articles_data[:5]
    ]

    return NarrativeMetrics(
        news_count_3mo=news_count,
        tier1_count=tier1_count,
        tier2_count=tier2_count,
        tier3_count=tier3_count,
        avg_sentiment=avg_sentiment,
        sentiment_trend=sentiment_trend,
        top_articles=article_summaries,
    )


async def narrative_scorer_agent(
    state: Dict[str, Any],
    driver: AsyncDriver
) -> Dict[str, Any]:
    """
    Narrative Scorer Agent - Main entry point.

    This agent scores Layer 4 narrative signals for a single technology.

    Args:
        state: LangGraph state dict with tech_id
        driver: Neo4j async driver

    Returns:
        Updated state with narrative_score and metrics

    State Updates:
        - narrative_score: float (0-100)
        - narrative_reasoning: str
        - narrative_metrics: dict
        - narrative_confidence: str

    Example:
        >>> state = {"tech_id": "evtol"}
        >>> result = await narrative_scorer_agent(state, driver)
        >>> result["narrative_score"]
        75.0
    """
    # Parse input
    input_data = NarrativeInput(**state)

    # Fetch metrics
    metrics = await get_narrative_metrics(
        driver=driver,
        tech_id=input_data.tech_id,
        start_date=input_data.start_date,
        end_date=input_data.end_date,
    )

    # Build prompt
    prompt = NARRATIVE_SCORING_PROMPT.format(
        tech_id=input_data.tech_id,
        news_count=metrics.news_count_3mo,
        tier1_count=metrics.tier1_count,
        tier2_count=metrics.tier2_count,
        tier3_count=metrics.tier3_count,
        avg_sentiment=metrics.avg_sentiment,
        sentiment_trend=metrics.sentiment_trend,
    )

    # Get structured LLM with temperature from constants
    llm = get_structured_llm(
        output_schema=NarrativeOutput,
        model="gpt-4o-mini",
        temperature=AGENT_TEMPERATURES["agent_04_narrative"],
    )

    # Score with LLM
    result = await llm.ainvoke(prompt)

    # Validate output
    output = NarrativeOutput(
        tech_id=input_data.tech_id,
        narrative_score=result.narrative_score,
        reasoning=result.reasoning,
        key_metrics=metrics,
        confidence=result.confidence,
    )

    # Return state update (for LangGraph compatibility)
    return {
        "tech_id": input_data.tech_id,
        "narrative_score": output.narrative_score,
        "narrative_reasoning": output.reasoning,
        "narrative_metrics": metrics.model_dump(),
        "narrative_confidence": output.confidence,
        # Document counts for evidence
        "news_count": metrics.news_count_3mo,
    }


# Standalone function for testing (non-LangGraph)
async def score_narrative(
    driver: AsyncDriver,
    tech_id: str,
    start_date: str = None,
    end_date: str = None
) -> NarrativeOutput:
    """
    Standalone function for scoring narrative (testing/debugging).

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID to score
        start_date: Start of temporal window
        end_date: End of temporal window

    Returns:
        NarrativeOutput with score and metrics

    Example:
        >>> from src.graph.neo4j_client import Neo4jClient
        >>> client = Neo4jClient()
        >>> await client.connect()
        >>> output = await score_narrative(client.driver, "evtol")
        >>> output.narrative_score
        75.0
    """
    state = {
        "tech_id": tech_id,
        "start_date": start_date,
        "end_date": end_date,
    }

    result = await narrative_scorer_agent(state, driver)

    return NarrativeOutput(
        tech_id=result["tech_id"],
        narrative_score=result["narrative_score"],
        reasoning=result["narrative_reasoning"],
        key_metrics=NarrativeMetrics(**result["narrative_metrics"]),
        confidence=result["narrative_confidence"],
    )
