"""
Agent 1: Tech Discovery - Implementation

Enumerates technologies from Neo4j graph with metadata for downstream agents.

This agent:
1. Queries all Technology nodes from graph
2. Aggregates document counts by type
3. Finds related companies
4. Returns structured list ready for layer scoring agents
"""

from typing import Dict, Any, List, Tuple
from neo4j import AsyncDriver
import json

from agents.agent_01_tech_discovery.schemas import (
    TechDiscoveryInput,
    TechDiscoveryOutput,
    Technology,
)
from agents.shared.queries import community_queries


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
    WHERE d.quality_score >= 0.75
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
        WHERE d.quality_score >= 0.75
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


def classify_communities_by_maturity(
    communities: List[Dict[str, Any]]
) -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict]]:
    """
    Classify communities into early/mid/late/hype stages based on doc_type_distribution.

    Maturity indicators (RECALIBRATED 2025-01-10):
    - Early-stage: High patent:news ratio (>2), few contracts (<5) → Innovation Trigger
    - Hype-stage: High news:patent ratio (>1.5), few contracts (<5) → Peak
    - Late-stage: Moderate contracts (≥3), balanced patent/news → Plateau
    - Mid-stage: Everything else → Slope

    Args:
        communities: List of community dicts from get_all_communities_for_version()

    Returns:
        Tuple of (early_communities, mid_communities, late_communities, hype_communities)

    Example:
        >>> early, mid, late, hype = classify_communities_by_maturity(communities)
        >>> len(early)
        12  # 12 communities in early-stage cluster
    """
    early_stage = []
    mid_stage = []
    late_stage = []
    hype_stage = []

    skipped_count = 0
    debug_first = True  # Print first community for debugging

    for comm in communities:
        doc_dist = comm.get("doc_type_distribution", {})

        # Handle JSON string
        if isinstance(doc_dist, str):
            try:
                doc_dist = json.loads(doc_dist)
            except:
                doc_dist = {}

        patents = doc_dist.get("patent", 0)
        news = doc_dist.get("news", 0)
        contracts = doc_dist.get("government_contract", 0)

        # Debug: Print first community
        if debug_first:
            print(f"[CLASSIFICATION DEBUG] First community sample:")
            print(f"  ID: {comm.get('id')}")
            print(f"  doc_type_distribution: {doc_dist}")
            print(f"  Patents: {patents}, News: {news}, Contracts: {contracts}")
            debug_first = False

        # Allow all communities (even without patent/news data)
        # Removed skip condition - communities with contracts-only are valid

        # Calculate total docs and ratios
        total_docs = patents + news + contracts
        patent_news_ratio = patents / (news + 1)
        news_patent_ratio = news / (patents + 1)

        # ADAPTIVE classification: Use absolute counts for small communities, ratios for large
        if total_docs < 10:
            # SMALL COMMUNITY: Use absolute differences instead of ratios
            # Late-stage: High commercialization (prioritize first)
            if contracts >= 2 and (patents >= 1 or news >= 1):
                late_stage.append(comm)
            # Early-stage: Clearly more patents than news, low contracts
            elif patents > news and patents >= 1 and contracts <= 1:
                early_stage.append(comm)
            # Hype-stage: Clearly more news than patents, low contracts
            elif news > patents and news >= 1 and contracts <= 1:
                hype_stage.append(comm)
            # Mid-stage: Balanced (equal patents/news) OR moderate contracts (==1)
            else:
                mid_stage.append(comm)
        else:
            # LARGE COMMUNITY: Use ratio-based classification (RELAXED 2025-01-10)
            if patent_news_ratio > 2 and contracts < 5:
                # High patent activity, low news → Early-stage innovation
                early_stage.append(comm)
            elif news_patent_ratio > 1.5 and contracts < 5:  # RELAXED: 2→1.5
                # High news activity, low patents → Hype/Peak
                hype_stage.append(comm)
            elif contracts >= 3 and patents > 2:  # RELAXED: >10→≥3, >5→>2
                # Moderate commercialization → Late-stage/Plateau
                late_stage.append(comm)
            else:
                # Balanced signals → Mid-stage/Slope
                mid_stage.append(comm)

    # Debug logging
    if skipped_count > 0:
        print(f"[CLASSIFICATION DEBUG] Skipped {skipped_count} communities with no patent/news data")

    return early_stage, mid_stage, late_stage, hype_stage


