# First Run Multi-Agent System for Hype Cycle Chart Generation

**Implementation-Focused Architecture for GraphRAG-Powered Technology Lifecycle Analysis**

Version: 1.0
Date: 2025-01-09
Focus: Single Deterministic Run (MVP)

---

## Executive Summary

This document defines the **12-agent LangGraph system** that transforms Neo4j graph data into executive-grade Hype Cycle positioning charts. The system analyzes emerging technologies across 4 intelligence layers (Innovation, Adoption, Risk, Narrative) to determine Gartner lifecycle phase with 85%+ confidence.

**Input**: Neo4j graph with 400-1,600 documents per industry (prerequisites completed)
**Output**: `hype_cycle_chart.json` with technologies positioned on 5 Gartner phases
**Runtime**: ~25 seconds per technology (with parallelization)
**Cost**: ~$0.50 per technology (GPT-4o-mini @ $0.15/$0.60 per M tokens)

### Core Architectural Decisions

1. **Pure GraphRAG**: Neo4j contains ZERO derived scores - agents compute everything on-demand using graph as RAG
2. **Prerequisites Pre-Computed**: All expensive operations done ONCE (embeddings, communities v0-v5, PageRank, indexes)
3. **Shared Query Library**: Centralized Cypher queries (7 modules) instead of Cypher Agent
4. **Parallel Execution**: Agents 2-5 run in parallel, Agents 10-11 run in parallel (20% speedup)
5. **Deterministic First Run**: temperature=0, seed=42, fixed date ranges, ORDER BY clauses everywhere
6. **LangChain Structured Outputs**: Leverage `.with_structured_output()` for guaranteed JSON schema compliance
7. **Validation Gate**: Agent 12 validates output before writing chart.json

### First Run vs Multi-Run Approach

**This Document: First Run (MVP)**
- Single execution with fixed parameters
- Deterministic output (same input → same output)
- Temperature=0, seed=42 for all LLM calls
- Fixed temporal windows (2yr innovation, 1yr adoption, 3mo narrative, 6mo risk)
- Fixed community version (always v1)
- Fixed layer weights (Innovation 30%, Adoption 35%, Narrative 15%, Risk 20%)
- **Goal**: Validate architecture, test each agent independently, get to first chart.json

