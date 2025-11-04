# Pura Vida Sloth - Multi-Source Data Harvesting System

**Industry-agnostic data collection platform for market intelligence and competitive analysis**

A professionally structured Python package for harvesting data from 10+ public sources including SEC filings, research papers, patents, news, and regulatory documents. Built with a clean architecture, comprehensive testing, and production-ready error handling.

---

## 🚀 Quick Start

### 1. Install

```bash
pip install -r requirements.txt
pip install -e .  # Install in development mode
```

### 2. Configure API Keys

```bash
cp .env.template .env
# Edit .env with your API keys
```

See [docs/API_SETUP_GUIDE.md](docs/API_SETUP_GUIDE.md) for registration instructions.

### 3. Run Test System

```bash
python tests/test_system.py
```

### 4. Run Harvest

```bash
python -m src.core.orchestrator --config configs/evtol_config.json
```

---

## 📦 Data Sources (10+)

| Source | Data Type | API/Method | Status |
|--------|-----------|------------|--------|
| **SEC EDGAR** | Corporate filings | SEC API | ✅ Working |
| **Earnings** | Earnings transcripts | FMP API + fallbacks | 🔧 Fixing |
| **Research** | Academic papers | CORE, arXiv, RSS | ✅ Working |
| **Patents** | Patent filings | PatentsView API | ✅ Working |
| **Press Releases** | Company news | RSS + web scraping | 🔧 Fixing |
| **Regulatory** | Federal documents | Federal Register API | 🔧 Fixing |
| **News** | News sentiment | GDELT API | ✅ Working |
| **GitHub** | Repository activity | GitHub API | ✅ Working |
| **Jobs** | Job postings | RSS feeds | ✅ Working |
| **Citations** | Academic citations | OpenAlex API | ✅ Working |

---

## ✨ Key Features

### Industry-Agnostic Design
- **JSON-driven configuration** - Change industry by updating config file
- **Parameterized downloaders** - No hardcoded companies or keywords
- **Works for any industry** - eVTOL, AI chips, biotech, fintech, etc.

### Professional Architecture
- **Clean package structure** - `src/`, `tests/`, `configs/`, `docs/`
- **Proper Python packaging** - Install with `pip install -e .`
- **Individual downloader tests** - Fast TDD workflow (10s vs 5min)
- **Comprehensive documentation** - Organized in `docs/` directory

### Production-Ready Features
- **Checkpoint/Resume** - Automatically resume interrupted downloads
- **Retry logic** - Exponential backoff with rate limit detection
- **Multi-level fallbacks** - Primary → Secondary → Tertiary sources
- **Progress tracking** - Real-time progress bars
- **Comprehensive logging** - Debug, info, warning, error levels
- **Metadata generation** - JSON metadata for all downloads

---

## 📁 Project Structure

```
pura-vida-sloth/
├── src/                    # Source code
│   ├── downloaders/        # 11 data source downloaders
│   ├── core/               # Orchestrator
│   └── utils/              # Utilities (API clients, retry, logging)
├── tests/                  # Test suite
│   ├── test_downloaders/   # Individual downloader tests
│   └── test_system.py      # Integration test
├── configs/                # JSON configurations
│   ├── evtol_config.json  # eVTOL industry example
│   └── schema.json         # Configuration schema
├── data/                   # Downloaded data (gitignored)
│   ├── {industry}/         # Industry-specific data
│   └── tests/              # Test outputs
├── docs/                   # Documentation
├── examples/               # Usage examples
├── setup.py                # Package configuration
└── README.md               # This file
```

---

## 🛠️ Usage

### Python API

```python
from src.core.orchestrator import InitialHarvest
from datetime import datetime, timedelta

# Run harvest
harvest = InitialHarvest(
    config_path='configs/evtol_config.json',
    dry_run=False,
    resume=True
)
harvest.run()
```

### Test Individual Downloader

```python
# Fast individual test (10-60 seconds)
python tests/test_downloaders/test_research_papers.py
python tests/test_downloaders/test_sec_filings.py
```

### Configuration Example

```json
{
  "industry": "evtol",
  "industry_name": "Electric Vertical Takeoff and Landing",
  "companies": {
    "public": {
      "JOBY": "Joby Aviation",
      "ACHR": "Archer Aviation",
      "LILM": "Lilium N.V."
    }
  },
  "keywords": ["eVTOL", "urban air mobility", "VTOL aircraft"],
  "data_sources": {
    "research": {"enabled": true},
    "sec_filings": {"enabled": true},
    "patents": {"enabled": true}
  }
}
```

---

## 📊 Expected Output

For a 90-day harvest window:

| Source | Documents | Format |
|--------|-----------|--------|
| Research Papers | 200-800 | PDF, HTML |
| SEC Filings | 50-200 | HTML |
| Patents | 20-100 | PDF, HTML |
| Press Releases | 50-150 | HTML |
| News Articles | 100-300 | JSON |
| Job Postings | 20-50 | HTML |
| **Total** | **440-1,600** | Mixed |

---

## 🧪 Testing

### Integration Test (All Downloaders)
```bash
python tests/test_system.py
# Runtime: ~5 minutes
# Tests all 10 downloaders
```

### Individual Tests (Fast TDD)
```bash
python tests/test_downloaders/test_research_papers.py
# Runtime: ~10-60 seconds
# Tests one downloader in isolation
```

---

## 📖 Documentation

- [Quick Start Guide](docs/QUICK_START.md) - Detailed setup instructions
- [API Setup Guide](docs/API_SETUP_GUIDE.md) - API key registration
- [Project Overview](docs/PROJECT_OVERVIEW.md) - Architecture and design
- [Testing Guide](docs/testing/TEST_GUIDE.md) - Testing workflows
- [Refactoring History](docs/refactoring/) - Project evolution

---

## ⚙️ Configuration

### Required API Keys
- **CORE_API_KEY** - Research papers (free, 10k/day)
- **GITHUB_TOKEN** - GitHub data (optional but recommended)

### Optional API Keys
- **FMP_API_KEY** - Financial data ($14/month or 250 calls/day free)
- **ALPHA_VANTAGE_KEY** - Market data (500 calls/day free)
- **TAVILY_API_KEY** - Enhanced search (for future features)

### Environment Variables
```bash
# Required
CORE_API_KEY=your_core_api_key

# Optional
GITHUB_TOKEN=your_github_token
FMP_API_KEY=your_fmp_api_key
ALPHA_VANTAGE_KEY=your_alpha_vantage_key
```

---

## 🔧 Current Status

### Completed ✅
- Professional package structure
- 10+ data source downloaders
- Checkpoint/resume capability
- Comprehensive error handling
- Individual test files (TDD-ready)
- Clean documentation structure

### In Progress 🔧
- Fixing remaining broken downloaders (SEC, Earnings, Press, Regulatory)
- Creating new downloaders (EDGAR, Alpha Vantage, Tavily)
- Industry-agnostic parameterization
- Enhanced testing suite

---

## 🤝 Contributing

1. Clone the repository
2. Install in development mode: `pip install -e .`
3. Make changes
4. Run tests: `python tests/test_system.py`
5. Submit pull request

---

## 📝 License

See [LICENSE](LICENSE) file for details.

---

## 📧 Support

- **Documentation**: See `docs/` directory
- **Issues**: Check logs in `data/{source}/{source}.log`
- **Testing**: Run `python tests/test_system.py`

---

**Built with:** Python 3.8+, Requests, BeautifulSoup, tqdm, feedparser
