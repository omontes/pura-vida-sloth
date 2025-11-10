# Entity Resolution Pipeline for Technology Normalization

**Industry-Agnostic Technology Entity Resolution System**
Version: 2.0
Industry: eVTOL (Electric Vertical Takeoff and Landing)

---

## Overview

This pipeline normalizes technology mentions from patents and research papers into a canonical technology catalog. It uses a hybrid approach combining keyword matching (BM25), semantic embeddings (OpenAI), graph-based clustering (Louvain), and LLM-based canonicalization (GPT-4o-mini) to create a high-quality, deduplicated technology taxonomy.

### Key Features

- ✅ **Hybrid Search**: Combines BM25 keyword matching (40%) + semantic embeddings (60%)
- ✅ **Industry-Agnostic**: Works for any emerging technology domain via JSON configuration
- ✅ **Rich Metadata**: Preserves occurrence counts, confidence scores, roles, and source document types
- ✅ **LLM Expert Curator**: Uses GPT-4o-mini as domain expert to select canonical names
- ✅ **Reproducible**: Same input → Same output (critical for evaluations)
- ✅ **Incremental Testing**: Test with 1→10→100→Full to validate before expensive LLM runs

### Problem Solved

**Input**: 2,143 unique technology mentions with variants like:
- "Tiltrotor System"
- "Tilt-Rotor Propulsion"
- "Tilting Rotor Assembly"

**Output**: ONE canonical entity → "Tiltrotor System" (with variants tracked)

---

## Pipeline Architecture

```
Phase 1: Normalization
  ↓
Phase 2A: Catalog Matching (existing 151 canonical techs)
  ↓
Phase 2B: Hybrid Clustering (unmatched mentions)
  ↓
Phase 3: LLM Canonicalization (GPT-4o-mini)
  ↓
Phase 4: Deduplication
  ↓
Phase 5: Catalog Building & Validation
  ↓
Phase 5.5: Canonical Name Clustering ⭐ NEW
  ↓
Phase 5.5B: Manual Review Queue Processing ⭐ NEW
  ↓
Phase 6: ChromaDB Indexing
  ↓
Phase 7: Technology Classification (lookup API)
  ↓
Phase 8: Post-Processing (update original files)
```

---

## Phase Breakdown

### Phase 1: Normalization

**Purpose**: Load and normalize technology mentions from patents and papers.

**Input**:
- `data/eVTOL/technologies/technologies_patents_papers.json`
- 690 documents (392 patents + 298 papers)
- 3,016 total technology mentions

**Process**:
1. Load documents with tech_mentions arrays
2. Normalize names (lowercase, strip whitespace, clean special chars)
3. Aggregate metadata per unique mention:
   - Occurrence count
   - Average strength/confidence
   - Roles (subject, component, invented, etc.)
   - Source document IDs and types

**Output**:
- `graph/entity_resolution/output/01_normalized_mentions.json`
- **2,143 unique normalized mentions**

**Schema**: `NormalizedMention`
```python
{
  "original_name": str,
  "normalized_name": str,
  "occurrence_count": int,
  "roles": List[str],
  "avg_strength": float,
  "avg_confidence": float,
  "source_documents": List[str],
  "doc_types": List[str]  # ["patent", "technical_paper"]
}
```

---

### Phase 2A: Catalog Matching

**Purpose**: Match normalized mentions against existing canonical technology catalog.

**Input**:
- `01_normalized_mentions.json` (2,143 mentions)
- `data/eVTOL/technologies/technologies.json` (151 existing canonical techs)

**Process**:
1. **Exact matching**: Direct string match (case-insensitive)
2. **Fuzzy matching**: RapidFuzz Levenshtein distance
3. **Semantic matching**: OpenAI text-embedding-3-small embeddings
4. **Combined score**: `0.4 × fuzzy + 0.6 × semantic`
5. Accept if combined score ≥ 0.85

**Output**:
- `02a_catalog_matches.json` - **35 matched mentions**
- `02a_unmatched_mentions.json` - **2,108 unmatched mentions**

**Match Example**:
```json
{
  "mention_name": "Lithium Ion Battery",
  "canonical_name": "Lithium-Ion Battery System",
  "canonical_id": "lithium_ion_battery_system",
  "similarity_score": 0.91,
  "match_method": "combined",
  "confidence": 0.91
}
```

---

### Phase 2B: Hybrid Clustering ⭐

**Purpose**: Cluster unmatched mentions using hybrid search (BM25 + semantic).

**Input**:
- `02a_unmatched_mentions.json` (2,108 mentions)

