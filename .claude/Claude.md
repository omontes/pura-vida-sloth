# Pura Vida Sloth - Strategic Intelligence Harvesting System

## Project Purpose

Multi-source intelligence harvesting for **strategic investment timing** in emerging technology markets. This system collects data from 14 independent sources to determine **where an industry sits on the Gartner Hype Cycle** and answer the C-level question: **"Should we invest NOW, or wait?"**

**End Goal**: Gartner-style executive reports with Hype Cycle positioning and BUY/HOLD/SELL recommendations based on multi-layer intelligence triangulation.

---

## Core Design Principles

### 1. Industry-Agnostic by Design (SACRED RULE)
**The entire value proposition is industry flexibility.** Change the industry by changing the JSON config, NEVER by changing code.

```python
# ✗ WRONG: Hardcoded industry data
class Downloader:
    def __init__(self):
        self.companies = ["Joby", "Archer"]  # Breaks agnostic design

# ✓ CORRECT: Config-driven
class Downloader:
    def __init__(self, companies: Dict[str, str]):
        self.companies = companies  # From config JSON
```

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

## Development Workflow: Test-Driven Development

### STEP 1: Write the Test FIRST (Non-Negotiable)

```python
# tests/test_downloaders/test_new_source.py
import pytest
from pathlib import Path
import json

def test_new_source_industry_agnostic(tmp_path):
    """Verify downloader works with ANY industry config (tests against eVTOL)"""

    # Load eVTOL config as test reference (but design must work for ANY industry)
    config = json.loads(Path('configs/evtol_config.json').read_text())

    downloader = NewSourceDownloader(
        output_dir=tmp_path,
        start_date=config['date_range']['start_date'],
        end_date=config['date_range']['end_date'],
        companies=config['companies']['public'],     # From config, not hardcoded
        keywords=config['keywords']['core'],          # From config, not hardcoded
        limit=1  # Fast test
    )

    stats = downloader.download()

    # Validate stats format (required keys)
    assert 'success' in stats
    assert 'failed' in stats
    assert stats['success'] >= 1, "Should download at least 1 document"

    # Validate output structure
    assert (tmp_path / 'new_source_metadata.json').exists()
    metadata = json.loads((tmp_path / 'new_source_metadata.json').read_text())
    assert len(metadata) >= 1

    # Validate checkpoint created
    checkpoint_files = list(tmp_path.glob('.checkpoint_*.json'))
    assert len(checkpoint_files) == 1

def test_no_hardcoded_industry_data():
    """Ensure downloader has NO hardcoded industry-specific strings"""
    source_code = Path('src/downloaders/new_source.py').read_text()

    # These should NOT appear in downloader code (industry-specific terms)
    forbidden = ['Joby', 'Archer', 'eVTOL', 'flying car', 'air taxi', 'urban air mobility']

    for term in forbidden:
        assert term not in source_code, f"Hardcoded industry term '{term}' found in downloader!"
```

### STEP 2: Run Test Against eVTOL Config
```bash
python tests/test_downloaders/test_new_source.py
```

**eVTOL config validates the STRUCTURE**, but implementation must work if config says "quantum computing" instead.

### STEP 3: Verify Industry-Agnostic Design

**The Validation Checklist**:
- ✅ Downloader accepts `keywords` parameter (not hardcoded search terms)
- ✅ Downloader accepts `companies` parameter (not hardcoded company names)
- ✅ Search logic uses config params, not string literals
- ✅ Output paths use `config['industry']` name
- ✅ No industry-specific strings in downloader code
- ✅ Test uses eVTOL but doesn't assume eVTOL

### STEP 4: Add to Orchestrator ONLY After Tests Pass

```python
# src/core/orchestrator.py:initialize_downloaders()

if self.config['data_sources'].get('new_source', {}).get('enabled'):
    from src.downloaders.new_source import NewSourceDownloader

    downloaders['new_source'] = NewSourceDownloader(
        output_dir=self.industry_root / folder_map['new_source'],
        start_date=start_date,
        end_date=end_date,
        companies=self.config['companies']['public'],  # Config-driven
        keywords=all_keywords,                          # Config-driven
        limit=self.config['data_sources']['new_source'].get('limit', 100)
    )
```

### STEP 5: Run Full Harvest with New Source

```bash
python -m src.core.orchestrator --config configs/evtol_config.json
```

Final integration test: Complete harvest with new source enabled.

---

## The Downloader Contract (Required Pattern)

Every downloader MUST implement this interface:

```python
from pathlib import Path
from typing import Dict, Any, List
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.logger import setup_logger

class YourDownloader:
    """
    Industry-agnostic downloader template.

    CRITICAL: This must work for ANY industry (eVTOL, biotech, fintech, etc.)
    by accepting config-driven parameters, not hardcoding industry data.
    """

    def __init__(
        self,
        output_dir: Path,
        start_date: str,
        end_date: str,
        companies: Dict[str, str],  # From config.companies
        keywords: List[str],        # From config.keywords
        **optional_params
    ):
        """
        Initialize downloader with config-driven parameters.

        NEVER hardcode: companies, keywords, search terms, industry names
        ALWAYS accept: From JSON config via orchestrator
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.start_date = start_date
        self.end_date = end_date
        self.companies = companies     # From config, NOT hardcoded
        self.keywords = keywords       # From config, NOT hardcoded

        # Checkpoint for resume capability (MANDATORY)
        self.checkpoint = CheckpointManager(self.output_dir, 'your_source')

        # Logger for debugging (MANDATORY)
        self.logger = setup_logger("YourSource", self.output_dir / "your_source.log")

    def download(self) -> Dict[str, Any]:
        """
        Main download method. Returns stats dict with REQUIRED keys.

        Returns:
            {
                'success': int,      # REQUIRED: Count of successful downloads
                'failed': int,       # REQUIRED: Count of failed downloads
                'skipped': int,      # OPTIONAL: Count of skipped (already processed)
                'total_size': float, # OPTIONAL: Total size in MB
                'by_source': dict    # OPTIONAL: Breakdown by subsource
            }
        """
        success_count = 0
        failed_count = 0

        try:
            items = self._search_items()  # Your search logic

            for item in items:
                item_id = self._get_item_id(item)

                # Check checkpoint (skip if already processed)
                if self.checkpoint.is_completed(item_id):
                    continue

                try:
                    self._download_item(item)
                    self.checkpoint.mark_completed(item_id, metadata={'title': item.get('title')})
                    success_count += 1
                except Exception as e:
                    self.checkpoint.mark_failed(item_id, str(e))
                    failed_count += 1
                    self.logger.error(f"Failed to download {item_id}: {e}")

            # Save metadata JSON (REQUIRED)
            self._save_metadata()

            # Finalize checkpoint (REQUIRED)
            self.checkpoint.finalize()

        except Exception as e:
            self.logger.error(f"Critical error in download: {e}")
            raise

        return {
            'success': success_count,
            'failed': failed_count,
            'total_size': self._calculate_size()
        }

    def _search_items(self) -> List[Dict]:
        """Search for items using config-driven params (NOT hardcoded)"""
        # Use self.companies, self.keywords, self.start_date, self.end_date
        pass

    def _download_item(self, item: Dict):
        """Download individual item"""
        pass

    def _save_metadata(self):
        """Save metadata JSON with all downloaded items"""
        pass
```

---

## Critical Patterns (Institutional Memory)

### Pattern 1: Multi-Source Fallback (Reliability)

```python
def download(self) -> Dict[str, Any]:
    """Try multiple sources in priority order (best → fallback)"""
    all_items = []

    # Primary API (best quality, rate-limited)
    try:
        all_items.extend(self._fetch_from_primary_api())
    except Exception as e:
        self.logger.warning(f"Primary API failed: {e}")

    # Secondary API (backup, lower quality)
    try:
        all_items.extend(self._fetch_from_secondary_api())
    except Exception as e:
        self.logger.warning(f"Secondary API failed: {e}")

    # RSS feeds (fallback, delayed data)
    try:
        all_items.extend(self._fetch_from_rss())
    except Exception as e:
        self.logger.warning(f"RSS feeds failed: {e}")

    # Web scraping (last resort)
    if len(all_items) == 0:
        all_items.extend(self._scrape_as_last_resort())

    # Deduplicate across sources
    unique_items = self._deduplicate_by_url(all_items)

    return self._process_items(unique_items)
```

**Real Example**: `research_papers.py` uses CORE API → arXiv → FRASER → RSS → SSRN scraping

### Pattern 2: Checkpoint Resume (Non-Negotiable)

```python
checkpoint = CheckpointManager(output_dir, 'source_name')

for item in items:
    item_id = self._generate_id(item)

    # Skip if already processed (resume capability)
    if checkpoint.is_completed(item_id):
        self.logger.info(f"Skipping {item_id} (already completed)")
        continue

    try:
        result = process_item(item)
        checkpoint.mark_completed(item_id, metadata={'title': item['title'], 'url': item['url']})
        success_count += 1
    except Exception as e:
        checkpoint.mark_failed(item_id, str(e))
        failed_count += 1
        self.logger.error(f"Failed {item_id}: {e}")

# Finalize checkpoint (REQUIRED - marks harvest complete)
checkpoint.finalize()
```

**Why This Matters**: Harvests can take hours. Network failures happen. Users must be able to resume without re-downloading completed items.

### Pattern 3: Sacred Folder Structure (NEVER Deviate)

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

## Quality Gates & Testing

### Before Committing New Downloader:

1. ✅ **Unit test exists**: `tests/test_downloaders/test_{source}.py`
2. ✅ **Test validates industry-agnostic design** (no hardcoded data)
3. ✅ **Test uses eVTOL config** (reference implementation)
4. ✅ **Test verifies required outputs**:
   - Stats dict with `success`, `failed` keys
   - Metadata JSON file created
   - Checkpoint file created
   - Log file created
5. ✅ **Integration test passes**: Full harvest with new source enabled

### Fast Test (10-60 seconds per source):
```bash
python tests/test_downloaders/test_research_papers.py
```

### Full Integration Test (~5 minutes):
```bash
python tests/test_system.py
```