async def sample_techs_from_communities(
    driver: AsyncDriver,
    communities: List[Dict[str, Any]],
    limit: int,
    version: str = "v1",
    min_document_count: int = 1
) -> List[Technology]:
    """
    Sample top N technologies from specified communities, ordered by PageRank.

    Args:
        driver: Neo4j async driver
        communities: List of community dicts to sample from
        limit: Maximum number of technologies to return
        version: Community version property (v0-v5)
        min_document_count: Minimum documents required

    Returns:
        List of Technology objects

    Example:
        >>> techs = await sample_techs_from_communities(driver, early_communities, 20, "v1")
        >>> len(techs)
        20  # Top 20 technologies from early-stage communities
    """
    if not communities:
        return []

    # Extract community IDs
    community_ids = [c["id"] for c in communities]

    # For v1, v2, etc., we need to get the numeric community ID from the node property
    # Community nodes have id="v1_42" but Technology nodes have community_v1=42
    # So we need to extract the numeric part
    community_numbers = []
    for comm_id in community_ids:
        if "_" in comm_id:
            # Extract number after underscore (e.g., "v1_42" → 42)
            try:
                num = int(comm_id.split("_")[1])
                community_numbers.append(num)
            except (IndexError, ValueError):
                pass
        else:
            # Direct number
            try:
                community_numbers.append(int(comm_id))
            except ValueError:
                pass

    if not community_numbers:
        return []

    query = f"""
    // Get technologies belonging to target communities
    MATCH (t:Technology)-[m:MENTIONED_IN]->(d:Document)
    WHERE t.community_{version} IN $community_numbers
      AND d.quality_score >= 0.75

    // Aggregate document counts
    WITH t,
         count(DISTINCT d) AS total_docs,
         collect(DISTINCT {{
           doc_type: d.doc_type,
           doc_id: d.doc_id
         }}) AS all_docs
    WHERE total_docs >= $min_document_count

    // Calculate doc_type breakdown
    WITH t, total_docs, all_docs,
         [doc_type IN apoc.coll.toSet([doc IN all_docs | doc.doc_type]) |
           {{
             type: doc_type,
             count: size([doc IN all_docs WHERE doc.doc_type = doc_type])
           }}
         ] AS breakdown

    // Get related companies
    OPTIONAL MATCH (c:Company)-[:RELATED_TO_TECH]->(t)
    WITH t, total_docs, breakdown,
         collect(DISTINCT c.ticker) AS companies

    // Calculate diversity score (bonus for multiple doc types)
    WITH t, total_docs, breakdown, companies,
         size(breakdown) AS doc_type_diversity,
         coalesce(t.pagerank, 0.0) AS pagerank

    // Return with smart ordering: PageRank + diversity bonus + document count
    RETURN
      t.id AS id,
      t.name AS name,
      coalesce(t.domain, 'Unknown') AS domain,
      coalesce(t.aliases, []) AS aliases,
      companies AS companies,
      total_docs AS document_count,
      breakdown AS doc_type_breakdown,
      t.community_{version} AS community_id,
      pagerank AS pagerank

    // Order by: PageRank (importance) + diversity (2+ types preferred) + total docs
    ORDER BY pagerank DESC, doc_type_diversity DESC, total_docs DESC
    LIMIT $limit
    """

    async with driver.session() as session:
        result = await session.run(
            query,
            community_numbers=community_numbers,
            min_document_count=min_document_count,
            limit=limit
        )
        records = await result.values()

        technologies = []
        for record in records:
            # Convert doc_type_breakdown from list of dicts to dict
            breakdown_dict = {}
            for item in record[6]:
                breakdown_dict[item["type"]] = item["count"]

            tech = Technology(
                id=record[0],
                name=record[1],
                domain=record[2],
                aliases=record[3] or [],
                companies=[c for c in record[4] if c],
                document_count=record[5],
                doc_type_breakdown=breakdown_dict,
                community_id=record[7],
                pagerank=record[8],
            )
            technologies.append(tech)

        return technologies


