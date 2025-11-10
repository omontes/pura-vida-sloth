"""
Risk Queries (Layer 3): SEC Filings, Insider Trading, Financial Metrics

Intelligence Layer: Financial Reality (Coincident 0-6 months)
Sources: SEC filings (10-K, 10-Q), Forms 3/4/5 (insider trades), 13F (institutional holdings)
Purpose: Measure current valuation vs actual performance

Key Insight: Insider selling at price peaks signals executive exits.
High risk mentions in SEC filings = trouble brewing.
"""

from typing import List, Dict, Any
from neo4j import AsyncDriver


# =============================================================================
# SEC RISK MENTION QUERIES
# =============================================================================

async def get_sec_risk_mentions_6mo(
    driver: AsyncDriver,
    tech_id: str,
    start_date: str = "2024-07-01",
    end_date: str = "2025-01-01"
) -> Dict[str, Any]:
    """
    Get SEC risk factor mentions in last 6 months.

    SEC filings (10-K, 10-Q) contain "Risk Factors" sections where companies
    disclose technology-related risks (regulatory, competitive, technical).

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        start_date: Start of analysis window
        end_date: End of analysis window

    Returns:
        {
            "count": int,
            "companies": List[str],
            "categories": List[str],  # regulatory, competitive, technical, market
            "top_mentions": List[dict]
        }

    Example:
        >>> result = await get_sec_risk_mentions_6mo(driver, "evtol")
        >>> result
        {
            'count': 12,
            'companies': ['JOBY', 'ACHR', 'LILM'],
            'categories': ['regulatory', 'certification', 'market'],
            'top_mentions': [...]
        }
    """
    query = """
    MATCH (c:Company)-[r:RELATED_TO_TECH]->(t:Technology {id: $tech_id})
    MATCH (c)-[:RELATED_TO_TECH]->(t)-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type = 'sec_filing'
      AND date(datetime(d.published_at)) >= date($start_date)
      AND date(datetime(d.published_at)) < date($end_date)
      AND (d.section = 'risk_factors' OR m.evidence_text CONTAINS 'risk')
      AND d.quality_score >= 0.75
    WITH c, d, m
    RETURN
      count(DISTINCT d) AS count,
      collect(DISTINCT c.ticker)[0..10] AS companies,
      collect(DISTINCT d.risk_category)[0..10] AS categories,
      collect({
        company: c.ticker,
        fiscal_period: d.fiscal_period,
        date: d.published_at,
        risk_category: d.risk_category,
        evidence: m.evidence_text,
        strength: m.strength
      })[0..10] AS top_mentions
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, start_date=start_date, end_date=end_date)
        record = await result.single()

        if not record:
            return {
                "count": 0,
                "companies": [],
                "categories": [],
                "top_mentions": [],
            }

        return {
            "count": record["count"] or 0,
            "companies": [c for c in (record["companies"] or []) if c],
            "categories": [cat for cat in (record["categories"] or []) if cat],
            "top_mentions": record["top_mentions"] or [],
        }


async def get_top_risk_mentions(
    driver: AsyncDriver,
    tech_id: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Get top SEC risk mentions by strength and recency.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        limit: Maximum number of mentions

    Returns:
        List of risk mention dicts

    Example:
        >>> mentions = await get_top_risk_mentions(driver, "evtol")
        >>> mentions[0]
        {
            'company': 'JOBY',
            'fiscal_period': 'Q3 2024',
            'date': '2024-11-08',
            'risk_category': 'regulatory',
            'evidence': 'FAA certification delays pose significant risks...',
            'strength': 0.88
        }
    """
    query = """
    MATCH (c:Company)-[r:RELATED_TO_TECH]->(t:Technology {id: $tech_id})
    MATCH (c)-[:RELATED_TO_TECH]->(t)-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type = 'sec_filing'
      AND (d.section = 'risk_factors' OR m.evidence_text CONTAINS 'risk')
      AND d.quality_score >= 0.75
    RETURN
      c.ticker AS company,
      d.fiscal_period AS fiscal_period,
      d.published_at AS date,
      d.risk_category AS risk_category,
      m.evidence_text AS evidence,
      m.strength AS strength
    ORDER BY d.published_at DESC, m.strength DESC, d.doc_id ASC
    LIMIT $limit
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, limit=limit)
        records = await result.values()

        return [
            {
                "company": record[0],
                "fiscal_period": record[1],
                "date": record[2],
                "risk_category": record[3],
                "evidence": record[4],
                "strength": record[5],
            }
            for record in records
        ]


# =============================================================================
# INSTITUTIONAL HOLDINGS QUERIES (13F Filings)
# =============================================================================

async def get_institutional_holdings(
    driver: AsyncDriver,
    tech_id: str
) -> Dict[str, Any]:
    """
    Get institutional holdings data from 13F filings.

    13F filings show quarterly holdings of institutional investors ($100M+ AUM).
    Position changes indicate institutional sentiment.

    NOTE: This function queries Neo4j for 13F documents. For detailed
    transaction analysis, use src/utils/duckdb_manager.py which has
    pre-computed aggregations.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID

    Returns:
        {
            "avg_change_pct": float,  # Average position change
            "holders_increasing": int,
            "holders_decreasing": int,
            "total_holders": int
        }

    Example:
        >>> result = await get_institutional_holdings(driver, "evtol")
        >>> result
        {
            'avg_change_pct': -12.5,  # Institutions reducing positions
            'holders_increasing': 8,
            'holders_decreasing': 15,
            'total_holders': 23
        }
    """
    query = """
    MATCH (c:Company)-[r:RELATED_TO_TECH]->(t:Technology {id: $tech_id})
    MATCH (c)-[:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type = 'form_13f'
      AND d.position_change_pct IS NOT NULL
    WITH d
    RETURN
      avg(d.position_change_pct) AS avg_change_pct,
      count(CASE WHEN d.position_change_pct > 0 THEN 1 END) AS holders_increasing,
      count(CASE WHEN d.position_change_pct < 0 THEN 1 END) AS holders_decreasing,
      count(d) AS total_holders
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id)
        record = await result.single()

        if not record:
            return {
                "avg_change_pct": 0.0,
                "holders_increasing": 0,
                "holders_decreasing": 0,
                "total_holders": 0,
            }

        return {
            "avg_change_pct": float(record["avg_change_pct"] or 0.0),
            "holders_increasing": record["holders_increasing"] or 0,
            "holders_decreasing": record["holders_decreasing"] or 0,
            "total_holders": record["total_holders"] or 0,
        }


