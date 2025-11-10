# Graph Prerequisites Configuration

**Setup scripts for Neo4j graph before running multi-agent Hype Cycle system**

## Overview

This directory contains 8 prerequisite scripts that configure your Neo4j graph database with all necessary indexes, embeddings, and pre-computed structures required by the 11-agent multi-agent system.

**IMPORTANT**: All these scripts must be run BEFORE starting the multi-agent system. They prepare the graph with:
- Temporal and composite indexes for fast queries
- OpenAI embeddings for vector search
- Full-text (BM25) and vector indexes for hybrid search
- 3 pre-computed community detection variants (Louvain at resolutions 0.8, 1.0, 1.2)
- LLM-generated semantic summaries for each community (GPT-4o-mini)
- Graph algorithms (PageRank, centrality metrics)

## Prerequisites

### Environment Variables

Ensure your `.env` file contains:

```bash
# Neo4j Connection
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j

# OpenAI API (for embeddings)
OPENAI_API_KEY=sk-your-key-here
```

### Python Dependencies

```bash
pip install neo4j python-dotenv openai
```

## Quick Start

### Option 1: Run All Prerequisites (Recommended)

```bash
# Interactive mode (prompts before expensive operations)
python graph/prerequisites_configuration/run_all_prerequisites.py

# Auto-approve mode (no prompts)
python graph/prerequisites_configuration/run_all_prerequisites.py --auto-approve

# Skip validation
python graph/prerequisites_configuration/run_all_prerequisites.py --skip-validation
```

### Option 2: Run Scripts Individually

```bash
# Step 1: Create indexes (fast, free)
python graph/prerequisites_configuration/01_create_indexes.py

# Step 2: Generate embeddings (10-15 min, ~$0.20-1.00)
python graph/prerequisites_configuration/02_generate_embeddings.py

# Step 3: Create full-text index (fast, free)
python graph/prerequisites_configuration/03_create_fulltext_index.py

# Step 4: Create vector index (fast, free)
python graph/prerequisites_configuration/04_create_vector_index.py

# Step 5: Compute communities (5-10 min, free)
python graph/prerequisites_configuration/05_compute_communities.py

# Step 5.5: Generate community summaries (5-10 min, ~$0.01-0.05)
python graph/prerequisites_configuration/05_5_generate_community_summaries.py

# Step 6: Compute graph algorithms (5-10 min, free)
python graph/prerequisites_configuration/06_compute_graph_algorithms.py

# Step 7: Validate all prerequisites (fast, free)
python graph/prerequisites_configuration/07_validate_prerequisites.py
```

## Scripts Details

### 01_create_indexes.py

**Purpose**: Create temporal and composite indexes for fast Neo4j queries

**Creates**:
- `document_published_at` - Temporal index on Document.published_at (datetime)
- `document_type_published` - Composite index on (doc_type, published_at)
- `technology_id` - Technology ID index
- `company_name` - Company name index (NOT ticker, per user spec)
- `document_doc_id` - Document doc_id index for deduplication

**Runtime**: ~2 minutes
**Cost**: Free
**Safe to run**: YES (idempotent)

**Important Notes**:
- All date fields are DATETIME not DATE (use `date(datetime(d.published_at))` format)
- Company index is on `name` field, NOT `ticker` field
- Uses `IF NOT EXISTS` - safe to re-run

---

### 02_generate_embeddings.py

**Purpose**: Generate OpenAI embeddings for vector search

**Creates**:
- Document.embedding (768-dim) from `title + " " + summary + " " + content`
- Technology.embedding (768-dim) from `name + " " + domain + " " + description`
- Company.embedding (768-dim) from `name + " " + aliases.join(" ")`

**Model**: OpenAI text-embedding-3-small (768 dimensions)
**Pricing**: $0.00002 per 1k tokens
**Estimated Cost**: ~$0.20-1.00 (depends on node count)
**Runtime**: ~10-15 minutes
**Safe to run**: YES (but expensive - prompts for confirmation)