async def discover_technologies_with_community_sampling(
    driver: AsyncDriver,
    version: str = "v1",
    total_limit: int = 100,
    early_pct: float = 0.20,
    mid_pct: float = 0.40,
    late_pct: float = 0.20,
    hype_pct: float = 0.20,
    min_document_count: int = 1
) -> TechDiscoveryOutput:
    """
    Discover technologies using ADAPTIVE community-based stratified sampling.

    ADAPTIVE STRATEGY (2025-01-09):
    - Instead of requesting fixed counts (20/40/20/20), we now sample ALL available
      technologies from each community type up to a per-stratum max
    - If total < target, we fill remaining slots from ALL communities by PageRank
    - This handles cases where communities have limited members passing quality filters

    Strategy:
    1. Get all communities for version (e.g., v1)
    2. Classify communities by maturity indicators:
       - Early-stage: High patent:news ratio → Innovation Trigger
       - Hype-stage: High news:patent ratio → Peak
       - Late-stage: High contracts → Plateau
       - Mid-stage: Balanced → Slope
    3. Sample ALL available techs from each stratum (up to per-stratum max)
    4. If total < target, fill remainder from top communities by member_count

    Args:
        driver: Neo4j async driver
        version: Community version (v0-v5)
        total_limit: Maximum total technologies
        early_pct: Target percentage from early-stage (default 20%)
        mid_pct: Target percentage from mid-stage (default 40%)
        late_pct: Target percentage from late-stage (default 20%)
        hype_pct: Target percentage from hype-stage (default 20%)
        min_document_count: Minimum documents required

    Returns:
        TechDiscoveryOutput with balanced technology sample

    Expected Phase Distribution:
    - Innovation Trigger: 15-20% (from early-stage communities)
    - Peak: 15-20% (from hype-stage communities)
    - Slope: 30-40% (from mid-stage communities)
    - Trough: 20-25% (underperformers from all communities)
    - Plateau: 10-15% (from late-stage communities)

    Example:
        >>> output = await discover_technologies_with_community_sampling(
        ...     driver, version="v1", total_limit=100
        ... )
        >>> len(output.technologies)
        100  # Adaptively sampled across available communities
    """
    # Step 1: Get all communities for version
    version_number = int(version[1]) if version.startswith("v") else int(version)

    communities = await community_queries.get_all_communities_for_version(
        driver,
        version=version_number,
        min_member_count=3  # Only communities with at least 3 members
    )

    print(f"\n[COMMUNITY SAMPLING] Found {len(communities)} communities (version={version})")

    # Step 2: Classify communities by maturity
    early, mid, late, hype = classify_communities_by_maturity(communities)

    print(f"[COMMUNITY SAMPLING] Classification:")
    print(f"  Early-stage (Innovation Trigger): {len(early)} communities")
    print(f"  Mid-stage (Slope): {len(mid)} communities")
    print(f"  Late-stage (Plateau): {len(late)} communities")
    print(f"  Hype-stage (Peak): {len(hype)} communities")

    # Step 3: ADAPTIVE SAMPLING - Sample ALL available from each stratum (up to max per stratum)
    technologies = []
    tech_ids_seen = set()  # Prevent duplicates

    # Per-stratum max = 2x the target (e.g., if target is 20, max is 40)
    early_max = int(total_limit * early_pct * 2)
    mid_max = int(total_limit * mid_pct * 2)
    late_max = int(total_limit * late_pct * 2)
    hype_max = int(total_limit * hype_pct * 2)

    # Early-stage: Boost Innovation Trigger representation
    early_techs = await sample_techs_from_communities(
        driver, early, early_max, version, min_document_count
    )
    for tech in early_techs:
        if tech.id not in tech_ids_seen:
            technologies.append(tech)
            tech_ids_seen.add(tech.id)
    print(f"[COMMUNITY SAMPLING] Sampled {len(early_techs)} from {len(early)} early-stage communities (target={int(total_limit*early_pct)})")

    # Mid-stage: Maintain Slope baseline
    mid_techs = await sample_techs_from_communities(
        driver, mid, mid_max, version, min_document_count
    )
    for tech in mid_techs:
        if tech.id not in tech_ids_seen:
            technologies.append(tech)
            tech_ids_seen.add(tech.id)
    print(f"[COMMUNITY SAMPLING] Sampled {len(mid_techs)} from {len(mid)} mid-stage communities (target={int(total_limit*mid_pct)})")

    # Late-stage: Boost Plateau representation
    late_techs = await sample_techs_from_communities(
        driver, late, late_max, version, min_document_count
    )
    for tech in late_techs:
        if tech.id not in tech_ids_seen:
            technologies.append(tech)
            tech_ids_seen.add(tech.id)
    print(f"[COMMUNITY SAMPLING] Sampled {len(late_techs)} from {len(late)} late-stage communities (target={int(total_limit*late_pct)})")

    # Hype-stage: Boost Peak representation
    hype_techs = await sample_techs_from_communities(
        driver, hype, hype_max, version, min_document_count
    )
    for tech in hype_techs:
        if tech.id not in tech_ids_seen:
            technologies.append(tech)
            tech_ids_seen.add(tech.id)
    print(f"[COMMUNITY SAMPLING] Sampled {len(hype_techs)} from {len(hype)} hype-stage communities (target={int(total_limit*hype_pct)})")

    current_count = len(technologies)
    print(f"[COMMUNITY SAMPLING] Stratified sampling yielded {current_count}/{total_limit} technologies")

    # Step 4: ADAPTIVE FILL - If we're under target, fill from ALL communities by PageRank
    if current_count < total_limit:
        remaining = total_limit - current_count
        print(f"[COMMUNITY SAMPLING] Filling {remaining} remaining slots from top communities by PageRank...")

        # Sample from ALL communities (combined)
        fill_techs = await sample_techs_from_communities(
            driver, communities, remaining * 2, version, min_document_count  # 2x to ensure we get enough after dedup
        )

        added = 0
        for tech in fill_techs:
            if tech.id not in tech_ids_seen and added < remaining:
                technologies.append(tech)
                tech_ids_seen.add(tech.id)
                added += 1

        print(f"[COMMUNITY SAMPLING] Added {added} technologies from fill sampling")

    # Limit to total_limit (in case we got more)
    technologies = technologies[:total_limit]

    print(f"[COMMUNITY SAMPLING] Final: {len(technologies)} technologies\n")

    return TechDiscoveryOutput(
        technologies=technologies,
        total_count=len(technologies),
        filtered_count=len(technologies),
    )


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
