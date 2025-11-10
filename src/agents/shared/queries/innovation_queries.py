"""
Innovation Queries (Layer 1): Patents, Research Papers, GitHub Activity

Intelligence Layer: Innovation Signals (Leading 18-24 months)
Sources: Patents, technical papers, GitHub repositories
Purpose: Predict technology emergence before commercialization

Key Insight: Patent surges and research activity happen 18-24 months
before products ship. High PageRank patents indicate foundational innovations.
"""

from typing import List, Dict, Any, Optional
from neo4j import AsyncDriver


# =============================================================================
# PATENT QUERIES (with PageRank weighting)
# =============================================================================

async def get_patent_count_2yr(
    driver: AsyncDriver,
    tech_id: str,
    start_date: str = "2023-01-01",
    end_date: str = "2025-01-01"
) -> Dict[str, Any]:
    """
    Count patents filed in last 2 years with PageRank weighting.

    PageRank reveals patent importance: high-PageRank patents are cited
    by other important patents (foundational vs incremental innovations).

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        start_date: Start of analysis window (ISO date string)
        end_date: End of analysis window (ISO date string)

    Returns:
        {
            "patent_count": int,
            "total_citations": int,
            "avg_pagerank": float,
            "pagerank_weighted_count": float  # Patents weighted by importance
        }

    Example:
        >>> result = await get_patent_count_2yr(driver, "evtol")
        >>> result
        {'patent_count': 42, 'total_citations': 287, 'avg_pagerank': 0.0023}
    """
    query = """
    MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type = 'patent'
      AND date(datetime(d.published_at)) >= date($start_date)
      AND date(datetime(d.published_at)) < date($end_date)
      AND m.role = 'invented'
      AND d.quality_score >= 0.75
    WITH d, coalesce(d.pagerank, 0.0) as pagerank
    RETURN
      count(d) AS patent_count,
      sum(coalesce(d.citation_count, 0)) AS total_citations,
      avg(pagerank) AS avg_pagerank,
      sum(1.0 + (pagerank * 100)) AS pagerank_weighted_count
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, start_date=start_date, end_date=end_date)
        record = await result.single()

        if not record:
            return {
                "patent_count": 0,
                "total_citations": 0,
                "avg_pagerank": 0.0,
                "pagerank_weighted_count": 0.0,
            }

        return {
            "patent_count": record["patent_count"] or 0,
            "total_citations": record["total_citations"] or 0,
            "avg_pagerank": record["avg_pagerank"] or 0.0,
            "pagerank_weighted_count": record["pagerank_weighted_count"] or 0.0,
        }


async def get_top_patents_by_citations(
    driver: AsyncDriver,
    tech_id: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Get top-cited patents with evidence text and PageRank.

    Returns the most influential patents for this technology, ranked by
    citation count and PageRank (importance).

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        limit: Maximum number of patents to return

    Returns:
        List of dicts with:
            - doc_id: Patent ID
            - title: Patent title
            - citations: Citation count
            - published_at: Publication date
            - pagerank: Importance score
            - evidence: Why this technology is mentioned
            - strength: Relevance strength (0.0-1.0)

    Example:
        >>> patents = await get_top_patents_by_citations(driver, "evtol", limit=3)
        >>> patents[0]
        {
            'doc_id': 'US20230123456',
            'title': 'Electric VTOL propulsion system',
            'citations': 45,
            'published_at': '2023-06-15',
            'pagerank': 0.0045,
            'evidence': 'Patent describes novel eVTOL battery architecture...',
            'strength': 0.92
        }
    """
    query = """
    MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type = 'patent'
      AND m.role = 'invented'
      AND d.quality_score >= 0.75
    RETURN
      d.doc_id AS doc_id,
      d.title AS title,
      coalesce(d.citation_count, 0) AS citations,
      d.published_at AS published_at,
      coalesce(d.pagerank, 0.0) AS pagerank,
      m.evidence_text AS evidence,
      m.strength AS strength
    ORDER BY citations DESC, pagerank DESC, d.doc_id ASC
    LIMIT $limit
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, limit=limit)
        records = await result.values()

        return [
            {
                "doc_id": record[0],
                "title": record[1],
                "citations": record[2],
                "published_at": record[3],
                "pagerank": record[4],
                "evidence": record[5],
                "strength": record[6],
            }
            for record in records
        ]


async def get_community_patents(
    driver: AsyncDriver,
    tech_id: str,
    community_version: str = "v1",
    start_date: str = "2023-01-01",
    end_date: str = "2025-01-01"
) -> int:
    """
    Count related patents in the same community.

    Uses technology's community assignment to find related innovations
    within the same innovation cluster.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        community_version: Community version ("v0", "v1", "v2", etc.)
        start_date: Start of analysis window
        end_date: End of analysis window

    Returns:
        Count of patents in the same community

    Example:
        >>> count = await get_community_patents(driver, "evtol", "v1")
        >>> count
        127  # Other eVTOL-related patents in same innovation cluster
    """
    query = f"""
    MATCH (t:Technology {{id: $tech_id}})
    WITH t, t.community_{community_version} AS community_id
    WHERE community_id IS NOT NULL
    MATCH (other:Technology)-[m:MENTIONED_IN]->(d:Document)
    WHERE other.community_{community_version} = community_id
      AND d.doc_type = 'patent'
      AND date(datetime(d.published_at)) >= date($start_date)
      AND date(datetime(d.published_at)) < date($end_date)
      AND d.quality_score >= 0.75
    RETURN count(DISTINCT d) AS community_patent_count
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, start_date=start_date, end_date=end_date)
        record = await result.single()

        if not record:
            return 0

        return record["community_patent_count"] or 0