**Future: Multi-Run Consensus**
- 10-20 runs with controlled variations (temporal windows, community versions v0-v5, hybrid search weights)
- Consensus aggregation (Cohen's Kappa > 0.75 for high confidence)
- Confidence intervals from run diversity
- **Goal**: Scientific convergence builds trust vs single deterministic verdict

---

## Architecture Overview

### System Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    1. Tech Discovery Agent                      │
│              (Enumerate all technologies from graph)            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              PARALLEL EXECUTION: Core Scoring Agents            │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│  │ 2. Innovation│ 3. Adoption  │ 4. Narrative │  5. Risk     │  │
│  │    Scorer    │    Scorer    │    Scorer    │   Scorer     │  │
│  │   (Layer 1)  │  (Layer 2)   │  (Layer 4)   │ (Layer 3)    │  │
│  └──────────────┴──────────────┴──────────────┴──────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │   6. Hype Scorer     │
                  │  (Cross-Layer        │
                  │   Contradiction)     │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ 7. Phase Detector    │
                  │  (Gartner Lifecycle  │
                  │   Classification)    │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  8. LLM Analyst      │
                  │  (GPT-4o-mini        │
                  │   Synthesis)         │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  9. Ensemble Agent   │
                  │  (Weighted Score     │
                  │   Combination)       │
                  └──────────┬───────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│         PARALLEL EXECUTION: Output Generation Agents            │
│  ┌──────────────────────────────┬──────────────────────────┐    │
│  │  10. Chart Generator         │ 11. Evidence Compiler    │    │
│  │  (X/Y Coordinates)           │ (Source Citations)       │    │
│  └──────────────────────────────┴──────────────────────────┘    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ 12. Output Validator │
                  │  (Quality Gate)      │
                  └──────────┬───────────┘
                             │
                             ▼
                   [hype_cycle_chart.json]
```

### Agent Dependencies

- **No Dependencies**: Agent 1
- **Depends on Agent 1**: Agents 2-5 (parallel)
- **Depends on Agents 2-5**: Agent 6
- **Sequential Chain**: Agent 6 → Agent 7 → Agent 8
- **Depends on Agents 2-5**: Agent 9 (parallel with chain)
- **Depends on Agent 9**: Agents 10-11 (parallel)
- **Depends on Agents 10-11**: Agent 12
- **Final Output**: chart.json

### Folder Structure

```
agents/
├── shared/
│   ├── queries/
│   │   ├── __init__.py
│   │   ├── innovation_queries.py    # Layer 1: Patents, papers, GitHub
│   │   ├── adoption_queries.py      # Layer 2: Gov contracts, regulations, revenue
│   │   ├── narrative_queries.py     # Layer 4: News articles, sentiment
│   │   ├── risk_queries.py          # Layer 3: SEC filings, insider trading
│   │   ├── hybrid_search.py         # Vector + BM25 fusion patterns
│   │   ├── community_queries.py     # Community-based queries
│   │   └── citation_queries.py      # Evidence/citation retrieval
│   ├── neo4j_client.py              # Neo4j connection pooling
│   ├── duckdb_client.py             # Scholarly papers + insider transactions
│   ├── openai_client.py             # ChatOpenAI with temp=0, seed=42
│   └── constants.py                 # Fixed date ranges, weights, thresholds
│
├── agent_01_tech_discovery/
│   ├── __init__.py
│   ├── agent.py
│   ├── schemas.py
│   └── tests/
│
├── agent_02_innovation_scorer/
│   ├── __init__.py
│   ├── agent.py
│   ├── schemas.py
│   ├── scoring.py
│   ├── llm_prompts.py
│   └── tests/
│
├── agent_03_adoption_scorer/
│   ├── __init__.py
│   ├── agent.py
│   ├── schemas.py
│   ├── scoring.py
│   ├── llm_prompts.py
│   └── tests/
│
├── agent_04_narrative_scorer/
│   ├── __init__.py
│   ├── agent.py
│   ├── schemas.py
│   ├── scoring.py
│   ├── llm_prompts.py
│   └── tests/
│
├── agent_05_risk_scorer/
│   ├── __init__.py
│   ├── agent.py
│   ├── schemas.py
│   ├── scoring.py
│   ├── llm_prompts.py
│   └── tests/
│
├── agent_06_hype_scorer/
│   ├── __init__.py
│   ├── agent.py
│   ├── schemas.py
│   ├── contradiction_rules.py
│   └── tests/
│
├── agent_07_phase_detector/
│   ├── __init__.py
│   ├── agent.py
│   ├── schemas.py
│   ├── classification_rules.py
│   └── tests/
│
├── agent_08_llm_analyst/
│   ├── __init__.py
│   ├── agent.py
│   ├── schemas.py
│   ├── llm_prompts.py
│   └── tests/
│
├── agent_09_ensemble/
│   ├── __init__.py
│   ├── agent.py
│   ├── schemas.py
│   ├── weighting.py
│   └── tests/
│
├── agent_10_chart_generator/
│   ├── __init__.py
│   ├── agent.py
│   ├── schemas.py
│   ├── coordinates.py
│   └── tests/
│
├── agent_11_evidence_compiler/
│   ├── __init__.py
│   ├── agent.py
│   ├── schemas.py
│   └── tests/
│
├── agent_12_output_validator/
│   ├── __init__.py
│   ├── agent.py
│   ├── schemas.py
│   ├── validation_rules.py
│   └── tests/
│
├── langgraph_orchestrator.py       # Main LangGraph workflow
├── state_schema.py                  # TechnologyState TypedDict
└── outputs/
    └── hype_cycle_chart_example.json
```

### GraphRAG Prerequisites (Assumed Complete)

The following graph features are **already configured** via `graph/prerequisites_configuration/`:

✅ **Embeddings** (768-dim, OpenAI text-embedding-3-small):
- `Document.embedding` (2,099 documents)
- `Technology.embedding` (1,755 technologies)
- `Company.embedding` (122 companies)

✅ **Indexes**:
- Temporal: `document_published_at` (DATETIME format)
- Composite: `document_type_published` (doc_type + published_at)
- Technology: `technology_id`
- Company: `company_name`
- Document: `document_doc_id`
- Full-text (BM25): `document_fulltext` (title, summary, content)
- Vector: `document_embeddings` (768-dim, cosine similarity)

✅ **Communities** (6 pre-computed versions):
- `community_v0`: Louvain (resolution 0.8) - Broader communities
- `community_v1`: Louvain (resolution 1.0) - Balanced **(FIRST RUN USES THIS)**
- `community_v2`: Louvain (resolution 1.2) - Finer communities
- `community_v3`: Leiden (resolution 0.8) - Higher quality broad
- `community_v4`: Leiden (resolution 1.0) - Higher quality balanced
- `community_v5`: Leiden (resolution 1.2) - Higher quality fine

✅ **Community Nodes** (158 nodes created, filtered by min_members>=5):
- **Schema**:
  ```python
  Community {
    id: str,                    # "v0_123" (version_communityId)
    version: int,               # 0-2 (Louvain variants only)
    community_id: int,          # Numeric community ID
    algorithm: str,             # "Louvain"
    resolution: float,          # 0.8, 1.0, or 1.2
    member_count: int,          # Number of member nodes
    tech_count: int,            # Technologies in community
    company_count: int,         # Companies in community
    doc_count: int,             # Documents in community
    summary: str,               # LLM-generated summary (1-2 sentences)
    embedding: List[float],     # 768-dim vector (text-embedding-3-small)
    top_technologies: List[str], # Top 5 technologies
    top_companies: List[str],   # Top 5 companies
    doc_type_distribution: str  # JSON string (use apoc.convert.fromJsonMap)
  }
  ```
- **Coverage**: v0 (59 nodes), v1 (49 nodes), v2 (50 nodes)
- **Embeddings**: 100% coverage for semantic search
- **Relationships**: `(node)-[:BELONGS_TO_COMMUNITY]->(Community)`
- **Key Feature**: Semantic search across communities using vector similarity

✅ **Graph Algorithms** (pre-computed on all nodes):
- **`pagerank`**: Technology/Company/Document importance (0.0-1.0)
  - High PageRank = well-connected to other important nodes
  - **Innovation Scorer**: Weight patents by PageRank (influential patents score higher)
  - **Phase Detector**: High PageRank + low recent activity → Peak saturation
- **`degree_centrality`**: Connection count (how many edges a node has)
  - High degree = activity hub
  - **Adoption Scorer**: Prioritize high-degree companies (most connected)
- **`betweenness_centrality`**: Bridging role (sits on shortest paths between clusters)
  - High betweenness = "bridge" or "connector" node
  - **Hype Scorer**: High betweenness nodes often show conflicting signals
  - **Evidence Compiler**: Recommend high-betweenness technologies (strategic connectors)

✅ **Relationship Evidence** (on all `MENTIONED_IN` edges):
- `evidence_text`: LLM-extracted justification (1-2 sentences)
- `strength`: Relevance score (0.0-1.0)
- `evidence_confidence`: Extraction confidence (0.0-1.0)
- `role`: Why mentioned (invented, studied, procured, regulated, subject)

✅ **Document Quality Scores** (pre-computed):
- `quality_score`: Document quality metric (0.0-1.0)
- **Standard filter**: `d.quality_score >= 0.85` (high-quality documents only)
- **Use case**: Filter out low-quality/noisy documents in all queries

---

## Shared Query Library

### Purpose

Centralized, reusable Cypher queries to avoid duplication across agents. Each module exports:
1. **Query templates** (parameterized Cypher strings)
2. **Execution functions** (takes neo4j driver, returns parsed results)
3. **Result parsers** (Neo4j records → Python dicts)

### Module 1: Innovation Queries (`shared/queries/innovation_queries.py`)

**Covers**: Patents, research papers, GitHub activity (Layer 1)

```python
def get_patent_count_2yr(driver, tech_id: str) -> dict:
    """Count patents filed in last 2 years with PageRank weighting."""
    query = """
    MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type = 'patent'
      AND date(datetime(d.published_at)) >= date('2023-01-01')
      AND date(datetime(d.published_at)) < date('2025-01-01')
      AND m.role = 'invented'
      AND d.quality_score >= 0.85
    RETURN count(d) AS patent_count,
           sum(d.citations_received) AS total_citations,
           avg(d.pagerank) AS avg_pagerank
    """
    # Returns: {"patent_count": int, "total_citations": int, "avg_pagerank": float}

def get_top_patents_by_citations(driver, tech_id: str, limit: int = 5) -> list:
    """Get top-cited patents with evidence text."""
    query = """
    MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type = 'patent'
      AND m.role = 'invented'
      AND d.quality_score >= 0.85
    RETURN d.doc_id, d.title, d.citations_received, d.published_at,
           m.evidence_text, m.strength
    ORDER BY d.citations_received DESC, d.published_at DESC, d.doc_id ASC
    LIMIT $limit
    """
    # Returns: List[{"doc_id": str, "title": str, "citations": int, "evidence": str}]

def get_community_patents(driver, tech_id: str, community_version: str = 'v1') -> int:
    """Count related patents in same community."""
    # Uses technology's community_v1 to find related innovations
```

### Module 2: Adoption Queries (`shared/queries/adoption_queries.py`)

**Covers**: Government contracts, regulations, SEC revenue mentions (Layer 2)

```python
def get_gov_contracts_1yr(driver, tech_id: str) -> dict:
    """Government contracts in last 1 year."""
    # Returns: {"count": int, "total_value": float, "agencies": List[str]}

def get_top_contracts_by_value(driver, tech_id: str, limit: int = 5) -> list:
    # Returns: List[{"doc_id": str, "awardee": str, "value": float, "evidence": str}]

def get_regulatory_approvals(driver, tech_id: str) -> dict:
    # Returns: {"count": int, "agencies": List[str], "top_approvals": List[dict]}

def get_revenue_mentions_by_company(driver, tech_id: str) -> list:
    # Returns: List[{"ticker": str, "fiscal_period": str, "date": str, "evidence": str}]
```

### Module 3: Narrative Queries (`shared/queries/narrative_queries.py`)

**Covers**: News articles, sentiment, press releases (Layer 4)

```python
def get_news_count_3mo(driver, tech_id: str) -> dict:
    """News coverage in last 3 months."""
    # Returns: {"article_count": int, "avg_sentiment": float}

def get_outlet_tier_breakdown(driver, tech_id: str) -> dict:
    # Returns: {"Industry Authority": int, "Financial Authority": int, ...}

def get_top_articles_by_prominence(driver, tech_id: str, limit: int = 10) -> list:
    # Prioritizes Industry Authority > Financial Authority > Mainstream
```

### Module 4: Risk Queries (`shared/queries/risk_queries.py`)

**Covers**: SEC risk factors, institutional holdings (Layer 3)

```python
def get_sec_risk_mentions_6mo(driver, tech_id: str) -> dict:
    """SEC risk factor mentions in last 6 months."""
    # Returns: {"count": int, "companies": List[str], "categories": List[str]}

def get_institutional_holdings(driver, tech_id: str) -> dict:
    """13F filings showing institutional position changes."""
    # Returns: {"avg_change_pct": float, "holders_increasing": int, "holders_decreasing": int}
```

### Module 5: Hybrid Search (`shared/queries/hybrid_search.py`)

**Covers**: Vector + BM25 fusion for semantic + keyword search

```python
def hybrid_search_documents(
    driver,
    tech_name: str,
    query_embedding: List[float],
    doc_types: List[str],
    k_vector: int = 20,
    k_bm25: int = 20,
    vector_weight: float = 0.3,  # First run: 30% vector, 70% BM25
    k_final: int = 10
) -> list:
    """Reciprocal Rank Fusion of vector + BM25 search."""
    # Step 1: Vector search (semantic)
    # Step 2: BM25 search (keyword)
    # Step 3: RRF fusion with configurable weights
    # Returns: List[{"doc_id": str, "title": str, "hybrid_score": float}]
```

### Module 6: Community Queries (`shared/queries/community_queries.py`)

**Covers**: Community-based filtering, semantic search, and analysis

```python
def get_technology_community(driver, tech_id: str, version: str = 'v1') -> int:
    """Get technology's community ID from node property."""
    query = """
    MATCH (t:Technology {id: $tech_id})
    RETURN t.community_v1 AS community_id  -- Use version parameter to select v0-v5
    """
    # Returns: community_id (int)

def get_community_by_text_search(driver, search_text: str, version: int = 1, limit: int = 10) -> list:
    """Find communities by text search on summaries (keyword matching)."""
    query = """
    MATCH (c:Community)
    WHERE c.version = $version
      AND (c.summary CONTAINS $search_text OR
           ANY(tech IN c.top_technologies WHERE tech CONTAINS $search_text))
    RETURN c.id, c.summary, c.member_count, c.top_technologies
    ORDER BY c.member_count DESC
    LIMIT $limit
    """
    # Returns: List[{"id": str, "summary": str, "member_count": int, "top_technologies": List[str]}]
    # Example: search_text="battery" finds all battery-related communities

def get_similar_communities_by_embedding(
    driver,
    query_embedding: List[float],
    version: int = 1,
    similarity_threshold: float = 0.8,
    limit: int = 10
) -> list:
    """Find semantically similar communities using vector similarity (cosine)."""
    query = """
    MATCH (c:Community)
    WHERE c.version = $version
      AND c.embedding IS NOT NULL
    WITH c,
         gds.similarity.cosine($query_embedding, c.embedding) AS similarity_score
    WHERE similarity_score >= $similarity_threshold
    RETURN c.id, c.summary, c.member_count, c.top_technologies, similarity_score
    ORDER BY similarity_score DESC
    LIMIT $limit
    """
    # Returns: List[{"id": str, "summary": str, "similarity_score": float}]
    # Use case: "Find communities similar to electric vehicle innovation"

def get_community_members(driver, community_id: str, limit: int = 25) -> list:
    """Get all members of a specific community via BELONGS_TO_COMMUNITY relationship."""
    query = """
    MATCH (n)-[:BELONGS_TO_COMMUNITY]->(c:Community {id: $community_id})
    RETURN
      labels(n)[0] AS node_type,
      coalesce(n.name, n.id, n.doc_id) AS identifier,
      n.pagerank AS importance
    ORDER BY n.pagerank DESC NULLS LAST, identifier ASC
    LIMIT $limit
    """
    # Returns: List[{"node_type": str, "identifier": str, "importance": float}]

def get_related_technologies_in_community(driver, tech_id: str, version: str = 'v1', limit: int = 10) -> list:
    """Find related technologies in same community, ranked by PageRank."""
    query = """
    MATCH (t:Technology {id: $tech_id})
    WITH t, t.community_v1 AS community_id  -- Adjust for version
    MATCH (other:Technology)
    WHERE other.community_v1 = community_id
      AND other.id <> t.id
      AND other.pagerank IS NOT NULL
    RETURN other.id, other.name, other.pagerank
    ORDER BY other.pagerank DESC, other.id ASC
    LIMIT $limit
    """
    # Returns: List[{"id": str, "name": str, "pagerank": float}]

def get_community_summary(driver, community_id: str) -> dict:
    """Get full Community node details including LLM summary and metadata."""
    query = """
    MATCH (c:Community {id: $community_id})
    RETURN
      c.summary AS summary,
      c.member_count AS member_count,
      c.top_technologies AS top_technologies,
      c.top_companies AS top_companies,
      apoc.convert.fromJsonMap(c.doc_type_distribution) AS doc_type_distribution
    """
    # Returns: {"summary": str, "member_count": int, "top_technologies": List[str], ...}
```

**Key Use Cases**:
- **Agent 6 (Hype Scorer)**: Use `get_similar_communities_by_embedding()` to find related innovation clusters
- **Agent 7 (Phase Detector)**: Use `get_community_members()` to analyze community composition (tech vs company ratio)
- **All Agents**: Filter by `get_community_by_text_search()` for domain-specific analysis (e.g., "autonomous vehicle" communities)

### Module 7: Citation Queries (`shared/queries/citation_queries.py`)

**Covers**: Evidence tracing for Agent 11

```python
def get_layer_citations(
    driver,
    tech_id: str,
    doc_types: List[str],
    roles: List[str],
    start_date: str,
    limit: int = 5
) -> list:
    """Get top citations for a specific layer."""
    query = """
    MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
    WHERE d.doc_type IN $doc_types
      AND m.role IN $roles
      AND date(datetime(d.published_at)) >= date($start_date)
      AND d.quality_score >= 0.85
    RETURN d.doc_id, d.title, d.doc_type, d.published_at,
           m.strength, m.evidence_text
    ORDER BY m.strength DESC, d.published_at DESC, d.doc_id ASC
    LIMIT $limit
    """
    # Returns: List[{"doc_id": str, "contribution": str, "strength": float}]
```

---

## Evidence Extraction Best Practices

**CRITICAL**: Every query MUST extract evidence for citation tracing. All agents must provide transparent provenance from graph → LLM output.

### Pattern 1: Always Include Evidence Fields

**Every `MENTIONED_IN` query must return**:
- `m.role` – WHY the technology is mentioned (invented, studied, procured, regulated, subject)
- `m.strength` – 0.0-1.0 relevance score
- `m.evidence_confidence` – 0.0-1.0 extraction confidence
- `m.evidence_text` – LLM-extracted justification (1-2 sentences)

```cypher
MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
WHERE datetime(d.published_at) >= datetime() - duration({days: $days_back})
RETURN
  d.doc_id,
  d.title,
  d.doc_type,
  d.published_at,
  m.role,                  -- WHY tech is mentioned
  m.strength,              -- 0.0-1.0 relevance
  m.evidence_confidence,   -- 0.0-1.0 extraction confidence
  m.evidence_text          -- LLM-extracted justification
ORDER BY m.strength DESC, m.evidence_confidence DESC, d.doc_id ASC
LIMIT $limit
```

### Pattern 2: Role-Based Filtering by Intelligence Layer

Each intelligence layer queries specific roles:

**Layer 1: Innovation Signals**
```cypher
MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
WHERE m.role IN ['invented', 'studied']  -- Patents + research papers
  AND d.doc_type IN ['patent', 'technical_paper']
  AND datetime(d.published_at) >= datetime() - duration({days: 730})
RETURN d.doc_id, d.title, m.strength, m.evidence_text
ORDER BY d.published_at DESC, m.strength DESC
```

**Layer 2: Market Formation Signals**
```cypher
MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
WHERE m.role = 'procured'  -- Government validation
  AND d.doc_type = 'government_contract'
  AND datetime(d.published_at) >= datetime() - duration({days: 540})
RETURN d.doc_id, d.title, d.award_amount, m.evidence_text
ORDER BY d.award_amount DESC
```

**Layer 3: Risk Signals**
```cypher
MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
WHERE m.role = 'regulated'  -- Regulatory constraints
  AND d.doc_type = 'regulation'
  AND datetime(d.published_at) >= datetime() - duration({days: 1095})
RETURN d.doc_id, d.title, d.published_at, m.evidence_text
ORDER BY d.published_at DESC
```

**Layer 4: Narrative Signals**
```cypher
MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
WHERE m.role = 'subject'  -- Media coverage
  AND d.doc_type = 'news'
  AND datetime(d.published_at) >= datetime() - duration({days: 180})
RETURN d.doc_id, d.title, d.source, d.published_at, d.tone, m.evidence_text
ORDER BY d.published_at DESC
```

### Pattern 3: Multi-Hop Evidence Paths

**Company → Technology → Document provenance**:

```cypher
MATCH (c:Company)-[r:RELATED_TO_TECH]->(t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
WHERE datetime(d.published_at) >= datetime() - duration({days: $days_back})
RETURN
  c.name                  AS company,
  t.name                  AS technology,
  d.doc_id                AS doc_id,
  d.doc_type              AS doc_type,
  r.relation_type         AS company_relation,
  r.evidence_confidence   AS company_confidence,
  r.evidence_text         AS company_evidence,     -- Why company linked to tech
  m.role                  AS doc_role,
  m.evidence_confidence   AS doc_confidence,
  m.evidence_text         AS doc_evidence          -- Why tech mentioned in doc
ORDER BY d.published_at DESC, r.evidence_confidence DESC
LIMIT $limit
```

**Use case**: Agent 3 (Adoption Scorer) traces company adoption signals back to source documents.

### Pattern 4: Aggregate Evidence by Document Type

**Group evidences by doc_type to show distribution**:

```cypher
MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
WHERE datetime(d.published_at) >= datetime() - duration({days: $days_back})
WITH d.doc_type AS doc_type,
     collect({
       doc_id:              d.doc_id,
       title:               d.title,
       role:                m.role,
       strength:            m.strength,
       evidence_confidence: m.evidence_confidence,
       evidence_text:       m.evidence_text
     })[0..$sample_per_type] AS sample_evidences,
     count(m) AS evidence_count
RETURN
  doc_type,
  evidence_count,
  sample_evidences
ORDER BY evidence_count DESC
```

**Use case**: Agent 11 (Evidence Compiler) creates evidence distribution summary.

### Pattern 5: Temporal Duration Patterns

**Fixed time window** (recommended for determinism):
```cypher
WHERE date(datetime(d.published_at)) >= date('2023-01-01')
  AND date(datetime(d.published_at)) < date('2025-01-01')
```

**Flexible duration** (for recent signals):
```cypher
WHERE datetime(d.published_at) >= datetime() - duration({days: $days_back})
```

**Determinism requirement**: For first run, use fixed dates (`'2023-01-01'`) not `datetime()`.

### Pattern 6: Co-Occurrence Analysis

**Find technologies mentioned in same documents**:

```cypher
MATCH (t:Technology {id: $tech_id})-[m1:MENTIONED_IN]->(d:Document)<-[m2:MENTIONED_IN]-(other:Technology)
WHERE other.id <> t.id
  AND datetime(d.published_at) >= datetime() - duration({days: $days_back})
WITH other, d, m1, m2
RETURN
  other.id          AS other_tech_id,
  other.name        AS other_tech_name,
  d.doc_id          AS shared_doc_id,
  d.doc_type        AS doc_type,
  m1.evidence_text  AS evidence_for_main_tech,
  m2.evidence_text  AS evidence_for_other_tech
ORDER BY other.name, d.doc_id
LIMIT $limit
```

**Use case**: Agent 6 (Hype Analyzer) identifies co-mentioned technologies for context.

### Pattern 7: GraphRAG Triplets for LLM Context

**Subject-Predicate-Object format** for LLM reasoning:

```cypher
MATCH (t:Technology)-[m:MENTIONED_IN]->(d:Document)
WHERE datetime(d.published_at) >= datetime() - duration({days: $days_back})
RETURN
  t.name                AS subject,
  m.role                AS predicate,
  d.doc_id              AS object,
  d.doc_type            AS object_type,
  m.evidence_confidence AS evidence_confidence,
  m.evidence_text       AS evidence_text
ORDER BY m.evidence_confidence DESC, t.name ASC, d.doc_id ASC
LIMIT $limit
```

**Use case**: Pass as structured context to LLM for reasoning.

---

### Common Query Patterns Quick Reference

| Agent | Layer | Roles Filter | Doc Types | Time Window |
|-------|-------|--------------|-----------|-------------|
| Agent 2 (Innovation) | Innovation | `invented`, `studied` | `patent`, `technical_paper`, `github` | 730 days |
| Agent 3 (Adoption) | Market Formation | `procured` | `government_contract`, `sec_filing`, `job_posting` | 540 days |
| Agent 4 (Narrative) | Narrative | `subject` | `news`, `press_release` | 180 days |
| Agent 5 (Risk) | Risk | `regulated` | `regulation` | 1095 days |
| Agent 7 (Phase Detector) | All | All roles | All types | 1095 days |
| Agent 11 (Evidence Compiler) | All | All roles | All types | 1095 days |

**Ordering for Determinism**:
```cypher
ORDER BY d.published_at DESC, m.strength DESC, d.doc_id ASC
```
Always include `d.doc_id` as tie-breaker for reproducibility.

**Quality Filtering**:
```cypher
WHERE m.evidence_confidence >= 0.75  -- High-confidence extractions only
  AND d.quality_score >= 0.85        -- High-quality documents only
```

---

## Graph Algorithms Usage Patterns

All nodes in the graph have pre-computed **PageRank**, **degree_centrality**, and **betweenness_centrality** metrics. These are critical for agent scoring, weighting, and contradiction detection.

### Why Pre-Compute Graph Algorithms?

1. **Performance**: These algorithms are expensive (5-10 minutes to run once)
   - PageRank: O(n × edges × iterations) ≈ O(n²)
   - Betweenness: O(n × edges) ≈ O(n³) for dense graphs

2. **Reproducibility**: Same input graph → same scores every time (critical for deterministic first run)

3. **GraphRAG Efficiency**: Agents query as node properties instantly (no expensive computation during execution)

### Pattern 1: PageRank for Document/Entity Importance

**PageRank reveals overall importance based on incoming connections from other important nodes.**

#### Agent 2 (Innovation Scorer): Weight Patents by PageRank

```cypher
MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
WHERE d.doc_type = 'patent'
  AND m.role = 'invented'
  AND d.quality_score >= 0.85
  AND d.pagerank IS NOT NULL
RETURN
  d.doc_id,
  d.title,
  d.citations_received,
  d.pagerank,
  (d.citations_received * d.pagerank) AS weighted_importance  -- Combine citation count + PageRank
ORDER BY weighted_importance DESC, d.doc_id ASC
LIMIT 10
```

**Scoring Formula Enhancement**:
```python
# Base patent score (count-based)
base_score = min(100, (recent_patents_2yr / 50) * 100)

# PageRank-weighted score (importance-based)
avg_patent_pagerank = sum(p.pagerank for p in top_patents) / len(top_patents)
pagerank_multiplier = 1.0 + (avg_patent_pagerank * 2)  # 1.0x to 3.0x boost

innovation_score = base_score * pagerank_multiplier
```

**Why this matters**: 1 highly-cited, high-PageRank patent (e.g., foundational battery tech) scores higher than 10 low-PageRank patents.

---

#### Agent 3 (Adoption Scorer): Prioritize High-PageRank Companies

```cypher
MATCH (c:Company)-[r:RELATED_TO_TECH]->(t:Technology {id: $tech_id})
WHERE c.pagerank IS NOT NULL
  AND r.relation_type IN ['adopts', 'develops']
RETURN
  c.name,
  c.pagerank,
  r.relation_type,
  r.evidence_confidence
ORDER BY c.pagerank DESC, c.name ASC
LIMIT 10
```

**Insight**: High-PageRank companies (well-connected, influential) adopting a technology is a stronger adoption signal than low-PageRank companies.

---

#### Agent 7 (Phase Detector): Detect Peak Saturation

**High PageRank + Low Recent Activity = Peak Phase Risk**

```cypher
MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
WHERE t.pagerank IS NOT NULL
WITH t,
     t.pagerank AS importance,
     count(CASE WHEN date(datetime(d.published_at)) >= date('2024-01-01') THEN 1 END) AS recent_docs,
     count(d) AS total_docs
WITH t, importance, recent_docs, total_docs,
     toFloat(recent_docs) / total_docs AS recent_activity_ratio
WHERE importance > 0.01  -- High PageRank (top 10% technologies)
  AND recent_activity_ratio < 0.2  -- Less than 20% of documents are recent
RETURN
  t.id,
  t.name,
  importance,
  recent_activity_ratio,
  "Peak saturation risk: High importance but declining activity" AS signal
ORDER BY importance DESC
```

**Phase Classification Rule**:
```python
if pagerank > 0.01 and recent_activity_ratio < 0.2:
    phase = "Peak of Inflated Expectations"  # Market attention peaked, now declining
    phase_confidence += 0.15  # Boost confidence
```

---

### Pattern 2: Degree Centrality for Activity Hubs

**Degree centrality = raw connection count (how many edges a node has).**

#### Agent 6 (Hype Scorer): Identify Over-Connected Technologies

```cypher
MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
WHERE t.degree_centrality IS NOT NULL
WITH t, t.degree_centrality AS connections, d.doc_type AS doc_type, count(d) AS doc_count
WITH t, connections, collect({type: doc_type, count: doc_count}) AS doc_distribution
RETURN
  t.id,
  t.name,
  connections,
  doc_distribution
ORDER BY connections DESC
```

**Hype Detection Logic**:
```python
# High degree centrality = mentioned in many documents (potential hype signal)
if degree_centrality > 50:  # Top 5% connectivity
    news_ratio = news_count / total_docs
    if news_ratio > 0.5:  # More than 50% news mentions
        hype_score += 20  # Likely narrative-driven hype
```

**Insight**: Technologies with high degree centrality but mostly news mentions (not patents/papers) are likely overhyped.

---

### Pattern 3: Betweenness Centrality for Bridge Technologies

**Betweenness centrality = "bridge" role (node sits on shortest paths between clusters).**

#### Agent 11 (Evidence Compiler): Recommend Strategic Connectors

```cypher
MATCH (t:Technology)
WHERE t.betweenness_centrality > 100  -- High betweenness (top 10%)
  AND t.pagerank > 0.001  -- Also important
WITH t
MATCH (t)-[:BELONGS_TO_COMMUNITY]->(c:Community)
RETURN
  t.id,
  t.name,
  t.betweenness_centrality AS bridging_score,
  t.pagerank AS importance,
  c.summary AS community_context,
  "Strategic connector: Bridges multiple innovation clusters" AS recommendation
ORDER BY t.betweenness_centrality DESC
LIMIT 5
```

**Strategic Insight Output**:
```json
{
  "recommendation": "Solid-state batteries bridge traditional battery tech + semiconductor manufacturing",
  "bridging_score": 250.4,
  "importance": 0.0234,
  "rationale": "High betweenness indicates cross-domain applicability"
}
```

---

#### Agent 6 (Hype Scorer): Detect Contradictions in Bridge Nodes

**Bridge technologies often show conflicting signals (connect opposing clusters).**

```cypher
MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
WHERE t.betweenness_centrality > 100  -- Bridge technology
WITH t, d.doc_type AS doc_type, avg(m.strength) AS avg_strength, count(d) AS doc_count
WITH t, collect({type: doc_type, avg_strength: avg_strength, count: doc_count}) AS layer_signals
RETURN
  t.id,
  t.betweenness_centrality,
  layer_signals
```

**Contradiction Detection Logic**:
```python
# Check if bridge technology has conflicting layer signals
patent_strength = layer_signals['patent']['avg_strength']  # Innovation layer
news_strength = layer_signals['news']['avg_strength']      # Narrative layer

if betweenness_centrality > 100:
    contradiction_score = abs(patent_strength - news_strength)
    if contradiction_score > 0.3:  # Significant divergence
        confidence_penalty = -0.1  # Reduce phase confidence
        reasoning = "Bridge technology shows conflicting innovation vs narrative signals"
```

---

### Pattern 4: Combined Metrics for Hidden Gems

**Find undervalued technologies: High PageRank in patents, low in news.**

```cypher
MATCH (t:Technology)<-[m1:MENTIONED_IN]-(p:Document {doc_type: 'patent'})
WHERE t.pagerank > 0.001
WITH t, count(p) AS patent_count, avg(m1.strength) AS patent_strength
MATCH (t)<-[m2:MENTIONED_IN]-(n:Document {doc_type: 'news'})
WITH t, patent_count, patent_strength, count(n) AS news_count
WHERE patent_count > 10 AND news_count < 3  -- High innovation, low narrative
RETURN
  t.id,
  t.name,
  t.pagerank,
  t.betweenness_centrality,
  patent_count,
  news_count,
  "Hidden gem: High innovation signals, low media attention" AS insight
ORDER BY t.pagerank DESC
LIMIT 10
```

**Strategic Insight**: These technologies may be in "Trough of Disillusionment" or early "Slope of Enlightenment" (strategic entry point).

---

### Agent-Specific Algorithm Usage Summary

| Agent | PageRank | Degree Centrality | Betweenness Centrality |
|-------|----------|-------------------|------------------------|
| **Agent 2 (Innovation)** | ✅ Weight patents by PageRank | - | - |
| **Agent 3 (Adoption)** | ✅ Prioritize high-PageRank companies | ✅ Identify most-connected companies | - |
| **Agent 4 (Narrative)** | - | ✅ Detect high-connectivity (hype signal) | - |
| **Agent 6 (Hype Scorer)** | ✅ Compare PageRank across layers | ✅ Over-connectivity = hype | ✅ Bridge nodes show contradictions |
| **Agent 7 (Phase Detector)** | ✅ High PageRank + low activity = Peak | - | - |
| **Agent 11 (Evidence Compiler)** | ✅ Rank recommendations by PageRank | - | ✅ Recommend high-betweenness techs |

---

## LangGraph Implementation Patterns

This section provides concrete LangGraph patterns extracted from production systems. These patterns are essential for implementing the 12-agent workflow correctly.

### Pattern 1: State Management with Type Annotations

**Global State** (flows through entire workflow):

```python
from typing import TypedDict, Annotated, List
from pydantic import BaseModel
import operator

class TechnologyState(TypedDict):
    """Main state that flows through all agents."""
    technology_id: str
    technology_name: str

    # Layer scores (populated by Agents 2-5)
    innovation_score: float
    adoption_score: float
    narrative_score: float
    risk_score: float

    # Evidence aggregation (auto-merged from parallel workers)
    layer_evidence: Annotated[List[dict], operator.add]

    # Analysis results (populated by Agents 6-9)
    hype_score: float
    phase: str
    phase_confidence: float

    # Final outputs (populated by Agents 10-11)
    chart_position: dict
    citations: Annotated[List[dict], operator.add]
```

**Worker State** (isolated to individual agents):

```python
class ScorerWorkerState(TypedDict):
    """Isolated state for each parallel layer scorer (Agents 2-5)."""
    technology_id: str
    technology_name: str
    layer_name: str  # "innovation" | "adoption" | "narrative" | "risk"

    # Worker outputs (merged back to main state via operator.add)
    layer_evidence: Annotated[List[dict], operator.add]
```

**Key Pattern**: Use `Annotated[List[T], operator.add]` for automatic aggregation from parallel workers.

---

### Pattern 2: Dynamic Fan-Out with Send()

Use `Send()` to dynamically create parallel worker nodes based on runtime data.

**Use Case**: Agents 2-5 run in parallel, one per technology.

```python
from langgraph.types import Send

def assign_layer_scorers(state: TechnologyState):
    """Fan out to 4 parallel layer scoring agents."""

    layers = [
        {"layer_name": "innovation", "agent": "innovation_scorer"},
        {"layer_name": "adoption", "agent": "adoption_scorer"},
        {"layer_name": "narrative", "agent": "narrative_scorer"},
        {"layer_name": "risk", "agent": "risk_scorer"}
    ]

    # Create Send() for each layer scorer
    return [
        Send(
            layer["agent"],
            {
                "technology_id": state["technology_id"],
                "technology_name": state["technology_name"],
                "layer_name": layer["layer_name"]
            }
        )
        for layer in layers
    ]

# In workflow builder:
builder.add_conditional_edges(
    "tech_discovery",           # Source node
    assign_layer_scorers,       # Routing function
    [                            # List of allowed target nodes
        "innovation_scorer",
        "adoption_scorer",
        "narrative_scorer",
        "risk_scorer"
    ]
)
```

**Benefits**:
- Parallel execution (4x speedup)
- Automatic result merging via `operator.add`
- Each worker sees isolated state slice

---

### Pattern 3: Conditional Routing

Route workflow dynamically based on state values.

**Use Case**: Agent 12 (Validator) → Retry or Finish

```python
def route_validation(state: TechnologyState) -> str:
    """Route based on validation results."""

    validation_errors = state.get("validation_errors", [])
    retry_count = state.get("retry_count", 0)

    # No errors → Accept
    if len(validation_errors) == 0:
        print("✅ Validation passed")
        return "accept"

    # Too many retries → Force accept
    elif retry_count >= 3:
        print("⚠️ Max retries reached, accepting with warnings")
        return "accept"

    # Has errors → Retry
    else:
        print(f"❌ Validation failed, retry {retry_count + 1}/3")
        return "retry"

# In workflow builder:
builder.add_conditional_edges(
    "output_validator",
    route_validation,
    {
        "accept": END,
        "retry": "chart_generator"  # Loop back
    }
)
```

**Pattern**: Use conditional edges for loops, retries, or multi-path workflows.

---

### Pattern 4: Complete Workflow Construction

**Step-by-step workflow building**:

```python
from langgraph.graph import StateGraph, START, END

# 1. Initialize with state schema
builder = StateGraph(TechnologyState)

# 2. Add all nodes
builder.add_node("tech_discovery", tech_discovery_agent)
builder.add_node("innovation_scorer", innovation_scorer_agent)
builder.add_node("adoption_scorer", adoption_scorer_agent)
builder.add_node("narrative_scorer", narrative_scorer_agent)
builder.add_node("risk_scorer", risk_scorer_agent)
builder.add_node("hype_scorer", hype_scorer_agent)
builder.add_node("phase_detector", phase_detector_agent)
builder.add_node("llm_analyst", llm_analyst_agent)
builder.add_node("ensemble", ensemble_agent)
builder.add_node("chart_generator", chart_generator_agent)
builder.add_node("evidence_compiler", evidence_compiler_agent)
builder.add_node("output_validator", output_validator_agent)

# 3. Define entry point
builder.add_edge(START, "tech_discovery")

# 4. Dynamic fan-out to parallel scorers
builder.add_conditional_edges(
    "tech_discovery",
    assign_layer_scorers,
    ["innovation_scorer", "adoption_scorer", "narrative_scorer", "risk_scorer"]
)

# 5. Sequential chain (Agents 6-9)
builder.add_edge("innovation_scorer", "hype_scorer")  # Wait for all scorers
builder.add_edge("adoption_scorer", "hype_scorer")
builder.add_edge("narrative_scorer", "hype_scorer")
builder.add_edge("risk_scorer", "hype_scorer")
builder.add_edge("hype_scorer", "phase_detector")
builder.add_edge("phase_detector", "llm_analyst")
builder.add_edge("llm_analyst", "ensemble")

# 6. Parallel output generation (Agents 10-11)
builder.add_edge("ensemble", "chart_generator")
builder.add_edge("ensemble", "evidence_compiler")

# 7. Validation gate
builder.add_edge("chart_generator", "output_validator")
builder.add_edge("evidence_compiler", "output_validator")

# 8. Conditional routing from validator
builder.add_conditional_edges(
    "output_validator",
    route_validation,
    {"accept": END, "retry": "chart_generator"}
)

# 9. Compile
workflow = builder.compile()
```

**Key Points**:
- Add all nodes first
- Connect edges second
- Conditional edges for dynamic routing
- START and END are special reserved nodes

---

### Pattern 5: Structured Output with Pydantic

**Always use `.with_structured_output()` for LLM calls**:

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

# 1. Define Pydantic output schema
class InnovationReasoningOutput(BaseModel):
    reasoning: str = Field(
        description="1-2 sentence reasoning for innovation score"
    )
    temporal_trend: str = Field(
        description="growing | stable | declining"
    )

# 2. Create LLM with deterministic settings
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    model_kwargs={"seed": 42}
)

# 3. Use with_structured_output()
structured_llm = llm.with_structured_output(InnovationReasoningOutput)

# 4. Create prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an innovation analyst."),
    ("human", "Patents: {patent_count}, Trend: {trend}")
])

# 5. Invoke (guaranteed schema compliance)
result = structured_llm.invoke(prompt.format_messages(
    patent_count=42,
    trend="declining"
))

# result.reasoning is guaranteed to be a string
# result.temporal_trend is guaranteed to be a string
```

**Benefits**:
- No JSON parsing errors
- Type safety at runtime
- Automatic retry if LLM returns malformed JSON
- Works with Pydantic v2

---

### Pattern 6: Testing Individual Nodes

**Test nodes independently before workflow integration**:

```python
# Create mock state
mock_state: TechnologyState = {
    "technology_id": "evtol",
    "technology_name": "eVTOL",
    "innovation_score": 0.0,
    "adoption_score": 0.0,
    "narrative_score": 0.0,
    "risk_score": 0.0,
    "layer_evidence": [],
    "hype_score": 0.0,
    "phase": "",
    "phase_confidence": 0.0,
    "chart_position": {},
    "citations": []
}

# Test individual node
result = innovation_scorer_agent(mock_state)

# Validate output
assert "innovation_score" in result
assert 0 <= result["innovation_score"] <= 100
assert "layer_evidence" in result
assert len(result["layer_evidence"]) > 0

print(f"✅ Innovation scorer test passed")
print(f"Score: {result['innovation_score']}")
print(f"Evidence count: {len(result['layer_evidence'])}")
```

**Pattern**: Test each agent with mock states before assembling workflow.

---

### Pattern 7: Workflow Visualization

**Generate Mermaid diagram for debugging**:

```python
from IPython.display import Image, display

# After compiling workflow
workflow = builder.compile()

# Generate and display Mermaid diagram
display(Image(workflow.get_graph().draw_mermaid_png()))

# Or save to file
mermaid_png = workflow.get_graph().draw_mermaid_png()
with open("agents/outputs/workflow_diagram.png", "wb") as f:
    f.write(mermaid_png)
```

**Benefits**:
- Visualize node connections
- Identify loops or conditional paths
- Debug workflow structure before execution
- Share architecture with team

---

### Pattern 8: Iteration Control

**Limit reflection loops to prevent infinite cycles**:

```python
class ReflectionState(TypedDict):
    generated_output: str
    evaluation_grade: str
    target_grade: str
    feedback: str
    iteration_count: int  # Track loops

def route_evaluation(state: ReflectionState, max_iterations: int = 5) -> str:
    """Route based on evaluation results."""

    current_grade = state.get("evaluation_grade", "")
    target_grade = state.get("target_grade", "")
    iterations = state.get("iteration_count", 0)

    print(f"Iteration {iterations}: Grade={current_grade}, Target={target_grade}")

    # Grades match → Accept
    if current_grade == target_grade:
        print("✅ Target reached")
        return "accept"

    # Too many iterations → Force stop
    elif iterations >= max_iterations:
        print("⚠️ Max iterations reached")
        return "accept"

    # Continue refining
    else:
        print("🔄 Refining...")
        return "refine"

# Update iteration counter in evaluator node
def evaluator_agent(state: ReflectionState) -> dict:
    # ... evaluation logic ...

    return {
        "evaluation_grade": grade,
        "feedback": feedback,
        "iteration_count": state.get("iteration_count", 0) + 1
    }
```

**Pattern**: Always add iteration counters for reflection loops.

---

### Pattern 9: Error Handling in Nodes

**Graceful degradation with try-except**:

```python
def innovation_scorer_agent(state: TechnologyState) -> dict:
    """Innovation scorer with error handling."""

    try:
        # Query Neo4j
        patent_count = get_patent_count_2yr(driver, state["technology_id"])

        # Calculate score
        innovation_score = calculate_innovation_score(patent_count)

        # Generate LLM reasoning
        reasoning = generate_reasoning(patent_count, innovation_score)

        return {
            "innovation_score": innovation_score,
            "layer_evidence": [{"layer": "innovation", "reasoning": reasoning}]
        }

    except Exception as e:
        print(f"❌ Innovation scorer failed: {e}")

        # Return default values instead of crashing
        return {
            "innovation_score": 50.0,  # Neutral score
            "layer_evidence": [{
                "layer": "innovation",
                "reasoning": f"Error: {str(e)}",
                "error": True
            }]
        }
```

**Pattern**: Nodes should never crash - return default values with error flags.

---

### Pattern 10: Deterministic Execution

**Ensure reproducibility**:

```python
# 1. Fix random seeds
import random
import numpy as np

random.seed(42)
np.random.seed(42)

# 2. LLM determinism
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,           # Deterministic
    model_kwargs={"seed": 42}  # Reproducibility
)

# 3. Sorted queries (ORDER BY)
query = """
MATCH (t:Technology {id: $tech_id})-[:MENTIONED_IN]->(d:Document)
RETURN d.doc_id, d.title, d.score
ORDER BY d.score DESC, d.doc_id ASC  -- Deterministic tie-breaking
LIMIT 10
"""

# 4. Fixed date ranges (not relative)
start_date = "2023-01-01"  # GOOD: Fixed date
# start_date = date.today() - timedelta(days=365)  # BAD: Changes daily

# 5. Deterministic aggregations
sorted_scores = sorted(scores, key=lambda x: x["doc_id"])
avg_score = sum(s["score"] for s in sorted_scores) / len(sorted_scores)
```

**Validation**: Run workflow 3 times, compare outputs with `md5sum`.

---

## Agent Specifications

### Agent 1: Tech Discovery

**Purpose**: Enumerate all technologies from graph to analyze

**GraphRAG Features**:
- Indexes: `technology_id`, `document_published_at`
- Queries: Basic aggregation (no embeddings/communities)

**Input Schema**: None (or optional industry filter)

**Output Schema**:
```python
class Technology(BaseModel):
    id: str
    name: str
    domain: str
    aliases: List[str]
    companies: List[str]  # Tickers
    document_count: int
    doc_type_breakdown: Dict[str, int]

class TechDiscoveryOutput(BaseModel):
    technologies: List[Technology]
```

**Shared Queries Used**: None (custom aggregation query)

**Cypher Pattern**:
```cypher
MATCH (t:Technology)-[:MENTIONED_IN]->(d:Document)
WITH t, d.doc_type AS doc_type, count(DISTINCT d) AS doc_count
WITH t, collect({doc_type: doc_type, count: doc_count}) AS breakdown, sum(doc_count) AS total
RETURN t.id, t.name, t.domain, t.aliases, total, breakdown
ORDER BY total DESC, t.id ASC  -- Deterministic ordering
LIMIT 20
```

**Testing**: Mock Neo4j → 15-20 technologies with metadata

---

### Agent 2: Innovation Scorer (Layer 1)

**Purpose**: Score innovation activity from patents, papers, GitHub

**GraphRAG Features**:
- Indexes: `document_published_at`, `document_type_published`
- Embeddings: Hybrid search for research papers
- Communities: `community_v1` for related patents
- Algorithms: `pagerank` for patent weighting

**Input Schema**:
```python
class InnovationScorerInput(BaseModel):
    technology_id: str
    technology_name: str
```

**Output Schema**:
```python
class InnovationEvidence(BaseModel):
    patent_count_2yr: int
    total_citations: int
    top_patents: List[dict]
    paper_count_2yr: int
    top_papers: List[dict]
    active_repos: int

class InnovationScorerOutput(BaseModel):
    technology_id: str
    innovation_score: float  # 0-100
    evidence: InnovationEvidence
    temporal_trend: str  # "growing" | "stable" | "declining"
    reasoning: str
```

**Shared Queries Used**:
- `innovation_queries.get_patent_count_2yr()`
- `innovation_queries.get_top_patents_by_citations()`
- `innovation_queries.get_community_patents()`
- `hybrid_search.hybrid_search_documents()` (for papers)

**DuckDB Integration**:
```python
from src.utils.duckdb_scholarly_analysis import ScholarlyPapersDatabase
db = ScholarlyPapersDatabase()
top_papers = db.get_top_papers_by_composite_score(limit=200, min_relevance_score=8.0)
```

**Scoring Formula** (with PageRank weighting):
```python
# Step 1: Base counts
base_patent_score = min(100, (recent_patents_2yr / 50) * 100)
base_citation_score = min(100, (total_citations / 500) * 100)
base_paper_score = min(100, (recent_papers_2yr / 30) * 100)
base_github_score = min(100, (active_repos / 10) * 100)

# Step 2: PageRank weighting (importance multiplier)
# Get average PageRank of top patents
avg_patent_pagerank = sum(p['pagerank'] for p in top_patents) / len(top_patents) if top_patents else 0
pagerank_multiplier = 1.0 + (avg_patent_pagerank * 2)  # 1.0x to 3.0x boost

# Step 3: Weighted scores
patent_score = base_patent_score * pagerank_multiplier * 5       # 50% weight
citation_score = base_citation_score * 0.1                        # 1% weight (already includes PageRank)
paper_score = base_paper_score * 3                                # 30% weight
github_score = base_github_score * 2                              # 20% weight

# Step 4: Final innovation score (0-100)
innovation_score = (patent_score + citation_score + paper_score + github_score) / 10.1
```

**Why PageRank matters**: 1 foundational patent (high PageRank) scores higher than 10 incremental patents (low PageRank).

**LLM Usage** (temperature=0, seed=42):
```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

class ReasoningOutput(BaseModel):
    reasoning: str

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, model_kwargs={"seed": 42})
structured_llm = llm.with_structured_output(ReasoningOutput)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an innovation analyst. Provide 1-2 sentence reasoning."),
    ("human", "Patents: {patent_count}, Trend: {trend}, Papers: {paper_count}")
])

result = structured_llm.invoke(prompt.format_messages(...))
# result.reasoning is guaranteed string
```

**Testing**: Mock Neo4j (fixed counts) + Mock DuckDB + Mock LLM → Validate determinism

---

### Agent 3: Adoption Scorer (Layer 2)

**Purpose**: Score market adoption from gov contracts, regulations, revenue

**GraphRAG Features**:
- Indexes: `document_published_at`, `document_type_published`
- Communities: `community_v1` for related companies

**Input Schema**:
```python
class AdoptionScorerInput(BaseModel):
    technology_id: str
    company_tickers: List[str]
```

**Output Schema**:
```python
class AdoptionScorerOutput(BaseModel):
    technology_id: str
    adoption_score: float  # 0-100
    evidence: AdoptionEvidence
    temporal_trend: str
    reasoning: str
```

**Shared Queries Used**:
- `adoption_queries.get_gov_contracts_1yr()`
- `adoption_queries.get_top_contracts_by_value()`
- `adoption_queries.get_regulatory_approvals()`
- `adoption_queries.get_revenue_mentions_by_company()`

**Scoring Formula**:
```python
contract_score = min(100, (total_value_usd / 100_000_000) * 100) * 8   # 23% weight
approval_score = min(100, (approval_count / 5) * 100) * 12             # 34% weight
revenue_score = min(100, (companies_with_revenue / 3) * 100) * 15      # 43% weight
adoption_score = (contract_score + approval_score + revenue_score) / 35
```

**LLM Usage**: Same pattern as Agent 2 (structured output)

---

### Agent 4: Narrative Scorer (Layer 4)

**Purpose**: Score media narrative intensity from news articles

**GraphRAG Features**:
- Indexes: `document_published_at`, `document_fulltext` (BM25)
- Embeddings: Vector search for related coverage (optional)

**Shared Queries Used**:
- `narrative_queries.get_news_count_3mo()`
- `narrative_queries.get_outlet_tier_breakdown()`
- `narrative_queries.get_top_articles_by_prominence()`

**Scoring Formula**:
```python
volume_score = min(100, (article_count_3mo / 100) * 100) * 1.5         # 3% weight
sentiment_score = ((avg_sentiment + 1) / 2 * 100) * 20                 # 39% weight
prominence_score = min(100, (weighted_prominence / 50) * 100) * 30     # 58% weight
narrative_score = (volume_score + sentiment_score + prominence_score) / 51.5
```

---

### Agent 5: Risk Scorer (Layer 3)

**Purpose**: Score financial risk from SEC filings, insider trading

**GraphRAG Features**:
- Indexes: `document_published_at`, `document_type_published`
- DuckDB: Insider transactions (Forms 3/4/5)

**Shared Queries Used**:
- `risk_queries.get_sec_risk_mentions_6mo()`
- `risk_queries.get_institutional_holdings()`

**DuckDB Integration**:
```python
from src.utils.duckdb_insider_transactions import InsiderTransactionsDatabase
db = InsiderTransactionsDatabase()
transactions = db.query_transactions_by_ticker(tickers=['JOBY', 'ACHR'], start_date='2024-05-01')
net_insider_value = transactions['net_insider_value_usd'].sum()
```

**Scoring Formula**:
```python
risk_mention_score = min(100, (risk_count / 30) * 100) * 10            # 22% weight
insider_score = min(100, (abs(net_insider_value) / 10_000_000) * 5) * 20  # 44% weight
institutional_score = min(100, abs(avg_change_pct) * 10) * 15 if avg_change_pct < 0 else 0  # 33% weight
risk_score = (risk_mention_score + insider_score + institutional_score) / 45
```

---

### Agent 6: Hype Scorer (Cross-Layer Contradiction Detection)

**Purpose**: Detect narrative-fundamentals mismatches using graph algorithms

**GraphRAG Features**:
- Algorithms: `degree_centrality` (over-connectivity = hype signal), `betweenness_centrality` (bridge nodes show contradictions)
- Uses Agents 2-5 layer score outputs

**Input Schema**:
```python
class HypeScorerInput(BaseModel):
    technology_id: str
    innovation_score: float
    adoption_score: float
    narrative_score: float
    risk_score: float
```

**Output Schema**:
```python
class Contradiction(BaseModel):
    type: str  # "NARRATIVE_EXCEEDS_INNOVATION" | "HIGH_RISK_WITH_HIGH_NARRATIVE" | "BRIDGE_NODE_CONFLICT" | ...
    severity: str  # "high" | "medium" | "low"
    evidence: str

class HypeScorerOutput(BaseModel):
    technology_id: str
    hype_score: float  # 0-100
    fundamentals_score: float
    hype_ratio: float
    key_contradictions: List[Contradiction]
    lifecycle_signal: str
    reasoning: str
```

**GraphRAG Queries** (query technology's graph metrics):
```python
# Get technology's degree centrality and betweenness for contradiction detection
query = """
MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
WHERE t.degree_centrality IS NOT NULL
  AND t.betweenness_centrality IS NOT NULL
WITH t,
     t.degree_centrality AS connections,
     t.betweenness_centrality AS bridge_score,
     d.doc_type AS doc_type,
     count(d) AS doc_count
WITH t, connections, bridge_score,
     collect({type: doc_type, count: doc_count}) AS doc_distribution
RETURN
  connections,
  bridge_score,
  doc_distribution
"""
```

**Contradiction Rules** (7 rules in `contradiction_rules.py`):
```python
# Rule 1: Narrative exceeds innovation (classic hype signal)
if narrative_score > innovation_score * 1.5:
    contradictions.append({"type": "NARRATIVE_EXCEEDS_INNOVATION", "severity": "high"})

# Rule 2: High risk + high narrative (Peak signal)
if risk_score > 60 and narrative_score > 80:
    contradictions.append({"type": "HIGH_RISK_WITH_HIGH_NARRATIVE", "severity": "high"})

# Rule 3: Over-connectivity with news dominance (degree centrality hype signal)
if degree_centrality > 50:  # Top 5% connectivity
    news_ratio = news_count / total_docs
    if news_ratio > 0.5:  # More than 50% news mentions
        contradictions.append({
            "type": "OVER_CONNECTED_NEWS_DOMINATED",
            "severity": "high",
            "evidence": f"High connectivity ({degree_centrality}) but {news_ratio:.0%} news mentions"
        })

# Rule 4: Bridge node with conflicting signals (betweenness contradiction)
if betweenness_centrality > 100:  # Bridge technology
    patent_strength_avg = layer_signals.get('patent', {}).get('avg_strength', 0)
    news_strength_avg = layer_signals.get('news', {}).get('avg_strength', 0)
    contradiction_score = abs(patent_strength_avg - news_strength_avg)

    if contradiction_score > 0.3:  # Significant divergence
        contradictions.append({
            "type": "BRIDGE_NODE_CONFLICT",
            "severity": "medium",
            "evidence": f"Bridge technology shows conflicting innovation ({patent_strength_avg:.2f}) vs narrative ({news_strength_avg:.2f}) signals"
        })

# ... 3 more rules
```

**Scoring Formula**:
```python
fundamentals_score = (innovation_score + adoption_score) / 2
hype_ratio = narrative_score / fundamentals_score if fundamentals_score > 0 else 10.0
hype_score = min(100, hype_ratio * 50)

# Risk amplification
if risk_score > 60:
    risk_amplifier = 1 + ((risk_score - 60) / 100)
    hype_score = min(100, hype_score * risk_amplifier)
```

**LLM Usage**: None (pure Python logic)

---

### Agent 7: Phase Detector (Gartner Lifecycle Classification)

**Purpose**: Map technology to 1 of 5 Gartner phases using graph algorithms

**GraphRAG Features**:
- Algorithms: `pagerank` (High PageRank + low recent activity = Peak saturation)
- Temporal indexes: `document_published_at` (activity trend analysis)
- Uses Agents 2-6 layer score outputs

**Input Schema**:
```python
class PhaseDetectorInput(BaseModel):
    technology_id: str
    innovation_score: float
    adoption_score: float
    narrative_score: float
    risk_score: float
    hype_score: float
    lifecycle_signal: str
```

**Output Schema**:
```python
class AlternativePhase(BaseModel):
    phase: str
    confidence: float
    reason: str

class PhaseDetectorOutput(BaseModel):
    technology_id: str
    phase: str  # "Technology Trigger" | "Peak of Inflated Expectations" | ...
    phase_code: str  # "TRIGGER" | "PEAK" | "TROUGH" | "SLOPE" | "PLATEAU"
    confidence: float  # 0.0-1.0
    supporting_evidence: List[str]
    alternative_phases: List[AlternativePhase]
    reasoning: str
```

**GraphRAG Query** (PageRank + temporal activity for Peak detection):
```python
# Query technology's PageRank and recent activity ratio
query = """
MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
WHERE t.pagerank IS NOT NULL
WITH t,
     t.pagerank AS importance,
     count(CASE WHEN date(datetime(d.published_at)) >= date('2024-01-01') THEN 1 END) AS recent_docs,
     count(d) AS total_docs
RETURN
  importance,
  recent_docs,
  total_docs,
  toFloat(recent_docs) / total_docs AS recent_activity_ratio
"""
```

**Classification Rules** (deterministic decision tree with PageRank boost in `classification_rules.py`):
```python
# Query PageRank + activity for Peak detection enhancement
pagerank = get_technology_pagerank(driver, tech_id)
recent_activity_ratio = get_recent_activity_ratio(driver, tech_id)

# PEAK: High narrative, declining innovation, high risk, high hype
# Enhanced with PageRank: High importance + declining activity = stronger Peak signal
if narrative >= 75 and hype_score >= 70 and innovation < 60 and risk >= 60:
    base_confidence = 0.85

    # PageRank boost: High historical importance + low recent activity = Peak saturation
    if pagerank > 0.01 and recent_activity_ratio < 0.2:  # Top 10% importance, <20% recent
        base_confidence += 0.10  # Boost confidence to 0.95
        supporting_evidence.append(f"High PageRank ({pagerank:.4f}) with declining activity ({recent_activity_ratio:.0%}) confirms Peak saturation")

    return {"phase": "Peak of Inflated Expectations", "phase_code": "PEAK", "confidence": base_confidence}

# TRIGGER: High innovation, low adoption, low narrative, low risk
elif innovation >= 60 and adoption < 40 and narrative < 40 and risk < 50:
    return {"phase": "Technology Trigger", "phase_code": "TRIGGER", "confidence": 0.80}

# TROUGH: Low narrative, moderate innovation, moderate risk, low hype
elif narrative < 40 and innovation >= 40 and hype_score < 50 and risk >= 40:
    return {"phase": "Trough of Disillusionment", "phase_code": "TROUGH", "confidence": 0.75}

# SLOPE: Moderate-high innovation, growing adoption, moderate narrative, low risk
elif innovation >= 50 and adoption >= 50 and 40 <= narrative < 75 and risk < 60:
    return {"phase": "Slope of Enlightenment", "phase_code": "SLOPE", "confidence": 0.70}

# PLATEAU: Stable innovation, high adoption, low narrative, low risk
elif adoption >= 70 and 40 <= innovation < 70 and narrative < 60 and risk < 50:
    return {"phase": "Plateau of Productivity", "phase_code": "PLATEAU", "confidence": 0.75}

else:
    # Fallback to lifecycle_signal
    return {"phase": "Slope of Enlightenment", "phase_code": "SLOPE", "confidence": 0.50}
```

**LLM Usage**: Structured output for reasoning only (temperature=0, seed=42)

---

### Agent 8: LLM Analyst (Executive Summary Generation)

**Purpose**: Generate executive summary with strategic implications

**GraphRAG Features**: None (uses all previous agent outputs)

**Input Schema**:
```python
class LLMAnalystInput(BaseModel):
    technology_id: str
    technology_name: str
    technology_domain: str
    innovation_score: float
    adoption_score: float
    narrative_score: float
    risk_score: float
    hype_score: float
    phase: str
    phase_confidence: float
    contradictions_summary: str
```

**Output Schema**:
```python
class StrategicImplication(BaseModel):
    stakeholder: str  # "Investors" | "Corporations" | "Regulators"
    implication: str
    timeframe: str

class InflectionPoint(BaseModel):
    trigger: str
    impact: str
    probability: str

class LLMAnalystOutput(BaseModel):
    technology_id: str
    executive_summary: str  # 3-4 sentences
    strategic_implications: List[StrategicImplication]
    inflection_points: List[InflectionPoint]
    comparative_analysis: dict
    confidence_assessment: dict
```

**LLM Usage** (temperature=0, seed=42):
```python
class ExecutiveSummaryOutput(BaseModel):
    executive_summary: str
    strategic_implications: List[StrategicImplication]
    inflection_points: List[InflectionPoint]
    comparative_analysis: dict
    confidence_assessment: dict

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, model_kwargs={"seed": 42})
structured_llm = llm.with_structured_output(ExecutiveSummaryOutput)

prompt = """
You are a strategic analyst for C-suite executives.

Technology: {tech_name}
Phase: {phase} ({confidence}% confidence)
Scores: Innovation={innovation}, Adoption={adoption}, Narrative={narrative}, Risk={risk}

Generate:
1. Executive Summary (3-4 sentences)
2. Strategic Implications (3 stakeholders: Investors, Corporations, Regulators)
3. Inflection Points (2-3 upcoming events)
4. Comparative Analysis (2 historical similar technologies)
5. Confidence Assessment (high confidence findings + uncertainty factors)

Be specific, quantitative, actionable.
"""

result = structured_llm.invoke(prompt.format(...))
```

---

### Agent 9: Ensemble (Weighted Score Combination)

**Purpose**: Combine layer scores using fixed weights + confidence intervals

**GraphRAG Features**: None (uses Agents 2-5 outputs)

**Input Schema**:
```python
class EnsembleInput(BaseModel):
    technology_id: str
    innovation_score: float
    adoption_score: float
    narrative_score: float
    risk_score: float
```

**Output Schema**:
```python
class ConfidenceInterval(BaseModel):
    lower_bound: float
    upper_bound: float
    confidence_level: float  # 0.90

class EnsembleOutput(BaseModel):
    technology_id: str
    composite_score: float  # 0-100
    layer_weights: Dict[str, float]
    weighted_contributions: Dict[str, float]
    confidence_interval: ConfidenceInterval
    reasoning: str
```

**Weighting Formula** (fixed for first run):
```python
layer_weights = {
    "innovation": 0.30,   # 30%
    "adoption": 0.35,     # 35% (highest - market traction matters most)
    "narrative": 0.15,    # 15% (down-weighted - lagging indicator)
    "risk": 0.20          # 20% (inverse-weighted)
}

composite_score = (
    (innovation_score * 0.30) +
    (adoption_score * 0.35) +
    (narrative_score * 0.15) +
    ((100 - risk_score) * 0.20)  # Risk is inverse
)
```

**Confidence Interval** (Monte Carlo with seed=42):
```python
import numpy as np

np.random.seed(42)
simulated_scores = []
for _ in range(1000):
    # Add ±10% noise
    sim_innovation = np.clip(np.random.normal(innovation, innovation * 0.10), 0, 100)
    sim_adoption = np.clip(np.random.normal(adoption, adoption * 0.10), 0, 100)
    sim_narrative = np.clip(np.random.normal(narrative, narrative * 0.10), 0, 100)
    sim_risk = np.clip(np.random.normal(risk, risk * 0.10), 0, 100)

    sim_composite = (sim_innovation * 0.30) + (sim_adoption * 0.35) + (sim_narrative * 0.15) + ((100 - sim_risk) * 0.20)
    simulated_scores.append(sim_composite)

confidence_interval = {
    "lower_bound": round(np.percentile(simulated_scores, 5), 1),
    "upper_bound": round(np.percentile(simulated_scores, 95), 1),
    "confidence_level": 0.90
}
```

---

### Agent 10: Chart Generator (X/Y Coordinate Calculation)

**Purpose**: Calculate X/Y coordinates for Hype Cycle visualization

**GraphRAG Features**: None (uses Agent 7 + 9 outputs)

**Input Schema**:
```python
class ChartGeneratorInput(BaseModel):
    technology_id: str
    technology_name: str
    phase: str
    phase_code: str
    composite_score: float
    narrative_score: float
```

**Output Schema**:
```python
class ChartPosition(BaseModel):
    x: float  # 0-100 (time/maturity axis)
    y: float  # 0-100 (expectations axis)

class VisualMetadata(BaseModel):
    color: str
    size: int
    opacity: float
    label_position: str

class ChartGeneratorOutput(BaseModel):
    technology_id: str
    chart_position: ChartPosition
    visual_metadata: VisualMetadata
```

**Coordinate Calculation**:
```python
phase_anchors = {
    "TRIGGER": {"x": 15, "y": 25},
    "PEAK": {"x": 35, "y": 90},
    "TROUGH": {"x": 55, "y": 20},
    "SLOPE": {"x": 75, "y": 55},
    "PLATEAU": {"x": 90, "y": 65}
}

anchor = phase_anchors[phase_code]
x_jitter = ((composite_score - 50) / 100) * 10  # -5 to +5
y_jitter = ((narrative_score - 50) / 100) * 10  # -5 to +5

x = np.clip(anchor["x"] + x_jitter, 0, 100)
y = np.clip(anchor["y"] + y_jitter, 0, 100)
```

**Visual Metadata**:
```python
phase_colors = {
    "TRIGGER": "#4ECDC4", "PEAK": "#FF6B6B", "TROUGH": "#95A5A6",
    "SLOPE": "#F7B731", "PLATEAU": "#26C281"
}

visual_metadata = {
    "color": phase_colors[phase_code],
    "size": 12,
    "opacity": 0.5 + (confidence * 0.5),  # 0.5-1.0
    "label_position": "top-right" if phase_code == "PEAK" else "top"
}
```

---

### Agent 11: Evidence Compiler (Source Citation Tracing + Strategic Insights)

**Purpose**: Trace every score back to source documents + recommend strategic connectors

**GraphRAG Features**:
- All indexes (temporal, composite, full-text, vector)
- Algorithms: `pagerank` (rank recommendations), `betweenness_centrality` (identify strategic connectors)
- Community nodes: Semantic context for bridge technologies
- Relationship: `MENTIONED_IN.strength` (for ranking)
- Relationship: `MENTIONED_IN.evidence_text` (for provenance)

**Input Schema**:
```python
class EvidenceCompilerInput(BaseModel):
    technology_id: str
    innovation_score: float
    adoption_score: float
    narrative_score: float
    risk_score: float
    company_tickers: List[str]
```

**Output Schema**:
```python
class Citation(BaseModel):
    doc_id: str
    title: str
    type: str
    date: str
    contribution: str  # Evidence text
    strength: float

class LayerEvidence(BaseModel):
    score: float
    document_count: int
    top_citations: List[Citation]

class StrategicInsight(BaseModel):
    technology_id: str
    technology_name: str
    recommendation_type: str  # "strategic_connector" | "hidden_gem" | "bridge_technology"
    bridging_score: float  # Betweenness centrality
    importance: float  # PageRank
    community_context: str  # Community summary
    rationale: str

class EvidenceCompilerOutput(BaseModel):
    technology_id: str
    layer_evidence: Dict[str, LayerEvidence]  # Keys: "innovation", "adoption", "narrative", "risk"
    confidence_by_layer: Dict[str, float]
    total_documents_cited: int
    strategic_insights: List[StrategicInsight]  # New: betweenness-based recommendations
```

**Shared Queries Used**:
- `citation_queries.get_layer_citations()`
- `community_queries.get_community_members()`

**Strategic Insights Query** (betweenness + PageRank for recommendations):
```python
# Find strategic connector technologies with high betweenness centrality
query = """
MATCH (t:Technology)
WHERE t.betweenness_centrality > 100  -- High betweenness (top 10% bridge technologies)
  AND t.pagerank > 0.001  -- Also important (not just bridges)
WITH t
MATCH (t)-[:BELONGS_TO_COMMUNITY]->(c:Community)
RETURN
  t.id AS tech_id,
  t.name AS tech_name,
  t.betweenness_centrality AS bridging_score,
  t.pagerank AS importance,
  c.summary AS community_context
ORDER BY t.betweenness_centrality DESC
LIMIT 5
"""

# Generate strategic insight
strategic_insights = []
for tech in results:
    if tech['bridging_score'] > 100:
        strategic_insights.append({
            "technology_id": tech['tech_id'],
            "technology_name": tech['tech_name'],
            "recommendation_type": "strategic_connector",
            "bridging_score": tech['bridging_score'],
            "importance": tech['importance'],
            "community_context": tech['community_context'],
            "rationale": f"High betweenness ({tech['bridging_score']:.1f}) indicates cross-domain applicability. Bridges multiple innovation clusters."
        })
```

**Layer Filters**:
```python
layer_filters = {
    "innovation": {
        "doc_types": ["patent", "technical_paper", "github"],
        "roles": ["invented", "studied", "implemented"],
        "start_date": "2023-01-01"
    },
    "adoption": {
        "doc_types": ["government_contract", "regulation", "sec_filing"],
        "roles": ["procured", "regulated", "commercialized"],
        "start_date": "2024-01-01"
    },
    "narrative": {
        "doc_types": ["news"],
        "roles": ["subject"],
        "start_date": "2024-08-01"
    },
    "risk": {
        "doc_types": ["sec_filing"],
        "roles": ["subject"],
        "start_date": "2024-05-01"
    }
}
```

**Confidence Calculation**:
```python
def calculate_layer_confidence(doc_count: int, layer: str) -> float:
    thresholds = {"innovation": 200, "adoption": 80, "narrative": 250, "risk": 60}
    return min(1.0, doc_count / thresholds[layer])
```

---

### Agent 12: Output Validator (Quality Gate)

**Purpose**: Validate final chart.json before output

**GraphRAG Features**: None (validates Agent 10-11 outputs)

**Input Schema**:
```python
class ValidatorInput(BaseModel):
    chart_data: HypeCycleChart  # Full chart.json structure
```

**Output Schema**:
```python
class ValidationError(BaseModel):
    field: str
    error_type: str
    message: str
    severity: str  # "critical" | "warning"

class ValidatorOutput(BaseModel):
    is_valid: bool
    validation_errors: List[ValidationError]
    validation_warnings: List[ValidationWarning]
    corrected_chart: Optional[HypeCycleChart]
```

**Validation Rules** (in `validation_rules.py`):

1. **Structure Validation**:
   - All required fields present
   - Technologies array not empty
   - Each technology has all required properties

2. **Data Type Validation**:
   - Scores are floats in [0, 100]
   - Confidence values in [0.0, 1.0]
   - Phase is one of 5 valid phases
   - Dates are ISO 8601 format

3. **Logical Consistency**:
   - PEAK phase → narrative_score > 70
   - TRIGGER phase → innovation_score > 60
   - TROUGH phase → narrative_score < 40
   - Evidence counts match layer scores (non-zero scores → non-zero evidence)

4. **Completeness**:
   - No null/NaN values in critical fields
   - All technologies have executive summary
   - All technologies have at least 1 citation per layer

**Error Handling**:
```python
def validate_chart(chart_data: HypeCycleChart) -> ValidatorOutput:
    errors = []
    warnings = []

    for tech in chart_data.technologies:
        # Structure checks
        if not tech.get("phase"):
            errors.append({"field": "phase", "error_type": "missing", "severity": "critical"})

        # Range checks
        if tech["scores"]["innovation"] > 100:
            errors.append({"field": "innovation_score", "error_type": "out_of_range", "severity": "critical"})

        # Logical consistency
        if tech["phase"] == "Peak of Inflated Expectations" and tech["scores"]["narrative"] < 70:
            warnings.append({"field": "phase", "error_type": "inconsistent", "severity": "warning"})

    is_valid = len([e for e in errors if e["severity"] == "critical"]) == 0
    return ValidatorOutput(is_valid=is_valid, errors=errors, warnings=warnings)
```

---

## LangChain Structured Output Integration

### Pattern (All LLM Agents: 2, 3, 4, 5, 8)

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

# 1. Define Pydantic output schema
class MyAgentOutput(BaseModel):
    reasoning: str = Field(description="1-2 sentence reasoning")
    # ... other fields

# 2. Create LLM with deterministic settings
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,          # Deterministic
    model_kwargs={"seed": 42}  # Reproducibility
)

# 3. Use with_structured_output() for guaranteed schema
structured_llm = llm.with_structured_output(MyAgentOutput)

# 4. Create prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert analyst."),
    ("human", "Analyze {data}")
])

