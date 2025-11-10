"""
Narrative Queries (Layer 4): News Articles, Sentiment, Media Coverage

Intelligence Layer: Narrative (Lagging Indicator)
Sources: News articles, press releases, media coverage
Purpose: Detect media saturation peaks (contrarian indicator)

Key Insight: News volume peaks typically coincide with valuation peaks.
High media coverage without fundamentals = hype signal.
"""

from typing import List, Dict, Any
from neo4j import AsyncDriver


# =============================================================================
# NEWS COVERAGE QUERIES
# =============================================================================

async def get_news_count_3mo(
    driver: AsyncDriver,
    tech_id: str,
    start_date: str = None,
    end_date: str = None
) -> Dict[str, Any]:
    """
    Get news coverage in last 3-6 months.

    News volume is a lagging indicator: peaks happen AFTER technology
    has already reached maximum hype.

    Note: Sentiment analysis removed as news documents lack sentiment property.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        start_date: Start of analysis window (default: 6 months)
        end_date: End of analysis window

    Returns:
        {
            "article_count": int,
            "avg_sentiment": float,  # Always 0.0 (property not available)
            "positive_count": int,   # Always 0
            "negative_count": int,   # Always 0
            "neutral_count": int     # Always 0
        }

    Example:
        >>> result = await get_news_count_3mo(driver, "evtol")
        >>> result
        {
            'article_count': 127,
            'avg_sentiment': 0.0,
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0
        }
    """
    query = """
    MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type = 'news'
      AND date(datetime(d.published_at)) >= date($start_date)
      AND date(datetime(d.published_at)) < date($end_date)
      AND m.role = 'subject'
      AND d.quality_score >= 0.75
    RETURN count(d) AS article_count
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, start_date=start_date, end_date=end_date)
        record = await result.single()

        if not record:
            return {
                "article_count": 0,
                "avg_sentiment": 0.0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
            }

        return {
            "article_count": record["article_count"] or 0,
            "avg_sentiment": 0.0,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
        }


# =============================================================================
# OUTLET TIER ANALYSIS
# =============================================================================

async def get_outlet_tier_breakdown(
    driver: AsyncDriver,
    tech_id: str,
    start_date: str = None,
    end_date: str = None
) -> Dict[str, int]:
    """
    Get news coverage breakdown by outlet tier (prominence).

    Outlet tiers (from project specification):
    - Industry Authority: Tech-specific publications (e.g., TechCrunch, The Verge)
    - Financial Authority: Business/finance media (e.g., WSJ, Bloomberg)
    - Mainstream: General news outlets (e.g., CNN, BBC)
    - Other: Blogs, regional news

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        start_date: Start of analysis window
        end_date: End of analysis window

    Returns:
        {
            "Industry Authority": int,
            "Financial Authority": int,
            "Mainstream": int,
            "Other": int
        }

    Example:
        >>> result = await get_outlet_tier_breakdown(driver, "evtol")
        >>> result
        {
            'Industry Authority': 45,   # TechCrunch, The Verge
            'Financial Authority': 32,   # WSJ, Bloomberg
            'Mainstream': 18,            # CNN, BBC
            'Other': 15                  # Blogs, regional
        }
    """
    query = """
    MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type = 'news'
      AND date(datetime(d.published_at)) >= date($start_date)
      AND date(datetime(d.published_at)) < date($end_date)
      AND m.role = 'subject'
      AND d.quality_score >= 0.75
    WITH d, coalesce(d.outlet_tier, 'Other') AS tier
    RETURN tier, count(d) AS count
    ORDER BY count DESC
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, start_date=start_date, end_date=end_date)
        records = await result.values()

        # Initialize all tiers to 0
        breakdown = {
            "Industry Authority": 0,
            "Financial Authority": 0,
            "Mainstream": 0,
            "Other": 0,
        }

        # Fill in actual counts
        for record in records:
            tier = record[0]
            count = record[1]
            if tier in breakdown:
                breakdown[tier] = count

        return breakdown


# =============================================================================
# TOP ARTICLES QUERIES
# =============================================================================

