# Pura Vida Sloth - Development Guide

**Multi-Source Intelligence Platform for Strategic Technology Market Research**

This guide defines development standards, workflows, and boundaries for the Pura Vida Sloth system.

---

## Project Vision

Build a strategic intelligence platform that determines **where emerging technologies sit on their adoption lifecycle** by triangulating 14 independent data sources across 4 temporal intelligence layers (Innovation, Market Formation, Financial Reality, Narrative).

**Goal**: Generate executive-grade market research reports showing technology maturity positioning 12-24 months ahead of market consensus.

**Architecture**: 6-phase pipeline with pure GraphRAG and reproducible multi-agent scoring:
- Phase 1: Data Collection (14 sources → 400-1,600 documents)
- Phase 2: Document Processing (LLM extraction → structured JSON)
- Phase 3: Graph Ingestion (Write to Neo4j, PURE storage)
- Phases 4+5: Multi-Agent System (LangGraph, 11 agents, reproducible)
- Phase 6: UI Rendering (React + D3.js)

---

## Core Design Principles

1. **Pure GraphRAG**: Neo4j contains ZERO derived scores, only raw data + relationships. Agents calculate scores on-demand using graph as RAG.

2. **Reproducibility First**: Same graph input → Same chart output. Critical for evaluations and iterative improvements.

3. **Phase Separation**: Each phase has single responsibility with clean interfaces. No mixing of concerns.

4. **Industry-Agnostic**: Change industry via JSON config, zero code changes. Works for any emerging tech market.

5. **Multi-Source Reliability**: No single API failure breaks the system. Graceful degradation with fallbacks.

---

## Architectural Rules

- **ONLY** `src/agents/` contains multi-agent logic (LangGraph state machine for Phases 4+5)
- **Phases 2-3** are single-purpose processors (NO multi-agent complexity)
- **Neo4j graph** is pure storage layer used as GraphRAG by agents
- **All scores** calculated on-demand by agents (NOT stored in graph)
- **Each phase** outputs to next phase via file system or graph (stateless)

---

## Development Workflow

### Incremental Testing Philosophy

**CRITICAL**: ALWAYS test with minimal examples before running full pipeline.

**Test Progression**:
1. **1 record** → Validate structure, API access, field extraction
2. **10 records** → Verify logic, error handling, file saving
3. **100 records** → Check performance, rate limiting, memory
4. **Full dataset** → Only after all above tests pass

**Why This Matters**:
- Prevents wasted API quota (OpenAI costs $0.001/doc)
- Catches missing field extraction before processing 1000+ docs
- Saves 1-2 hours vs re-running full pipeline
- Avoids corrupted data from schema mismatches

### Phase Development Process

**For ANY Phase**:
1. Understand phase's single responsibility
2. Identify input/output interfaces
3. Review ARCHITECTURE.md for implementation details
4. Write minimal test case first
5. Implement with incremental testing (1→10→100→Full)
6. Validate quality gates (see Testing section)
7. Update tests and documentation

---

## Naming and File Standards

### Folder Structure

```
src/
├── downloaders/      # Phase 1: {source}_downloader.py
├── processors/       # Phase 2: document_processor.py + doc_type_handlers/
├── ingestion/        # Phase 3: graph_ingestor.py, batch_writer.py
├── agents/           # Phases 4+5: langgraph_orchestrator.py + 11 agents
├── graph/            # Neo4j: neo4j_client.py, entity_resolver.py
├── schemas/          # Pydantic: documents.py, technologies.py, companies.py
├── prompts/          # LLM prompts: document_extraction.py, agent_prompts.py
├── utils/            # Shared utilities
├── core/             # Pipeline coordinator
└── cli/              # CLI: harvest.py, process.py, ingest.py, analyze.py
```

### File Naming Conventions

- **Downloaders**: `{source}_downloader.py` (e.g., `lens_patents_downloader.py`)
- **Agents**: `{role}.py` (e.g., `scorer_innovation.py`, `phase_detector.py`)
- **Schemas**: `{entity_type}.py` (e.g., `documents.py`, `technologies.py`)
- **Tests**: `test_{module}.py` (mirrors source structure)
- **Configs**: `{industry}_config.json` (e.g., `evtol_config.json`)

### Variable Naming

- **Technologies**: Use canonical ID (e.g., `"evtol"` not `"eVTOL"`)
- **Companies**: Use ticker when available (e.g., `"JOBY"` not `"Joby Aviation"`)
- **Document IDs**: `{doc_type}_{source_id}` (e.g., `"patent_US1234567"`)
- **Phase references**: Use numbers (Phase 1, Phase 2) not descriptive names

### Code Style

- **Python**: PEP 8, use `ruff` for linting, `mypy` for type checking
- **Type hints**: Required for all functions
- **Docstrings**: Google style for public functions/classes
- **Max line length**: 100 characters
- **Imports**: Absolute imports from `src.`, grouped by standard/third-party/local