**Features**:
- Cost estimation before running
- Checkpoint/resume capability (saves progress every 10 nodes)
- Rate limiting (50 req/sec, well under OpenAI limits)
- Progress tracking

**Resume from failure**:
```bash
# Just re-run - automatically resumes from checkpoint
python graph/prerequisites_configuration/02_generate_embeddings.py
```

**Reset checkpoint**:
```bash
rm graph/prerequisites_configuration/.checkpoint_embeddings.json
```

---

### 03_create_fulltext_index.py

**Purpose**: Create BM25 full-text search index

**Creates**:
- Full-text index `document_fulltext` on Document (title, summary, content)
- Analyzer: `standard-no-stop-words`
- Mode: `eventually_consistent` (for performance)

**Runtime**: ~2-3 minutes
**Cost**: Free
**Safe to run**: YES (requires embeddings exist)

**Usage Example**:
```cypher
CALL db.index.fulltext.queryNodes('document_fulltext', 'eVTOL OR aircraft')
YIELD node, score
RETURN node.title, score
ORDER BY score DESC
LIMIT 10
```

---

### 04_create_vector_index.py

**Purpose**: Create vector similarity search index

**Creates**:
- Vector index `document_embeddings` on Document.embedding
- Dimensions: 768 (matching text-embedding-3-small)
- Similarity metric: cosine

**Runtime**: ~2-3 minutes
**Cost**: Free
**Safe to run**: YES (requires embeddings from Script 2)

**Usage Example**:
```cypher
// Assuming $query_embedding is a 768-dim vector
CALL db.index.vector.queryNodes('document_embeddings', 20, $query_embedding)
YIELD node, score
RETURN node.title, score
ORDER BY score DESC
```

**Hybrid Search (Vector + BM25)**:
```cypher
// Reciprocal Rank Fusion (RRF)
CALL {
  // BM25 search
  CALL db.index.fulltext.queryNodes('document_fulltext', 'eVTOL')
  YIELD node, score
  RETURN node, score AS bm25_score
  ORDER BY score DESC LIMIT 20
}
WITH node, bm25_score,
     row_number() OVER (ORDER BY bm25_score DESC) AS bm25_rank
CALL {
  WITH node
  // Vector search
  CALL db.index.vector.queryNodes('document_embeddings', 20, $query_embedding)
  YIELD node AS vnode, score AS vector_score
  RETURN vnode, vector_score,
         row_number() OVER (ORDER BY vector_score DESC) AS vector_rank
}
WITH node,
     1.0 / (60 + bm25_rank) + 1.0 / (60 + vector_rank) AS rrf_score
RETURN node, rrf_score
ORDER BY rrf_score DESC
LIMIT 20
```

---

### 05_compute_communities.py

**Purpose**: Pre-compute 6 community detection variants for multi-run diversity

**Creates** (as node properties):
- `community_v0` - Louvain (resolution 0.8) - broader communities
- `community_v1` - Louvain (resolution 1.0) - balanced communities
- `community_v2` - Louvain (resolution 1.2) - finer communities
- `community_v3` - Leiden (resolution 0.8) - broader communities (higher quality)
- `community_v4` - Leiden (resolution 1.0) - balanced communities (higher quality)
- `community_v5` - Leiden (resolution 1.2) - finer communities (higher quality)

**Why 6 versions?**
Multi-run consensus strategy uses different community perspectives per run. Each run randomly selects a community version, providing different analytical lenses on the same graph.

**Runtime**: ~5-10 minutes (depends on graph size)
**Cost**: Free (computation only)
**Safe to run**: YES (but expensive - prompts for confirmation)

**Algorithm Details**:
- **Louvain**: Fast, good modularity optimization
- **Leiden**: Higher quality, better resolution handling
- **Random Seed**: Fixed at 42 for reproducibility across runs

**Usage Examples**:

