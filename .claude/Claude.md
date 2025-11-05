# Pura Vida Sloth - Strategic Intelligence Harvesting System

## Project Vision

Multi-source intelligence harvesting for **strategic investment timing** in emerging technology markets. This system collects data from 14 independent sources to determine **where an industry sits on the Gartner Hype Cycle** and answer the C-level question: **"Should we invest NOW, or wait?"**

**End Goal**: Gartner-style executive reports with Hype Cycle positioning and BUY/HOLD/SELL recommendations based on multi-layer intelligence triangulation.

---

## The Problem We Solve

### The $1 Trillion Mistake

Between 2010-2023, corporations and VCs invested $1+ trillion in emerging tech at the WRONG time:
- **3D Printing (2013)**: "Manufacturing revolution!" → Stocks crashed 80%
- **Blockchain (2017)**: $20K Bitcoin → Crashed to $3K (85% loss)
- **Metaverse (2021)**: "Virtual future!" → Meta down 70%

**Why it happened**: Single-source bias (only reading press releases, or only watching stock prices).

### Our Solution: Multi-Source Triangulation

14 independent data sources across 4 time horizons reveal the truth. When layers contradict, that's an actionable investment signal.

---

## The 4-Layer Intelligence Framework

The system operates like a strategic radar with four independent layers, each looking at different time horizons:

### LAYER 1: Innovation Signals (Leading 18-24 months)
**Data Sources**: Patents, Research Papers, GitHub Activity, Academic Citations

**Purpose**: Predict which technologies will emerge before commercialization

**Key Insight**: Patent surges happen 18 months before products ship. Research paper volume validates technical feasibility 2 years ahead of adoption.

### LAYER 2: Market Formation (Leading 12-18 months)
**Data Sources**: Government Contracts, Regulatory Filings, Job Postings

**Purpose**: Predict when commercialization begins

**Key Insight**: Government validation (NASA, DoD contracts) signals institutional confidence. Regulatory activity precedes market entry.

### LAYER 3: Financial Reality (Coincident 0-6 months)
**Data Sources**: SEC Filings, Earnings Reports, Stock Prices, Insider Trading, Institutional Holdings

**Purpose**: Measure current valuation vs actual performance

**Key Insight**: SEC filings reveal truth (fraud charges ensure honesty). Insider selling at highs = executives cashing out before decline.

### LAYER 4: Narrative (Lagging indicator)
**Data Sources**: News Sentiment, Press Releases

**Purpose**: Detect hype peaks and contrarian signals

**Key Insight**: News volume peaks when market peaks. High media attention + negative fundamentals = sell signal.

---

## How Contradictions Reveal Investment Opportunities

**The Magic**: When layers disagree, that pinpoints where we are on the Hype Cycle:

### Peak Signal (SELL)
- **Layer 1-2**: Innovation slowing (GitHub inactive, patent decline)
- **Layer 3**: Insiders selling, valuations stretched
- **Layer 4**: News bullish, high media coverage
- **Action**: Exit positions, wait for 70-80% decline

### Trough Signal (BUY)
- **Layer 1-2**: Innovation recovering (patents increasing, gov contracts awarded)
- **Layer 3**: Insiders buying, valuations compressed
- **Layer 4**: News bearish, media quiet
- **Action**: Enter positions, ride recovery to "Slope of Enlightenment"

### Real Example: eVTOL (November 2024)
- **L1**: GitHub repos 0% active (innovation dead)
- **L2**: $274M DoD/NASA contracts (government validation)
- **L3**: Insiders selling at $16-18 (executives exiting)
- **L4**: 269 news articles (1.5/day - high hype)
- **Verdict**: PEAK → entering trough. Sell/trim, re-enter 2026-2027 after 70% decline.

---

## Core Design Principles

### 1. Industry-Agnostic Architecture
**The entire value proposition is industry flexibility.**

Switch from eVTOL to quantum computing, biotech, or AI by changing a JSON config file. Zero code changes required.

**Use Cases**:
- Emerging technologies (eVTOL, quantum computing, fusion energy)
- Regulated industries (biotech, fintech, cannabis)
- Platform shifts (Web3, AI, metaverse)

### 2. Multi-Source Reliability
No single API failure breaks the system. Primary sources fail gracefully to backups (APIs → RSS → web scraping).

### 3. Evidence-Based Decision Making
Every recommendation backed by 400-1,600 source documents. Data provenance tracked for audit trails.

### 4. Executive-Grade Output
Output format mirrors Gartner/McKinsey reports:
- Hype Cycle positioning with confidence intervals
- Investment timing recommendations (BUY/HOLD/SELL)
- Comparable historical examples (e.g., "eVTOL 2024 = Tesla 2018")
- Risk-adjusted return projections

---

## System Architecture (High-Level)

```
INPUT LAYER (Harvest)
└─ 14 data source collectors (configurable)
   └─ Output: 400-1,600 documents per 90-day window

PROCESSING LAYER (Analysis) [NOT YET IMPLEMENTED]
└─ Hype cycle scoring algorithm
└─ Cross-layer contradiction detection
└─ Temporal pattern analysis

OUTPUT LAYER (Reporting) [NOT YET IMPLEMENTED]
└─ Gartner-style executive reports
└─ Hype Cycle visualizations
└─ Magic Quadrant positioning
```

**Current Status**: Input layer complete. Analysis and reporting layers are future work.

---

## What Makes This Different

### vs. Traditional Financial Analysis
- **Traditional**: Looks backward (last quarter's earnings)
- **This System**: Looks forward 12-24 months (patent trends, GitHub activity)

### vs. News/Media Analysis
- **Media**: Lags reality, amplifies hype
- **This System**: Uses news as contrarian indicator (high coverage = potential peak)

### vs. Single-Source Platforms
- **Bloomberg/Morningstar**: Financial data only (Layer 3)
- **This System**: 4 independent layers catch contradictions

### vs. Manual Research
- **Analysts**: Sample 20-50 documents, weeks of work
- **This System**: Processes 1,600 documents in hours, reproducible

---

## Key Success Metrics

- **Coverage**: 14 independent data sources
- **Depth**: 400-1,600 documents per 90-day harvest
- **Accuracy**: <10% data collection failure rate
- **Flexibility**: Works with any industry via config change
- **Reproducibility**: Auditable data provenance

---

## When to Use This System

**Ideal for**:
- Investment timing in emerging tech markets
- Detecting hype cycle peaks before crashes
- Finding trough entry points (buy low opportunities)
- Validating VC/PE thesis before deployment
- Strategic planning for corporate R&D investment

**Not suitable for**:
- Day trading (this is long-term strategic intelligence)
- Mature markets (designed for emerging tech)
- Real-time decisions (harvest cycle is 90 days)

---

**Remember**: This system helps executives avoid $100M+ mistakes by predicting hype cycle position 12-24 months ahead. Multi-source triangulation reveals truth that single-source analysis misses.

**For implementation details, see `.claude/CLAUDE.local.md`**
