"""
Shared Cypher query modules for GraphRAG-powered agent scoring.

This package provides centralized, reusable Cypher queries organized by
intelligence layer. Each module exports:
1. Query templates (parameterized Cypher strings)
2. Execution functions (takes neo4j driver, returns parsed results)
3. Result parsers (Neo4j records → Python dicts)

Query Modules:
- innovation_queries: Patents, papers, GitHub (Layer 1)
- adoption_queries: Gov contracts, regulations, revenue (Layer 2)
- narrative_queries: News articles, sentiment (Layer 4)
- risk_queries: SEC filings, insider trading (Layer 3)
- hybrid_search: Vector + BM25 fusion patterns
- community_queries: Community-based analysis
- citation_queries: Evidence/citation retrieval
"""

from agents.shared.queries import (
    innovation_queries,
    adoption_queries,
    narrative_queries,
    risk_queries,
    hybrid_search,
    community_queries,
    citation_queries,
)

__all__ = [
    "innovation_queries",
    "adoption_queries",
    "narrative_queries",
    "risk_queries",
    "hybrid_search",
    "community_queries",
    "citation_queries",
]