```cypher
// 1. Community Overview - All Variants
MATCH (n)
WHERE n.community_v0 IS NOT NULL
WITH
    count(DISTINCT n.community_v0) AS v0_communities,
    count(DISTINCT n.community_v1) AS v1_communities,
    count(DISTINCT n.community_v2) AS v2_communities,
    count(n) AS total_nodes
RETURN
    v0_communities,
    v1_communities,
    v2_communities,
    total_nodes,
    round(toFloat(total_nodes) / v0_communities, 1) AS v0_avg_size,
    round(toFloat(total_nodes) / v1_communities, 1) AS v1_avg_size,
    round(toFloat(total_nodes) / v2_communities, 1) AS v2_avg_size

// 2. View Largest Communities (v1 - Balanced)
MATCH (n)
WHERE n.community_v1 IS NOT NULL
WITH n.community_v1 AS community, count(n) AS size, collect(labels(n)[0]) AS node_labels
ORDER BY size DESC
LIMIT 10
RETURN
    community,
    size,
    node_labels[0..5] AS sample_labels

// 3. Explore a Specific Community's Members
MATCH (n)
WHERE n.community_v1 = 123  // Replace with actual community ID
RETURN
    labels(n)[0] AS node_type,
    coalesce(n.name, n.id, n.doc_id) AS identifier,
    n.community_v0 AS also_in_v0,
    n.community_v2 AS also_in_v2
LIMIT 25

// 4. Community Size Distribution
MATCH (n)
WHERE n.community_v1 IS NOT NULL
WITH n.community_v1 AS community, count(n) AS size
WITH size, count(*) AS num_communities
ORDER BY size DESC
RETURN
    size AS community_size,
    num_communities,
    (size * num_communities) AS total_nodes_in_this_size_bucket
LIMIT 20

// 5. Compare Community Assignments Across Variants
MATCH (n)
WHERE n.community_v0 IS NOT NULL
RETURN
    labels(n)[0] AS node_type,
    coalesce(n.name, n.id, n.doc_id) AS identifier,
    n.community_v0 AS v0_community,
    n.community_v1 AS v1_community,
    n.community_v2 AS v2_community
LIMIT 50

// 6. Find Technologies in Same Community
MATCH (t:Technology)
WHERE t.community_v1 = 1  // Replace with actual community ID
RETURN
    t.id AS tech_id,
    t.name AS tech_name,
    t.community_v1 AS community
ORDER BY t.name
LIMIT 25

// 7. Community Cross-Reference (Multi-Resolution Analysis)
MATCH (n)
WHERE n.community_v0 IS NOT NULL
WITH n.community_v0 AS broad_community, collect(DISTINCT n.community_v2) AS fine_communities
WHERE size(fine_communities) > 1
RETURN
    broad_community,
    size(fine_communities) AS num_subcommunities,
    fine_communities
ORDER BY num_subcommunities DESC
LIMIT 10
```

---

### 05_5_generate_community_summaries.py

**Purpose**: Generate semantic descriptions for community detection variants using concurrent batch processing

**Creates**:
- Community nodes for 3 Louvain variants (v0-v2)
- LLM-generated summaries (1-2 sentences per community)
- **Vector embeddings** (768-dimensional) for each community summary
- Rich metadata (member counts, top entities, doc type distribution)
- BELONGS_TO_COMMUNITY relationships linking members to communities

**Why add this?**
Makes communities semantically queryable. Instead of just knowing "community_v1 = 123", agents can understand "Battery companies and solid-state innovation patents" and filter communities by meaning, not just IDs.

**Runtime**: ~3-5 minutes (concurrent processing with 4 workers)
**Cost**: ~$0.01-0.05 (GPT-4o-mini for summaries + text-embedding-3-small for vectors)
**Safe to run**: YES (but requires approval - creates new nodes and calls OpenAI API)

**Models**:
- GPT-4o-mini: $0.000150 per 1k input tokens, $0.000600 per 1k output tokens
- text-embedding-3-small: $0.00002 per 1k tokens (768 dimensions)

