# Graph Layer - Phase 3 Entity Linking

**Version**: v1.0 (Exact Keyword Matching)
**Status**: First approach for sample data ingestion
**Purpose**: Load `data/samples/` into Neo4j Aura for initial testing

---

## Current Approach: Exact Keyword Matching

This is a **first-pass implementation** designed to quickly load sample data into Neo4j for testing the full Phase 3 pipeline. The entity linking strategy uses **exact keyword matching** against static catalogs.

### How It Works

1. **Load Catalogs**
   - Read `data/catalog/companies.json` (268 companies)
   - Read `data/catalog/technologies.json` (186 technologies)
   - Build lookup dictionaries: `{lowercase_name: canonical_id}`

2. **Resolve Entities**
   - For each entity mention in processed documents:
     - Normalize to lowercase
     - Check exact match against canonical name
     - Check exact match against all aliases
     - Return canonical ID if matched, `None` otherwise

3. **Track Unmatched**
   - Log all unmatched entity mentions
   - Count frequencies for catalog expansion analysis

### Advantages (v1)

✅ **Fast**: No embeddings, no vector search overhead
✅ **Simple**: Easy to debug and understand
✅ **Deterministic**: Same input → same output
✅ **Works for sample data**: Sample JSONs were generated with catalog names in mind

### Limitations (v1)

❌ **No fuzzy matching**: Typos and variations break matching
❌ **Case-sensitive issues**: Misses capitalization differences
❌ **No semantic understanding**: Cannot handle synonyms or descriptions
❌ **Catalog-dependent**: Only resolves entities already in catalogs
❌ **No confidence scores**: Binary match/no-match

### Sample Data Expectations

The sample data in `data/samples/` was **explicitly generated** to use exact catalog names. This means:

- Company mentions use exact names from `companies.json`
- Technology mentions use exact names or aliases from `technologies.json`
- ~95%+ match rate expected for sample data
- Minimal unmatched entities (edge cases only)

This is **intentional** to enable rapid Phase 3 testing without complex entity linking.

---

## Architecture

```
src/graph/
├── neo4j_client.py          # Async Neo4j driver wrapper
├── entity_resolver.py       # v1: Exact keyword matching (THIS MODULE)
├── node_writer.py           # Write Technology, Company, Document nodes
├── relationship_writer.py   # Write all 5 relationship types
└── README.md                # This file
```

### Entity Resolver API

```python
from src.graph.entity_resolver import EntityResolver

# Initialize with catalogs
resolver = EntityResolver(
    companies_catalog_path="data/catalog/companies.json",
    technologies_catalog_path="data/catalog/technologies.json"
)

# Resolve entities
company_id = resolver.resolve_company("Joby Aviation")  # -> "joby"
tech_id = resolver.resolve_technology("eVTOL")          # -> "evtol"

# Get unmatched statistics
stats = resolver.get_unmatched_stats()
resolver.log_unmatched_summary()
```

---

## Next Steps: v2 Entity Linking

The v2 implementation will address v1 limitations with advanced techniques:

### Phase 1: Fuzzy Matching (v2.0)

**Goal**: Handle typos and minor variations

- **Levenshtein distance** for string similarity
- **Token-based matching** for multi-word names
- **Confidence thresholding** (e.g., similarity > 0.85)
- **Abbreviation expansion** (e.g., "FAA" → "Federal Aviation Administration")

**Estimated Impact**: +10-15% match rate for real-world data

### Phase 2: Embedding-Based Matching (v2.1)

**Goal**: Semantic understanding of entity mentions

- **ChromaDB** for vector storage
- **OpenAI text-embedding-3-small** for embeddings
- **Cosine similarity** for semantic search
- **Multi-candidate ranking** with confidence scores

**Workflow**:
1. Embed all catalog entities (one-time setup)
2. Embed entity mention from document
3. Query ChromaDB for top-K similar entities
4. Return best match with confidence score
5. Fallback to fuzzy matching if confidence < threshold

**Estimated Impact**: +20-30% match rate, handles synonyms/descriptions

