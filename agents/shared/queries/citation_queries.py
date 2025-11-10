"""
Citation Queries: Evidence Retrieval and Source Citation Tracing

Provides transparent provenance from graph → agent scores → chart output.
Every score must link back to source documents with evidence text.

Key Insight: Reproducibility requires full citation tracing. Users must be
able to verify each agent's reasoning by inspecting source documents.
"""

from typing import List, Dict, Any, Optional
from neo4j import AsyncDriver


# =============================================================================
# LAYER-SPECIFIC CITATION QUERIES
# =============================================================================

async def get_layer_citations(
    driver: AsyncDriver,
    tech_id: str,
    doc_types: List[str],
    roles: List[str],
    start_date: str,
    end_date: Optional[str] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Get top citations for a specific intelligence layer.

    Returns documents with evidence text showing WHY the technology is mentioned.
    Used by Agent 11 (Evidence Compiler) to trace layer scores back to sources.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        doc_types: Document types for this layer (e.g., ['patent', 'technical_paper'])
        roles: Relationship roles (e.g., ['invented', 'studied'])
        start_date: Start of analysis window
        end_date: End of analysis window (optional)
        limit: Maximum number of citations

    Returns:
        List of citation dicts with doc_id, title, contribution, strength

    Example - Innovation Layer (Layer 1):
        >>> citations = await get_layer_citations(
        ...     driver,
        ...     tech_id="evtol",
        ...     doc_types=['patent', 'technical_paper'],
        ...     roles=['invented', 'studied'],
        ...     start_date='2023-01-01',
        ...     end_date='2025-01-01',
        ...     limit=5
        ... )
        >>> citations[0]
        {
            'doc_id': 'US20230123456',
            'title': 'Electric VTOL propulsion system',
            'doc_type': 'patent',
            'published_at': '2023-06-15',
            'role': 'invented',
            'strength': 0.92,
            'evidence_text': 'Patent describes novel eVTOL battery architecture...',
            'evidence_confidence': 0.95,
            'contribution': 'Foundational patent for electric propulsion systems'
        }
    """
    # Build end_date filter
    end_date_filter = ""
    if end_date:
        end_date_filter = "AND date(datetime(d.published_at)) < date($end_date)"

    query = f"""
    MATCH (t:Technology {{id: $tech_id}})-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type IN $doc_types
      AND m.role IN $roles
      AND date(datetime(d.published_at)) >= date($start_date)
      {end_date_filter}
      AND d.quality_score >= 0.75
      AND m.evidence_confidence >= 0.75
    RETURN
      d.doc_id AS doc_id,
      d.title AS title,
      d.doc_type AS doc_type,
      d.published_at AS published_at,
      m.role AS role,
      m.strength AS strength,
      m.evidence_text AS evidence_text,
      m.evidence_confidence AS evidence_confidence
    ORDER BY m.strength DESC, m.evidence_confidence DESC, d.published_at DESC, d.doc_id ASC
    LIMIT $limit
    """

    params = {
        "tech_id": tech_id,
        "doc_types": doc_types,
        "roles": roles,
        "start_date": start_date,
        "limit": limit,
    }

    if end_date:
        params["end_date"] = end_date

    async with driver.session() as session:
        result = await session.run(query, **params)
        records = await result.values()

        return [
            {
                "doc_id": record[0],
                "title": record[1],
                "doc_type": record[2],
                "published_at": record[3],
                "role": record[4],
                "strength": record[5],
                "evidence_text": record[6],
                "evidence_confidence": record[7],
                "contribution": f"{record[2].replace('_', ' ').title()} showing {record[4]} relationship",
            }
            for record in records
        ]


# =============================================================================
# INTELLIGENCE LAYER CITATION HELPERS
# =============================================================================

async def get_innovation_citations(
    driver: AsyncDriver,
    tech_id: str,
    start_date: str = "2023-01-01",
    end_date: str = "2025-01-01",
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Get innovation layer citations (patents, papers, GitHub).

    Wrapper for get_layer_citations() with Innovation layer defaults.
    """
    return await get_layer_citations(
        driver=driver,
        tech_id=tech_id,
        doc_types=["patent", "technical_paper", "github"],
        roles=["invented", "studied"],
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )


async def get_adoption_citations(
    driver: AsyncDriver,
    tech_id: str,
    start_date: str = "2023-07-01",
    end_date: str = "2025-01-01",
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Get adoption layer citations (gov contracts, regulations).

    Wrapper for get_layer_citations() with Adoption layer defaults.
    """
    return await get_layer_citations(
        driver=driver,
        tech_id=tech_id,
        doc_types=["government_contract", "regulation", "sec_filing"],
        roles=["procured", "regulated"],
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )


async def get_narrative_citations(
    driver: AsyncDriver,
    tech_id: str,
    start_date: str = "2024-07-01",
    end_date: str = "2025-01-01",
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Get narrative layer citations (news articles, press releases).

    Wrapper for get_layer_citations() with Narrative layer defaults.
    """
    return await get_layer_citations(
        driver=driver,
        tech_id=tech_id,
        doc_types=["news", "press_release"],
        roles=["subject"],
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )


async def get_risk_citations(
    driver: AsyncDriver,
    tech_id: str,
    start_date: str = "2024-07-01",
    end_date: str = "2025-01-01",
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Get risk layer citations (SEC filings with risk mentions).

    Wrapper for get_layer_citations() with Risk layer defaults.
    """
    return await get_layer_citations(
        driver=driver,
        tech_id=tech_id,
        doc_types=["sec_filing"],
        roles=["regulated"],
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )


# =============================================================================
# AGGREGATE EVIDENCE BY DOCUMENT TYPE
# =============================================================================

async def get_evidence_distribution_by_doc_type(
    driver: AsyncDriver,
    tech_id: str,
    days_back: int = 730,
    sample_per_type: int = 3
) -> List[Dict[str, Any]]:
    """
    Group evidence by document type to show distribution.

    Returns evidence count per doc type + sample citations for each type.
    Used by Agent 11 to create evidence distribution summary.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        days_back: Number of days to look back
        sample_per_type: Number of sample citations per doc type

    Returns:
        List of doc type dicts with counts and sample evidence

    Example:
        >>> distribution = await get_evidence_distribution_by_doc_type(driver, "evtol")
        >>> distribution[0]
        {
            'doc_type': 'patent',
            'evidence_count': 42,
            'sample_evidences': [
                {
                    'doc_id': 'US20230123456',
                    'title': '...',
                    'role': 'invented',
                    'strength': 0.92,
                    'evidence_text': '...'
                },
                ...
            ]
        }
    """
    query = """
    MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
    WHERE datetime(d.published_at) >= datetime() - duration({days: $days_back})
      AND d.quality_score >= 0.75
    WITH d.doc_type AS doc_type,
         collect({
           doc_id: d.doc_id,
           title: d.title,
           role: m.role,
           strength: m.strength,
           evidence_confidence: m.evidence_confidence,
           evidence_text: m.evidence_text
         })[0..$sample_per_type] AS sample_evidences,
         count(m) AS evidence_count
    RETURN
      doc_type,
      evidence_count,
      sample_evidences
    ORDER BY evidence_count DESC
    """

    async with driver.session() as session:
        result = await session.run(
            query,
            tech_id=tech_id,
            days_back=days_back,
            sample_per_type=sample_per_type
        )
        records = await result.values()

        return [
            {
                "doc_type": record[0],
                "evidence_count": record[1],
                "sample_evidences": record[2],
            }
            for record in records
        ]


# =============================================================================
# CO-OCCURRENCE ANALYSIS (Related Technologies)
# =============================================================================

async def get_co_mentioned_technologies(
    driver: AsyncDriver,
    tech_id: str,
    days_back: int = 730,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Find technologies mentioned in same documents (co-occurrence).

    Identifies related technologies based on shared document mentions.
    Used by Agent 6 (Hype Scorer) to find context and Agent 11 for recommendations.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        days_back: Number of days to look back
        limit: Maximum number of co-mentioned technologies

    Returns:
        List of co-mentioned technology dicts

    Example:
        >>> co_mentioned = await get_co_mentioned_technologies(driver, "evtol")
        >>> co_mentioned[0]
        {
            'tech_id': 'electric_propulsion',
            'tech_name': 'Electric Propulsion',
            'shared_doc_count': 23,
            'shared_doc_types': ['patent', 'news', 'technical_paper'],
            'sample_shared_doc': {
                'doc_id': 'patent_US20230123',
                'title': '...',
                'evidence_main': 'eVTOL mentioned because...',
                'evidence_other': 'Electric propulsion mentioned because...'
            }
        }
    """
    query = """
    MATCH (t:Technology {id: $tech_id})-[m1:MENTIONED_IN]->(d:Document)<-[m2:MENTIONED_IN]-(other:Technology)
    WHERE other.id <> t.id
      AND datetime(d.published_at) >= datetime() - duration({days: $days_back})
      AND d.quality_score >= 0.75
    WITH other, d, m1, m2
    WITH other,
         count(DISTINCT d) AS shared_doc_count,
         collect(DISTINCT d.doc_type) AS shared_doc_types,
         collect({
           doc_id: d.doc_id,
           title: d.title,
           evidence_main: m1.evidence_text,
           evidence_other: m2.evidence_text
         })[0] AS sample_shared_doc
    RETURN
      other.id AS tech_id,
      other.name AS tech_name,
      shared_doc_count,
      shared_doc_types,
      sample_shared_doc
    ORDER BY shared_doc_count DESC
    LIMIT $limit
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, days_back=days_back, limit=limit)
        records = await result.values()

        return [
            {
                "tech_id": record[0],
                "tech_name": record[1],
                "shared_doc_count": record[2],
                "shared_doc_types": record[3],
                "sample_shared_doc": record[4],
            }
            for record in records
        ]


# =============================================================================
# MULTI-HOP EVIDENCE PATHS (Company → Technology → Document)
# =============================================================================

async def get_company_tech_document_provenance(
    driver: AsyncDriver,
    tech_id: str,
    days_back: int = 365,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Trace company → technology → document evidence paths.

    Multi-hop provenance showing:
    1. Why company is related to technology (company_evidence)
    2. Why technology is mentioned in document (doc_evidence)

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        days_back: Number of days to look back
        limit: Maximum number of paths

    Returns:
        List of provenance path dicts

    Example:
        >>> paths = await get_company_tech_document_provenance(driver, "evtol")
        >>> paths[0]
        {
            'company': 'Joby Aviation',
            'company_relation': 'develops',
            'company_evidence': 'Joby is developing eVTOL aircraft...',
            'company_confidence': 0.95,
            'doc_id': 'sec_filing_JOBY_10Q_2024Q3',
            'doc_type': 'sec_filing',
            'doc_role': 'subject',
            'doc_evidence': 'SEC filing discusses eVTOL certification progress...',
            'doc_confidence': 0.88,
            'published_at': '2024-11-08'
        }
    """
    query = """
    MATCH (c:Company)-[r:RELATED_TO_TECH]->(t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
    WHERE datetime(d.published_at) >= datetime() - duration({days: $days_back})
      AND d.quality_score >= 0.75
    RETURN
      c.name AS company,
      r.relation_type AS company_relation,
      r.evidence_text AS company_evidence,
      r.evidence_confidence AS company_confidence,
      d.doc_id AS doc_id,
      d.doc_type AS doc_type,
      m.role AS doc_role,
      m.evidence_text AS doc_evidence,
      m.evidence_confidence AS doc_confidence,
      d.published_at AS published_at
    ORDER BY d.published_at DESC, r.evidence_confidence DESC, m.evidence_confidence DESC
    LIMIT $limit
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, days_back=days_back, limit=limit)
        records = await result.values()

        return [
            {
                "company": record[0],
                "company_relation": record[1],
                "company_evidence": record[2],
                "company_confidence": record[3],
                "doc_id": record[4],
                "doc_type": record[5],
                "doc_role": record[6],
                "doc_evidence": record[7],
                "doc_confidence": record[8],
                "published_at": record[9],
            }
            for record in records
        ]


# =============================================================================
# GRAPHRAG TRIPLETS FOR LLM CONTEXT
# =============================================================================

async def get_evidence_triplets_for_llm(
    driver: AsyncDriver,
    tech_id: str,
    days_back: int = 730,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get evidence in Subject-Predicate-Object triplet format for LLM reasoning.

    Structured format optimized for LLM context windows:
    (Technology, invented, Document)
    (Technology, procured, Document)
    etc.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        days_back: Number of days to look back
        limit: Maximum number of triplets

    Returns:
        List of triplet dicts

    Example:
        >>> triplets = await get_evidence_triplets_for_llm(driver, "evtol")
        >>> triplets[0]
        {
            'subject': 'eVTOL',
            'predicate': 'invented',
            'object': 'patent_US20230123456',
            'object_type': 'patent',
            'evidence_confidence': 0.95,
            'evidence_text': 'Patent describes eVTOL battery architecture...'
        }
    """
    query = """
    MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
    WHERE datetime(d.published_at) >= datetime() - duration({days: $days_back})
      AND d.quality_score >= 0.75
      AND m.evidence_confidence >= 0.75
    RETURN
      t.name AS subject,
      m.role AS predicate,
      d.doc_id AS object,
      d.doc_type AS object_type,
      m.evidence_confidence AS evidence_confidence,
      m.evidence_text AS evidence_text
    ORDER BY m.evidence_confidence DESC, t.name ASC, d.doc_id ASC
    LIMIT $limit
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, days_back=days_back, limit=limit)
        records = await result.values()

        return [
            {
                "subject": record[0],
                "predicate": record[1],
                "object": record[2],
                "object_type": record[3],
                "evidence_confidence": record[4],
                "evidence_text": record[5],
            }
            for record in records
        ]
