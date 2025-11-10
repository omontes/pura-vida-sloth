"""
Adoption Queries (Layer 2): Government Contracts, Regulations, Revenue

Intelligence Layer: Market Formation (Leading 12-18 months)
Sources: Government contracts, regulatory filings, SEC revenue mentions
Purpose: Predict when commercialization begins

Key Insight: Government validation precedes market entry by 12+ months.
Regulatory approvals signal market readiness. Revenue mentions show traction.
"""

from typing import List, Dict, Any
from neo4j import AsyncDriver


# =============================================================================
# GOVERNMENT CONTRACT QUERIES
# =============================================================================

async def get_gov_contracts_1yr(
    driver: AsyncDriver,
    tech_id: str,
    start_date: str = "2024-01-01",
    end_date: str = "2025-01-01"
) -> Dict[str, Any]:
    """
    Get government contracts in last 1 year with total value.

    Government contracts are a strong adoption signal: agencies validate
    technology viability before commercial market adoption.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        start_date: Start of analysis window
        end_date: End of analysis window

    Returns:
        {
            "count": int,
            "total_value": float,  # USD
            "agencies": List[str],
            "avg_contract_value": float
        }

    Example:
        >>> result = await get_gov_contracts_1yr(driver, "evtol")
        >>> result
        {
            'count': 8,
            'total_value': 45000000.0,
            'agencies': ['NASA', 'USAF', 'DARPA'],
            'avg_contract_value': 5625000.0
        }
    """
    query = """
    MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type = 'government_contract'
      AND date(datetime(d.published_at)) >= date($start_date)
      AND date(datetime(d.published_at)) < date($end_date)
      AND m.role IN ['deployed', 'funded', 'researched']
      AND d.quality_score >= 0.75
    WITH d, coalesce(d.award_amount, 0.0) AS award_amount
    RETURN
      count(d) AS count,
      sum(award_amount) AS total_value,
      collect(DISTINCT d.awarding_agency)[0..10] AS agencies,
      avg(award_amount) AS avg_contract_value
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, start_date=start_date, end_date=end_date)
        record = await result.single()

        if not record:
            return {
                "count": 0,
                "total_value": 0.0,
                "agencies": [],
                "avg_contract_value": 0.0,
            }

        return {
            "count": record["count"] or 0,
            "total_value": float(record["total_value"] or 0.0),
            "agencies": record["agencies"] or [],
            "avg_contract_value": float(record["avg_contract_value"] or 0.0),
        }


async def get_top_contracts_by_value(
    driver: AsyncDriver,
    tech_id: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Get top government contracts by dollar value with evidence.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        limit: Maximum number of contracts

    Returns:
        List of contract dicts with doc_id, agency, value, evidence, strength

    Example:
        >>> contracts = await get_top_contracts_by_value(driver, "evtol", limit=3)
        >>> contracts[0]
        {
            'doc_id': 'contract_NASA_2024_001',
            'agency': 'NASA',
            'awardee': 'Joby Aviation',
            'value': 15000000.0,
            'date': '2024-03-15',
            'evidence': 'NASA awarded Joby for eVTOL flight testing...',
            'strength': 0.95
        }
    """
    query = """
    MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type = 'government_contract'
      AND m.role IN ['deployed', 'funded', 'researched']
      AND d.quality_score >= 0.75
    WITH d, m, coalesce(d.award_amount, 0.0) AS award_amount
    RETURN
      d.doc_id AS doc_id,
      d.awarding_agency AS agency,
      d.awardee AS awardee,
      award_amount AS value,
      d.published_at AS date,
      m.evidence_text AS evidence,
      m.strength AS strength
    ORDER BY award_amount DESC, d.published_at DESC, d.doc_id ASC
    LIMIT $limit
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, limit=limit)
        records = await result.values()

        return [
            {
                "doc_id": record[0],
                "agency": record[1],
                "awardee": record[2],
                "value": float(record[3]),
                "date": record[4],
                "evidence": record[5],
                "strength": record[6],
            }
            for record in records
        ]


# =============================================================================
# REGULATORY APPROVAL QUERIES
# =============================================================================

async def get_regulatory_approvals(
    driver: AsyncDriver,
    tech_id: str,
    start_date: str = "2023-01-01",
    end_date: str = "2025-01-01"
) -> Dict[str, Any]:
    """
    Get regulatory approvals and filings for this technology.

    Regulatory approvals (FDA, FAA, EPA, etc.) signal market readiness
    and technology maturity.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        start_date: Start of analysis window
        end_date: End of analysis window

    Returns:
        {
            "count": int,
            "agencies": List[str],
            "approval_types": List[str],
            "top_approvals": List[dict]
        }

    Example:
        >>> result = await get_regulatory_approvals(driver, "evtol")
        >>> result
        {
            'count': 5,
            'agencies': ['FAA', 'EASA'],
            'approval_types': ['type_certification', 'airworthiness'],
            'top_approvals': [...]
        }
    """
    query = """
    MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type = 'regulation'
      AND date(datetime(d.published_at)) >= date($start_date)
      AND date(datetime(d.published_at)) < date($end_date)
      AND m.role = 'regulated'
      AND d.quality_score >= 0.75
    WITH d, m
    RETURN
      count(d) AS count,
      collect(DISTINCT d.regulatory_body)[0..10] AS agencies,
      collect(DISTINCT d.document_type)[0..10] AS approval_types,
      collect({
        doc_id: d.doc_id,
        agency: d.regulatory_body,
        type: d.document_type,
        date: d.published_at,
        evidence: m.evidence_text,
        strength: m.strength
      })[0..5] AS top_approvals
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, start_date=start_date, end_date=end_date)
        record = await result.single()

        if not record:
            return {
                "count": 0,
                "agencies": [],
                "approval_types": [],
                "top_approvals": [],
            }

        return {
            "count": record["count"] or 0,
            "agencies": record["agencies"] or [],
            "approval_types": record["approval_types"] or [],
            "top_approvals": record["top_approvals"] or [],
        }