# 5. Invoke and receive validated Pydantic object
result = structured_llm.invoke(prompt.format_messages(data="..."))
# result.reasoning is guaranteed to be a string
```

### Benefits
- **No JSON parsing errors**: LangChain handles extraction
- **Type safety**: Pydantic validates at runtime
- **Retry logic**: Built-in fallback if LLM returns malformed JSON
- **Determinism**: seed=42 ensures reproducibility

---

## Implementation Sequence

### Phase 1: Shared Infrastructure (Day 1, 4 hours)

1. Create folder structure
2. Implement `shared/neo4j_client.py` (connection pooling)
3. Implement `shared/duckdb_client.py` (scholarly + insider DBs)
4. Implement `shared/openai_client.py` (temperature=0, seed=42)
5. Implement `shared/constants.py` (date ranges, weights, thresholds)
6. Implement 7 query modules in `shared/queries/`
7. Create `state_schema.py` (TechnologyState TypedDict)

**Testing**: Unit tests for each query module with mocked Neo4j

### Phase 2: Layer Scoring Agents (Day 1-2, 8 hours)

**Build order** (test each independently):
1. Agent 1 (Tech Discovery) - Simplest, no dependencies
2. Agent 2 (Innovation Scorer) - Most complex (tests shared queries + DuckDB + LLM)
3. Agents 3-5 (parallel) - Similar patterns to Agent 2

**Testing per agent**:
- Unit tests with mocked Neo4j/DuckDB/OpenAI
- Integration tests with real graph (1 technology)
- Validate determinism (run 3 times → identical output)

### Phase 3: Analysis Agents (Day 2, 4 hours)

**Build sequentially** (dependencies):
1. Agent 6 (Hype Scorer) - Requires Agents 2-5 outputs
2. Agent 7 (Phase Detector) - Requires Agent 6 output
3. Agent 8 (LLM Analyst) - Requires Agent 7 output
4. Agent 9 (Ensemble) - Requires Agents 2-5 outputs

**Testing**: Use fixed mock scores from Agents 2-5

### Phase 4: Output Agents (Day 3, 4 hours)

**Build in parallel**:
1. Agent 10 (Chart Generator)
2. Agent 11 (Evidence Compiler)
3. Agent 12 (Output Validator)

### Phase 5: LangGraph Orchestrator (Day 3, 4 hours)

1. Implement `langgraph_orchestrator.py`
2. Define workflow graph (12 nodes + edges)
3. Implement parallel execution (Agents 2-5, Agents 10-11)
4. Add error handling
5. Add logging/timing

### Phase 6: Integration Testing (Day 4, 8 hours)

1. End-to-end test (1 technology)
2. Reproducibility test (3 runs, same tech → byte-identical JSON)
3. Full industry test (15 technologies)
4. Performance profiling

---

## First Run Execution

### Prerequisites Validation

```bash
python graph/prerequisites_configuration/07_validate_prerequisites.py

