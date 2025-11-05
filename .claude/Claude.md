# Pura Vida Sloth - Strategic Intelligence Harvesting System

## Project Purpose

Multi-source intelligence harvesting for **strategic investment timing** in emerging technology markets. This system collects data from 14 independent sources to determine **where an industry sits on the Gartner Hype Cycle** and answer the C-level question: **"Should we invest NOW, or wait?"**

**End Goal**: Gartner-style executive reports with Hype Cycle positioning and BUY/HOLD/SELL recommendations based on multi-layer intelligence triangulation.

---

## Core Design Principles

### 1. Industry-Agnostic by Design (SACRED RULE)
**The entire value proposition is industry flexibility.** Change the industry by changing the JSON config, NEVER by changing code.

**eVTOL is the reference implementation, not the only use case.** System must work for quantum computing, biotech, fintech, or any emerging technology by ONLY editing the config file.

### 2. Test-Driven Development is MANDATORY
Any new data source MUST pass this workflow before integration:

```
1. Write test FIRST → 2. Validate with eVTOL config → 3. Verify NO hardcoding →
4. Tests pass → 5. Add to orchestrator.py → 6. Run full harvest
```

**NO source gets added to orchestrator.py without passing TDD validation.**

### 3. The 4-Layer Intelligence Framework
Every downloader contributes to one layer of the intelligence pyramid:

```
LAYER 1: Innovation Signals (Leading 18-24 months)
└─ Patents, Research Papers, GitHub, Citations
   Purpose: Predict which technologies will emerge

LAYER 2: Market Formation (Leading 12-18 months)
└─ Government Contracts, Regulatory Filings, Job Postings
   Purpose: Predict when commercialization begins

LAYER 3: Financial Reality (Coincident 0-6 months)
└─ SEC Filings, Earnings, Stock Data, Fundamentals, Holdings, Insider Trades
   Purpose: Measure current valuation vs reality

LAYER 4: Narrative (Lagging, confirms trends)
└─ News Sentiment, Press Releases
   Purpose: Detect hype peaks (when news peaks, market often peaks)
```

**Why This Matters**: When layers contradict = investment signal:
- News bullish + GitHub dead + Insiders selling = **PEAK** → Sell
- News bearish + Gov contracts up + Insider buying = **TROUGH** → Buy

### 4. Quality is the Gold Standard
Bad data = Wrong hype cycle position = Bad investment decisions = Executives lose $100M+

**Quality Metrics**:
- 400-1,600 documents per 90-day harvest window
- <10% download failure rate
- Checkpoint resume capability (hours-long harvests must survive failures)
- Every document has metadata (title, date, source, URL, file_path)

---

## Folder Structure (NEVER Deviate)

```
data/{industry}/                        # From config.industry (e.g., "eVTOL")
├── research_papers/                   # From config.folder_structure.research
│   ├── {filename}.pdf
│   ├── research_papers_metadata.json  # REQUIRED: All document metadata
│   ├── .checkpoint_research_papers.json  # Checkpoint for resume
│   └── research_papers.log            # Source-specific log
├── sec_filings/
├── stock_market/
├── government_contracts/
├── _consolidated/                     # REQUIRED: Aggregate statistics
│   ├── harvest_summary.json           # REQUIRED: Cross-source stats
│   └── hype_cycle_data.json          # Preliminary hype cycle data
├── harvest_config.json                # Copy of config used
└── harvest.log                        # Main orchestrator log
```

**System depends on this structure for consolidation and analysis. DO NOT change folder names or structure.**

---

## Configuration Schema (JSON-Driven Design)

### Example: eVTOL Config (configs/evtol_config.json)

