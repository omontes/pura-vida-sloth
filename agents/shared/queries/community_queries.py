"""
Community Queries: Community-Based Filtering and Analysis

Uses pre-computed community assignments (v0-v5) for:
- Finding related technologies in same innovation cluster
- Semantic search across communities using embeddings
- Community composition analysis (tech vs company ratio)
- Cross-community technology discovery

Key Insight: Communities reveal innovation clusters. Technologies in the same
community are conceptually related even if not directly connected.
"""

from typing import List, Dict, Any, Optional
from neo4j import AsyncDriver


# =============================================================================
# TECHNOLOGY COMMUNITY QUERIES
# =============================================================================

async def get_technology_community(
    driver: AsyncDriver,
    tech_id: str,
    version: str = "v1"
) -> Optional[int]:
    """
    Get technology's community ID from node property.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        version: Community version ("v0", "v1", "v2", "v3", "v4", "v5")

    Returns:
        Community ID (int) or None if not assigned

    Example:
        >>> community_id = await get_technology_community(driver, "evtol", "v1")
        >>> community_id
        42  # eVTOL belongs to community 42 in v1
    """
    query = f"""
    MATCH (t:Technology {{id: $tech_id}})
    RETURN t.community_{version} AS community_id
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id)
        record = await result.single()

        if not record or record["community_id"] is None:
            return None

        return record["community_id"]


# =============================================================================
# COMMUNITY NODE QUERIES
# =============================================================================

async def get_community_summary(
    driver: AsyncDriver,
    community_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get full Community node details including LLM summary and metadata.

    Community nodes contain:
    - LLM-generated summary (1-2 sentences)
    - 768-dim embedding for semantic search
    - Top technologies, companies
    - Document type distribution
    - Member count statistics

    Args:
        driver: Neo4j async driver
        community_id: Community ID (e.g., "v1_42")

    Returns:
        Community summary dict or None if not found

    Example:
        >>> summary = await get_community_summary(driver, "v1_42")
        >>> summary
        {
            'id': 'v1_42',
            'version': 1,
            'algorithm': 'Louvain',
            'resolution': 1.0,
            'summary': 'Electric vertical takeoff and landing aircraft...',
            'member_count': 85,
            'tech_count': 12,
            'company_count': 8,
            'doc_count': 65,
            'top_technologies': ['eVTOL', 'electric propulsion', ...],
            'top_companies': ['Joby Aviation', 'Archer Aviation', ...],
            'doc_type_distribution': {'patent': 35, 'news': 20, ...}
        }
    """
    query = """
    MATCH (c:Community {id: $community_id})
    RETURN
      c.id AS id,
      c.version AS version,
      c.algorithm AS algorithm,
      c.resolution AS resolution,
      c.summary AS summary,
      c.member_count AS member_count,
      c.tech_count AS tech_count,
      c.company_count AS company_count,
      c.doc_count AS doc_count,
      c.top_technologies AS top_technologies,
      c.top_companies AS top_companies,
      c.doc_type_distribution AS doc_type_distribution
    """

    async with driver.session() as session:
        result = await session.run(query, community_id=community_id)
        record = await result.single()

        if not record:
            return None

        # Parse JSON string for doc_type_distribution
        import json
        doc_type_dist = record["doc_type_distribution"]
        if isinstance(doc_type_dist, str):
            doc_type_dist = json.loads(doc_type_dist)

        return {
            "id": record["id"],
            "version": record["version"],
            "algorithm": record["algorithm"],
            "resolution": record["resolution"],
            "summary": record["summary"],
            "member_count": record["member_count"],
            "tech_count": record["tech_count"],
            "company_count": record["company_count"],
            "doc_count": record["doc_count"],
            "top_technologies": record["top_technologies"],
            "top_companies": record["top_companies"],
            "doc_type_distribution": doc_type_dist,
        }


