# Phase 2: Document Processing

**Purpose**: Transform raw harvested documents into structured knowledge graphs using dual-track processing: Landing AI's Advanced Document Extraction (ADE) for high-fidelity PDF parsing and specialized LLM parsers for knowledge graph triplet extraction.

**Architecture**: 2 processing tracks covering all 14 data sources across 4 intelligence layers.

**Output**: High-quality structured data (Markdown, JSON) + Neo4j-ready triplets (Subject → Predicate → Object) with evidence and confidence scores.

---

## Table of Contents

1. [Executive Overview](#executive-overview)
2. [Dual-Track Architecture](#dual-track-architecture)
3. [Track 1: ADE Parser (Landing AI)](#track-1-ade-parser-landing-ai)
4. [Track 2: Specialized LLM Parsers](#track-2-specialized-llm-parsers)
5. [Parser Comparison Matrix](#parser-comparison-matrix)
6. [Data Flow Architecture](#data-flow-architecture)
7. [Common Parsing Pattern](#common-parsing-pattern)
8. [Individual Parser Documentation](#individual-parser-documentation)
9. [Industry-Agnostic Configuration](#industry-agnostic-configuration)
10. [Testing Workflow](#testing-workflow)
11. [Performance & Cost Analysis](#performance--cost-analysis)
12. [Troubleshooting Guide](#troubleshooting-guide)
13. [Key Achievements](#key-achievements)

---

## Executive Overview

### What Phase 2 Does

Phase 2 transforms **400-1,600 raw documents** from Phase 1 (Data Collection) into **structured knowledge graphs** ready for Neo4j ingestion (Phase 3). This is achieved through a **dual-track processing architecture**:

**Track 1: Landing AI ADE Parser**
- **Purpose**: Extract high-fidelity structured content from PDF documents
- **Technology**: Landing AI's Advanced Document Extraction API (dpt-2-latest model)
- **Volume**: 45+ PDFs processed (regulatory filings, patent documents)
- **Quality**: Preserves tables, formatting, structure, and document hierarchy

**Track 2: Specialized LLM Parsers Using Langchain + Few Shot Examples**
- **Purpose**: Extract entity mentions and relationships for knowledge graph construction
- **Technology**: OpenAI GPT-4o-mini with few-shot prompting (temperature: 0.0)
- **Coverage**: 7 specialized parsers for each intelligence layer
- **Output**: Neo4j-ready triplets (company-tech, tech-tech, company-company relations)
- **Design**: Config-driven, industry-agnostic, with batch processing and checkpoints

### Why This Architecture?

1. **Quality First**: ADE parser delivers exceptional extraction quality (tables, formatting preserved)
2. **Scalability**: Dual-track design allows parallel processing of different document types
3. **Fault Tolerance**: Checkpoint systems across all parsers prevent data loss
4. **Reproducibility**: Temperature 0.0 ensures deterministic LLM outputs
5. **Industry-Agnostic**: Single JSON config change works for any emerging technology market

---

## Dual-Track Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   PHASE 2: DUAL-TRACK KNOWLEDGE EXTRACTION                  │
└─────────────────────────────────────────────────────────────────────────────┘

INPUT (Phase 1)                                               OUTPUT (Phase 3)
┌──────────────────┐                                         ┌─────────────────┐
│ Raw Documents    │                                         │ Structured JSON │
│ • PDFs           │ ─────────────────────────────────▶     │  • Markdown     │
│ • JSON (APIs)    │                                         │ • Neo4j Triplets│
│ • HTML/TXT       │                                         │ • Metadata      │
└──────────────────┘                                         └─────────────────┘
         │
         ├─────────────────────────────────────────────────────────┐
         │                                                           │
         ▼                                                           ▼
┌───────────────────────────────────────┐    ┌─────────────────────────────────┐
│ TRACK 1: ADE PARSER (Landing AI)      │    │ TRACK 2: LLM PARSERS (OpenAI)   │
│ ════════════════════════════════════  │    │ ═══════════════════════════════ │
│                                       │    │                                 │
│ High-Fidelity PDF Extraction          │    │ Knowledge Graph Triplets        │
│ ──────────────────────────────────    │    │ ──────────────────────────────  │
│ Model: dpt-2-latest (Landing AI)      │    │ Model: GPT-4o-mini (temp=0.0)   │
│ Processed: 45+ PDFs                   │    │ Coverage: 7 specialized parsers │
│                                       │    │ Design: Config-driven           │
│                                       │    │                                 │
│ Features:                             │    │ Intelligence Layers:            │
│ • Async concurrent (5 PDFs at once)   │    │ ┌────────────────────────────┐  │
│ • Checkpoint system (resume capable)  │    │ │ L1: Innovation Signals     │  │
│ • PDF validation (magic bytes check)  │    │ │  • Patents                 │  │
│ • Table preservation                  │    │ │  • Scholarly Papers        │  │
│ • Formatting maintained               │    │ │  • GitHub Activity         │  │
│                                       │    │ └────────────────────────────┘  │
│ Data Sources:                         │    │ ┌────────────────────────────┐  │
│ • Regulatory docs: 39 PDFs            │    │ │ L2: Market Formation       │  │
│   (FAA, EPA, DoD, NASA, FCC)          │    │ │  • Gov Contracts           │  │
│ • Patent PDFs: 6 documents            │    │ │  • Regulatory (uses ADE)   │  │
│                                       │    │ └────────────────────────────┘  │
│ Output:                               │    │ ┌────────────────────────────┐  │
│ • Markdown (clean, structured)        │    │ │ L3: Financial Reality      │  │
│ • JSON (full metadata)                │    │ │  • SEC Filings (uses ADE)  │  │
│                                       │    │ └────────────────────────────┘  │
│ Code: src/parsers/ade_parser.py       │    │ ┌────────────────────────────┐  │
│                                       │    │ │ L4: Narrative              │  │
│ Limit by credits:                     │    │ │  • News Articles           │  │
│   Pending PDFs:                       │    │ └────────────────────────────┘  │
│  • Scientific Papers: +200            │    │                                 │
│  • Patent PDFs: +250                  │    │ Features:                       │
│              |                        │    │ • Entity extraction (companies, │
│              |                        │    │   technologies, concepts)       │
│              ▼                        │    │ • Relationship mapping          │
│          LLM Parser                   │    │ • Evidence + confidence scores  │
│                                       │    │ • Batch processing (4 workers)  │
│                                       │    │ • Checkpoint system             │
│                                       │    │ • Industry Relevance            │
└───────────────────────────────────────┘    └─────────────────────────────────┘
         │                                                   │
         └───────────────────┬───────────────────────────────┘
                             │
                             ▼
         ┌────────────────────────────────────────────┐
         │     PHASE 3: NEO4J GRAPH INGESTION         │
         │  (Entities → Nodes, Relations → Edges)     │
         └────────────────────────────────────────────┘
```

### Processing Pipeline Flow

1. **Phase 1 Harvesting** → Raw documents collected from 14 sources
2. **Phase 2 Extraction** → Dual-track processing:
   - **Track 1 (ADE)**: PDFs → Structured Markdown + JSON → LLM Parser
   - **Track 2 (LLM)**: All formats → Neo4j triplets
3. **Phase 3 Ingestion** → Structured data → Neo4j graph database
4. **Phases 4-5 Analysis** → Multi-agent system queries graph for insights
5. **Phase 6 Visualization** → React + D3.js renders executive reports

---

## Track 1: ADE Parser (Landing AI)

### Overview

The **Landing AI Advanced Document Extraction (ADE) Parser** provides high-fidelity PDF parsing using state-of-the-art document understanding models. This is critical for complex documents like regulatory filings and patent PDFs where preserving structure, tables, and formatting is essential.

### Architecture

**Code Reference**: [src/parsers/ade_parser.py:33-131](../parsers/ade_parser.py#L33-L131)

**Key Components**:
1. **PDF Validator** (lines 161-216): Magic byte verification, page count limits
2. **Async Parser** (lines 287-361): Concurrent processing with semaphore control
3. **Checkpoint Manager** (lines 98-102): Resume capability after interruptions
4. **Results Saver** (lines 363-403): Dual output (Markdown + JSON)

**Technology Stack**:
- **Model**: `dpt-2-latest` (Landing AI's flagship document parsing model)
- **API**: Landing AI Advanced Document Extraction API
- **Concurrency**: Async processing with configurable semaphore (default: 5 concurrent PDFs)
- **Fault Tolerance**: Checkpoint system for resume capability
- **Validation**: PDF magic bytes, file size, page count checks

### Processing Statistics

**Data Sources Processed**:

| Source | Total PDFs | Successful | Failed | Success Rate | Output Location |
|--------|-----------|------------|--------|--------------|-----------------|
| **Regulatory Docs** | 46 | 39 | 7 | **84.78%** | [data/eVTOL/regulatory_docs/ade_parsed_results/](../../data/eVTOL/regulatory_docs/ade_parsed_results/) |
| **Patent PDFs** | 6 | 6 | 0 | **100%** | [data/eVTOL/lens_patents/ade_parsed_results/](../../data/eVTOL/lens_patents/ade_parsed_results/) |
| **Total** | **52** | **45** | **7** | **86.54%** | - |

**Regulatory Documents Breakdown** (from Federal Register):
- Federal Aviation Administration (FAA): 24 documents
- Environmental Protection Agency (EPA): 10 documents
- Defense Department (DoD): 5 documents
- NASA: 2 documents
- Federal Communications Commission (FCC): 2 documents
- Other agencies: 3 documents

### Output Quality

**Example Output**: [federal-aviation-administration_2024-25812.md](../../data/eVTOL/regulatory_docs/ade_parsed_results/markdown/federal-aviation-administration_2024-25812.md)

**Quality Features**:
- ✅ **Tables Preserved**: Complex tables maintained with cell IDs and structure
- ✅ **Formatting Retained**: Headers, bold, italics, bullet points
- ✅ **Document Hierarchy**: Sections, subsections, and paragraph structure
- ✅ **Metadata Extraction**: Document type, agency, docket numbers
- ✅ **Clean Markdown**: Human-readable and machine-parseable

**Example Table Extraction**:
```markdown
| Modality | Respondents | Frequency | Total Responses | Burden (min) | Total Burden (hrs) |
|----------|-------------|-----------|-----------------|--------------|-------------------|
| Workshop Wage Reporting | 244 | 12 | 2,928 | 15 | 732 |
```

### Usage

**CLI Command**:
```bash
# Basic usage (processes all PDFs in directory)
python -m src.parsers.ade_parser --pdf_dir data/eVTOL/regulatory_docs/pdfs

# Custom concurrency (10 PDFs at once)
python -m src.parsers.ade_parser \
    --pdf_dir data/eVTOL/regulatory_docs/pdfs \
    --max_concurrent 10

# Page limit (skip large PDFs)
python -m src.parsers.ade_parser \
    --pdf_dir data/eVTOL/lens_patents/pdfs \
    --max_pages 50

# Custom model
python -m src.parsers.ade_parser \
    --pdf_dir data/quantum/regulatory_docs/pdfs \
    --model dpt-2-latest
```

**Programmatic Usage**:
```python
from src.parsers.ade_parser import ADEParser
import asyncio

# Initialize parser
parser = ADEParser(
    pdf_dir="data/eVTOL/regulatory_docs/pdfs",
    max_concurrent=5,
    max_pages=100
)

# Process all PDFs (async)
stats = asyncio.run(parser.process_directory_async())

# Generate report
report_path = parser.generate_report()
print(f"Report: {report_path}")
```

### Output Structure

**Directory Layout**:
```
data/eVTOL/regulatory_docs/
├── pdfs/                                    # Input PDFs
│   ├── federal-aviation-administration_2024-25812.pdf
│   └── ...
└── ade_parsed_results/                      # ADE outputs
    ├── markdown/                            # Clean, structured markdown
    │   ├── federal-aviation-administration_2024-25812.md
    │   └── ...
    ├── json/                                # Full API response (metadata)
    │   ├── federal-aviation-administration_2024-25812.json
    │   └── ...
    ├── checkpoints/                         # Resume capability
    │   └── ade_parser_checkpoint.json
    ├── parse_report.json                    # Summary statistics
    └── ade_parser.log                       # Processing logs
```

**JSON Metadata Example**:
```json
{
  "markdown": "...",
  "metadata": {
    "page_count": 15,
    "duration_ms": 12500,
    "credit": 0.15,
    "model": "dpt-2-latest"
  }
}
```

### Checkpoint System

**Resume After Interruption**:
```bash
# First run (processes 20 PDFs, then crashes)
python -m src.parsers.ade_parser --pdf_dir data/eVTOL/regulatory_docs/pdfs

# Resume (skips already processed PDFs)
python -m src.parsers.ade_parser --pdf_dir data/eVTOL/regulatory_docs/pdfs
```

**Checkpoint Format**:
```json
{
  "completed": [
    {
      "file": "federal-aviation-administration_2024-25812.pdf",
      "timestamp": "2025-11-06T10:30:00Z",
      "metadata": {
        "page_count": 15,
        "duration_ms": 12500
      }
    }
  ],
  "failed": [
    {
      "file": "environmental-protection-agency_2025-11326.pdf",
      "reason": "API parsing failed"
    }
  ]
}
```

### Integration with Specialized Parsers

**ADE as Preprocessor**:

Several specialized parsers use ADE-extracted markdown as input:

1. **Regulatory Parser** ([src/parsers/regulatory/regulatory_parser.py](../parsers/regulatory/regulatory_parser.py))
   - **Input**: ADE markdown files
   - **Process**: Extract entities and relationships from structured text
   - **Output**: Neo4j triplets

2. **SEC Filings Parser** ([src/parsers/sec/sec_parser.py](../parsers/sec/sec_parser.py))
   - **Input**: ADE markdown files (10-K, 10-Q, 8-K, S-1)
   - **Process**: Section-specific extraction (MD&A, Risk Factors, etc.)
   - **Output**: Neo4j triplets with SEC-specific metadata

**Data Flow**:
```
PDF Document
    ↓
ADE Parser (Track 1)
    ↓
Markdown + JSON
    ↓
Specialized LLM Parser (Track 2)
    ↓
Neo4j Triplets
```

### Key Features

1. **Async Concurrent Processing**: Process 5-10 PDFs simultaneously for faster throughput
2. **Automatic Retries**: Failed requests can be retried automatically
3. **Validation Layer**: Pre-flight checks prevent wasted API calls on invalid files
4. **Cost Tracking**: Monitor Landing AI credits consumed per document
5. **Detailed Logging**: Comprehensive logs for debugging and auditing

### When to Use ADE Parser

**Best For**:
- ✅ Complex PDFs with tables and formatting
- ✅ Government regulatory filings (Federal Register, SEC)
- ✅ Patent documents with claims and diagrams
- ✅ Scientific papers with equations and figures
- ✅ Any PDF where structure preservation is critical

**Not Needed For**:
- ❌ Simple JSON API responses (use specialized parsers directly)
- ❌ Plain text files
- ❌ HTML pages (use web scraping tools)
- ❌ Data already in structured format

---

## Track 2: Specialized LLM Parsers

### Overview

**7 specialized LLM parsers** extract knowledge graph triplets from domain-specific data sources. Each parser is optimized for its intelligence layer and data format.

### Common Architecture

Every specialized parser follows this pattern:

**1. Parser Class** - LangChain + OpenAI GPT-4o-mini
- **Model**: `gpt-4o-mini` (cost-optimized, high accuracy)
- **Temperature**: `0.0` (deterministic, reproducible outputs)
- **Prompting**: Few-shot examples with industry context
- **Config**: Closed relation sets from JSON config

**2. Entity Extraction**
- **Technology Mentions**: name, role, strength, evidence, confidence
- **Company Mentions**: name, role, strength, evidence, confidence
- **Concept Mentions**: abstract approaches and methodologies

**3. Relationship Mapping**
- **Company-Tech Relations**: `develops`, `uses`, `invests_in`, `researches`, `owns_ip`
- **Tech-Tech Relations**: `enables`, `competes_with`, `supersedes`, `complements`, `requires`, etc.
- **Company-Company Relations**: `partners_with`, `acquires`, `competes_with`, `supplies`, etc.

**4. Batch Processor**
- **Concurrency**: ThreadPoolExecutor with 4 workers
- **Progress**: tqdm progress bars with real-time stats
- **Error Handling**: Graceful degradation on API failures

**5. Checkpoint Manager**
- **Auto-save**: Every N items (configurable, default: 100)
- **Resume**: Skip already-processed items after crash
- **Incremental**: Validate outputs during long runs

**6. Test Scripts**
- **Single-item test**: Validate setup, API access, schema
- **Small batch**: Verify logic, error handling, checkpoints
- **Cost estimation**: Preview API costs before full runs

### Parser Implementations

---

## Parser Comparison Matrix

| Parser | Intelligence Layer | Input Format | Processing Model | Output Format | Success Rate | Volume Processed | Code Reference |
|--------|-------------------|--------------|------------------|---------------|--------------|------------------|----------------|
| **ADE (Landing AI)** | **All Layers** | **PDF** | **dpt-2-latest** | **Markdown + JSON** | **86.54%** | **45 PDFs** | [ade_parser.py](../parsers/ade_parser.py) |
| **Patents** | L1: Innovation Signals | Lens.org JSON | GPT-4o-mini (temp=0.0) | Neo4j triplets | ~95% | 100+ patents | [patents/patents_parser.py](../parsers/patents/patents_parser.py) |
| **Scholarly Papers** | L1: Innovation Signals | Lens.org JSON | GPT-4o-mini (temp=0.0) | Neo4j triplets + relevance | ~90% | 5,322 papers | [scholarly/scholarly_parser.py](../parsers/scholarly/scholarly_parser.py) |
| **GitHub Activity** | L1: Innovation Signals | GitHub API JSON | GPT-4o-mini (temp=0.0) | Neo4j triplets | ~92% | 50+ repos | [github_activity/github_activity_parser.py](../parsers/github_activity/github_activity_parser.py) |
| **Gov Contracts** | L2: Market Formation | USASpending JSON | GPT-4o-mini (temp=0.0) | Neo4j triplets | ~93% | 200+ contracts | [gov_contracts/gov_contracts_parser.py](../parsers/gov_contracts/gov_contracts_parser.py) |
| **Regulatory** | L2: Market Formation | ADE Markdown | GPT-4o-mini (temp=0.0) | Neo4j triplets | ~88% | 39 docs | [regulatory/regulatory_parser.py](../parsers/regulatory/regulatory_parser.py) |
| **SEC Filings** | L3: Financial Reality | ADE Markdown | GPT-4o-mini (temp=0.0) | Neo4j triplets | ~90% | 10+ filings | [sec/sec_parser.py](../parsers/sec/sec_parser.py) |
| **News Articles** | L4: Narrative | Tavily + NewsAPI | GPT-4o-mini (temp=0.0) | Neo4j triplets + sentiment | ~91% | 500+ articles | [news/news_parser.py](../parsers/news/news_parser.py) |

### Feature Comparison

| Feature | ADE Parser | LLM Parsers |
|---------|-----------|-------------|
| **Primary Purpose** | High-fidelity document extraction | Knowledge graph triplet extraction |
| **Technology** | Landing AI dpt-2-latest | OpenAI GPT-4o-mini |
| **Input Formats** | PDF only | JSON, Markdown, HTML |
| **Output** | Markdown + JSON (structure preserved) | Neo4j triplets (entities + relations) |
| **Concurrency** | Async (5 concurrent) | ThreadPool (4 workers) |
| **Checkpoint System** | ✅ Yes | ✅ Yes |
| **Resume Capability** | ✅ Yes | ✅ Yes |
| **Industry-Agnostic** | ✅ Yes (format-independent) | ✅ Yes (config-driven) |
| **Cost per Item** | Variable (Landing AI credits) | $0.001-0.005 (OpenAI) |
| **Batch Processing** | ✅ Yes | ✅ Yes |
| **Quality Focus** | Structure, tables, formatting | Entity relations, evidence, confidence |

---

## Data Flow Architecture

### End-to-End Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 1: INPUT VALIDATION                                                │
│ ────────────────────────────────────────────────────────────────────────│
│                                                                         │
│  Raw Document ──▶ Format Check ──▶ Schema Validation ──▶ Preprocessed │
│                                                                         │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌───────────────────────────────┐   ┌──────────────────────────────────┐
│ STEP 2A: ADE EXTRACTION       │   │ STEP 2B: LLM EXTRACTION          │
│ (Track 1: PDF Processing)     │   │ (Track 2: Knowledge Graph)       │
│ ───────────────────────────── │   │ ──────────────────────────────── │
│                               │   │                                  │
│  PDF Document                 │   │  JSON/Markdown Document          │
│       ↓                       │   │       ↓                          │
│  Landing AI API               │   │  Config Relations                │
│  (dpt-2-latest)               │   │  (eVTOL_graph_relations.json)    │
│       ↓                       │   │       ↓                          │
│  Markdown + JSON              │   │  GPT-4o-mini (temp=0.0)          │
│  • Tables preserved           │   │  • Few-shot prompting            │
│  • Formatting maintained      │   │  • Domain-specific examples      │
│  • Structure retained         │   │       ↓                          │
│                               │   │  Structured JSON                 │
│                               │   │  {                               │
│                               │   │    tech_mentions: [...],         │
│                               │   │    company_mentions: [...],      │
│                               │   │    relations: [...]              │
│                               │   │  }                               │
└────────────────┬──────────────┘   └───────────────┬──────────────────┘
                 │                                   │
                 └───────────────┬───────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 3: POST-PROCESSING LLM PARSER WITH FEW SHOT                        │
│ ─────────────────────────────────────────────────────────────────────── │
│                                                                         │
│  • Add doc_ref to all relations (document provenance)                   │
│  • Generate quality_score (LLM confidence assessment)                   │
│  • Filter placeholder entities (e.g., "Unknown Company")                │
│  • Normalize entity names (e.g., "Joby Aero" → "Joby Aero Inc")         │
│  • Validate relation types against config enums                         │
│  • Calculate confidence scores based on evidence                        │
│                                                                         │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 4: NEO4J-READY OUTPUT                                              │
│ ─────────────────────────────────────────────────────────────────────── │
│                                                                         │
│  {                                                                      │
│    "document": {                                                        │
│      "doc_id": "003-712-519-476-908",                                   │
│      "doc_type": "patent",                                              │
│      "title": "ROTOR ASSEMBLY DEPLOYMENT MECHANISM",                    │
│      "quality_score": 0.95,                                             │
│      ...                                                                │
│    },                                                                   │
│    "tech_mentions": [                                                   │
│      {                                                                  │
│        "name": "Rotor Assembly Deployment Mechanism",                   │
│        "role": "subject",                                               │
│        "strength": 0.95,                                                │
│        "evidence_confidence": 0.98,                                     │
│        "evidence_text": "Primary invention..."                          │
│      }                                                                  │
│    ],                                                                   │
│    "company_tech_relations": [                                          │
│      {                                                                  │
│        "company_name": "Joby Aero Inc",                                 │
│        "technology_name": "Rotor Assembly Deployment Mechanism",        │
│        "relation_type": "owns_ip",                                      │
│        "evidence_confidence": 1.0,                                      │
│        "doc_ref": "003-712-519-476-908"                                 │
│      }                                                                  │
│    ],                                                                   │
│    "tech_tech_relations": [                                             │
│      {                                                                  │
│        "from_tech_name": "Rotor Assembly Deployment Mechanism",         │
│        "to_tech_name": "Torsion Box Construction",                      │
│        "relation_type": "supports",                                     │
│        "evidence_confidence": 0.95,                                     │
│        "doc_ref": "003-712-519-476-908"                                 │
│      }                                                                  │
│    ]                                                                    │
│  }                                                                      │
│                                                                         │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    ▼
                        ┌──────────────────────────┐
                        │  PHASE 3: NEO4J INGESTION│
                        │  (Graph Database)        │
                        └──────────────────────────┘
```

### ADE Integration Flow

For parsers that leverage ADE-extracted content:

```
PDF Document (Regulatory/SEC Filing)
         │
         ▼
┌─────────────────────────┐
│  ADE Parser (Track 1)   │  ◄── Landing AI API
│  • PDF validation       │
│  • Async processing     │
│  • Structure extraction │
└────────┬────────────────┘
         │
         ▼
  Markdown + JSON Output
  (High-Fidelity, Tables Preserved)
         │
         ├──► Regulatory LLM Parser ───────┐
         │    (Extract entities from FAA,  │
         │     EPA, DoD docs)              │
         │                                 │
         └──► SEC LLM Parser ──────────────┤
              (Extract 10-K sections,      │
               MD&A, risk factors)         │
                                           │
                                           ▼
                         ┌────────────────────────────┐
                         │  Knowledge Graph Triplets  │
                         │  (Neo4j-Ready)             │
                         └────────────────────────────┘
```

---

## Common Parsing Pattern

All 8 parsers (1 ADE + 7 specialized LLM) follow a consistent architecture pattern.

### Standard Components

#### 1. Parser Class

**ADE Parser Example** ([ade_parser.py:33-131](../parsers/ade_parser.py#L33-L131)):
```python
class ADEParser:
    def __init__(self, pdf_dir, api_key, model="dpt-2-latest", max_concurrent=5):
        self.pdf_dir = Path(pdf_dir)
        self.model = model
        self.api_key = api_key
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.checkpoint = CheckpointManager(...)
```

**LLM Parser Example** ([patents/patents_parser.py:28-54](../parsers/patents/patents_parser.py#L28-L54)):
```python
class PatentTechnologyParser:
    def __init__(self, openai_api_key, config_path, model_name="gpt-4o-mini", temperature=0.0):
        # Load allowed relations from config
        with open(config_path, 'r') as f:
            self.graph_config = json.load(f)

        # Initialize LLM
        self.llm = ChatOpenAI(temperature=temperature, model=model_name, api_key=openai_api_key)
        self.chain = self._create_chain()  # Few-shot prompting
```

#### 2. Processing Method

**ADE**: `async def parse_pdf_async(pdf_path, session) → Dict`
- Async processing with semaphore control
- Returns: `{"markdown": "...", "metadata": {...}}`

**LLM**: `def parse_{type}(data: Dict) → Dict`
- Synchronous processing (batch parallelized at higher level)
- Returns: `{"document": {...}, "tech_mentions": [...], "relations": [...]}`

#### 3. Batch Processor

**ADE** ([ade_parser.py:564-598](../parsers/ade_parser.py#L564-L598)):
```python
async def process_directory_async(self) -> Dict:
    tasks = [self.process_single_pdf_async(pdf, session, pbar) for pdf in pdf_files]
    await asyncio.gather(*tasks)
```

**LLM** (e.g., [patents/batch_process_patents.py](../parsers/patents/batch_process_patents.py)):
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(parser.parse_patent, patent_batch))
```

#### 4. Checkpoint Manager

**Shared Component** ([src/utils/checkpoint_manager.py](../../src/utils/checkpoint_manager.py)):
```python
class CheckpointManager:
    def mark_completed(self, item_id, metadata=None):
        """Mark item as successfully processed"""

    def is_completed(self, item_id) -> bool:
        """Check if item was already processed"""

    def mark_failed(self, item_id, reason):
        """Mark item as failed with reason"""
```

#### 5. Test Scripts

**Pattern**: Every parser has `test_single_{type}.py`

**ADE Test**:
```bash
python -m src.parsers.ade_parser --pdf_dir data/test_pdfs --max_concurrent 1
```

**LLM Test** (e.g., [patents/test_single_patent.py](../parsers/patents/test_single_patent.py)):
```bash
python src/parsers/patents/test_single_patent.py
# Output: test_patent_output.json
```

### Incremental Testing Workflow

**CRITICAL**: Always test incrementally before full production runs.

```bash
# ═══════════════════════════════════════════════════════════════
# STEP 1: Single Item Test (Validate Setup)
# ═══════════════════════════════════════════════════════════════
# ✅ Validates: API access, field extraction, output schema

# ADE Parser
python -m src.parsers.ade_parser --pdf_dir data/test_pdfs --max_concurrent 1

# LLM Parser (Patents)
python src/parsers/patents/test_single_patent.py

# LLM Parser (Scholarly)
python src/parsers/scholarly/test_single_paper.py


# ═══════════════════════════════════════════════════════════════
# STEP 2: Small Batch (10 items, Verify Logic)
# ═══════════════════════════════════════════════════════════════
# ✅ Validates: Error handling, checkpoint system, file saving

# ADE Parser (10 PDFs)
python -m src.parsers.ade_parser \
    --pdf_dir data/eVTOL/regulatory_docs/pdfs \
    --max_concurrent 2

# LLM Parser (10 patents)
python src/parsers/patents/batch_process_patents.py --limit 10 --checkpoint 5

# LLM Parser (10 papers)
python src/parsers/scholarly/batch_process_papers.py --limit 10 --checkpoint 5


# ═══════════════════════════════════════════════════════════════
# STEP 3: Resume Test (Verify Fault Tolerance)
# ═══════════════════════════════════════════════════════════════
# ✅ Should skip already processed items

# ADE Parser (resume)
python -m src.parsers.ade_parser --pdf_dir data/eVTOL/regulatory_docs/pdfs

# LLM Parser (resume)
python src/parsers/patents/batch_process_patents.py --limit 10 --checkpoint 5


# ═══════════════════════════════════════════════════════════════
# STEP 4: Full Dataset (Only After Above Tests Pass)
# ═══════════════════════════════════════════════════════════════

# ADE Parser (all PDFs)
python -m src.parsers.ade_parser \
    --pdf_dir data/eVTOL/regulatory_docs/pdfs \
    --max_concurrent 5

# LLM Parser (all patents)
python src/parsers/patents/batch_process_patents.py --checkpoint 100

# LLM Parser (all papers)
python src/parsers/scholarly/batch_process_papers.py --checkpoint 100
```

### Why Incremental Testing Saves Time

| Step | Purpose | Time Investment | Potential Savings |
|------|---------|-----------------|-------------------|
| **1 item** | Validate setup, API keys, schema | 30 seconds | Avoid wasting quota on broken setup |
| **10 items** | Verify logic, error handling | 2-5 minutes | Catch schema mismatches before 1000+ items |
| **Resume test** | Validate checkpoints work | 1 minute | Prevent data loss from crashes |
| **Full run** | Production processing | Hours | Confident in success, no re-runs |

**Cost Savings**:
- **Without testing**: Waste $5-10 on failed runs, 2-3 hours re-processing
- **With testing**: $0.10 in test costs, catch issues in 5 minutes

---

## Individual Parser Documentation

### 1. Patents Parser

**Purpose**: Extract technology innovations from patent abstracts and claims.

**Intelligence Layer**: L1 - Innovation Signals (18-24 months leading indicator)

**Input**: Lens.org patent JSON records

**Code**: [src/parsers/patents/patents_parser.py](../parsers/patents/patents_parser.py)

**Key Extraction**:
- **Technology nodes**: Core innovations with maturity assessment
- **Company nodes**: Assignees and developers
- **Relationships**: `enables`, `requires`, `supports`, `competes_with`, `advances_beyond`

**Example Output**: [test_patent_output.json](../parsers/test_patent_output.json)

**Usage**:
```bash
# Single patent test
python src/parsers/patents/test_single_patent.py

# Batch processing (10 patents)
python src/parsers/patents/batch_process_patents.py --limit 10

# Full dataset
python src/parsers/patents/batch_process_patents.py --checkpoint 100
```

**Output Structure**:
```json
{
  "document": {
    "doc_id": "003-712-519-476-908",
    "doc_type": "patent",
    "title": "ROTOR ASSEMBLY DEPLOYMENT MECHANISM",
    "assignee_name": "Joby Aero, Inc.",
    "quality_score": 0.95
  },
  "tech_mentions": [
    {
      "name": "Rotor Assembly Deployment Mechanism",
      "role": "subject",
      "strength": 0.95,
      "evidence_confidence": 0.98
    }
  ],
  "company_tech_relations": [
    {
      "company_name": "Joby Aero Inc",
      "technology_name": "Rotor Assembly Deployment Mechanism",
      "relation_type": "owns_ip",
      "evidence_confidence": 1.0,
      "doc_ref": "003-712-519-476-908"
    }
  ]
}
```

**Cost**: ~$0.001 per patent (GPT-4o-mini)

---

### 2. Scholarly Papers Parser

**Purpose**: Filter relevant research papers and extract technical relationships.

**Intelligence Layer**: L1 - Innovation Signals (validates technical feasibility 18-24 months ahead)

**Input**: Lens.org scholarly API JSON

**Code**: [src/parsers/scholarly/scholarly_parser.py](../parsers/scholarly/scholarly_parser.py)

**Key Features**:
- **Relevance Filtering**: Scores papers 0-10 based on industry alignment
- **Threshold**: Only papers ≥8.0/10 get full graph extraction (saves ~60% of LLM costs)
- **Batch Processing**: Concurrent processing with checkpoint system

**Example Output**: [test_scholarly_output.json](../parsers/test_scholarly_output.json)

**Usage**:
```bash
# Single paper test
python src/parsers/scholarly/test_single_paper.py

# Batch with checkpoint
python src/parsers/scholarly/batch_process_papers.py --limit 500 --checkpoint 100

# Full dataset (5,322 papers)
python src/parsers/scholarly/batch_process_papers.py --checkpoint 100
```

**Cost**: ~$0.0012 per paper (includes relevance check)
**Estimated Full Run**: 5,322 papers × $0.0012 = ~$6.40 USD

---

### 3. GitHub Activity Parser

**Purpose**: Extract technology innovation signals from repository activity.

**Intelligence Layer**: L1 - Innovation Signals

**Input**: GitHub API JSON (repositories, commits, issues)

**Code**: [src/parsers/github_activity/github_activity_parser.py](../parsers/github_activity/github_activity_parser.py)

**Key Extraction**:
- Repository metadata (stars, forks, activity)
- Technology stack identification
- Development velocity signals

---

### 4. Government Contracts Parser

**Purpose**: Extract technology commercialization signals from government contracts.

**Intelligence Layer**: L2 - Market Formation (12-18 months leading indicator)

**Input**: USASpending.gov API JSON

**Code**: [src/parsers/gov_contracts/gov_contracts_parser.py](../parsers/gov_contracts/gov_contracts_parser.py)

**Key Extraction**:
- Contract value and duration
- Technology applications
- Government agency relationships

---

### 5. Regulatory Documents Parser

**Purpose**: Extract compliance and regulatory signals from government filings.

**Intelligence Layer**: L2 - Market Formation

**Input**: **ADE-parsed markdown** from regulatory PDFs

**Code**: [src/parsers/regulatory/regulatory_parser.py](../parsers/regulatory/regulatory_parser.py)

**ADE Dependency**: This parser uses [ADE-extracted markdown](../../data/eVTOL/regulatory_docs/ade_parsed_results/markdown/) as input.

**Key Extraction**:
- Regulatory requirements
- Compliance timelines
- Technology certifications

**Data Flow**:
```
PDF (Federal Register)
  → ADE Parser (Track 1)
  → Markdown
  → Regulatory Parser (Track 2)
  → Neo4j Triplets
```

---

### 6. SEC Filings Parser

**Purpose**: Extract financial reality signals from corporate filings.

**Intelligence Layer**: L3 - Financial Reality (coincident 0-6 months)

**Input**: **ADE-parsed markdown** from SEC EDGAR filings

**Code**: [src/parsers/sec/sec_parser.py](../parsers/sec/sec_parser.py)

**ADE Dependency**: This parser uses [ADE-extracted markdown](../../data/eVTOL/sec_filings/ade_parsed_results/markdown/) as input.

**Supported Filings**: 10-K, 10-Q, 8-K, S-1

**Key Extraction**:
- **Section-specific** extraction (MD&A, Risk Factors, Business Description)
- Technology investments and R&D spending
- Corporate partnerships and acquisitions
- Financial performance metrics

**Section Extractors** ([sec/section_extractors.py](../parsers/sec/section_extractors.py)):
- Item 1: Business Description
- Item 1A: Risk Factors
- Item 7: MD&A (Management Discussion & Analysis)

**Data Flow**:
```
SEC Filing PDF (10-K)
  → ADE Parser (Track 1)
  → Markdown
  → SEC Parser (Track 2)
    → Section extraction
    → Entity identification
  → Neo4j Triplets
```

**Example Output**: [test_sec_output.json](../parsers/test_sec_output.json)

---

### 7. News Articles Parser

**Purpose**: Extract narrative and sentiment signals from news coverage.

**Intelligence Layer**: L4 - Narrative (lagging indicator, contrarian signal)

**Input**: NewsAPI + Tavily content extraction

**Code**: [src/parsers/news/news_parser.py](../parsers/news/news_parser.py)

**Key Extraction**:
- Article sentiment (positive, negative, neutral)
- Media outlet tier classification
- Technology mentions and company relations
- Virality indicators

**Tavily Integration**: Uses Tavily API for full-text extraction from URLs

---

## Industry-Agnostic Configuration

All specialized LLM parsers use a **single JSON configuration file** to define allowed relationship types. This enables the system to work for **any emerging technology market** by simply changing the config.

### Configuration File

**Location**: [configs/eVTOL_graph_relations.json](../../configs/eVTOL_graph_relations.json)

**Schema Version**: 1.1

**Purpose**: Define closed relation sets for consistent LLM extraction across all document types.

### Relation Types

**1. Company-Tech Relations** (5 types):
```json
[
  "develops",      // Company builds/engineers the technology
  "uses",          // Company operates the technology in production
  "invests_in",    // Company provides financial investment
  "researches",    // Company conducts R&D on technology
  "owns_ip"        // Company holds patents/IP
]
```

**2. Tech-Tech Relations** (14 types):
```json
[
  "competes_with",              // Direct competitors
  "alternative_to",             // Different approach, same problem
  "enables",                    // Makes another tech possible
  "supersedes",                 // Replaces older technology
  "complements",                // Works together
  "requires",                   // Hard dependency
  "supports",                   // Soft dependency
  "advances_beyond",            // Improves over previous
  "contradicts",                // Challenges assumptions
  "extends_life_of",            // Improves durability
  "improves_performance_of",    // Enhances capability
  "improves_efficiency_of",     // Reduces waste/losses
  "builds_on",                  // Based on prior work
  "validates"                   // Research validates claims
]
```

**3. Company-Company Relations** (6 types):
```json
[
  "partners_with",   // Strategic partnership
  "invests_in",      // VC/strategic investment
  "acquires",        // M&A
  "competes_with",   // Direct competition
  "supplies",        // Supply chain
  "licenses_from"    // IP licensing
]
```

### How Parsers Use Config

**1. Loading Config**:
```python
# Every parser initializes with config
with open(config_path, 'r', encoding='utf-8') as f:
    self.graph_config = json.load(f)

self.allowed_company_tech_relations = self.graph_config["allowed_company_tech_relations"]
self.allowed_tech_tech_relations = self.graph_config["allowed_tech_tech_relations"]
self.allowed_company_company_relations = self.graph_config["allowed_company_company_relations"]
```

**2. LLM Prompting**:
```python
# Few-shot prompt includes allowed relations
prompt = f"""
Extract entities and relationships from this patent.

Allowed Company-Tech Relations: {self.allowed_company_tech_relations}
Allowed Tech-Tech Relations: {self.allowed_tech_tech_relations}

ONLY use relations from the allowed lists above.
"""
```

**3. Validation**:
```python
# Post-processing validates LLM output
def validate_relation(relation, allowed_relations):
    if relation not in allowed_relations:
        raise ValueError(f"Invalid relation: {relation}")
```

### Switching Industries

To adapt the system for a different industry (e.g., Quantum Computing):

**Step 1**: Copy config file:
```bash
cp configs/eVTOL_graph_relations.json configs/quantum_graph_relations.json
```

**Step 2**: Update industry context:
```json
{
  "schema_version": "1.1",
  "industry": "Quantum Computing",
  "description": "Relation sets for quantum computing knowledge graph",
  "allowed_company_tech_relations": [...],
  "allowed_tech_tech_relations": [...]
}
```

**Step 3**: Run parsers with new config:
```bash
python src/parsers/patents/batch_process_patents.py \
    --config configs/quantum_graph_relations.json \
    --industry quantum
```

**No code changes required!**

### Why This Design Matters

1. **Consistency**: All parsers use same relation vocabulary
2. **Validation**: LLM can't hallucinate invalid relations
3. **Industry-Agnostic**: Works for any emerging tech market
4. **Neo4j Ready**: Relations map directly to edge types
5. **Evolution**: Easy to add new relation types across all parsers

---

## Testing Workflow

### Philosophy: Incremental Validation

**CRITICAL**: Always test with minimal examples before running full pipeline.

### Test Progression

#### 1️⃣ **Single Item Test** (30 seconds)

**Purpose**: Validate API access, field extraction, output schema

**ADE Parser**:
```bash
# Create test directory with 1 PDF
mkdir -p data/test_pdfs
cp data/eVTOL/regulatory_docs/pdfs/federal-aviation-administration_2024-25812.pdf data/test_pdfs/

# Test with single PDF
python -m src.parsers.ade_parser --pdf_dir data/test_pdfs --max_concurrent 1

# ✅ Check: Markdown and JSON files created
# ✅ Check: No errors in ade_parser.log
```

**LLM Parser (Patents)**:
```bash
# Test with hardcoded patent
python src/parsers/patents/test_single_patent.py

# ✅ Check: test_patent_output.json created
# ✅ Check: Contains tech_mentions, company_mentions, relations
# ✅ Check: Token usage logged
```

#### 2️⃣ **Small Batch Test** (2-5 minutes)

**Purpose**: Verify logic, error handling, checkpoint system, file saving

**ADE Parser (10 PDFs)**:
```bash
python -m src.parsers.ade_parser \
    --pdf_dir data/eVTOL/regulatory_docs/pdfs \
    --max_concurrent 2

# ✅ Check: Progress bar shows 10/46 PDFs
# ✅ Check: Checkpoint file created
# ✅ Check: parse_report.json shows success rate
```

**LLM Parser (10 patents)**:
```bash
python src/parsers/patents/batch_process_patents.py --limit 10 --checkpoint 5

# ✅ Check: 10 output JSON files created
# ✅ Check: Checkpoint files every 5 items
# ✅ Check: No errors in batch processing
```

#### 3️⃣ **Resume Test** (1 minute)

**Purpose**: Validate checkpoint system works, no duplicate processing

**ADE Parser**:
```bash
# Re-run same command (should skip already processed)
python -m src.parsers.ade_parser --pdf_dir data/eVTOL/regulatory_docs/pdfs

# ✅ Check: Logs show "Skipping already processed: ..."
# ✅ Check: No duplicate API calls
# ✅ Check: Stats show 'skipped' count
```

**LLM Parser**:
```bash
# Re-run (should resume from checkpoint)
python src/parsers/patents/batch_process_patents.py --limit 10 --checkpoint 5

# ✅ Check: Skips first 10 items
# ✅ Check: No duplicate output files
```

#### 4️⃣ **Full Dataset** (Hours)

**Purpose**: Production processing (only after all above tests pass)

**ADE Parser (all PDFs)**:
```bash
python -m src.parsers.ade_parser \
    --pdf_dir data/eVTOL/regulatory_docs/pdfs \
    --max_concurrent 5 \
    > ade_full_run.log 2>&1 &

# Monitor progress
tail -f ade_full_run.log
```

**LLM Parser (all items)**:
```bash
python src/parsers/scholarly/batch_process_papers.py \
    --checkpoint 100 \
    > scholarly_full_run.log 2>&1 &

# Monitor progress
tail -f scholarly_full_run.log
```

### Quality Gates

Before moving from one test level to the next, verify:

| Gate | Check | Command |
|------|-------|---------|
| **Schema** | Output matches expected JSON structure | `python -m json.tool output.json` |
| **Completeness** | All expected fields present | Check for null/missing values |
| **Relations** | Only allowed relation types used | Validate against config |
| **Evidence** | Every relation has evidence_text | Grep for empty evidence |
| **Confidence** | Scores between 0.0-1.0 | Check for invalid values |
| **Doc Refs** | All relations have doc_ref | Ensure provenance tracking |

### Cost Estimation

Before full runs, estimate costs:

```bash
# ADE Parser
# Cost: Variable (Landing AI credits, ~$0.05-0.15 per PDF)
# 46 PDFs × $0.10 avg = ~$4.60

# Patents Parser
# Cost: ~$0.001 per patent
# 100 patents × $0.001 = $0.10

# Scholarly Parser
# Cost: ~$0.0012 per paper
# 5,322 papers × $0.0012 = $6.39

# Total Phase 2: ~$15-20 for full eVTOL dataset
```

---

## Performance & Cost Analysis

### Processing Statistics

| Parser | Items Processed | Success Rate | Avg Time/Item | Total Time | Total Cost |
|--------|----------------|--------------|---------------|------------|------------|
| **ADE (Regulatory)** | 46 PDFs | **84.78%** | ~30s | 23 minutes | ~$4.60 |
| **ADE (Patents)** | 6 PDFs | **100%** | ~25s | 2.5 minutes | ~$0.60 |
| **Patents (LLM)** | 100 patents | ~95% | ~5s | 8 minutes | ~$0.10 |
| **Scholarly (LLM)** | 5,322 papers | ~90% | ~5s | ~7 hours | ~$6.40 |
| **GitHub (LLM)** | 50 repos | ~92% | ~8s | 7 minutes | ~$0.05 |
| **Gov Contracts (LLM)** | 200 contracts | ~93% | ~6s | 20 minutes | ~$0.20 |
| **Regulatory (LLM)** | 39 docs | ~88% | ~10s | 7 minutes | ~$0.08 |
| **SEC (LLM)** | 10 filings | ~90% | ~15s | 2.5 minutes | ~$0.05 |
| **News (LLM)** | 500 articles | ~91% | ~4s | 33 minutes | ~$0.40 |

**Total Phase 2 Cost**: ~$12-15 USD for full eVTOL dataset

### Cost Breakdown

**Track 1 (ADE)**:
- **Model**: Landing AI dpt-2-latest
- **Pricing**: Variable per page, typically $0.05-0.15 per document
- **Volume**: 52 PDFs total
- **Total**: ~$5.20

**Track 2 (LLM)**:
- **Model**: OpenAI GPT-4o-mini
- **Pricing**: $0.150/1M input tokens, $0.600/1M output tokens
- **Avg Document**: ~4,000-6,000 tokens total
- **Cost per Item**: $0.001-0.0012
- **Volume**: ~6,200 documents
- **Total**: ~$7.50

### Performance Optimization

**1. ADE Parser**:
- **Concurrency**: Increase `--max_concurrent` to 10 for faster processing
- **Page Limits**: Use `--max_pages 50` to skip large PDFs
- **Resume**: Always use checkpoints for long runs

**2. LLM Parsers**:
- **Workers**: Increase to 8 workers for 2x speedup (if API limits allow)
- **Batching**: Process in sub-batches of 8-10 items
- **Caching**: Reuse parsed outputs when rerunning analysis

**3. Network**:
- **Async I/O**: ADE parser uses async for max throughput
- **Retries**: Automatic retries for transient failures
- **Timeouts**: 5-minute timeout prevents stuck requests

### Scalability

**Current System** (eVTOL dataset):
- **Total Items**: ~6,250 documents
- **Processing Time**: ~8-10 hours (with concurrency)
- **Cost**: ~$12-15 USD

**Scaled to 10x** (larger industry):
- **Total Items**: ~62,500 documents
- **Processing Time**: ~80-100 hours (3-4 days)
- **Cost**: ~$120-150 USD

**Optimization for Scale**:
1. Increase concurrency (10-20 workers)
2. Use GPT-4o-mini-batch API (50% cost reduction)
3. Parallel processing across multiple machines
4. Selective parsing (filter low-quality sources first)

---

## Troubleshooting Guide

### Common Issues

#### 1. API Key Errors

**ADE Parser**:
```bash
# Error: Landing AI API key not found
# Solution: Set in .env file
echo "LANDING_API_KEY=your_key_here" >> .env

# Verify key loaded
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('LANDING_API_KEY')[:10])"
```

**LLM Parsers**:
```bash
# Error: OpenAI API key not found
# Solution: Set in .env file
echo "OPENAI_API_KEY=sk-..." >> .env

# Verify key loaded
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('OPENAI_API_KEY')[:10])"
```

#### 2. Rate Limits

**Symptoms**: `RateLimitError: 429 Too Many Requests`

**Solutions**:

For **ADE Parser**:
```bash
# Reduce concurrent requests
python -m src.parsers.ade_parser --pdf_dir data/pdfs --max_concurrent 3

# Add delays between requests (modify code)
# In ade_parser.py, add: await asyncio.sleep(2) between requests
```

For **LLM Parsers**:
```bash
# Reduce worker count
python batch_process.py --workers 2

# Upgrade OpenAI tier (https://platform.openai.com/account/limits)
```

#### 3. Checkpoint Recovery

**Symptoms**: Processing interrupted, need to resume

**ADE Parser**:
```bash
# Check checkpoint status
cat data/eVTOL/regulatory_docs/ade_parsed_results/checkpoints/ade_parser_checkpoint.json

# Resume (automatically skips completed)
python -m src.parsers.ade_parser --pdf_dir data/eVTOL/regulatory_docs/pdfs

# Force restart (ignore checkpoints)
rm data/eVTOL/regulatory_docs/ade_parsed_results/checkpoints/*
python -m src.parsers.ade_parser --pdf_dir data/eVTOL/regulatory_docs/pdfs
```

**LLM Parsers**:
```bash
# Check checkpoint files
ls data/eVTOL/lens_scholarly/checkpoints/

# Resume from specific point
python batch_process_papers.py --start 500 --limit 500

# Clear checkpoints and restart
rm data/eVTOL/lens_scholarly/checkpoints/*
python batch_process_papers.py
```

#### 4. PDF Validation Failures

**Symptoms**: "Invalid PDF file" errors

**ADE Parser Checks**:
1. **Magic bytes**: File must start with `%PDF-`
2. **File size**: Must be > 1 KB
3. **Page count**: Must be ≤ 100 pages (default)

**Solutions**:
```bash
# Increase page limit
python -m src.parsers.ade_parser --pdf_dir data/pdfs --max_pages 200

# Check PDF manually
file data/pdfs/document.pdf

# Repair corrupt PDF
pdftk input.pdf output fixed.pdf
```

#### 5. LLM Parsing Failures

**Symptoms**: Empty `tech_mentions` or `relations` arrays

**Common Causes**:
1. **Irrelevant content**: Document doesn't mention technologies
2. **LLM hallucination**: Invalid relation types
3. **Schema mismatch**: LLM output doesn't match expected format

**Solutions**:
```bash
# Check LLM output in logs
tail -f batch_processing.log

# Test with single item to debug
python test_single_patent.py

# Adjust relevance threshold (scholarly parser)
python batch_process_papers.py --threshold 7.0  # Lower threshold

# Validate config relations loaded
python -c "import json; print(json.load(open('configs/eVTOL_graph_relations.json'))['allowed_tech_tech_relations'])"
```

#### 6. Memory Issues

**Symptoms**: `MemoryError` or system slowdown

**Solutions**:
```bash
# Reduce batch size
# In batch_process.py, change: batch_size = 8 → batch_size = 4

# Reduce concurrent workers
python batch_process.py --workers 2

# Process in smaller chunks
python batch_process.py --start 0 --limit 1000
python batch_process.py --start 1000 --limit 1000
```

#### 7. Network Timeouts

**Symptoms**: `Timeout error (exceeded 300s)`

**ADE Parser**:
```python
# Increase timeout in ade_parser.py
# Line 322: timeout = aiohttp.ClientTimeout(total=600)  # 10 minutes
```

**LLM Parsers**:
```python
# Increase timeout in parser class
# self.llm = ChatOpenAI(..., timeout=600.0)
```

## Key Achievements

### 1. Dual-Track Architecture

**Innovation**: Separated high-fidelity document extraction (ADE) from knowledge graph extraction (LLM).

**Benefits**:
- ✅ **Quality**: ADE preserves document structure (tables, formatting, hierarchy)
- ✅ **Scalability**: Parallel processing of different document types
- ✅ **Flexibility**: Can swap models independently (ADE vs. GPT-4o-mini)
- ✅ **Cost-Effective**: Use expensive ADE only where needed, cheap LLM for relations

### 2. High Success Rates

| Parser | Success Rate | Notes |
|--------|--------------|-------|
| **ADE (Regulatory)** | **84.78%** | 39/46 PDFs successfully parsed |
| **ADE (Patents)** | **100%** | 6/6 PDFs successfully parsed |
| Patents (LLM) | ~95% | Rare failures on malformed JSON |
| Scholarly (LLM) | ~90% | Some papers too abstract |
| Gov Contracts (LLM) | ~93% | Excellent on structured data |

### 3. Processed 45+ PDFs with ADE

**Regulatory Documents**:
- Federal Aviation Administration (FAA): 24 documents
- Environmental Protection Agency (EPA): 10 documents
- Defense Department (DoD): 5 documents
- NASA, FCC, and others: 7 documents

**Patents**:
- 6 high-quality PDF patents processed with 100% success

**Total**: 45 PDFs successfully extracted with structure preservation

### 4. Industry-Agnostic Design

**Single Config Change** adapts system to any industry:
- **eVTOL**: Current implementation
- **Quantum Computing**: Change config, no code changes
- **Biotech**: Change config, no code changes
- **Clean Energy**: Change config, no code changes

**Config File**: [configs/eVTOL_graph_relations.json](../../configs/eVTOL_graph_relations.json)

### 5. Fault Tolerance at Scale

**Checkpoint Systems**:
- ✅ Resume after crashes (no data loss)
- ✅ Incremental validation during long runs
- ✅ Auto-save every N items (configurable)
- ✅ Failed item tracking with reasons

**Impact**: 7-hour scholarly parsing run can resume from exact position after interruption.

### 6. Cost Efficiency

**Total Phase 2 Cost**: ~$12-15 USD for full eVTOL dataset (6,250 documents)

**Per-Document Costs**:
- ADE: $0.05-0.15 per PDF (high quality)
- LLM: $0.001-0.0012 per document (bulk extraction)

**Cost Optimization**:
- Scholarly relevance filtering saves ~60% LLM costs
- GPT-4o-mini 10x cheaper than GPT-4
- Batch processing minimizes API overhead

### 7. Reproducible Outputs

**Deterministic LLM** (temperature=0.0):
- Same input → Same output (critical for evaluations)
- Reproducible analysis across runs
- Consistent knowledge graph construction

**Config-Driven Relations**:
- Closed relation sets prevent hallucinations
- Consistent vocabulary across all parsers
- Easier debugging and validation

### 8. Evidence-Based Extraction

**Every Relation Includes**:
- `evidence_text`: Direct quote supporting the relation
- `evidence_confidence`: LLM's confidence score (0.0-1.0)
- `doc_ref`: Source document ID (provenance tracking)

**Example**:
```json
{
  "from_tech_name": "Rotor Assembly Deployment Mechanism",
  "to_tech_name": "Torsion Box Construction",
  "relation_type": "supports",
  "evidence_confidence": 0.95,
  "evidence_text": "Deployment mechanism utilizes torsion box construction for strength",
  "doc_ref": "003-712-519-476-908"
}
```

---

## Summary

**Phase 2: Knowledge Graph Extraction** transforms raw documents into structured knowledge graphs through a **dual-track architecture**:

**Track 1 (ADE Parser)**:
- Processed **45 PDFs** with **86.54% success rate**
- High-fidelity extraction (tables, formatting, structure preserved)
- Landing AI dpt-2-latest model
- Async concurrent processing with checkpoints

**Track 2 (LLM Parsers)**:
- **7 specialized parsers** covering all 14 data sources
- Config-driven, industry-agnostic design
- GPT-4o-mini with temperature 0.0 (reproducible)
- Neo4j-ready triplets with evidence and confidence

**Key Numbers**:
- **52 PDFs** processed by ADE (regulatory + patents)
- **6,250 total documents** across all parsers
- **~$12-15 USD** total cost for full eVTOL dataset
- **84.78%** success rate on regulatory documents

**Next Phase**: Phase 3 ingests this structured data into Neo4j graph database for multi-agent analysis.

---
