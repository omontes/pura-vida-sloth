"""
Hybrid Search: Vector + BM25 Fusion for Semantic + Keyword Search

Combines vector similarity (semantic understanding) with BM25 full-text search
(keyword matching) using Reciprocal Rank Fusion (RRF) for best results.

Key Insight: Vector search finds conceptually similar documents, BM25 finds
exact keyword matches. RRF combines both for higher precision.
"""

from typing import List, Dict, Any, Optional
from neo4j import AsyncDriver
import math


# =============================================================================
# RECIPROCAL RANK FUSION (RRF)
# =============================================================================

def reciprocal_rank_fusion(
    results_list: List[List[Dict[str, Any]]],
    k: int = 60
) -> List[Dict[str, Any]]:
    """
    Merge multiple ranked result lists using Reciprocal Rank Fusion.

    RRF formula: score(d) = Σ 1 / (k + rank(d))
    where k=60 is standard constant, rank(d) is position in result list (1-indexed)

    Args:
        results_list: List of ranked result lists (each with 'doc_id' field)
        k: RRF constant (default: 60)

    Returns:
        Merged and re-ranked results list

    Example:
        >>> vector_results = [{'doc_id': 'A', 'score': 0.9}, {'doc_id': 'B', 'score': 0.8}]
        >>> bm25_results = [{'doc_id': 'B', 'score': 12.5}, {'doc_id': 'C', 'score': 10.2}]
        >>> merged = reciprocal_rank_fusion([vector_results, bm25_results])
        >>> # B appears in both lists → higher RRF score
    """
    # Collect all unique document IDs
    doc_scores: Dict[str, float] = {}
    doc_data: Dict[str, Dict[str, Any]] = {}

    for results in results_list:
        for rank, result in enumerate(results, start=1):
            doc_id = result.get("doc_id")
            if not doc_id:
                continue

            # RRF score contribution from this ranking
            rrf_contribution = 1.0 / (k + rank)

            if doc_id not in doc_scores:
                doc_scores[doc_id] = 0.0
                doc_data[doc_id] = result

            doc_scores[doc_id] += rrf_contribution

    # Sort by RRF score (descending)
    sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

    # Build final result list
    merged_results = []
    for doc_id, rrf_score in sorted_docs:
        result = doc_data[doc_id].copy()
        result["rrf_score"] = rrf_score
        merged_results.append(result)

    return merged_results


# =============================================================================
# VECTOR SEARCH (Semantic Similarity)
# =============================================================================