# =============================================================================
# REVENUE MENTION QUERIES (SEC Filings)
# =============================================================================

async def get_revenue_mentions_by_company(
    driver: AsyncDriver,
    tech_id: str,
    start_date: str = "2024-01-01",
    end_date: str = "2025-01-01"
) -> List[Dict[str, Any]]:
    """
    Get companies mentioning this technology in revenue context (SEC filings).

    Revenue mentions in SEC filings (10-K, 10-Q) indicate commercial traction.
    Companies only discuss revenue when products are shipping.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        start_date: Start of analysis window
        end_date: End of analysis window

    Returns:
        List of revenue mention dicts with company, ticker, filing, evidence

    Example:
        >>> mentions = await get_revenue_mentions_by_company(driver, "evtol")
        >>> mentions[0]
        {
            'company': 'Joby Aviation',
            'ticker': 'JOBY',
            'fiscal_period': 'Q3 2024',
            'date': '2024-11-08',
            'doc_type': 'sec_filing',
            'evidence': 'Revenue from eVTOL pre-orders increased 45%...',
            'strength': 0.88
        }
    """
    query = """
    MATCH (c:Company)-[r:RELATED_TO_TECH]->(t:Technology {id: $tech_id})
    MATCH (c)-[:RELATED_TO_TECH]->(t)-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type = 'sec_filing'
      AND date(datetime(d.published_at)) >= date($start_date)
      AND date(datetime(d.published_at)) < date($end_date)
      AND (m.evidence_text CONTAINS 'revenue' OR m.evidence_text CONTAINS 'sales')
      AND d.quality_score >= 0.75
    RETURN
      c.name AS company,
      c.ticker AS ticker,
      d.fiscal_period AS fiscal_period,
      d.published_at AS date,
      d.doc_type AS doc_type,
      m.evidence_text AS evidence,
      m.strength AS strength
    ORDER BY d.published_at DESC, m.strength DESC, d.doc_id ASC
    LIMIT 20
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, start_date=start_date, end_date=end_date)
        records = await result.values()

        return [
            {
                "company": record[0],
                "ticker": record[1],
                "fiscal_period": record[2],
                "date": record[3],
                "doc_type": record[4],
                "evidence": record[5],
                "strength": record[6],
            }
            for record in records
        ]


# =============================================================================
# COMPANY ADOPTION ANALYSIS
# =============================================================================

async def get_companies_developing_tech(
    driver: AsyncDriver,
    tech_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get companies actively developing this technology (high PageRank).

    Uses company PageRank to prioritize influential companies (well-connected,
    important players) over startups.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        limit: Maximum number of companies

    Returns:
        List of company dicts with name, ticker, pagerank, relation_type

    Example:
        >>> companies = await get_companies_developing_tech(driver, "evtol")
        >>> companies[0]
        {
            'name': 'Joby Aviation',
            'ticker': 'JOBY',
            'pagerank': 0.0045,
            'relation_type': 'develops',
            'evidence': 'Joby is developing eVTOL aircraft for air taxi services',
            'confidence': 0.95
        }
    """
    query = """
    MATCH (c:Company)-[r:RELATED_TO_TECH]->(t:Technology {id: $tech_id})
    WHERE r.relation_type IN ['adopts', 'develops']
      AND c.pagerank IS NOT NULL
    RETURN
      c.name AS name,
      c.ticker AS ticker,
      c.pagerank AS pagerank,
      r.relation_type AS relation_type,
      r.evidence_text AS evidence,
      r.evidence_confidence AS confidence
    ORDER BY c.pagerank DESC, c.name ASC
    LIMIT $limit
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, limit=limit)
        records = await result.values()

        return [
            {
                "name": record[0],
                "ticker": record[1],
                "pagerank": record[2],
                "relation_type": record[3],
                "evidence": record[4],
                "confidence": record[5],
            }
            for record in records
        ]


async def get_adoption_temporal_trend(
    driver: AsyncDriver,
    tech_id: str,
    window_months: int = 6
) -> str:
    """
    Analyze adoption trend over time (growing, stable, declining).

    Compares recent government contract activity + regulatory approvals
    to historical average.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        window_months: Number of months for recent window

    Returns:
        "growing" | "stable" | "declining"
    """
    query = """
    MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type IN ['government_contract', 'regulation']
      AND m.role IN ['procured', 'regulated']
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
        WHEN recent_rate > historical_rate * 1.2 THEN 'growing'
        WHEN recent_rate < historical_rate * 0.8 THEN 'declining'
        ELSE 'stable'
      END AS trend
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, window_months=window_months)
        record = await result.single()

        if not record or record["trend"] is None:
            return "stable"

        return record["trend"]
