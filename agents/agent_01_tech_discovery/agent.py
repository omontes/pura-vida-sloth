"""
Agent 1: Tech Discovery - Implementation

Enumerates technologies from Neo4j graph with metadata for downstream agents.

This agent:
1. Queries all Technology nodes from graph
2. Aggregates document counts by type
3. Finds related companies
4. Returns structured list ready for layer scoring agents
"""

from typing import Dict, Any
from neo4j import AsyncDriver

from agents.agent_01_tech_discovery.schemas import (
    TechDiscoveryInput,
    TechDiscoveryOutput,
    Technology,
)


async def get_all_technologies(
    driver: AsyncDriver,
    industry_filter: str = None,
    min_document_count: int = 1,
    limit: int = None
) -> Dict[str, Any]:
    """
    Query all technologies from graph with aggregated metadata.

    Args:
        driver: Neo4j async driver
        industry_filter: Optional industry/domain filter
        min_document_count: Minimum number of documents required
        limit: Maximum number of technologies to return

    Returns:
        Dict with technologies list and counts

    Query Logic:
    1. Match all Technology nodes
    2. Get document counts via MENTIONED_IN relationships
    3. Aggregate by doc_type for breakdown
    4. Get related companies
    5. Get community_v1 and pagerank
    6. Order by document_count DESC for most important technologies first
    """
    # Build optional filters
    industry_clause = ""
    if industry_filter:
        industry_clause = "AND t.domain = $industry_filter"

    limit_clause = ""
    if limit:
        limit_clause = f"LIMIT {limit}"

    query = f"""
    // Step 1: Get all technologies with document relationships
    MATCH (t:Technology)-[m:MENTIONED_IN]->(d:Document)
    WHERE d.quality_score >= 0.85
      {industry_clause}

    // Step 2: Aggregate document counts by type
    WITH t,
         count(DISTINCT d) AS total_docs,
         collect(DISTINCT {{
           doc_type: d.doc_type,
           doc_id: d.doc_id
         }}) AS all_docs
    WHERE total_docs >= $min_document_count

    // Step 3: Calculate doc_type breakdown
    WITH t, total_docs, all_docs,
         [doc_type IN apoc.coll.toSet([doc IN all_docs | doc.doc_type]) |
           {{
             type: doc_type,
             count: size([doc IN all_docs WHERE doc.doc_type = doc_type])
           }}
         ] AS breakdown

    // Step 4: Get related companies (optional - may not exist for all techs)
    OPTIONAL MATCH (c:Company)-[r:RELATED_TO_TECH]->(t)
    WITH t, total_docs, breakdown,
         collect(DISTINCT c.ticker) AS companies

    // Step 5: Return technology with all metadata
    RETURN
      t.id AS id,
      t.name AS name,
      coalesce(t.domain, 'Unknown') AS domain,
      coalesce(t.aliases, []) AS aliases,
      companies AS companies,
      total_docs AS document_count,
      breakdown AS doc_type_breakdown,
      t.community_v1 AS community_id,
      coalesce(t.pagerank, 0.0) AS pagerank

    // Step 6: Order by importance (document count DESC, then PageRank DESC)
    ORDER BY total_docs DESC, pagerank DESC, id ASC
    {limit_clause}
    """

    params = {
        "min_document_count": min_document_count,
    }

    if industry_filter:
        params["industry_filter"] = industry_filter

    async with driver.session() as session:
        result = await session.run(query, **params)
        records = await result.values()

        # Also get total count before filtering
        count_query = """
        MATCH (t:Technology)-[:MENTIONED_IN]->(d:Document)
        WHERE d.quality_score >= 0.85
        RETURN count(DISTINCT t) AS total_count
        """

        count_result = await session.run(count_query)
        count_record = await count_result.single()
        total_count = count_record["total_count"] if count_record else 0

        # Parse results into Technology objects
        technologies = []
        for record in records:
            # Convert doc_type_breakdown from list of dicts to dict
            breakdown_dict = {}
            for item in record[6]:  # doc_type_breakdown
                breakdown_dict[item["type"]] = item["count"]

            tech = Technology(
                id=record[0],
                name=record[1],
                domain=record[2],
                aliases=record[3] or [],
                companies=[c for c in record[4] if c],  # Filter out None
                document_count=record[5],
                doc_type_breakdown=breakdown_dict,
                community_id=record[7],
                pagerank=record[8],
            )
            technologies.append(tech)

        return {
            "technologies": technologies,
            "total_count": total_count,
            "filtered_count": len(technologies),
        }


async def tech_discovery_agent(
    state: Dict[str, Any],
    driver: AsyncDriver
) -> Dict[str, Any]:
    """
    Tech Discovery Agent - Main entry point.

    This agent is the first in the pipeline. It enumerates all technologies
    from the graph and prepares them for downstream scoring agents.

    Args:
        state: LangGraph state dict (optional filters)
        driver: Neo4j async driver

    Returns:
        Updated state with technologies list

    State Updates:
        - technologies: List[Technology] - All discovered technologies

    Example:
        >>> state = {}
        >>> result = await tech_discovery_agent(state, driver)
        >>> len(result["technologies"])
        1755  # Total technologies in graph
    """
    # Parse input (if provided)
    input_data = TechDiscoveryInput(**state) if state else TechDiscoveryInput()

    # Query technologies from graph
    result = await get_all_technologies(
        driver=driver,
        industry_filter=input_data.industry_filter,
        min_document_count=input_data.min_document_count,
        limit=input_data.limit,
    )

    # Validate output
    output = TechDiscoveryOutput(
        technologies=result["technologies"],
        total_count=result["total_count"],
        filtered_count=result["filtered_count"],
    )

    # Return state update (for LangGraph compatibility)
    return {
        "technologies": [tech.model_dump() for tech in output.technologies],
        "total_technology_count": output.total_count,
        "filtered_technology_count": output.filtered_count,
    }


# Standalone function for testing (non-LangGraph)
async def discover_technologies(
    driver: AsyncDriver,
    industry_filter: str = None,
    min_document_count: int = 1,
    limit: int = None
) -> TechDiscoveryOutput:
    """
    Standalone function for discovering technologies (testing/debugging).

    Args:
        driver: Neo4j async driver
        industry_filter: Optional industry filter
        min_document_count: Minimum documents required
        limit: Maximum technologies to return

    Returns:
        TechDiscoveryOutput with technologies list

    Example:
        >>> from src.graph.neo4j_client import Neo4jClient
        >>> client = Neo4jClient()
        >>> await client.connect()
        >>> output = await discover_technologies(client.driver, limit=10)
        >>> len(output.technologies)
        10
    """
    result = await get_all_technologies(
        driver=driver,
        industry_filter=industry_filter,
        min_document_count=min_document_count,
        limit=limit,
    )

    return TechDiscoveryOutput(
        technologies=result["technologies"],
        total_count=result["total_count"],
        filtered_count=result["filtered_count"],
    )