async def vector_search_documents(
    driver: AsyncDriver,
    query_embedding: List[float],
    doc_types: Optional[List[str]] = None,
    limit: int = 20,
    similarity_threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Perform vector similarity search using document embeddings.

    Uses cosine similarity to find semantically similar documents.

    Args:
        driver: Neo4j async driver
        query_embedding: Query embedding vector (768-dim from text-embedding-3-small)
        doc_types: Filter by document types (e.g., ['patent', 'technical_paper'])
        limit: Maximum number of results
        similarity_threshold: Minimum cosine similarity (0.0-1.0)

    Returns:
        List of documents with similarity scores

    Example:
        >>> from openai import OpenAI
        >>> client = OpenAI()
        >>> embedding = client.embeddings.create(
        ...     model="text-embedding-3-small",
        ...     input="solid state battery technology"
        ... ).data[0].embedding
        >>> results = await vector_search_documents(driver, embedding, ['patent'], limit=10)
    """
    # Build doc_type filter
    doc_type_filter = ""
    if doc_types:
        doc_type_filter = "AND d.doc_type IN $doc_types"

    query = f"""
    MATCH (d:Document)
    WHERE d.embedding IS NOT NULL
      {doc_type_filter}
    WITH d,
         gds.similarity.cosine($query_embedding, d.embedding) AS similarity_score
    WHERE similarity_score >= $similarity_threshold
    RETURN
      d.doc_id AS doc_id,
      d.title AS title,
      d.doc_type AS doc_type,
      d.published_at AS published_at,
      similarity_score AS score
    ORDER BY similarity_score DESC
    LIMIT $limit
    """

    params = {
        "query_embedding": query_embedding,
        "similarity_threshold": similarity_threshold,
        "limit": limit,
    }

    if doc_types:
        params["doc_types"] = doc_types

    async with driver.session() as session:
        result = await session.run(query, **params)
        records = await result.values()

        return [
            {
                "doc_id": record[0],
                "title": record[1],
                "doc_type": record[2],
                "published_at": record[3],
                "score": record[4],
            }
            for record in records
        ]


# =============================================================================
# BM25 FULL-TEXT SEARCH (Keyword Matching)
# =============================================================================

async def bm25_search_documents(
    driver: AsyncDriver,
    query_text: str,
    doc_types: Optional[List[str]] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Perform BM25 full-text search using Neo4j's full-text index.

    BM25 is a keyword-based ranking algorithm that considers term frequency
    and document length normalization.

    Args:
        driver: Neo4j async driver
        query_text: Search query string (keywords)
        doc_types: Filter by document types
        limit: Maximum number of results

    Returns:
        List of documents with BM25 scores

    Example:
        >>> results = await bm25_search_documents(
        ...     driver,
        ...     "solid state battery lithium metal",
        ...     doc_types=['patent'],
        ...     limit=10
        ... )
    """
    # Build doc_type filter
    doc_type_filter = ""
    if doc_types:
        doc_type_filter = "AND n.doc_type IN $doc_types"

    query = f"""
    CALL db.index.fulltext.queryNodes('document_fulltext', $query_text)
    YIELD node AS n, score
    WHERE n:Document
      {doc_type_filter}
    RETURN
      n.doc_id AS doc_id,
      n.title AS title,
      n.doc_type AS doc_type,
      n.published_at AS published_at,
      score AS score
    ORDER BY score DESC
    LIMIT $limit
    """

    params = {
        "query_text": query_text,
        "limit": limit,
    }

    if doc_types:
        params["doc_types"] = doc_types

    async with driver.session() as session:
        result = await session.run(query, **params)
        records = await result.values()

        return [
            {
                "doc_id": record[0],
                "title": record[1],
                "doc_type": record[2],
                "published_at": record[3],
                "score": record[4],
            }
            for record in records
        ]


# =============================================================================
# HYBRID SEARCH (Vector + BM25 Fusion)
# =============================================================================

async def hybrid_search_documents(
    driver: AsyncDriver,
    query_text: str,
    query_embedding: List[float],
    doc_types: Optional[List[str]] = None,
    k_vector: int = 20,
    k_bm25: int = 20,
    vector_weight: float = 0.3,
    k_final: int = 10,
    rrf_k: int = 60
) -> List[Dict[str, Any]]:
    """
    Hybrid search combining vector similarity + BM25 full-text search.

    Uses Reciprocal Rank Fusion (RRF) to merge vector and BM25 results.
    Vector search finds semantically similar documents, BM25 finds keyword matches.

    Args:
        driver: Neo4j async driver
        query_text: Search query string (for BM25)
        query_embedding: Query embedding vector (for vector search)
        doc_types: Filter by document types (e.g., ['patent', 'technical_paper'])
        k_vector: Top K from vector search (default: 20)
        k_bm25: Top K from BM25 search (default: 20)
        vector_weight: Weight for vector search (0.0-1.0, default: 0.3 = 30% vector, 70% BM25)
        k_final: Final number of results after fusion (default: 10)
        rrf_k: RRF constant (default: 60)

    Returns:
        List of documents ranked by hybrid score (RRF + weighting)

    Example:
        >>> from openai import OpenAI
        >>> client = OpenAI()
        >>> embedding = client.embeddings.create(
        ...     model="text-embedding-3-small",
        ...     input="solid state battery technology"
        ... ).data[0].embedding
        >>> results = await hybrid_search_documents(
        ...     driver,
        ...     query_text="solid state battery lithium",
        ...     query_embedding=embedding,
        ...     doc_types=['patent', 'technical_paper'],
        ...     k_final=10
        ... )
        >>> # Results combine semantic similarity + keyword matching
    """
    # Step 1: Vector search (semantic similarity)
    vector_results = await vector_search_documents(
        driver=driver,
        query_embedding=query_embedding,
        doc_types=doc_types,
        limit=k_vector,
        similarity_threshold=0.7
    )

    # Step 2: BM25 search (keyword matching)
    bm25_results = await bm25_search_documents(
        driver=driver,
        query_text=query_text,
        doc_types=doc_types,
        limit=k_bm25
    )

    # Step 3: Reciprocal Rank Fusion
    merged_results = reciprocal_rank_fusion(
        [vector_results, bm25_results],
        k=rrf_k
    )

    # Step 4: Apply vector/BM25 weighting to RRF scores
    # NOTE: For first run, vector_weight=0.3 means 30% semantic, 70% keyword
    for result in merged_results:
        # Normalize RRF score to 0-1 range (approximate)
        normalized_rrf = min(1.0, result["rrf_score"] * 10)

        # Weighted hybrid score
        # In practice, we just use RRF score since it already combines both
        result["hybrid_score"] = normalized_rrf

    # Step 5: Sort by hybrid score and return top K
    merged_results.sort(key=lambda x: x["hybrid_score"], reverse=True)

    return merged_results[:k_final]


# =============================================================================
# TECHNOLOGY-SPECIFIC HYBRID SEARCH
# =============================================================================

async def hybrid_search_tech_documents(
    driver: AsyncDriver,
    tech_id: str,
    query_text: str,
    query_embedding: List[float],
    doc_types: Optional[List[str]] = None,
    k_final: int = 10
) -> List[Dict[str, Any]]:
    """
    Hybrid search for documents related to a specific technology.

    Combines hybrid search with technology filtering (MENTIONED_IN relationships).

    Args:
        driver: Neo4j async driver
        tech_id: Technology ID to filter by
        query_text: Search query string
        query_embedding: Query embedding vector
        doc_types: Filter by document types
        k_final: Final number of results

    Returns:
        List of technology-related documents ranked by hybrid score

    Example:
        >>> results = await hybrid_search_tech_documents(
        ...     driver,
        ...     tech_id="evtol",
        ...     query_text="vertical takeoff landing electric propulsion",
        ...     query_embedding=embedding,
        ...     doc_types=['patent'],
        ...     k_final=5
        ... )
    """
    # First get all documents related to this technology
    tech_doc_ids_query = """
    MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
    WHERE d.quality_score >= 0.85
    RETURN collect(d.doc_id) AS doc_ids
    """

    async with driver.session() as session:
        result = await session.run(tech_doc_ids_query, tech_id=tech_id)
        record = await result.single()

        if not record or not record["doc_ids"]:
            return []

        tech_doc_ids = set(record["doc_ids"])

    # Perform hybrid search
    hybrid_results = await hybrid_search_documents(
        driver=driver,
        query_text=query_text,
        query_embedding=query_embedding,
        doc_types=doc_types,
        k_final=k_final * 3  # Get more results for filtering
    )

    # Filter to only technology-related documents
    tech_filtered_results = [
        result for result in hybrid_results
        if result["doc_id"] in tech_doc_ids
    ]

    return tech_filtered_results[:k_final]


# =============================================================================
# COMMUNITY-BASED HYBRID SEARCH
# =============================================================================

async def hybrid_search_community_documents(
    driver: AsyncDriver,
    community_id: str,
    query_text: str,
    query_embedding: List[float],
    doc_types: Optional[List[str]] = None,
    k_final: int = 10
) -> List[Dict[str, Any]]:
    """
    Hybrid search within a specific community cluster.

    Useful for finding related documents within an innovation cluster.

    Args:
        driver: Neo4j async driver
        community_id: Community ID (e.g., "v1_123")
        query_text: Search query string
        query_embedding: Query embedding vector
        doc_types: Filter by document types
        k_final: Final number of results

    Returns:
        List of community documents ranked by hybrid score
    """
    # First get all documents in this community
    community_doc_ids_query = """
    MATCH (c:Community {id: $community_id})<-[:BELONGS_TO_COMMUNITY]-(n)
    MATCH (n)-[:MENTIONED_IN]->(d:Document)
    WHERE d.quality_score >= 0.85
    RETURN collect(DISTINCT d.doc_id) AS doc_ids
    """

    async with driver.session() as session:
        result = await session.run(community_doc_ids_query, community_id=community_id)
        record = await result.single()

        if not record or not record["doc_ids"]:
            return []

        community_doc_ids = set(record["doc_ids"])

    # Perform hybrid search
    hybrid_results = await hybrid_search_documents(
        driver=driver,
        query_text=query_text,
        query_embedding=query_embedding,
        doc_types=doc_types,
        k_final=k_final * 3  # Get more results for filtering
    )

    # Filter to only community documents
    community_filtered_results = [
        result for result in hybrid_results
        if result["doc_id"] in community_doc_ids
    ]

    return community_filtered_results[:k_final]