# =============================================================================
# INSIDER TRADING QUERIES (Forms 3/4/5)
# =============================================================================

async def get_insider_trading_summary(
    driver: AsyncDriver,
    tech_id: str,
    start_date: str = "2024-07-01",
    end_date: str = "2025-01-01"
) -> Dict[str, Any]:
    """
    Get insider trading summary for companies developing this technology.

    Forms 3/4/5 report insider buy/sell transactions. Insider selling
    at high prices = executives cashing out (potential Peak signal).

    NOTE: For detailed insider transaction analysis with DuckDB aggregations,
    use src/utils/duckdb_insider_transactions.py which provides:
    - query_transactions_by_ticker()
    - get_insider_summary_stats()
    - get_top_insiders_by_volume()

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        start_date: Start of analysis window
        end_date: End of analysis window

    Returns:
        {
            "transaction_count": int,
            "net_shares": int,  # Positive = net buying, negative = net selling
            "net_value_usd": float,
            "buy_count": int,
            "sell_count": int,
            "companies": List[str]
        }

    Example:
        >>> result = await get_insider_trading_summary(driver, "evtol")
        >>> result
        {
            'transaction_count': 23,
            'net_shares': -150000,  # Net selling
            'net_value_usd': -8500000.0,
            'buy_count': 5,
            'sell_count': 18,
            'companies': ['JOBY', 'ACHR']
        }
    """
    query = """
    MATCH (c:Company)-[r:RELATED_TO_TECH]->(t:Technology {id: $tech_id})
    MATCH (c)-[:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type IN ['form_3', 'form_4', 'form_5']
      AND date(datetime(d.published_at)) >= date($start_date)
      AND date(datetime(d.published_at)) < date($end_date)
    WITH c, d,
         coalesce(d.shares_transacted, 0) AS shares,
         coalesce(d.transaction_value_usd, 0.0) AS value,
         d.transaction_type AS tx_type
    RETURN
      count(d) AS transaction_count,
      sum(CASE WHEN tx_type = 'buy' THEN shares ELSE -shares END) AS net_shares,
      sum(CASE WHEN tx_type = 'buy' THEN value ELSE -value END) AS net_value_usd,
      count(CASE WHEN tx_type = 'buy' THEN 1 END) AS buy_count,
      count(CASE WHEN tx_type = 'sell' THEN 1 END) AS sell_count,
      collect(DISTINCT c.ticker)[0..10] AS companies
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, start_date=start_date, end_date=end_date)
        record = await result.single()

        if not record:
            return {
                "transaction_count": 0,
                "net_shares": 0,
                "net_value_usd": 0.0,
                "buy_count": 0,
                "sell_count": 0,
                "companies": [],
            }

        return {
            "transaction_count": record["transaction_count"] or 0,
            "net_shares": record["net_shares"] or 0,
            "net_value_usd": float(record["net_value_usd"] or 0.0),
            "buy_count": record["buy_count"] or 0,
            "sell_count": record["sell_count"] or 0,
            "companies": record["companies"] or [],
        }


# =============================================================================
# FINANCIAL HEALTH METRICS
# =============================================================================

async def get_cash_burn_analysis(
    driver: AsyncDriver,
    tech_id: str
) -> Dict[str, Any]:
    """
    Analyze cash burn rate from SEC filings (10-K, 10-Q).

    Cash burn = how fast company is spending cash reserves.
    High burn + low revenue = runway risk.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID

    Returns:
        {
            "companies_tracked": int,
            "avg_cash_burn_quarterly": float,  # USD
            "avg_runway_months": float,
            "high_risk_count": int  # Companies with <12 months runway
        }

    Example:
        >>> result = await get_cash_burn_analysis(driver, "evtol")
        >>> result
        {
            'companies_tracked': 3,
            'avg_cash_burn_quarterly': 45000000.0,
            'avg_runway_months': 18.5,
            'high_risk_count': 1  # 1 company has <12 months runway
        }
    """
    query = """
    MATCH (c:Company)-[r:RELATED_TO_TECH]->(t:Technology {id: $tech_id})
    MATCH (c)-[:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type = 'sec_filing'
      AND d.fiscal_period IS NOT NULL
      AND d.cash_burn_quarterly IS NOT NULL
      AND d.cash_reserves IS NOT NULL
    WITH c,
         d.cash_burn_quarterly AS burn,
         d.cash_reserves AS reserves,
         CASE WHEN d.cash_burn_quarterly > 0
              THEN toFloat(d.cash_reserves) / d.cash_burn_quarterly
              ELSE 999.0 END AS runway_months
    WITH
      count(DISTINCT c) AS companies_tracked,
      avg(burn) AS avg_cash_burn_quarterly,
      avg(runway_months) AS avg_runway_months,
      count(CASE WHEN runway_months < 12 THEN 1 END) AS high_risk_count
    RETURN
      companies_tracked,
      avg_cash_burn_quarterly,
      avg_runway_months,
      high_risk_count
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id)
        record = await result.single()

        if not record:
            return {
                "companies_tracked": 0,
                "avg_cash_burn_quarterly": 0.0,
                "avg_runway_months": 0.0,
                "high_risk_count": 0,
            }

        return {
            "companies_tracked": record["companies_tracked"] or 0,
            "avg_cash_burn_quarterly": float(record["avg_cash_burn_quarterly"] or 0.0),
            "avg_runway_months": float(record["avg_runway_months"] or 0.0),
            "high_risk_count": record["high_risk_count"] or 0,
        }