### Quality Metrics:
- **Success Rate**: >90% downloads succeed
- **Resume Capability**: Harvest can resume after failure
- **Industry Agnostic**: Works with quantum_computing_config.json (not just eVTOL)
- **Metadata Complete**: Every document has title, date, source, URL

---

## Boundaries: NEVER Do This

### ❌ NEVER: Hardcode Industry Data

```python
# ✗ WRONG:
class SECDownloader:
    def __init__(self):
        self.tickers = ["JOBY", "ACHR"]  # Hardcoded!

# ✓ CORRECT:
class SECDownloader:
    def __init__(self, tickers: Dict[str, str]):
        self.tickers = tickers  # From config
```

### ❌ NEVER: Skip Retry Logic for External APIs

```python
# ✗ WRONG:
response = requests.get(url)  # No retries!

# ✓ CORRECT:
from src.utils.retry_handler import retry_on_error

@retry_on_error(max_retries=5, backoff_factor=2)
def fetch_data(url):
    response = requests.get(url)
    response.raise_for_status()
    return response
```

### ❌ NEVER: Commit Data Files

From `.gitignore`:
```
data/*              # Downloaded data (NEVER commit)
.env                # API keys (NEVER commit)
logs/               # Log files (NEVER commit)
.checkpoint_*.json  # Checkpoint files (NEVER commit)
```

### ❌ NEVER: Break Folder Structure

```
# ✓ CORRECT:
data/{industry}/research_papers/
data/{industry}/sec_filings/
data/{industry}/_consolidated/

# ✗ WRONG:
data/papers/              # Custom naming breaks system
data/{industry}/docs/     # Non-standard folder
```

### ❌ NEVER: Skip Checkpoints

```python
# ✗ WRONG:
for item in items:
    download(item)  # No checkpoint tracking

# ✓ CORRECT:
checkpoint = CheckpointManager(output_dir, 'source')
for item in items:
    if checkpoint.is_completed(item['id']):
        continue
    download(item)
    checkpoint.mark_completed(item['id'])
checkpoint.finalize()
```

---

## Strategic Context: The C-Level Problem We Solve

### The $1 Trillion Mistake

Between 2010-2023, corporations and VCs invested $1+ trillion in emerging tech at the WRONG time:
- **3D Printing (2013)**: "Manufacturing revolution!" → Stocks crashed 80%
- **Blockchain (2017)**: $20K Bitcoin → Crashed to $3K (85% loss)
- **Metaverse (2021)**: "Virtual future!" → Meta down 70%

**Why it happened**: Single-source bias (only reading press releases, or only watching stock prices).

### Our Solution: Multi-Source Triangulation

14 independent data sources across 4 time horizons reveal the truth:

**Leading Indicators (Predict 12-24mo ahead)**:
- Patents surge 18mo before commercial products
- Research papers validate technology 2 years before adoption
- GitHub activity predicts developer interest 12mo ahead
- Government contracts signal public sector validation

**Coincident Indicators (Current reality)**:
- SEC filings show actual financials (can't lie - fraud charges)
- Stock prices aggregate market expectations
- Insider transactions reveal executive confidence

**Lagging Indicators (Confirm trends)**:
- News volume peaks when market peaks (contrarian signal)

**When layers contradict = ACTIONABLE SIGNAL**:
- Layers 1-3 positive + Layer 4 bearish = **Trough entry point (BUY)**
- Layers 1-3 negative + Layer 4 bullish = **Peak exit point (SELL)**

### Real Example: eVTOL (November 2025)

**Evidence from 634 documents**:
- **Layer 1 (Innovation)**: GitHub 0% active repos despite 4,044 stars → Developers abandoned
- **Layer 2 (Market)**: $274M gov contracts from DoD/NASA → Technology validated
- **Layer 3 (Financial)**: SEC Form 4 shows insider selling at $16-18 → Executives cashing out
- **Layer 4 (Narrative)**: 269 news articles (1.5/day) → High media attention

**Interpretation**: Peak of Inflated Expectations → Entering Trough
**Recommendation**: SELL/TRIM positions, wait for 70-80% decline, re-enter 2026-2027

**Comparable**: Tesla 2017-2019 (same pattern → crashed 50%, then 10x recovery)

---

## Dependencies & Tools

### Core Libraries
- Python 3.8+
- requests, beautifulsoup4, lxml (web scraping)
- pandas, openpyxl (data processing)
- feedparser (RSS feeds)
- yfinance (stock data - FREE)

### External APIs
- **FREE**: SEC EDGAR, USASpending.gov, GDELT, GitHub, OpenAlex, yfinance
- **FREE (Key Required)**: PatentsView, CORE
- **PAID (Optional)**: FMP ($29/month for earnings/fundamentals)

### Testing
- pytest (unit tests)
- pytest-cov (coverage reporting)

### Security
All API keys in `.env` (never committed):
```
FMP_API_KEY=your_key_here
CORE_API_KEY=your_key_here
GITHUB_TOKEN=your_token_here
```

Loaded via `src/utils/config.py`:
```python
from src.utils.config import Config
api_key = Config.FMP_API_KEY
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

## System Status & Roadmap

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