### Phase 3: Hybrid Approach (v2.2)

**Goal**: Combine exact, fuzzy, and semantic matching

**Cascade Strategy**:
1. **Exact match** (instant, 100% precision)
2. **Fuzzy match** (fast, high precision for typos)
3. **Embedding search** (slower, handles semantics)
4. **Manual review queue** (human validation for low-confidence)

**Estimated Impact**: 90%+ match rate for real-world data

### Phase 4: Dynamic Catalog Expansion (v3.0)

**Goal**: Automatically grow catalogs from unmatched entities

- **LLM-based entity classification** (is this a company/tech?)
- **Web search verification** (does this entity exist?)
- **Crowdsourced validation** (human-in-the-loop)
- **Auto-add to catalogs** with confidence flags

---

## Performance Considerations

### Current (v1)

- **Latency**: ~0.1ms per entity resolution (in-memory dict lookup)
- **Memory**: ~2MB for catalogs (268 companies + 186 technologies)
- **Throughput**: 10,000+ resolutions/second

### Future (v2.1 with ChromaDB)

- **Latency**: ~10-50ms per entity resolution (vector search)
- **Memory**: ~100MB for embeddings (depends on model)
- **Throughput**: 100-500 resolutions/second

**Optimization Strategy**: Use v1 exact matching as first pass, only invoke v2 for unmatched entities (best of both worlds).

---

## Implementation Roadmap

| Version | Feature | Estimated Effort | Impact |
|---------|---------|------------------|--------|
| **v1.0** | Exact keyword matching | ✅ **DONE** | Baseline for sample data |
| v2.0 | Fuzzy matching (Levenshtein) | 2-3 days | +10-15% match rate |
| v2.1 | Embedding-based (ChromaDB) | 4-5 days | +20-30% match rate |
| v2.2 | Hybrid cascade strategy | 2-3 days | 90%+ match rate |
| v3.0 | Dynamic catalog expansion | 5-7 days | Self-improving system |

---

## Why This Approach?

### Design Philosophy

1. **Incremental Complexity**: Start simple (v1), add sophistication only when needed
2. **Test-Driven Development**: v1 enables testing Phase 3 pipeline end-to-end
3. **Data-Informed Evolution**: Use v1 unmatched stats to guide v2 design
4. **Performance-Aware**: Keep exact matching fast path, use advanced techniques selectively

### Strategic Benefits

- **Immediate Value**: v1 works for sample data TODAY
- **Learn Fast**: Discover real-world entity linking challenges early
- **Avoid Premature Optimization**: Don't build complex embeddings until we need them
- **Incremental Investment**: Each version adds measurable value

---

## Usage Guidelines

### When to Use v1 (Current)

✅ Sample data ingestion (`data/samples/`)
✅ Controlled testing environments
✅ Catalog-aligned data sources
✅ Proof-of-concept demonstrations

### When to Use v2 (Future)

⚠️ Real-world data with typos/variations
⚠️ User-generated content (social media, forums)
⚠️ Multi-lingual entity mentions
⚠️ Novel technologies not in catalogs

---

## Monitoring and Metrics

Track these metrics to inform v2 development:

- **Match rate**: `(matched / total_mentions) * 100`
- **Top unmatched entities**: Identify catalog gaps
- **Ambiguous matches**: Multiple possible resolutions
- **Performance**: Resolution latency percentiles (p50, p95, p99)

Use `EntityResolver.get_unmatched_stats()` and `log_unmatched_summary()` to analyze results.

---

## References

- **Neo4j Best Practices**: [Graph Data Modeling](https://neo4j.com/developer/data-modeling/)
- **ChromaDB Docs**: [Embeddings Database](https://docs.trychroma.com/)
- **Entity Linking Survey**: [arxiv.org/abs/2006.01969](https://arxiv.org/abs/2006.01969)

---

**Last Updated**: 2025-01-15
**Author**: Pura Vida Sloth Team
**Contact**: For questions about v2 roadmap, see [ARCHITECTURE.md](../../docs/ARCHITECTURE.md)