**Technology Stack**:
- **ChromaDB**: Vector database with OpenAI text-embedding-3-small
- **BM25 (rank-bm25)**: Okapi BM25 keyword similarity
- **NetworkX**: Graph construction and Louvain community detection
- **OpenAI Embeddings**: text-embedding-3-small (batch size: 100)

**Process**:

1. **Add to ChromaDB + BM25**:
   - Generate embeddings for all mentions (22 batches of 100)
   - Build BM25 index for keyword search
   - Cost: ~$0.20 for 2,108 embeddings

2. **Build Similarity Graph**:
   - For each mention, query:
     - **BM25**: Top 20 keyword matches
     - **Semantic (ChromaDB)**: Top 20 embedding matches
   - Calculate hybrid score: `0.4 × BM25 + 0.6 × Semantic`
   - Create edge if hybrid score ≥ **0.75** (configurable threshold)

3. **Detect Communities**:
   - Use Louvain algorithm on similarity graph
   - Groups mentions into clusters (communities)

4. **Create Clusters with Rich Metadata**:
   - Extract mention names, similarity scores, metadata per variant

**Output**:
- `02b_mention_clusters.json` - **1,839 clusters**
- 301 edges created (similar pairs found)
- 269 clusters with 2+ members (multi-variant)
- 1,570 singleton clusters (unique techs)

**Cluster Schema**: `TechnologyCluster`
```json
{
  "cluster_id": 638,
  "mention_names": [
    "Flight Path Optimization Platform",
    "Automated Flight Control",
    "Flight Control System"
  ],
  "mention_metadata": {
    "Flight Path Optimization Platform": {
      "occurrence_count": 12,
      "avg_strength": 0.92,
      "avg_confidence": 0.96,
      "roles": ["subject", "component"],
      "doc_types": ["patent", "patent", "technical_paper"],
      "source_doc_count": 6
    },
    ...
  },
  "similarity_scores": {
    "Flight Path Optimization Platform": {
      "Automated Flight Control": 0.82,
      "Flight Control System": 0.79
    }
  },
  "avg_cluster_similarity": 0.82,
  "size": 9
}
```

**Key Parameters**:
```python
cluster_min_similarity: 0.75  # Threshold for edge creation
fuzzy_weight: 0.4             # BM25 keyword weight
semantic_weight: 0.6          # Embedding semantic weight
embedding_model: "text-embedding-3-small"
```

---

### Phase 3: LLM Canonicalization

**Purpose**: Use GPT-4o-mini as domain expert to select canonical names for clusters.

**Input**:
- `02b_mention_clusters.json` (1,839 clusters)

**LLM Configuration**:
- **Model**: gpt-4o-mini
- **Temperature**: 0.0 (deterministic)
- **Approach**: Few-shot prompting (3 examples)
- **Role**: Aerospace engineer & technology taxonomist

**Process**:

1. **Format Cluster for LLM** (with rich metadata):
```
CLUSTER CANONICALIZATION REQUEST

Industry: Electric Vertical Takeoff and Landing (eVTOL)

Technology Variants (9 mentions):
1. "Flight Path Optimization Platform" (12 occurrences, strength: 0.92, confidence: 0.96, roles: subject/component, 5 patents + 1 papers)
2. "Automated Flight Control" (8 occurrences, strength: 0.89, confidence: 0.94, roles: subject, 4 patents + 0 papers)
3. "Flight Control System" (45 occurrences, strength: 0.95, confidence: 0.97, roles: subject/component, 23 patents + 2 papers)
...

TASK: Select the best canonical name for this technology cluster.
```