**Community Node Schema**:
```cypher
CREATE (c:Community {
  id: "v0_123",                        // Unique ID: version_communityId
  version: 0,                           // Variant (0-2)
  community_id: 123,                    // Numeric community ID
  algorithm: "Louvain",                 // Louvain only
  resolution: 0.8,                      // Resolution parameter (0.8, 1.0, or 1.2)
  member_count: 45,                     // Number of member nodes
  tech_count: 20,                       // Technologies in community
  company_count: 10,                    // Companies in community
  doc_count: 15,                        // Documents in community
  summary: "Battery companies...",      // LLM-generated summary
  embedding: [0.123, -0.456, ...],      // 768-dimensional vector (text-embedding-3-small)
  top_technologies: ["battery", "solid-state"],  // Top 5 technologies (array)
  top_companies: ["ACME", "Corp"],      // Top 5 companies (array)
  doc_type_distribution: '{"patent": 20, "research_paper": 15, "news": 10}'  // JSON string (parse with apoc.convert.fromJsonMap)
})
```

**Note**: `doc_type_distribution` is stored as a JSON string because Neo4j doesn't support nested maps as property values. Use `apoc.convert.fromJsonMap()` to parse it in queries.

**Features**:
- **Concurrent processing** with ThreadPoolExecutor (4 workers default, ~50% faster)
- **Enhanced checkpoint system** with batch files saved every 100 communities
- **Test mode** (`--limit 10`) for validating with first 10 communities
- **Progress tracking** with tqdm (real-time ETA and speed)
- **Retry logic** with exponential backoff for OpenAI API failures
- **Resume capability** - skip already-processed communities automatically
- **Merge functionality** to consolidate checkpoint files

**Usage**:
```bash
# Test with first 10 communities
python graph/prerequisites_configuration/05_5_generate_community_summaries.py --limit 10

# Full run (all communities)
python graph/prerequisites_configuration/05_5_generate_community_summaries.py

# Filter small communities (skip communities with < 5 members)
python graph/prerequisites_configuration/05_5_generate_community_summaries.py --min-members 5

# Clean existing Community nodes before creating new ones
python graph/prerequisites_configuration/05_5_generate_community_summaries.py --clean

# Custom workers and checkpoint interval
python graph/prerequisites_configuration/05_5_generate_community_summaries.py --workers 8 --checkpoint 50

# Auto-approve mode (no prompts)
python graph/prerequisites_configuration/05_5_generate_community_summaries.py --auto-approve
```

**Resume from failure**:
```bash
# Just re-run - automatically resumes from checkpoint
python graph/prerequisites_configuration/05_5_generate_community_summaries.py
```

**Reset checkpoints**:
```bash
rm graph/prerequisites_configuration/.checkpoint_community_batch.json
rm -rf graph/prerequisites_configuration/batch_processing/checkpoints/
```

**Usage Examples**:
```cypher
// 1. Find all battery-related communities semantically (text search)
MATCH (c:Community)
WHERE c.summary CONTAINS 'battery' OR c.summary CONTAINS 'energy storage'
RETURN c.id, c.summary, c.member_count, c.top_technologies
ORDER BY c.member_count DESC

// 2. Find similar communities using vector similarity (semantic search)
// First, get the embedding of a community of interest
MATCH (c:Community {id: 'v1_123'})
WITH c.embedding AS query_embedding
// Then find communities with similar embeddings (cosine similarity)
MATCH (similar:Community)
WHERE similar.id <> 'v1_123'  // Exclude the query community itself
WITH similar,
     gds.similarity.cosine(query_embedding, similar.embedding) AS similarity_score
WHERE similarity_score > 0.8  // High similarity threshold
RETURN similar.id, similar.summary, similarity_score
ORDER BY similarity_score DESC
LIMIT 10

// 3. Get all members of a specific community
MATCH (n)-[:BELONGS_TO_COMMUNITY]->(c:Community {id: 'v1_123'})
RETURN labels(n)[0] AS node_type, n.name, c.summary
LIMIT 25

// 4. Parse doc_type_distribution (stored as JSON string)
MATCH (c:Community {id: 'v1_123'})
RETURN c.id, c.summary,
       apoc.convert.fromJsonMap(c.doc_type_distribution) AS doc_types
```

