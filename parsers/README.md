# Parsers - Knowledge Graph Extraction & Quality Verification

## Overview

Parsers transform raw harvested data into **structured knowledge graphs** suitable for multi-layer strategic intelligence analysis. Each parser:

1. **Assesses Relevance**: Filters data by industry alignment (threshold-based scoring)
2. **Extracts Knowledge Graphs**: Identifies technology nodes and their relationships
3. **Validates Data Quality**: Ensures structured output for downstream analysis
4. **Provides Metadata**: Innovation signals, maturity assessments, confidence scores

## Implemented Parsers

### 1. Patents Parser (`patents/`)
- **Data Source**: Lens patent data (Layer 1: Innovation Signals)
- **Purpose**: Extract technology innovations from patent abstracts
- **Leading Indicator**: 18-24 months ahead of commercialization
- **Output**: Technology nodes, relationships, innovation signals

### 2. Scholarly Papers Parser (`scholarly/`)
- **Data Source**: Lens scholarly papers (Layer 1: Innovation Signals)
- **Purpose**: Filter relevant research and extract technical relationships
- **Relevance Threshold**: 8.0/10 (papers scoring ≥8.0 get full graph extraction)
- **Output**: Relevance assessment, knowledge graph (if relevant), innovation signals
- **Features**: Batch processing with checkpoints and resume capability

---

## Patents Parser

### Purpose

Patents are **leading indicators (18-24 months ahead)** of technology commercialization. This parser extracts:

1. **Technology Nodes**: Core innovations and enabling technologies
2. **Relationships**: How technologies support, contradict, or compete with each other
3. **Innovation Signals**: Maturity assessment for lifecycle positioning

### Knowledge Graph Structure

**Node Types**:
- **Technology Nodes** (`tech_*`): Core innovations (e.g., `tech_magnetic_levitation_rotor`)
- **Organization Nodes** (`company_*`): Companies developing technologies (e.g., `company_joby`)
- **Concept Nodes** (`concept_*`): Abstract approaches (e.g., `concept_battery_swapping`)

**Relationship Types** (Predicates)

| Predicate | Meaning |
|-----------|---------|
| `enables` | Technology A makes B possible |
| `requires` | Technology A needs B to function |
| `supports` | Technology A helps B work better |
| `advances_beyond` | Technology A improves over B |
| `competes_with` | Technology A is alternative to B |
| `develops` | Organization develops technology |
| `builds_on` | Technology A based on prior work B |

**Innovation Signals**: `maturity_level`, `innovation_type`, `competitive_positioning`, `technical_risk`, `adoption_indicators`

### Usage

**Single Patent Test** (recommended first):
```bash
python parsers/patents/patents_parser.py
```
Output: [parsers/patents/test_patent_output.json](parsers/patents/test_patent_output.json)

**Full Batch**:
```python
from parsers.patents.patents_parser import parse_all_patents
results = parse_all_patents(industry="eVTOL", limit=100)
```
Output: `parsers/output/eVTOL_patents/*.json`

**Cost**: ~$0.001 per patent (gpt-4o-mini)

### Example Output

```json
{
  "patent_metadata": { "title": "...", "assignee": "Joby Aero", "lens_id": "..." },
  "technology_nodes": [
    {
      "node_id": "tech_magnetic_levitation_rotor",
      "name": "Magnetic Levitation Rotor System",
      "maturity": "emerging",
      "domain": "propulsion"
    }
  ],
  "relationships": [
    {
      "subject": "tech_magnetic_levitation_rotor",
      "predicate": "enables",
      "object": "tech_independent_blade_control",
      "confidence": 0.95
    }
  ],
  "innovation_signals": { "maturity_level": "early_commercial", ... }
}
```

---

## Scholarly Papers Parser

### Purpose

Scholarly papers validate **technical feasibility 18-24 months ahead** of commercialization. This parser:

1. **Assesses Relevance**: Scores papers 0-10 based on industry alignment
2. **Filters by Threshold**: Only papers ≥8.0/10 get full graph extraction
3. **Extracts Knowledge Graph**: Technology nodes and relationships (for relevant papers)
4. **Batch Processing**: Concurrent processing with checkpoint system for large datasets

### Why Relevance Filtering?

Not all papers are relevant to an industry. Example for eVTOL:
- **Relevant (9.0/10)**: "Tilt-rotor aerodynamics for urban air mobility"
- **Not Relevant (3.0/10)**: "Social media marketing strategies for airlines"

By filtering first, we avoid extracting knowledge graphs from irrelevant papers, saving ~60% of LLM costs.

### Batch Processing Architecture

For large datasets (5,000+ papers), the scholarly parser uses:

**Concurrent Processing**:
- **ThreadPoolExecutor**: 4 workers process papers in parallel
- **Sub-batches**: Papers grouped into batches of 8 for efficiency
- **Progress Tracking**: tqdm progress bar shows real-time status

**Checkpoint System** (Fault Tolerance):
- **Auto-Save**: Results saved every N papers (configurable, default: 100)
- **Resume Capability**: Rerunning after crash skips already-processed papers
- **Incremental Output**: Checkpoint files prevent data loss
- **Final Merge**: All checkpoints merged with deduplication

**Why Checkpoints?**
- Large batches take hours (5,000 papers × 5 seconds = ~7 hours)
- API failures, crashes, or interruptions don't lose progress
- Can resume from exact position after fixing issues
- Incremental validation during long runs

### Usage

**Single Paper Test** (recommended first):
```bash
cd parsers/scholarly
python test_single_paper.py
```
Output: [parsers/scholarly/test_output_single.json](parsers/scholarly/test_output_single.json)
Shows: relevance score, nodes, relationships, cost estimate