async def get_community_by_text_search(
    driver: AsyncDriver,
    search_text: str,
    version: int = 1,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Find communities by text search on summaries (keyword matching).

    Args:
        driver: Neo4j async driver
        search_text: Search keyword (e.g., "battery", "autonomous vehicle")
        version: Community version (0-5)
        limit: Maximum number of communities

    Returns:
        List of community dicts

    Example:
        >>> communities = await get_community_by_text_search(driver, "battery", version=1)
        >>> communities[0]
        {
            'id': 'v1_23',
            'summary': 'Solid-state battery technology development...',
            'member_count': 67,
            'top_technologies': ['solid-state battery', 'lithium metal', ...]
        }
    """
    query = """
    MATCH (c:Community)
    WHERE c.version = $version
      AND (toLower(c.summary) CONTAINS toLower($search_text) OR
           ANY(tech IN c.top_technologies WHERE toLower(tech) CONTAINS toLower($search_text)))
    RETURN
      c.id AS id,
      c.summary AS summary,
      c.member_count AS member_count,
      c.top_technologies AS top_technologies,
      c.top_companies AS top_companies
    ORDER BY c.member_count DESC
    LIMIT $limit
    """

    async with driver.session() as session:
        result = await session.run(query, search_text=search_text, version=version, limit=limit)
        records = await result.values()

        return [
            {
                "id": record[0],
                "summary": record[1],
                "member_count": record[2],
                "top_technologies": record[3],
                "top_companies": record[4],
            }
            for record in records
        ]


async def get_similar_communities_by_embedding(
    driver: AsyncDriver,
    query_embedding: List[float],
    version: int = 1,
    similarity_threshold: float = 0.8,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Find semantically similar communities using vector similarity (cosine).

    Uses community embeddings to find conceptually related innovation clusters.

    Args:
        driver: Neo4j async driver
        query_embedding: Query embedding vector (768-dim)
        version: Community version (0-5)
        similarity_threshold: Minimum cosine similarity (0.0-1.0)
        limit: Maximum number of communities

    Returns:
        List of similar community dicts with similarity scores

    Example:
        >>> from openai import OpenAI
        >>> client = OpenAI()
        >>> embedding = client.embeddings.create(
        ...     model="text-embedding-3-small",
        ...     input="electric vehicle battery technology"
        ... ).data[0].embedding
        >>> communities = await get_similar_communities_by_embedding(
        ...     driver, embedding, version=1
        ... )
        >>> communities[0]
        {
            'id': 'v1_23',
            'summary': 'Battery technology innovations...',
            'similarity_score': 0.92,
            'member_count': 67
        }
    """
    query = """
    MATCH (c:Community)
    WHERE c.version = $version
      AND c.embedding IS NOT NULL
    WITH c,
         gds.similarity.cosine($query_embedding, c.embedding) AS similarity_score
    WHERE similarity_score >= $similarity_threshold
    RETURN
      c.id AS id,
      c.summary AS summary,
      c.member_count AS member_count,
      c.top_technologies AS top_technologies,
      similarity_score AS similarity_score
    ORDER BY similarity_score DESC
    LIMIT $limit
    """

    async with driver.session() as session:
        result = await session.run(
            query,
            query_embedding=query_embedding,
            version=version,
            similarity_threshold=similarity_threshold,
            limit=limit
        )
        records = await result.values()

        return [
            {
                "id": record[0],
                "summary": record[1],
                "member_count": record[2],
                "top_technologies": record[3],
                "similarity_score": record[4],
            }
            for record in records
        ]


# =============================================================================
# COMMUNITY MEMBER QUERIES
# =============================================================================

async def get_community_members(
    driver: AsyncDriver,
    community_id: str,
    limit: int = 25
) -> List[Dict[str, Any]]:
    """
    Get all members of a specific community via BELONGS_TO_COMMUNITY relationship.

    Args:
        driver: Neo4j async driver
        community_id: Community ID (e.g., "v1_42")
        limit: Maximum number of members

    Returns:
        List of member dicts with node_type, identifier, importance

    Example:
        >>> members = await get_community_members(driver, "v1_42", limit=10)
        >>> members[0]
        {
            'node_type': 'Technology',
            'identifier': 'eVTOL',
            'importance': 0.0045  # PageRank
        }
    """
    query = """
    MATCH (n)-[:BELONGS_TO_COMMUNITY]->(c:Community {id: $community_id})
    RETURN
      labels(n)[0] AS node_type,
      coalesce(n.name, n.id, n.doc_id) AS identifier,
      coalesce(n.pagerank, 0.0) AS importance
    ORDER BY importance DESC NULLS LAST, identifier ASC
    LIMIT $limit
    """

    async with driver.session() as session:
        result = await session.run(query, community_id=community_id, limit=limit)
        records = await result.values()

        return [
            {
                "node_type": record[0],
                "identifier": record[1],
                "importance": record[2],
            }
            for record in records
        ]


# =============================================================================
# RELATED TECHNOLOGY QUERIES
# =============================================================================

async def get_related_technologies_in_community(
    driver: AsyncDriver,
    tech_id: str,
    version: str = "v1",
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Find related technologies in same community, ranked by PageRank.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        version: Community version ("v0"-"v5")
        limit: Maximum number of related technologies

    Returns:
        List of related technology dicts

    Example:
        >>> related = await get_related_technologies_in_community(driver, "evtol", "v1")
        >>> related[0]
        {
            'id': 'electric_propulsion',
            'name': 'Electric Propulsion',
            'pagerank': 0.0038,
            'community_id': 42
        }
    """
    query = f"""
    MATCH (t:Technology {{id: $tech_id}})
    WITH t, t.community_{version} AS community_id
    WHERE community_id IS NOT NULL
    MATCH (other:Technology)
    WHERE other.community_{version} = community_id
      AND other.id <> t.id
      AND other.pagerank IS NOT NULL
    RETURN
      other.id AS id,
      other.name AS name,
      other.pagerank AS pagerank,
      community_id AS community_id
    ORDER BY other.pagerank DESC, other.id ASC
    LIMIT $limit
    """

    async with driver.session() as session:
        result = await session.run(query, tech_id=tech_id, limit=limit)
        records = await result.values()

        return [
            {
                "id": record[0],
                "name": record[1],
                "pagerank": record[2],
                "community_id": record[3],
            }
            for record in records
        ]


# =============================================================================
# COMMUNITY COMPOSITION ANALYSIS
# =============================================================================

async def get_community_composition(
    driver: AsyncDriver,
    community_id: str
) -> Dict[str, Any]:
    """
    Analyze community composition (technology vs company vs document ratio).

    Useful for Agent 7 (Phase Detector) to understand community maturity:
    - High tech/company ratio = early innovation cluster
    - High company/tech ratio = mature market cluster
    - High doc/tech ratio = well-documented technologies

    Args:
        driver: Neo4j async driver
        community_id: Community ID (e.g., "v1_42")

    Returns:
        Composition statistics

    Example:
        >>> composition = await get_community_composition(driver, "v1_42")
        >>> composition
        {
            'technology_count': 12,
            'company_count': 8,
            'document_count': 65,
            'tech_to_company_ratio': 1.5,  # More techs than companies = early
            'doc_to_tech_ratio': 5.4,       # Well-documented
            'avg_member_pagerank': 0.0023
        }
    """
    query = """
    MATCH (n)-[:BELONGS_TO_COMMUNITY]->(c:Community {id: $community_id})
    WITH n, labels(n)[0] AS node_type, coalesce(n.pagerank, 0.0) AS pagerank
    RETURN
      count(CASE WHEN node_type = 'Technology' THEN 1 END) AS technology_count,
      count(CASE WHEN node_type = 'Company' THEN 1 END) AS company_count,
      count(CASE WHEN node_type = 'Document' THEN 1 END) AS document_count,
      avg(pagerank) AS avg_member_pagerank
    """

    async with driver.session() as session:
        result = await session.run(query, community_id=community_id)
        record = await result.single()

        if not record:
            return {
                "technology_count": 0,
                "company_count": 0,
                "document_count": 0,
                "tech_to_company_ratio": 0.0,
                "doc_to_tech_ratio": 0.0,
                "avg_member_pagerank": 0.0,
            }

        tech_count = record["technology_count"] or 0
        company_count = record["company_count"] or 1  # Avoid division by zero
        doc_count = record["document_count"] or 0

        return {
            "technology_count": tech_count,
            "company_count": company_count,
            "document_count": doc_count,
            "tech_to_company_ratio": float(tech_count) / company_count,
            "doc_to_tech_ratio": float(doc_count) / tech_count if tech_count > 0 else 0.0,
            "avg_member_pagerank": float(record["avg_member_pagerank"] or 0.0),
        }


# =============================================================================
# CROSS-COMMUNITY ANALYSIS
# =============================================================================

async def get_bridge_technologies(
    driver: AsyncDriver,
    tech_id: str,
    version: str = "v1",
    min_betweenness: float = 100.0,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Find bridge technologies that connect different communities.

    Technologies with high betweenness centrality sit between communities,
    indicating cross-domain applicability.

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID
        version: Community version
        min_betweenness: Minimum betweenness centrality threshold
        limit: Maximum number of bridge technologies

    Returns:
        List of bridge technology dicts

    Example:
        >>> bridges = await get_bridge_technologies(driver, "evtol", "v1")
        >>> bridges[0]
        {
            'id': 'solid_state_battery',
            'name': 'Solid-State Battery',
            'betweenness_centrality': 250.4,
            'community_id': 23,
            'reason': 'Bridges battery tech + eVTOL communities'
        }
    """
    query = f"""
    MATCH (t:Technology {{id: $tech_id}})
    WITH t, t.community_{version} AS source_community
    WHERE source_community IS NOT NULL
    MATCH (bridge:Technology)
    WHERE bridge.betweenness_centrality >= $min_betweenness
      AND bridge.community_{version} IS NOT NULL
    RETURN
      bridge.id AS id,
      bridge.name AS name,
      bridge.betweenness_centrality AS betweenness_centrality,
      bridge.community_{version} AS community_id,
      bridge.pagerank AS pagerank
    ORDER BY bridge.betweenness_centrality DESC
    LIMIT $limit
    """

    async with driver.session() as session:
        result = await session.run(
            query,
            tech_id=tech_id,
            min_betweenness=min_betweenness,
            limit=limit
        )
        records = await result.values()

        return [
            {
                "id": record[0],
                "name": record[1],
                "betweenness_centrality": record[2],
                "community_id": record[3],
                "pagerank": record[4],
                "reason": "Strategic connector between innovation clusters",
            }
            for record in records
        ]


async def get_all_communities_for_version(
    driver: AsyncDriver,
    version: int = 1,
    min_member_count: int = 5
) -> List[Dict[str, Any]]:
    """
    Get all communities for a specific version (filtered by minimum size).

    Args:
        driver: Neo4j async driver
        version: Community version (0-5)
        min_member_count: Minimum number of members

    Returns:
        List of community summaries

    Example:
        >>> communities = await get_all_communities_for_version(driver, version=1)
        >>> len(communities)
        49  # 49 communities in v1 with min_members>=5
    """
    query = """
    MATCH (c:Community)
    WHERE c.version = $version
      AND c.member_count >= $min_member_count
    RETURN
      c.id AS id,
      c.summary AS summary,
      c.member_count AS member_count,
      c.tech_count AS tech_count,
      c.company_count AS company_count,
      c.top_technologies AS top_technologies,
      c.doc_type_distribution AS doc_type_distribution
    ORDER BY c.member_count DESC
    """

    async with driver.session() as session:
        result = await session.run(
            query,
            version=version,
            min_member_count=min_member_count
        )
        records = await result.values()

        # Parse JSON string for doc_type_distribution
        import json

        return [
            {
                "id": record[0],
                "summary": record[1],
                "member_count": record[2],
                "tech_count": record[3],
                "company_count": record[4],
                "top_technologies": record[5],
                "doc_type_distribution": json.loads(record[6]) if isinstance(record[6], str) else record[6],
            }
            for record in records
        ]