**Validation Results** (from Script 7):
```
Graph Statistics:
  - Total nodes: 4,134
  - Total relationships: 21,516
  - Documents: 2,099 (100% embeddings)
  - Technologies: 1,755 (100% embeddings)
  - Companies: 122 (100% embeddings)

Community Summaries:
  - Community nodes created: 158 (filtered from 1,879 total communities)
  - v0 (Louvain 0.8): 59 Community nodes
  - v1 (Louvain 1.0): 49 Community nodes
  - v2 (Louvain 1.2): 50 Community nodes
  - Embedding coverage: 100% (768-dimensional vectors)
  - Summary coverage: 100% (LLM-generated descriptions)

Community Detection Coverage:
  - Nodes with community assignments: 3,976/4,134 (96.2%)
  - v0: 671 total communities (59 with summaries after min_members=5 filter)
  - v1: 599 total communities (49 with summaries)
  - v2: 609 total communities (50 with summaries)
```

**Benefits for Multi-Agent System**:
- **Agent 7 (Contradiction Analyzer)**: Can filter by community AND understand semantic meaning
- **All Agents**: Can query "battery-related communities" semantically, not just by ID
- **Multi-run Diversity**: Each run gets different community perspectives with semantic context
- **Debugging**: Easier to understand what each community represents

---

### 06_compute_graph_algorithms.py

**Purpose**: Pre-compute graph algorithms for node importance/centrality

**Creates** (as node properties):
- `pagerank` - PageRank score (technology/company importance)
- `degree_centrality` - Degree centrality (connection count)
- `betweenness_centrality` - Betweenness centrality (bridging role)

**Runtime**: ~5-10 minutes (depends on graph size)
**Cost**: Free (computation only)
**Safe to run**: YES (but expensive - prompts for confirmation)

**What Each Algorithm Reveals**:

1. **PageRank** - Overall importance/influence based on incoming connections
   - High PageRank = Node is well-connected to other important nodes
   - **For Technologies**: Which innovations are central to the ecosystem (many patents, papers, mentions)
   - **For Companies**: Which companies are most influential (connected to many technologies, documents)
   - **For Documents**: Which documents are most referenced/important
   - **Agent Use**: Phase Detector uses high PageRank + low recent activity to detect Peak saturation

2. **Degree Centrality** - Raw connection count (how many edges a node has)
   - High Degree = Most directly connected node (activity hub)
   - **For Technologies**: Which technologies appear in the most documents
   - **For Companies**: Which companies are involved in the most technologies
   - **Agent Use**: Contradiction Analyzer finds high-connectivity nodes to detect inconsistencies

3. **Betweenness Centrality** - Bridging role (how often node sits on shortest paths)
   - High Betweenness = "Bridge" or "connector" node between clusters
   - **For Technologies**: Which innovations connect otherwise separate clusters (e.g., solid-state batteries bridging traditional batteries + semiconductors)
   - **For Companies**: Which companies bridge different technology domains
   - **Agent Use**: Strategic Insights recommends technologies with high betweenness (cross-domain connectors)

**Why Pre-Compute Instead of Calculate On-Demand?**

1. **Performance**: These algorithms are computationally expensive (5-10 minutes to run once)
   - PageRank: O(n × edges × iterations) ≈ O(n²)
   - Betweenness: O(n × edges) ≈ O(n³) for dense graphs

2. **Reproducibility**: Same input graph → same scores every time
   - Critical for your multi-agent system's 10-run reproducibility requirements
   - Agents get consistent importance metrics across all runs

3. **GraphRAG Efficiency**: Agents query these as node properties instantly
   - No need to run expensive algorithms during agent execution
   - Queries like `MATCH (t:Technology) WHERE t.pagerank > 0.01` are fast

**Algorithm Details**:
- **PageRank**: MaxIterations=20, DampingFactor=0.85, Tolerance=0.0000001
- **Degree Centrality**: Counts incoming + outgoing connections
- **Betweenness Centrality**: Measures node's role in shortest paths between all node pairs

**Multi-Agent Use Cases**:

- **Phase Detector (Agent 1)**: High PageRank + low recent activity → Peak saturation risk
- **Innovation Scorer (Agent 2)**: Weight patents by PageRank (high-PageRank patents = more influential)
- **Market Formation Scorer (Agent 3)**: Prioritize high-PageRank companies for gov contracts
- **Contradiction Analyzer (Agent 7)**: High betweenness nodes often show conflicting signals (bridge opposing clusters)
- **Strategic Insights (Agent 11)**: Recommend technologies with high betweenness (strategic connectors), identify companies with high PageRank + insider buying (hidden gems)

**Usage Examples**:

```cypher
// 1. Top 10 most important technologies by PageRank
MATCH (t:Technology)
WHERE t.pagerank IS NOT NULL
RETURN t.id, t.name, t.pagerank AS importance
ORDER BY t.pagerank DESC
LIMIT 10

// 2. Find bridge technologies (high betweenness) - strategic connectors
MATCH (t:Technology)
WHERE t.betweenness_centrality > 100
RETURN t.id, t.name, t.betweenness_centrality AS bridging_score
ORDER BY t.betweenness_centrality DESC
LIMIT 10

// 3. Find undervalued technologies (high PageRank in patents, low in news)
MATCH (t:Technology)<-[:MENTIONS]-(p:Document {doc_type: 'patent'})
WHERE t.pagerank > 0.001
WITH t, count(p) AS patent_count
MATCH (t)<-[:MENTIONS]-(n:Document {doc_type: 'news'})
WITH t, patent_count, count(n) AS news_count
WHERE patent_count > 10 AND news_count < 3
RETURN t.id, t.name, t.pagerank, patent_count, news_count
ORDER BY t.pagerank DESC
LIMIT 10

// 4. Compare PageRank across document types (detect layer mismatches)
MATCH (t:Technology)<-[:MENTIONS]-(d:Document)
WHERE t.pagerank IS NOT NULL
WITH t, d.doc_type AS doc_type, count(d) AS mention_count
ORDER BY t.pagerank DESC, mention_count DESC
RETURN t.id, t.name, t.pagerank,
       collect({type: doc_type, count: mention_count})[0..5] AS top_doc_types
LIMIT 10

// 5. Find influential companies (high PageRank + high degree centrality)
MATCH (c:Company)
WHERE c.pagerank IS NOT NULL AND c.degree_centrality IS NOT NULL
RETURN c.name, c.pagerank, c.degree_centrality,
       (c.pagerank * c.degree_centrality) AS influence_score
ORDER BY influence_score DESC
LIMIT 10

// 6. Detect strategic connectors (betweenness + community analysis)
MATCH (t:Technology)
WHERE t.betweenness_centrality > 100 AND t.community_v1 IS NOT NULL
RETURN t.id, t.name,
       t.betweenness_centrality AS bridging_role,
       t.community_v1 AS community,
       t.pagerank AS importance
ORDER BY t.betweenness_centrality DESC
LIMIT 10
```

**Benefits for Multi-Agent System**:
- **Evidence Weighting**: Agents weight documents/technologies by PageRank for scoring
- **Hidden Patterns**: Reveals undervalued technologies (high PageRank in patents, low in news)
- **Strategic Positioning**: Identifies bridge technologies that connect separate innovation clusters
- **Cross-Layer Analysis**: Compare PageRank across L1-L4 to detect contradictions
- **Reproducible Scoring**: Pre-computed metrics ensure same scores across all 10 agent runs

---

### 07_validate_prerequisites.py

**Purpose**: Comprehensive validation of all graph prerequisites

**Validates**:
1. Indexes (5 total)
2. Embeddings coverage (Documents, Technologies, Companies)
3. Full-text index (BM25)
4. Vector index (cosine similarity)
5. Communities (6 versions)
6. Community summaries (6 versions with LLM-generated descriptions)
7. Graph algorithms (3 algorithms)

**Runtime**: ~1 minute
**Cost**: Free
**Safe to run**: YES (read-only, always safe)

**Output**:
- Console report with PASS/WARNING/FAIL status
- JSON report: `graph/prerequisites_configuration/validation_report.json`