# =============================================================================
# RESEARCH PAPER QUERIES
# =============================================================================

async def get_paper_count_2yr(
    driver: AsyncDriver,
    tech_id: str,
    start_date: str = "2023-01-01",
    end_date: str = "2025-01-01"
) -> Dict[str, Any]:
    """
    Count research papers published in last 2 years.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        start_date: Start of analysis window
        end_date: End of analysis window

    Returns:
        {
            "paper_count": int,
            "total_citations": int,
            "avg_pagerank": float
        }
    """
    query = """
    MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type = 'technical_paper'
      AND date(datetime(d.published_at)) >= date($start_date)
      AND date(datetime(d.published_at)) < date($end_date)
      AND m.role IN ['invented', 'studied']
      AND d.quality_score >= 0.75
    RETURN
      count(d) AS paper_count,
      sum(coalesce(d.citation_count, 0)) AS total_citations,
      avg(coalesce(d.pagerank, 0.0)) AS avg_pagerank
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, start_date=start_date, end_date=end_date)
        record = await result.single()

        if not record:
            return {"paper_count": 0, "total_citations": 0, "avg_pagerank": 0.0}

        return {
            "paper_count": record["paper_count"] or 0,
            "total_citations": record["total_citations"] or 0,
            "avg_pagerank": record["avg_pagerank"] or 0.0,
        }


async def get_top_papers_by_citations(
    driver: AsyncDriver,
    tech_id: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Get top-cited research papers with evidence.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        limit: Maximum number of papers

    Returns:
        List of paper dicts with doc_id, title, citations, evidence, strength
    """
    query = """
    MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type = 'technical_paper'
      AND m.role IN ['invented', 'studied']
      AND d.quality_score >= 0.75
    RETURN
      d.doc_id AS doc_id,
      d.title AS title,
      coalesce(d.citation_count, 0) AS citations,
      d.published_at AS published_at,
      coalesce(d.pagerank, 0.0) AS pagerank,
      m.evidence_text AS evidence,
      m.strength AS strength
    ORDER BY citations DESC, pagerank DESC, d.doc_id ASC
    LIMIT $limit
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, limit=limit)
        records = await result.values()

        return [
            {
                "doc_id": record[0],
                "title": record[1],
                "citations": record[2],
                "published_at": record[3],
                "pagerank": record[4],
                "evidence": record[5],
                "strength": record[6],
            }
            for record in records
        ]


# =============================================================================
# GITHUB ACTIVITY QUERIES
# =============================================================================

async def get_github_repo_count(
    driver: AsyncDriver,
    tech_id: str,
    start_date: str = "2023-01-01",
    end_date: str = "2025-01-01"
) -> Dict[str, Any]:
    """
    Count active GitHub repositories for this technology.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        start_date: Start of analysis window
        end_date: End of analysis window

    Returns:
        {
            "repo_count": int,
            "total_stars": int,
            "total_forks": int,
            "avg_activity_score": float
        }
    """
    query = """
    MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type = 'github'
      AND date(datetime(d.published_at)) >= date($start_date)
      AND date(datetime(d.published_at)) < date($end_date)
      AND d.quality_score >= 0.75
    RETURN
      count(d) AS repo_count,
      sum(coalesce(d.stars, 0)) AS total_stars,
      sum(coalesce(d.forks, 0)) AS total_forks,
      avg(coalesce(d.activity_score, 0.0)) AS avg_activity_score
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, start_date=start_date, end_date=end_date)
        record = await result.single()

        if not record:
            return {
                "repo_count": 0,
                "total_stars": 0,
                "total_forks": 0,
                "avg_activity_score": 0.0,
            }

        return {
            "repo_count": record["repo_count"] or 0,
            "total_stars": record["total_stars"] or 0,
            "total_forks": record["total_forks"] or 0,
            "avg_activity_score": record["avg_activity_score"] or 0.0,
        }


# =============================================================================
# TEMPORAL TREND ANALYSIS
# =============================================================================

async def get_innovation_temporal_trend(
    driver: AsyncDriver,
    tech_id: str,
    window_months: int = 6
) -> str:
    """
    Analyze innovation trend over time (growing, stable, declining).

    Compares recent activity (last 6 months) to historical average to
    determine if innovation is accelerating or slowing.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        window_months: Number of months for recent window

    Returns:
        "growing" | "stable" | "declining"

    Example:
        >>> trend = await get_innovation_temporal_trend(driver, "evtol")
        >>> trend
        "growing"  # Innovation activity increasing
    """
    query = """
    MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type IN ['patent', 'technical_paper', 'github']
      AND m.role IN ['invented', 'studied']
      AND d.quality_score >= 0.75
    WITH d,
         date(datetime(d.published_at)) AS pub_date,
         date() - duration({months: $window_months}) AS cutoff_date
    WITH
      count(CASE WHEN pub_date >= cutoff_date THEN 1 END) AS recent_count,
      count(CASE WHEN pub_date < cutoff_date THEN 1 END) AS historical_count,
      count(d) AS total_count
    WITH
      recent_count,
      historical_count,
      total_count,
      toFloat(recent_count) / $window_months AS recent_rate,
      toFloat(historical_count) / CASE WHEN total_count - recent_count > 0
                                       THEN (total_count - recent_count) / 12.0
                                       ELSE 1.0 END AS historical_rate
    RETURN
      recent_rate,
      historical_rate,
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