# Expected output:
# [SUCCESS] ALL PREREQUISITES READY
# - Indexes: 5/5 created
# - Embeddings: 100% coverage (2099 docs, 1755 tech, 122 companies)
# - Full-text index: READY
# - Vector index: READY
# - Communities: 6 versions (v0-v5) with summaries
# - Graph algorithms: PageRank, degree centrality, betweenness centrality
```

### Execution Command

```bash
# All technologies
python agents/langgraph_orchestrator.py \
    --industry="eVTOL" \
    --output="agents/outputs/hype_cycle_chart.json" \
    --verbose

# Single technology (testing)
python agents/langgraph_orchestrator.py \
    --tech-id="evtol" \
    --output="agents/outputs/test.json" \
    --debug
```

### Expected Output Format

Match structure of `agents/outputs/hype_cycle_chart_example.json`:

```json
{
  "industry": "eVTOL & Advanced Air Mobility",
  "generated_at": "2025-11-09T10:30:00Z",
  "metadata": {
    "total_documents": 1247,
    "date_range": "2020-01-01 to 2025-11-09"
  },
  "technologies": [
    {
      "id": "evtol",
      "name": "Electric Vertical Takeoff and Landing",
      "phase": "Peak of Inflated Expectations",
      "phase_confidence": 0.92,
      "chart_x": 35.2,
      "chart_y": 88.7,
      "scores": {
        "innovation": 45.2,
        "adoption": 62.3,
        "narrative": 89.4,
        "risk": 71.2,
        "hype": 83.2,
        "composite": 61.8
      },
      "summary": "High media coverage but minimal revenue...",
      "evidence_counts": {
        "patents": 42,
        "papers": 18,
        "news": 269,
        "sec_filings": 12
      }
    }
  ]
}
```

### Validation Criteria

**Correctness**:
- All 15 technologies have valid phase classification
- All scores in [0, 100] range
- Confidence values in [0.0, 1.0] range
- No missing required fields

**Reproducibility** (CRITICAL):
- Run same technology 3 times → byte-identical JSON
- Validate: `md5sum hype_cycle_chart.json` (should be identical across runs)

**Performance**:
- < 30s per technology (with parallelization)
- < 10min for 15 technologies
- Memory usage < 2GB

**Cost**:
- < $0.50 per technology
- ~$7.50 for 15 technologies

---

## Key Technical Details

### Date Handling (CRITICAL)

Graph uses **DATETIME** not DATE:

```cypher
-- WRONG (will fail)
WHERE d.published_at >= date('2023-01-01')