**Validation Criteria**:
- **PASS**: ≥95% coverage
- **WARNING**: 80-95% coverage
- **FAIL**: <80% coverage or missing

**Example Output**:
```
[1/9] Validating Indexes...
  [OK] document_published_at
  [OK] document_type_published
  [OK] technology_id
  [OK] company_name
  [OK] document_doc_id

[2/9] Validating Embeddings...
  Documents: 2099/2099 (100.0%)
    [OK] PASS (≥95% coverage)
  Technologies: 1755/1755 (100.0%)
    [OK] PASS (≥95% coverage)
  Companies: 122/122 (100.0%)
    [OK] PASS (≥95% coverage)

[8/9] Computing Overall Status...
  PASS: 25/25
  WARNING: 0/25
  FAIL: 0/25

[9/9] Validation Summary
========================================
[SUCCESS] ALL PREREQUISITES READY
```

---

### run_all_prerequisites.py

**Purpose**: Master orchestrator to run all 8 scripts in correct order

**Features**:
- Interactive approval for expensive operations (Scripts 2, 5, 5.5, 6)
- Resume capability (checkpoint saves progress)
- Error handling with rollback
- Cost estimation before execution
- Skip completed steps automatically

**Workflow**:
1. Create Indexes (fast, free)
2. Generate Embeddings (10-15 min, $0.20-1.00) ← **REQUIRES APPROVAL**
3. Create Full-Text Index (fast, free)
4. Create Vector Index (fast, free)
5. Compute Communities (5-10 min, free) ← **REQUIRES APPROVAL**
6. Generate Community Summaries (5-10 min, $0.01-0.05) ← **REQUIRES APPROVAL**
7. Compute Graph Algorithms (5-10 min, free) ← **REQUIRES APPROVAL**
8. Validate Prerequisites (fast, free)

**Usage**:
```bash
# Interactive mode (default)
python graph/prerequisites_configuration/run_all_prerequisites.py

# Auto-approve all steps (no prompts)
python graph/prerequisites_configuration/run_all_prerequisites.py --auto-approve

# Skip final validation
python graph/prerequisites_configuration/run_all_prerequisites.py --skip-validation
```

**Resume from interruption**:
```bash
# Just re-run - automatically resumes from last completed step
python graph/prerequisites_configuration/run_all_prerequisites.py
```

**Reset all progress**:
```bash
rm graph/prerequisites_configuration/.checkpoint_orchestrator.txt
rm graph/prerequisites_configuration/.checkpoint_embeddings.json
```

## Current Graph Status

Based on validation run:

**Graph Size**:
- Total nodes: 3,976
- Documents: 2,099
- Technologies: 1,755
- Companies: 122

**Status**:
- Indexes: 3/5 created (document_published_at and document_doc_id need investigation)
- Embeddings: 0% coverage (Script 2 not run yet)
- Full-text index: Missing (Script 3 not run)
- Vector index: Missing (Script 4 not run)
- Communities: Not computed (Script 5 not run)
- Graph algorithms: Not computed (Script 6 not run)

**Next Steps**:
1. Investigate why 2 indexes show as missing
2. Run Script 2 (generate embeddings) - **REQUIRES APPROVAL** (~$0.20-1.00)
3. Run Scripts 3-6
4. Re-validate with Script 7

## Troubleshooting

### Indexes show as "MISSING" after creation

**Possible causes**:
- Case-sensitivity in index names
- Neo4j Aura version differences
- Timing delay (indexes still being built)

**Solution**:
```bash
# Check all indexes in Neo4j Browser
SHOW INDEXES

# If missing, re-run Script 1
python graph/prerequisites_configuration/01_create_indexes.py
```

### Embeddings generation fails

**Possible causes**:
- OpenAI API key invalid
- Rate limiting
- Network issues

**Solution**:
```bash
# Check API key
echo $OPENAI_API_KEY

# Resume from checkpoint
python graph/prerequisites_configuration/02_generate_embeddings.py

# If stuck, reset checkpoint
rm graph/prerequisites_configuration/.checkpoint_embeddings.json
```