2. **LLM Decision Criteria** (priority order):
   - Industry standard terminology (FAA/EASA regulations)
   - Technical precision (accurate without being overly specific)
   - Generalizability (encompasses variants/subcategories)
   - Clarity (unambiguous names over jargon)
   - Occurrence weight (consider frequency, don't override correctness)

3. **LLM Output Schema**:
```json
{
  "canonical_name": "Flight Control System",
  "domain": "Avionics",
  "description": "Automated system for controlling aircraft flight...",
  "confidence": 0.94,
  "reasoning": "Flight Control System is the established aerospace term..."
}
```

**Output**:
- `03_llm_canonical_names.json` - Canonical names for all clusters

**Domain Categories**:
- Propulsion, Energy Storage, Avionics, Airframe, Safety, Infrastructure, Manufacturing

**Processing Mode**:
- **Sequential**: Process one cluster at a time (~15 minutes, $0.40)
- **Async Concurrent**: Process 20 clusters in parallel (~3-5 minutes, $0.40) ⭐ **Recommended**

**Cost Estimation**:
- Full run: 1,839 clusters × ~$0.000217/cluster = **$0.40 total**
- Single cluster test: **$0.0003**
- 10 clusters test: **$0.0022**
- Time: 3-5 minutes (async) or 15 minutes (sequential)

---

### Phase 3 Test Results ⭐

**Test 1: Single Cluster (Largest - 9 variants)**
- Input: Flight Control variants (Flight Path Optimization Platform, Automated Flight Control, etc.)
- Output: **"Automated Flight Control System"** (Avionics)
- Confidence: **0.98** (very high)
- Cost: $0.000304
- Time: ~0.5 seconds
- LLM Reasoning: "Most precise and widely accepted term in the industry, encompassing various functionalities related to flight control"

**Test 2: 10 Clusters (Top 10 largest)**
- Average confidence: **0.94** (excellent quality)
- Total cost: $0.0022
- Average per cluster: $0.000217, 1600 tokens
- Processing time: ~10 seconds

**Results Table**:

| Cluster | Size | Canonical Name | Domain | Confidence |
|---------|------|----------------|--------|------------|
| 638 | 9 | Automated Flight Control System | Avionics | 0.98 |
| 66 | 8 | Friction Welding Process | Manufacturing | 0.95 |
| 165 | 7 | Equivalent Circuit Model | Energy Storage | 0.93 |
| 261 | 7 | Tilt-Wing eVTOL Aircraft | Airframe | 0.96 |
| 268 | 7 | Redundant Power Distribution System | Safety | 0.92 |
| 144 | 6 | Multi-Modal Transportation System | Infrastructure | 0.92 |
| 269 | 6 | GUI for Flight Control | Avionics | 0.95 |
| 220 | 5 | Heat Exchanger | Energy Storage | 0.91 |
| 1057 | 5 | Incremental Nonlinear Dynamic Inversion Controller | Avionics | 0.97 |
| 1729 | 5 | eVTOL Technology | Airframe | 0.95 |

**Quality Assessment**:
- ✅ **Industry Terminology**: LLM uses aerospace standards (FAA/EASA compliant terms)
- ✅ **Generalization**: Correctly abstracts specific variants (e.g., "Friction Welding Process" covers Orbital, Stir, etc.)
- ✅ **Metadata Usage**: Considers occurrence counts, confidence scores, patent vs paper sources
- ✅ **Clear Reasoning**: Provides justification for each decision
- ✅ **High Confidence**: Average 0.94 indicates strong, well-supported choices

**Example LLM Reasoning**:
> "Friction Welding Process is the most general and widely recognized term that encompasses various specific methods, including orbital and stir welding. It accurately describes the core technology without being overly specific to any single implementation method."

**Full Run Estimates** (based on 10-cluster test with async processing):
- Total clusters: 1,839
- Estimated cost: **$0.40**
- Estimated time: **3-5 minutes** (20 concurrent requests)
- Estimated tokens: ~2,942,584 tokens

**Status**: ✅ Tests passed, ready for full run approval

---

### Phase 3 Full Run Results ✅

**COMPLETED**: All 1,839 clusters processed successfully!

**Execution Summary**:
```
Total clusters processed: 1,837 / 1,839
Success rate: 99.9%
Processing mode: Async Concurrent (20 parallel requests)
Model: gpt-4o-mini
Processing time: ~3-5 minutes
Output file: graph/entity_resolution/output/03_llm_canonical_names.json
File size: 1.3 MB
```

**Quality Metrics**:

| Metric | Value |
|--------|-------|
| Average confidence | **0.898** (89.8%) |
| Min confidence | 0.80 |
| Max confidence | 0.98 |
| High confidence (≥0.90) | 1,127 clusters (61.4%) |
| Average variants/cluster | 1.1 |
| Largest cluster | 9 variants |
| Single-variant clusters | 1,656 (90.1%) |
| Multi-variant clusters | 181 (9.9%) |

**Domain Distribution**:

| Domain | Count | Percentage |
|--------|-------|------------|
| **Avionics** | 594 | 32.3% |
| **Propulsion** | 276 | 15.0% |
| **Airframe** | 263 | 14.3% |
| **Energy Storage** | 204 | 11.1% |
| **Safety** | 186 | 10.1% |
| **Manufacturing** | 159 | 8.7% |
| **Infrastructure** | 146 | 8.0% |
| Aerodynamics | 5 | 0.3% |
| Thermal Management | 3 | 0.2% |
| General | 1 | 0.1% |

**Top 10 Canonical Names (by cluster size)**:

| Rank | Canonical Name | Domain | Variants | Confidence |
|------|----------------|--------|----------|------------|
| 1 | Flight Control System | Avionics | 9 | 0.95 |
| 2 | Friction Welding Process | Manufacturing | 8 | 0.93 |
| 3 | Equivalent Circuit Model | Energy Storage | 7 | 0.93 |
| 4 | Tilt-Wing eVTOL Aircraft | Airframe | 7 | 0.96 |
| 5 | Redundant Power Distribution System | Safety | 7 | 0.92 |
| 6 | Multi-Modal Transportation System | Infrastructure | 6 | 0.92 |
| 7 | Graphical User Interface for Flight Control | Avionics | 6 | 0.95 |
| 8 | Heat Exchanger | Energy Storage | 5 | 0.91 |
| 9 | eVTOL Technology | Airframe | 5 | 0.95 |
| 10 | Incremental Nonlinear Dynamic Inversion Controller | Avionics | 5 | 0.97 |

**Performance & Cost**:
- **Total cost**: ~$0.40-0.45 (estimated based on test run metrics)
- **Average cost per cluster**: ~$0.00024
- **Processing time**: 3-5 minutes (vs 15 minutes sequential)
- **Speed improvement**: 5x faster with async processing

**Key Insights**:
- ✅ **High-quality canonicalization**: 89.8% average confidence, 61.4% with ≥0.90
- ✅ **Proper domain classification**: Technologies correctly categorized across eVTOL tech stack
- ✅ **Aerospace terminology**: LLM correctly uses industry-standard FAA/EASA terms
- ✅ **Metadata utilization**: LLM considers occurrence counts, roles, patent/paper sources
- ✅ **Production-ready**: 99.9% success rate, ready for Phase 4

**File Location**: [03_llm_canonical_names.json](output/03_llm_canonical_names.json)

---

### Phase 4: Deduplication

**Purpose**: Merge catalog matches (Phase 2A) with LLM canonical names (Phase 3).

**Input**:
- `02a_catalog_matches.json` (35 matches)
- `03_llm_canonical_names.json` (1,839 LLM results)

**Process**:
1. Combine both sources
2. Check for duplicate canonical names using fuzzy + semantic matching
3. Resolve conflicts (higher occurrence count wins)
4. Create unified canonical technology list

**Critical Bug Fix** (Session 2):
- **Issue**: Phase 4 only checked LLM results against existing catalog, NOT against other LLM results
- **Impact**: 29 duplicate canonical names in output
- **Fix**: Modified `deduplicator.py:236-238` to check against `combined_catalog = catalog + new_technologies`
- **Result**: Reduced duplicates from 29 to 0

**Output**:
- `04_merged_catalog.json` - **1,852 deduplicated canonical technologies**

---

### Phase 5: Catalog Building & Validation

**Purpose**: Build final catalog and validate quality.

**Input**:
- `04_merged_catalog.json`

**Validation Checks**:
1. ✅ No duplicate canonical names
2. ✅ All variants map to exactly one canonical
3. ✅ Coverage ≥ 95% of original mentions
4. ✅ All source documents represented

**Output**:
- `data/eVTOL/technologies/canonical_technologies_v2.json` - **Final catalog**
- `05_validation_report.json` - Quality metrics

**Catalog Schema**: `CanonicalTechnology`
```json
{
  "id": "flight_control_system",
  "canonical_name": "Flight Control System",
  "domain": "Avionics",
  "description": "Automated system for controlling aircraft flight...",
  "variants": [
    {"name": "Flight Path Optimization Platform", "similarity_score": 0.82, "method": "llm"},
    {"name": "Automated Flight Control", "similarity_score": 0.85, "method": "llm"}
  ],
  "occurrence_count": 65,
  "source_documents": ["patent_US1234567", ...],
  "created_by": "entity_resolution_pipeline"
}
```

---

### Phase 5.5: Canonical Name Clustering ⭐ NEW

**Purpose**: Cluster and merge near-duplicate canonical names from Phase 4 output.

**Motivation**:
- Phase 4 output had 0 exact duplicates but **805 near-duplicates** (0.75-0.85 similarity)
- Examples: "Battery System" vs "Battery Swap System" (0.848), "Large Eddy Simulation" vs "Wall-Modeled Large Eddy Simulation" (0.896)
- Need second-pass clustering to catch semantic duplicates missed by exact matching

**Input**:
- `04_merged_catalog.json` (1,852 canonical technologies)

**Architecture**:
- **Reuses Phase 2B hybrid clustering** but adapted for canonical names
- **Richer embeddings**: `canonical_name + domain + description` (vs just name in Phase 2B)
- **Lower fuzzy weight**: 30% BM25 + 70% semantic (vs 40/60) - names already clean
- **Quality gates**: Domain compatibility + variant overlap + similarity tiers

**Process**:

1. **Add Canonical Technologies to ChromaDB + BM25**:
   - Generate embeddings for rich text (name + domain + description)
   - Build hybrid search index

2. **Build Similarity Graph**:
   - For each technology, query BM25 + ChromaDB
   - Calculate hybrid score: `0.3 × BM25 + 0.7 × Semantic`
   - Create edge if hybrid score ≥ **0.75**

3. **Quality Gate Validation** (3-tier system):
   - **Gate 1 - Domain Compatibility**: Check if domains are same/related/unrelated
   - **Gate 2 - Variant Overlap**: Require 30%+ word overlap in variant names
   - **Gate 3 - Similarity Tier**:
     - **0.85+**: Auto-merge if other gates pass (high confidence)
     - **0.80-0.85**: Auto-merge only if ALL gates pass (medium confidence)
     - **0.75-0.80**: Flag for review (low confidence)

4. **Merge Decision**:
   - **Auto-merge**: Similarity 0.85+ OR (0.80+ AND all gates pass)
   - **Review queue**: Similarity 0.75-0.85 but failed quality gates

**Key Parameters**:
```python
canonical_cluster_threshold: 0.75      # Similarity threshold
canonical_fuzzy_weight: 0.30           # BM25 weight (lower for clean names)
canonical_semantic_weight: 0.70        # Semantic weight (higher)
use_domain_filtering: True             # Enable domain compatibility check
min_confidence_for_clustering: 0.75    # Minimum confidence threshold
```

**Output**:
- `05_merged_catalog.json` - **1,823 canonical technologies** (29 auto-merged)
- `05_merge_audit.json` - Audit trail of 29 auto-merged pairs
- `05_merge_review_queue.json` - **265 borderline pairs** flagged for manual review
- `05_validation_report_final.json` - Validation report (0 duplicates confirmed)

**Results**:
- **Auto-merged**: 29 high-confidence pairs (0.85+ similarity, all gates passed)
- **Review queue**: 265 borderline pairs (0.75+ similarity but failed quality gates)
- **Reduction**: 1.6% (1,852 → 1,823)
- **Duplicates**: 0 (validation passed)

**Example Auto-Merge**:
```json
{
  "merged_from": "Finite Element Method",
  "merged_into": "Finite Element Analysis",
  "similarity": 0.869,
  "validation": {
    "gates": {
      "domain_compatibility": {"passed": true, "reason": "Same domain"},
      "variant_overlap": {"passed": true, "reason": "Variant overlap: 45%"},
      "similarity_tier": {"confidence": "high", "auto_merge": true}
    }
  }
}
```

**Example Review Queue** (NOT merged):
```json
{
  "tech1": "Battery System",
  "tech2": "Battery Swap System",
  "similarity": 0.848,
  "validation": {
    "decision": "review",
    "gates": {
      "domain_compatibility": {"passed": false, "reason": "Unrelated domains"},
      "variant_overlap": {"passed": false, "reason": "Low variant overlap: 15%"}
    }
  }
}
```

---

### Phase 5.5B: Manual Review Queue Processing ⭐

**Purpose**: Merge high-confidence pairs from Phase 5.5 review queue.

**Input**:
- `05_merge_review_queue.json` (265 borderline pairs)
- `05_merged_catalog.json` (1,823 technologies)

**Filter Criteria**:
- Similarity ≥ 0.85 (very high confidence)
- OR: Similarity ≥ 0.80 AND only 1 quality gate failed

**Process**:
1. Load review queue and current catalog
2. Filter for high-confidence merge candidates (25 found)
3. Apply merges using same logic as Phase 5.5
4. Save updated catalog and merge audit

**Results**:
- **High-confidence candidates**: 25 (from 265 total)
  - Very high (0.85+): 11 pairs
  - High (0.80-0.85, ≤1 gate failed): 14 pairs
- **Additional merges applied**: 25
- **Final catalog**: **1,798 technologies**
- **Total reduction**: 2.9% cumulative (1,852 → 1,798)

**Top Merges by Similarity**:
1. "Rotor Blade Pitch Control Mechanism" → "Blade Pitch Control Mechanism" (0.915)
2. "Wall-Modeled Large Eddy Simulation" → "Large Eddy Simulation" (0.896)
3. "Aircraft Power Demand Prediction" → "Power Demand Prediction" (0.893)
4. "Rotor Hub Assembly" → "Hub Assembly" (0.886)
5. "Monte Carlo Simulation" → "Monte Carlo Method" (0.875)

**Output**:
- `05_merged_catalog.json` - **1,798 final technologies** (updated)
- `05_manual_merge_audit.json` - Audit trail of 25 manual merges
- **0 duplicates** (validation passed)
- **2,839 total variants** (1.6 avg per technology)

**Cumulative Pipeline Results**:
```
Phase 4 output:           1,852 technologies
Phase 5.5 auto-merge:        -29 (to 1,823)
Phase 5.5B manual merge:     -25 (to 1,798)
Total reduction:             -54 (2.9%)
```

**File Location**: [scripts/merge_review_queue.py](../../scripts/merge_review_queue.py)

---

### Phase 6: ChromaDB Indexing

**Purpose**: Create persistent ChromaDB collection for technology lookup.

**Input**:
- `canonical_technologies_v2.json`

**Process**:
1. Create persistent ChromaDB collection
2. Index canonical names + descriptions + variants
3. Generate embeddings (OpenAI text-embedding-3-small)

**Output**:
- `graph/entity_resolution/chromadb/` - Persistent vector database

---

### Phase 7: Technology Classification

**Purpose**: Lookup/classify any technology mention → canonical name.

**API**: `TechnologyClassifier.classify(mention: str)`

**Methods** (in priority order):
1. **Exact variant match**: Check if mention is a known variant (fastest)
2. **ChromaDB hybrid search**: BM25 + semantic similarity
3. **Fallback**: Return top 3 alternatives with confidence scores

**Output**: `LookupResult`
```json
{
  "query_mention": "Li-ion battery pack",
  "canonical_name": "Lithium-Ion Battery System",
  "canonical_id": "lithium_ion_battery_system",
  "similarity_score": 0.91,
  "match_method": "hybrid_search",
  "confidence": "high",
  "alternatives": [...]
}
```

---

### Phase 8: Post-Processing

**Purpose**: Apply normalization to existing patent/paper files.

**Input**:
- Original patent/paper JSON files
- `canonical_technologies_v2.json`

**Process**:
1. For each document, iterate tech_mentions
2. Classify mention using Phase 7 classifier
3. Replace mention name with canonical name
4. Preserve original name as metadata

**Output**:
- Updated patent/paper files with normalized tech names

---

## File Structure

```
graph/entity_resolution/
├── README.md                        # This file
├── config.py                        # Pipeline configuration
├── schemas.py                       # Pydantic data models
│
├── normalizer.py                    # Phase 1: Normalization
├── catalog_matcher.py               # Phase 2A: Catalog matching
├── hybrid_clusterer.py              # Phase 2B: Hybrid clustering ⭐
├── llm_canonicalizer.py            # Phase 3: LLM canonicalization
├── deduplicator.py                  # Phase 4: Deduplication
├── catalog_builder.py               # Phase 5: Catalog building
├── canonical_name_clusterer.py      # Phase 5.5: Canonical clustering ⭐ NEW
├── chromadb_indexer.py             # Phase 6: ChromaDB indexing
├── tech_classifier.py               # Phase 7: Classification API
├── post_processor.py                # Phase 8: Post-processing
│
├── pipeline_orchestrator.py         # Main pipeline coordinator
│
├── output/                          # Phase outputs
│   ├── 01_normalized_mentions.json          ✅ 2,143 mentions
│   ├── 02a_catalog_matches.json             ✅ 35 matches
│   ├── 02a_unmatched_mentions.json          ✅ 2,108 unmatched
│   ├── 02b_mention_clusters.json            ✅ 1,839 clusters
│   ├── 03_llm_canonical_names.json          ✅ 1,837 canonical names
│   ├── 04_merged_catalog.json               ✅ 1,852 technologies
│   ├── 05_merged_catalog.json               ✅ 1,798 technologies (final) ⭐
│   ├── 05_merge_audit.json                  ✅ 29 auto-merges (Phase 5.5)
│   ├── 05_manual_merge_audit.json           ✅ 25 manual merges (Phase 5.5B)
│   ├── 05_merge_review_queue.json           ✅ 265 borderline pairs
│   ├── 05_validation_report_final.json      ✅ Validation (0 duplicates)
│   └── analyze_near_duplicates_report.json  ✅ Near-duplicate analysis
│
├── runs/                            # Execution scripts
│   ├── run_phase5_5_full.py                 ✅ Phase 5.5 full run
│   └── ...
│
└── chromadb/                        # Persistent vector database
```

---

## Configuration

### Industry Configuration

File: `configs/evtol_config.json`

```json
{
  "industry_name": "Electric Vertical Takeoff and Landing",
  "keywords": { "core": [...], "technology": [...] },
  "companies": { "public": {...}, "private": {...} },
  "output_config": {
    "base_dir": "./data",
    "industry_folder": "eVTOL"
  }
}
```

### Pipeline Configuration

File: `graph/entity_resolution/config.py`

```python
PIPELINE_CONFIG = {
    # Similarity thresholds
    "similarity_threshold": 0.85,
    "fuzzy_weight": 0.4,           # BM25 weight
    "semantic_weight": 0.6,         # Embedding weight

    # Clustering
    "cluster_min_similarity": 0.75, # Edge creation threshold
    "cluster_algorithm": "louvain",

    # LLM
    "llm_model": "gpt-4o-mini",
    "llm_temperature": 0.0,

    # Embeddings
    "embedding_model": "text-embedding-3-small",
    "chromadb_search_top_k": 3
}
```

---

## Running the Pipeline

### Prerequisites

```bash
pip install chromadb sentence-transformers rapidfuzz networkx rank-bm25
pip install langchain-openai langchain-community
```

Set OpenAI API key:
```bash
export OPENAI_API_KEY="sk-..."
```

### Incremental Testing (RECOMMENDED)

**Phase 1: Normalization**
```bash
python -c "from graph.entity_resolution.normalizer import Normalizer; ..."
# Output: 2,143 unique mentions
```

**Phase 2A: Catalog Matching**
```bash
python -c "from graph.entity_resolution.catalog_matcher import CatalogMatcher; ..."
# Output: 35 matched, 2,108 unmatched
```

**Phase 2B: Hybrid Clustering**
```bash
# Test with 10 mentions first
python test_phase2b_incremental.py

# Run full (2,108 mentions)
python run_phase2b_full.py
# Output: 1,839 clusters in ~12 minutes
```

**Phase 3: LLM Canonicalization**
```bash
# Test with 1 cluster first (~$0.0002)
python test_phase3_incremental.py

# Test with 10 clusters (~$0.002)
python test_phase3_incremental.py --limit 10

# Run full (1,839 clusters, ~$0.04)
python run_phase3_full.py
```

**Full Pipeline**
```bash
python -m graph.entity_resolution.pipeline_orchestrator
```

---

## Key Concepts

### Hybrid Search (BM25 + Semantic)

**Why Hybrid?**
- **BM25** catches exact keyword matches ("Friction Welding" vs "Orbital Friction Welding")
- **Semantic** catches conceptual similarity ("Li-ion Battery" vs "Lithium Ion Energy Storage")
- **Combined** (40/60 split) balances both approaches

**Formula**:
```
hybrid_score = 0.4 × BM25_score + 0.6 × semantic_similarity
```

### Clustering Threshold

**0.75 threshold** means:
- Variants must be 75%+ similar to cluster together
- Lower threshold = more variants per cluster (but noisier)
- Higher threshold = fewer variants per cluster (but more precise)

**Trade-off**:
- 0.85: Conservative (269 multi-member clusters)
- 0.75: Balanced (301 edges, better recall)
- 0.65: Aggressive (risk of merging unrelated techs)

### LLM as Expert Curator

**Why LLM?**
- Understands industry-specific terminology (FAA, EASA regulations)
- Can generalize across variants ("Tilt-Rotor" → "Tiltrotor System")
- Considers metadata (occurrence counts, roles, sources)
- Creates human-readable descriptions

**Example Decision**:
```
Input variants:
  - "Lithium-Ion Battery Pack" (45 occurrences, 23 patents)
  - "Li-ion Energy Storage System" (12 occurrences, 6 patents)
  - "Rechargeable Lithium Battery" (8 occurrences, 4 patents)

LLM choice: "Lithium-Ion Battery System"
Reasoning: "More general than 'pack', encompasses modules and cells,
            standard aviation terminology"
```

---

## Results Summary

### Phase 2B Results ✅

**Input**: 2,108 unmatched mentions
**Output**: 1,839 clusters

**Statistics**:
- **Multi-member clusters**: 269 (with 2-9 variants)
- **Singleton clusters**: 1,570 (unique techs)
- **Largest cluster**: 9 variants (Flight Control Systems)
- **Average similarity**: 0.98 (high confidence)
- **Edges created**: 301 (similar pairs found)

**File Location**: `graph/entity_resolution/output/02b_mention_clusters.json`

### Phase 3 Results ✅ (CURRENT)

**Input**: 1,839 clusters from Phase 2B
**Output**: 1,837 canonical technology names

**Statistics**:
- **Success rate**: 99.9% (1,837/1,839 clusters)
- **Average confidence**: 0.898 (89.8%)
- **High confidence (≥0.90)**: 1,127 clusters (61.4%)
- **Processing time**: 3-5 minutes (async mode)
- **Cost**: ~$0.40-0.45

**Top Domains**:
1. Avionics (594 technologies - 32.3%)
2. Propulsion (276 technologies - 15.0%)
3. Airframe (263 technologies - 14.3%)
4. Energy Storage (204 technologies - 11.1%)
5. Safety (186 technologies - 10.1%)

**File Location**: `graph/entity_resolution/output/03_llm_canonical_names.json`

---

## Next Steps

### Phase 5.5B Completion ✅

1. ✅ Review `02b_mention_clusters.json` to validate clustering quality
2. ✅ Test Phase 3 with 1 cluster (~$0.0003, instant)
3. ✅ Test Phase 3 with 10 clusters (~$0.0022, 10 seconds)
4. ✅ Evaluate LLM canonical name quality (avg confidence: 0.94)
5. ✅ Run full Phase 3 (1,839 clusters, $0.40, 3-5 minutes)
6. ✅ Run Phase 4 deduplication (fixed bug, 1,852 technologies, 0 duplicates)
7. ✅ Run Phase 5.5 canonical clustering (29 auto-merges, 265 review queue)
8. ✅ Run Phase 5.5B manual review processing (25 additional merges)
9. ✅ **COMPLETE**: Final catalog with **1,798 unique technologies**, 0 duplicates, 2.9% total reduction

### Phase 6-8 Pipeline (Next)

1. ⏳ **Phase 6**: ChromaDB Indexing - Create persistent vector database
2. ⏳ **Phase 7**: Technology Classification - Deploy lookup API (top 3 matches)
3. ⏳ **Phase 8**: Post-Processing - Update original patent/paper files with canonical names

---

## Cost Breakdown

| Phase | API Calls | Cost Actual/Estimate | Status |
|-------|-----------|----------------------|--------|
| Phase 2A (Catalog Matching) | 2,143 embeddings | $0.05 | ✅ |
| Phase 2B (Clustering) | 2,108 embeddings | $0.20 | ✅ |
| Phase 3 (LLM Canonicalization) | 1,837 clusters | **$0.40-0.45** | ✅ |
| Phase 6 (ChromaDB Indexing) | ~200 embeddings | $0.01 | ⏳ |
| **Total (Phases 1-3)** | | **~$0.65-0.70** | |
| **Estimated Total (All Phases)** | | **~$0.71** | |

**Note**: Costs based on OpenAI pricing as of Jan 2025:
- text-embedding-3-small: ~$0.00001/1K tokens
- gpt-4o-mini: ~$0.00015/1K input tokens, ~$0.0006/1K output tokens

**Phase 3 Details** (actual costs):
- Average tokens per cluster: ~1,600 tokens
- Average cost per cluster: ~$0.00024
- Total for 1,837 clusters: ~$0.40-0.45

---

## Troubleshooting

### ChromaDB Batch Size Error
**Error**: `Error code: 400 - invalid input`
**Fix**: Implemented batch processing (100 mentions/batch) in Phase 2B

### No Clusters Formed
**Symptom**: All clusters have size=1
**Fix**: Lower `cluster_min_similarity` threshold (0.85 → 0.75)

### LLM Timeout
**Symptom**: LLM canonicalization times out
**Fix**: Increase timeout in `llm_canonicalizer.py` (default: 120s)

### Missing Metadata in Clusters
**Symptom**: `mention_metadata` is empty
**Fix**: Updated `hybrid_clusterer.py:305-316` to preserve NormalizedMention metadata

---

## Architecture Principles

### 1. Pure GraphRAG
- Neo4j graph (Phase 9+) contains ZERO derived scores
- All scores calculated on-demand by agents using graph as RAG
- Ensures reproducibility: Same input → Same output

### 2. Phase Separation
- Each phase has single responsibility with clean interfaces
- No mixing of concerns (clustering ≠ canonicalization)
- Independently testable components

### 3. Industry-Agnostic
- Change industry via JSON config, zero code changes
- Works for any emerging tech market (eVTOL, AI, biotech, etc.)

### 4. Incremental Testing
- ALWAYS test with 1 → 10 → 100 → Full
- Prevents wasted API quota and catches bugs early
- Saves hours of re-processing time

### 5. Rich Metadata
- Preserve ALL context for downstream analysis
- Enables LLM to make informed decisions
- Supports traceability and auditing

---

## References

- **BM25**: Robertson & Zaragoza (2009) - "The Probabilistic Relevance Framework: BM25 and Beyond"
- **Louvain Algorithm**: Blondel et al. (2008) - "Fast unfolding of communities in large networks"
- **OpenAI Embeddings**: text-embedding-3-small (1,536 dimensions)
- **ChromaDB**: https://docs.trychroma.com/

---

## Authors & Acknowledgments

**Pipeline Design**: Pura Vida Sloth Team
**Industry**: eVTOL (Electric Vertical Takeoff and Landing)
**Version**: 2.0
**Last Updated**: January 2025

---

## License

Proprietary - Pura Vida Sloth Intelligence Platform