-- CORRECT
WHERE date(datetime(d.published_at)) >= date('2023-01-01')
```

### Multi-Query GraphRAG Strategy

Each agent queries 3-5 ways:
1. Direct Cypher aggregation
2. Hybrid search (vector + BM25)
3. Community filtering (`community_v1`)
4. PageRank weighting
5. Evidence relationships (`MENTIONED_IN.strength`)

**Why?** Graph is imperfect. Multiple perspectives reveal truth.

### Community Usage Pattern

```cypher
-- Always filter by technology's community
MATCH (t:Technology {id: $tech_id})
MATCH (related:Technology)
WHERE related.community_v1 = t.community_v1
RETURN related
ORDER BY related.pagerank DESC
```

### Evidence Text Extraction

```cypher
-- Use relationship properties for citations
MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
RETURN d.doc_id, d.title,
       m.evidence_text,  -- LLM-extracted justification
       m.strength        -- 0.0-1.0 relevance
ORDER BY m.strength DESC
```

### Determinism Checklist

- ✅ LLM: temperature=0, seed=42
- ✅ Queries: ORDER BY with deterministic tie-breaking (e.g., `ORDER BY score DESC, doc_id ASC`)
- ✅ Dates: Fixed ranges (not relative to current date)
- ✅ Aggregations: Sorted inputs before aggregation
- ✅ Random operations: `np.random.seed(42)` if needed
- ✅ Community version: Always v1 for first run

---

## Summary

This document provides all essential information to implement the 12-agent first run system:

1. **Architecture**: Clear data flow, dependencies, folder structure
2. **Shared Query Library**: 7 modules with reusable Cypher queries
3. **12 Agent Specifications**: Input/output schemas, GraphRAG features, scoring formulas
4. **LangChain Integration**: Structured outputs for guaranteed JSON compliance
5. **Implementation Sequence**: Day-by-day build order with testing strategy
6. **Execution Guide**: Commands, validation, expected outputs

**Next Steps**:
1. Complete Phase 1 (shared infrastructure)
2. Build Agents 1-5 (layer scoring)
3. Build Agents 6-9 (analysis)
4. Build Agents 10-12 (output generation + validation)
5. Implement LangGraph orchestrator
6. Run integration tests
7. Generate first `hype_cycle_chart.json`

**Success Criteria**: Same input → Same output (byte-identical JSON across runs)