# =============================================================================
# RISK TEMPORAL TREND
# =============================================================================

async def get_risk_temporal_trend(
    driver: AsyncDriver,
    tech_id: str,
    window_months: int = 3
) -> str:
    """
    Analyze risk trend over time (increasing, stable, decreasing).

    Compares recent risk mentions to historical average.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        window_months: Number of months for recent window

    Returns:
        "increasing" | "stable" | "decreasing"

    Example:
        >>> trend = await get_risk_temporal_trend(driver, "evtol")
        >>> trend
        "increasing"  # Risk mentions are growing (concerning)
    """
    query = """
    MATCH (c:Company)-[r:RELATED_TO_TECH]->(t:Technology {id: $tech_id})
    MATCH (c)-[:RELATED_TO_TECH]->(t)-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type = 'sec_filing'
      AND (d.section = 'risk_factors' OR m.evidence_text CONTAINS 'risk')
      AND d.quality_score >= 0.75
    WITH d,
         date(datetime(d.published_at)) AS pub_date,
         date() - duration({months: $window_months}) AS cutoff_date
    WITH
      count(CASE WHEN pub_date >= cutoff_date THEN 1 END) AS recent_count,
      count(CASE WHEN pub_date < cutoff_date THEN 1 END) AS historical_count
    WITH
      recent_count,
      historical_count,
      toFloat(recent_count) / $window_months AS recent_rate,
      toFloat(historical_count) / CASE WHEN historical_count > 0
                                       THEN (historical_count / 12.0)
                                       ELSE 1.0 END AS historical_rate
    RETURN
      CASE
        WHEN recent_rate > historical_rate * 1.3 THEN 'increasing'
        WHEN recent_rate < historical_rate * 0.7 THEN 'decreasing'
        ELSE 'stable'
      END AS trend
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, window_months=window_months)
        record = await result.single()

        if not record or record["trend"] is None:
            return "stable"

        return record["trend"]


# =============================================================================
# HELPER NOTE: DuckDB Integration
# =============================================================================

"""
IMPORTANT: This module queries Neo4j for document-level SEC data.

For detailed analytics on insider transactions and institutional holdings,
use the existing DuckDB utilities:

1. Insider Transactions (Forms 3/4/5):
   - src/utils/duckdb_insider_transactions.py
   - InsiderTransactionsDatabase class
   - Methods: query_transactions_by_ticker(), get_insider_summary_stats()

2. Institutional Holdings (Form 13F):
   - src/utils/duckdb_manager.py
   - Form13FDatabase class
   - Methods: query_holdings_by_ticker(), get_holder_trends()

3. Scholarly Papers (for Innovation Layer):
   - src/utils/duckdb_scholarly_analysis.py
   - ScholarlyPapersDatabase class
   - Methods: get_top_papers_by_composite_score()

Example usage in Agent 5 (Risk Scorer):
```python
from src.utils.duckdb_insider_transactions import InsiderTransactionsDatabase

db = InsiderTransactionsDatabase()
transactions = db.query_transactions_by_ticker(
    tickers=['JOBY', 'ACHR'],
    start_date='2024-05-01'
)
net_insider_value = transactions['net_insider_value_usd'].sum()
```
"""