---


## Boundaries and Expectations

### What You MUST Do

1. **Test incrementally**: 1 → 10 → 100 → Full (NEVER skip)
2. **Keep graph pure**: NO scores in Neo4j (agents calculate on-demand)
3. **Ensure reproducibility**: Same input → Same output (for evals)
4. **Validate with Pydantic**: All structured data uses schemas
5. **Track costs**: Log OpenAI API usage per phase
6. **Use async I/O**: For Neo4j and OpenAI API calls

### What You MUST NOT Do

1. **❌ Store scores in Neo4j**: Breaks reproducibility, couples storage to logic
2. **❌ Add multi-agent logic outside `src/agents/`**: LangGraph ONLY in Phases 4+5
3. **❌ Hardcode entities**: Use entity catalogs + config files
4. **❌ Skip incremental testing**: Wastes API quota, breaks iterative flow
5. **❌ Mix phase responsibilities**: Processor ≠ Ingestor ≠ Agent
6. **❌ Use blocking I/O**: Kills performance at scale

### When to Ask for Clarification

**Ask the user when**:
- Ambiguous phase boundaries
- Missing requirements or thresholds
- Architecture changes affecting multiple phases
- Performance vs cost trade-offs

**Do NOT ask when**:
- Implementation details (decide using best practices)
- Variable naming (follow conventions)
- Testing approach (follow incremental philosophy)
- Code structure (follow folder conventions)

---

## The 4-Layer Intelligence Framework

This is the CORE analytical insight. When coding, always consider which intelligence layer(s) your work touches.

### Layer 1: Innovation Signals (Leading 18-24 months)
**Sources**: Patents, Research Papers, GitHub Activity
**Purpose**: Predict tech emergence before commercialization
**Insight**: Patent surges happen 18 months before products ship

### Layer 2: Market Formation (Leading 12-18 months)
**Sources**: Government Contracts, Regulatory Filings, Job Postings
**Purpose**: Predict when commercialization begins
**Insight**: Government validation precedes market entry by 12+ months

### Layer 3: Financial Reality (Coincident 0-6 months)
**Sources**: SEC Filings, Earnings, Stock Prices, Insider Trading
**Purpose**: Measure current valuation vs actual performance
**Insight**: Insider selling at price peaks signals executive exits

### Layer 4: Narrative (Lagging indicator)
**Sources**: News Sentiment, Press Releases
**Purpose**: Detect media saturation peaks (contrarian indicator)
**Insight**: News volume peaks typically coincide with valuation peaks

### Cross-Layer Contradiction Analysis

**The Magic**: When layers disagree, that reveals lifecycle position.

**Peak Phase Indicators**:
- L1-2: Innovation slowing (GitHub inactive, patent decline)
- L3: Insiders selling, valuations stretched
- L4: Media coverage maximum
→ **Signal**: Market saturation risk

**Trough Phase Indicators**:
- L1-2: Innovation recovering (patents increasing, gov contracts)
- L3: Insiders buying, valuations compressed
- L4: Media coverage minimal
→ **Signal**: Strategic opportunity phase

---

## Technology Stack

### Core Technologies

**Backend (Python 3.13)**:
- Neo4j Aura (graph database, vector-enabled)
- LangGraph (multi-agent state machine)
- OpenAI GPT-4o-mini (LLM, cost-optimized)
- LandingAI Agent Data Engine (SEC filings)
- Pydantic v2 (schema validation)
- FastAPI (REST + WebSocket)

**Frontend (React + TypeScript)**:
- React 18 (UI framework)
- D3.js v7 (visualization)
- React Query (state management)
- Vite (build tool)

**Development Tools**:
- pytest (testing framework)
- ruff (linting)
- mypy (type checking)
- Git + GitHub (version control)

---

## Key Insights

### Why This Architecture?

1. **Pure GraphRAG = Reproducibility**: Same input → Same output (critical for evals)
2. **Phase Separation = Testability**: Each phase independently testable
3. **Multi-Agent = Transparency**: Agents expose reasoning, easy to debug
4. **Industry-Agnostic = Scalability**: Works for any emerging tech market

### Common Pitfalls to Avoid

1. **Storing scores in graph**: Breaks reproducibility, couples storage to logic
2. **Skipping incremental tests**: Wastes API quota, breaks iterative development
3. **Mixing phase logic**: Makes debugging impossible, violates single responsibility
4. **Hardcoding entities**: Breaks industry-agnostic design
5. **Blocking I/O**: Kills performance at scale

---

**Remember**: This system helps organizations avoid capital deployment mistakes by identifying technology lifecycle position 12-24 months ahead. Multi-source triangulation reveals truth that single-source analysis misses.