### Community detection fails

**Possible causes**:
- Neo4j GDS library not installed
- Graph too large for available memory
- Empty graph (no relationships)

**Solution**:
```bash
# Check GDS library availability
CALL gds.version()

# If unavailable, contact Neo4j Aura support
```

### Validation fails with Unicode errors

**Issue**: Windows terminal encoding (CP1252) doesn't support emojis

**Solution**: Already fixed - all emojis replaced with ASCII ([OK], [WARN], [ERROR])

## Cost Breakdown

| Script | Runtime | Cost | Notes |
|--------|---------|------|-------|
| 01_create_indexes | ~2 min | Free | Idempotent, safe to re-run |
| 02_generate_embeddings | 10-15 min | $0.20-1.00 | One-time cost, checkpoint/resume |
| 03_create_fulltext_index | ~2 min | Free | Requires embeddings |
| 04_create_vector_index | ~2 min | Free | Requires embeddings |
| 05_compute_communities | 5-10 min | Free | Computation only |
| 06_compute_graph_algorithms | 5-10 min | Free | Computation only |
| 07_validate_prerequisites | ~1 min | Free | Read-only validation |
| **TOTAL** | **25-40 min** | **$0.20-1.00** | One-time setup |

**Per-run cost** (after setup): ~$0.00 (all pre-computed, agents just query graph)

## Integration with Multi-Agent System

After completing all prerequisites, the multi-agent system will:

1. **Agent 1 (Tech Discovery)**: Uses `technology_id` index
2. **Agents 2-5 (Layer Scorers)**: Use hybrid search (vector + BM25)
3. **Agent 6 (Phase Detector)**: Uses temporal indexes (`document_published_at`)
4. **Agent 7 (Contradiction Analyzer)**: Uses community filters (`community_v0` through `community_v5`)
5. **Agent 8 (Confidence Scorer)**: Uses graph algorithms (`pagerank`, `betweenness_centrality`)

**Multi-Run Variation**: Each of 10-20 runs randomly selects:
- Community version (v0-v5)
- Hybrid search weight (30-70% vector)
- Temporal windows (18-30 months innovation, 9-15 months adoption, etc.)

This produces convergent results from diverse perspectives, building scientific confidence in lifecycle positioning.

## File Structure

```
graph/prerequisites_configuration/
├── README.md                          # This file
├── __init__.py                        # Package initialization
├── 01_create_indexes.py               # Create indexes
├── 02_generate_embeddings.py          # Generate embeddings
├── 03_create_fulltext_index.py        # Create full-text index
├── 04_create_vector_index.py          # Create vector index
├── 05_compute_communities.py          # Compute communities
├── 06_compute_graph_algorithms.py     # Compute graph algorithms
├── 07_validate_prerequisites.py       # Validate all prerequisites
├── run_all_prerequisites.py           # Master orchestrator
├── .checkpoint_embeddings.json        # Embeddings checkpoint (auto-created)
├── .checkpoint_orchestrator.txt       # Orchestrator checkpoint (auto-created)
└── validation_report.json             # Validation report (auto-created)
```

## References

- **Neo4j Graph Data Science**: https://neo4j.com/docs/graph-data-science/current/
- **OpenAI Embeddings**: https://platform.openai.com/docs/guides/embeddings
- **Louvain Algorithm**: https://en.wikipedia.org/wiki/Louvain_method
- **Leiden Algorithm**: https://www.nature.com/articles/s41598-019-41695-z
- **PageRank**: https://en.wikipedia.org/wiki/PageRank
- **Hybrid Search (RRF)**: https://www.elastic.co/guide/en/elasticsearch/reference/current/rrf.html

## Support

For issues or questions:
1. Check validation report: `graph/prerequisites_configuration/validation_report.json`
2. Review Neo4j logs in Neo4j Browser
3. Check OpenAI API usage: https://platform.openai.com/usage
4. Consult main documentation: `agents/multi_agentic_approach.md` Section 2.4