```json
{
  "industry": "eVTOL",
  "industry_name": "Electric Vertical Takeoff and Landing",

  "companies": {
    "public": {
      "JOBY": "Joby Aviation",
      "ACHR": "Archer Aviation",
      "LILM": "Lilium"
    },
    "private": {
      "Volocopter": "Volocopter GmbH",
      "Wisk": "Wisk Aero"
    }
  },

  "keywords": {
    "core": ["eVTOL", "electric vertical takeoff", "urban air mobility", "air taxi"],
    "technical": ["electric propulsion", "distributed electric propulsion", "DEP"],
    "regulatory": ["FAA Part 135", "type certificate", "airworthiness"]
  },

  "date_range": {
    "start_date": "2024-05-01",
    "end_date": "2024-11-01",
    "days_back": 180
  },

  "data_sources": {
    "research_papers": {"enabled": true, "limit": 100},
    "sec_filings": {"enabled": true},
    "stock_market": {"enabled": true},
    "government_contracts": {"enabled": true, "years_back": 5},
    "news_sentiment": {"enabled": true}
  },

  "folder_structure": {
    "research": "research_papers",
    "sec": "sec_filings",
    "stock": "stock_market",
    "gov_contracts": "government_contracts"
  }
}
```

### Adding a New Industry (Zero Code Changes)

```bash
# 1. Copy reference config
cp configs/evtol_config.json configs/quantum_computing_config.json

# 2. Edit JSON only (change industry, companies, keywords)
{
  "industry": "quantum_computing",
  "companies": {
    "public": {"IONQ": "IonQ Inc.", "RGTI": "Rigetti Computing"}
  },
  "keywords": {
    "core": ["quantum computing", "qubit", "quantum supremacy"]
  }
}

# 3. Run harvest (NO code changes needed)
python -m src.core.orchestrator --config configs/quantum_computing_config.json

# Result: data/quantum_computing/ folder with same structure
```

---

## Quick Reference: Adding a New Data Source

```bash
# 1. Create test FIRST
touch tests/test_downloaders/test_my_source.py

# 2. Write test validating industry-agnostic design
# 3. Create downloader: src/downloaders/my_source.py
# 4. Implement using Downloader Contract pattern
# 5. Run test: python tests/test_downloaders/test_my_source.py
# 6. Verify: No hardcoded industry data
# 7. Add to orchestrator.py:initialize_downloaders()
# 8. Add to config: configs/evtol_config.json
# 9. Run full harvest: python -m src.core.orchestrator --config configs/evtol_config.json
# 10. Verify output in data/eVTOL/my_source/
```

---

## Downloader Requirements

Every downloader MUST:
- Accept `companies` and `keywords` from config (NEVER hardcode)
- Return stats dict with `success` and `failed` keys
- Use `CheckpointManager` for resume capability
- Save metadata JSON with all downloaded items
- Use retry logic for external API calls

See `.claude/CLAUDE.local.md` for detailed implementation patterns and code examples.

---

## Critical Rules

### ✅ ALWAYS
- Config-driven parameters (from JSON)
- Test-driven development (write test FIRST)
- Checkpoint resume capability
- Industry-agnostic design

### ❌ NEVER
- Hardcode industry data (companies, keywords, terms)
- Skip retry logic for external APIs
- Commit data files, .env, or checkpoints
- Change folder structure
- Add source to orchestrator without passing tests

---

## System Status

### ✅ Implemented (Data Collection Layer)
- 14 data source downloaders (9/14 working, 5 disabled/stub)
- Industry-agnostic orchestrator
- Checkpoint resume capability
- Multi-source fallback patterns
- Consolidated statistics generation

### ⚠️ Gap (Analysis Layer - NOT IMPLEMENTED)
- Hype cycle scoring algorithm
- Phase classification (Technology Trigger → Peak → Trough → Slope → Plateau)
- Cross-layer contradiction detection
- Automated trend analysis

### 🎯 Future (Report Layer - NOT IMPLEMENTED)
- Gartner-style report generator (Markdown/PDF)
- Hype Cycle visualizations
- Magic Quadrant positioning
- Investment timing recommendations

---

**Remember**: This system helps executives avoid $100M+ mistakes by predicting hype cycle position 12-24 months ahead. Every downloader you build contributes to that strategic goal. Quality matters.

**For detailed implementation patterns, code examples, and comprehensive workflows, see `.claude/CLAUDE.local.md`**