**Batch Processing** (with checkpoints):
```bash
# Process first 500 papers with checkpoint every 100 papers
python parsers/scholarly/batch_process_papers.py --limit 500 --checkpoint 100

# Resume: Process papers 500-1000 (skips already completed)
python parsers/scholarly/batch_process_papers.py --start 500 --limit 500 --checkpoint 100

# Full dataset (5,322 papers)
python parsers/scholarly/batch_process_papers.py --checkpoint 100
```

**Command-Line Options**:
- `--limit N`: Process only N papers
- `--start N`: Start from paper N (0-indexed)
- `--checkpoint N`: Save checkpoint every N papers (default: 100)
- `--workers N`: Concurrent workers (default: 4)
- `--threshold X`: Relevance threshold (default: 8.0)
- `--no-resume`: Ignore existing checkpoints and restart

**Output Structure**:
```
data/eVTOL/lens_scholarly/
├── checkpoints/
│   ├── checkpoint_0000-0099.json          # All papers in batch
│   ├── checkpoint_relevant_0000-0099.json # Relevant papers only
│   ├── checkpoint_0100-0199.json
│   └── ...
├── parsed_papers_all.json                 # Final merged results
└── parsed_papers_relevant.json            # Relevant papers only
```

**Cost**: ~$0.0012 per paper (gpt-4o-mini)
**Estimated**: 5,322 papers × $0.0012 = ~$6.40 USD

### Example Output

```json
{
  "paper_metadata": {
    "title": "Aerodynamic analysis of tilt-rotor for eVTOL",
    "lens_id": "123-456-789",
    "year_published": 2024
  },
  "relevance_assessment": {
    "relevance_score": 9.0,
    "is_relevant": true,
    "relevance_category": "direct_application",
    "confidence": 0.95,
    "justification": "Paper directly addresses propulsion system design for electric VTOL aircraft"
  },
  "technology_nodes": [
    {
      "node_id": "tech_tilt_rotor_aerodynamics",
      "name": "Tilt-Rotor Aerodynamics",
      "maturity": "advanced",
      "domain": "propulsion"
    }
  ],
  "relationships": [
    {
      "subject": "tech_tilt_rotor_aerodynamics",
      "predicate": "enables",
      "object": "tech_transition_flight_mode",
      "confidence": 0.90
    }
  ],
  "innovation_signals": {
    "research_stage": "applied_research",
    "innovation_type": "incremental_breakthrough",
    "impact_potential": "high"
  }
}
```

---

## General Configuration

### Environment Variables

Required in `.env`:
```bash
OPENAI_API_KEY=sk-...
```

### Model Configuration

Both parsers use **gpt-4o-mini** by default:
- **Cost**: $0.150/1M input tokens, $0.600/1M output tokens
- **Typical**: ~4,000-6,000 tokens per item = $0.001-0.0012 per item
- **Temperature**: 0.0 (deterministic output)

### Dependencies

```bash
pip install langchain langchain-openai langchain-core langchain-community openai
```

---

## Creating New Parsers

Follow this pattern when creating parsers for new data sources:

### 1. Determine Parser Type

**Simple Extraction** (like patents):
- Single-pass processing
- No relevance filtering needed
- All items get full graph extraction

**Filtered Extraction** (like scholarly):
- Two-pass: relevance scoring → graph extraction
- Threshold-based filtering (saves costs)
- Only relevant items get full graph extraction

### 2. Core Components

Every parser should have:
1. **Parser Class**: Main logic (LangChain + few-shot prompting)
2. **Test Script**: Single-item test for validation
3. **Batch Script**: Concurrent processing with checkpoints (for large datasets)
4. **Checkpoint Manager**: Resume capability (if batch processing)

### 3. Testing Workflow

**CRITICAL**: Always test incrementally before full runs.

```bash
# 1. Single item test (validate setup)
python parsers/your_parser/test_single.py

# 2. Small batch (10-50 items, verify checkpoints)
python parsers/your_parser/batch_process.py --limit 10 --checkpoint 5

# 3. Resume test (verify checkpoint system)
python parsers/your_parser/batch_process.py --limit 10 --checkpoint 5  # Should skip

# 4. Full dataset (only after validation)
python parsers/your_parser/batch_process.py --checkpoint 100
```

### 4. Industry-Agnostic Design

Use config files for industry-specific parameters:
- Industry name and description
- Keywords (core, adjacent, excluded)
- Relevance threshold
- Domain categories

Example:
```python
config = load_industry_config("configs/evtol_config.json")
parser = YourParser(
    industry_name=config["industry"],
    industry_keywords=config["keywords"]["core"],
    relevance_threshold=8.0
)
```

### 5. Output Schema

Standardize output format:
```json
{
  "item_metadata": { ... },
  "relevance_assessment": { "score": X, "is_relevant": bool, ... },  // Optional
  "technology_nodes": [ ... ],
  "relationships": [ ... ],
  "innovation_signals": { ... }
}
```

---

## Troubleshooting

**API Key Issues**:
```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('OPENAI_API_KEY'))"
```

**Rate Limits**:
- Reduce `--workers` count
- Add delays between requests
- Upgrade OpenAI tier

**Checkpoint Issues**:
- Check `.checkpoint_*.json` files exist
- Use `--no-resume` to force restart
- Delete checkpoint files to reset

**Parsing Failures**:
- Check error logs in output directory
- Verify input data schema matches expected format
- Test with single item first to isolate issues

---

**Last Updated**: 2025-11-06
**Version**: 2.0.0
**Status**: Production Ready (Patents + Scholarly Parsers)