async def get_top_articles_by_prominence(
    driver: AsyncDriver,
    tech_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get top news articles prioritized by outlet tier and sentiment.

    Priority order:
    1. Industry Authority (most relevant)
    2. Financial Authority (most influential)
    3. Mainstream (widest reach)
    4. Other (least priority)

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        limit: Maximum number of articles

    Returns:
        List of article dicts with doc_id, title, source, sentiment, evidence

    Example:
        >>> articles = await get_top_articles_by_prominence(driver, "evtol")
        >>> articles[0]
        {
            'doc_id': 'news_techcrunch_20241115',
            'title': 'eVTOL Revolution: Joby Gets FAA Approval',
            'source': 'TechCrunch',
            'outlet_tier': 'Industry Authority',
            'sentiment': 0.78,
            'published_at': '2024-11-15',
            'evidence': 'Article discusses eVTOL certification milestone...',
            'strength': 0.92
        }
    """
    query = """
    MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type = 'news'
      AND m.role = 'subject'
      AND d.quality_score >= 0.75
    WITH d, m,
         CASE coalesce(d.outlet_tier, 'Other')
           WHEN 'Industry Authority' THEN 1
           WHEN 'Financial Authority' THEN 2
           WHEN 'Mainstream' THEN 3
           ELSE 4
         END AS tier_priority
    RETURN
      d.doc_id AS doc_id,
      d.title AS title,
      d.source AS source,
      d.outlet_tier AS outlet_tier,
      d.published_at AS published_at,
      m.evidence_text AS evidence,
      m.strength AS strength
    ORDER BY tier_priority ASC, d.published_at DESC, m.strength DESC, d.doc_id ASC
    LIMIT $limit
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, limit=limit)
        records = await result.values()

        return [
            {
                "doc_id": record[0],
                "title": record[1],
                "source": record[2],
                "outlet_tier": record[3],
                "sentiment": 0.0,  # Property not available in news docs
                "published_at": record[4],
                "evidence": record[5],
                "strength": record[6],
            }
            for record in records
        ]


# =============================================================================
# SENTIMENT ANALYSIS
# =============================================================================

async def get_sentiment_temporal_trend(
    driver: AsyncDriver,
    tech_id: str,
    window_months: int = 3
) -> Dict[str, Any]:
    """
    Analyze sentiment trend over time (improving, stable, deteriorating).

    Note: Sentiment analysis removed as news documents lack sentiment property.
    This function now always returns stable trend with 0.0 sentiment.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        window_months: Number of months for recent window

    Returns:
        {
            "recent_avg": float,      # Always 0.0
            "historical_avg": float,  # Always 0.0
            "trend": "stable"         # Always stable
        }

    Example:
        >>> result = await get_sentiment_temporal_trend(driver, "evtol")
        >>> result
        {
            'recent_avg': 0.0,
            'historical_avg': 0.0,
            'trend': 'stable'
        }
    """
    # Sentiment property not available - return neutral results
    return {
        "recent_avg": 0.0,
        "historical_avg": 0.0,
        "trend": "stable",
    }


# =============================================================================
# NARRATIVE MOMENTUM
# =============================================================================

async def get_narrative_momentum(
    driver: AsyncDriver,
    tech_id: str
) -> Dict[str, Any]:
    """
    Calculate narrative momentum (velocity of media coverage change).

    Measures how quickly media coverage is growing or declining.
    High momentum = rapid narrative buildup (potential Peak signal).

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID

    Returns:
        {
            "last_30_days": int,
            "previous_30_days": int,
            "momentum": float,  # Ratio (e.g., 2.5 = 150% increase)
            "trend": "accelerating" | "stable" | "decelerating"
        }
    """
    query = """
    MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type = 'news'
      AND m.role = 'subject'
      AND d.quality_score >= 0.75
    WITH d,
         date(datetime(d.published_at)) AS pub_date,
         date() - duration({days: 30}) AS cutoff_30,
         date() - duration({days: 60}) AS cutoff_60
    WITH
      count(CASE WHEN pub_date >= cutoff_30 THEN 1 END) AS last_30_days,
      count(CASE WHEN pub_date >= cutoff_60 AND pub_date < cutoff_30 THEN 1 END) AS previous_30_days
    WITH
      last_30_days,
      previous_30_days,
      CASE WHEN previous_30_days > 0
           THEN toFloat(last_30_days) / previous_30_days
           ELSE toFloat(last_30_days) END AS momentum
    RETURN
      last_30_days,
      previous_30_days,
      momentum,
      CASE
        WHEN momentum > 1.5 THEN 'accelerating'
        WHEN momentum < 0.5 THEN 'decelerating'
        ELSE 'stable'
      END AS trend
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id)
        record = await result.single()

        if not record:
            return {
                "last_30_days": 0,
                "previous_30_days": 0,
                "momentum": 0.0,
                "trend": "stable",
            }

        return {
            "last_30_days": record["last_30_days"] or 0,
            "previous_30_days": record["previous_30_days"] or 0,
            "momentum": float(record["momentum"] or 0.0),
            "trend": record["trend"] or "stable",
        }
