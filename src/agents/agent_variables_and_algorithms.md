# Agent Variables & Algorithms Reference

**Complete reference for data sources, algorithms, and scoring variables used by each agent in the multi-agent system.**

---

## Quick Reference: Agent Overview

| Agent | Role | Data Sources | Graph Algorithms | Key Output |
|-------|------|--------------|------------------|------------|
| **Agent 1** | Tech Discovery | All doc types (patents, papers, contracts, news, SEC, GitHub) | PageRank, Community Detection, Degree Centrality | Technology list with metadata |
| **Agent 2** | Innovation Scorer | Patents, Research Papers | PageRank (weighted), Citation Analysis, Temporal Trends | `innovation_score` (0-100) |
| **Agent 3** | Adoption Scorer | Gov Contracts, Regulations, SEC Filings, Companies | PageRank (companies), Relationship Strength | `adoption_score` (0-100) |
| **Agent 4** | Narrative Scorer | News Articles, Real-time Web Search | Outlet Tier Hierarchy, Temporal Momentum, Freshness Analysis | `narrative_score` (0-100) |
| **Agent 5** | Risk Scorer | SEC Filings (risk mentions), Insider Trading, Institutional Holdings | Count Aggregations | `risk_score` (0-100) |
| **Agent 6** | Hype Scorer | *(Uses scores from Agents 2-5)* | Standard Deviation, Divergence Analysis | `hype_score` (0-100) |
| **Agent 7** | Phase Detector | *(Uses scores from Agents 2-6)* | Spread Analysis, Rule-based Classification | `hype_cycle_phase` + confidence |
| **Agent 8** | LLM Analyst | *(Uses all prior scores)* | LLM Synthesis | Executive summary + recommendations |
| **Agent 9** | Ensemble | *(Uses all prior scores)* | Weighted Averages, Phase Multipliers | `chart_x`, `chart_y` positioning |
| **Agent 10** | Chart Generator | *(Uses all prior data)* | None (formatting only) | JSON for D3.js visualization |
| **Agent 11** | Evidence Compiler | *(Uses metrics from Agents 2-7)* | None (aggregation only) | Evidence bundle for all scores |
| **Agent 12** | Output Validator | *(Uses all state fields)* | None (validation only) | Validation status + errors |

---

## Detailed Agent Specifications

### Agent 1: Tech Discovery

**File**: `agent_01_tech_discovery/agent.py`

**Purpose**: Enumerate technologies from graph and prepare for downstream scoring

**Data Sources**:
- All Technology nodes in Neo4j
- All document types: `patent`, `technical_paper`, `government_contract`, `regulation`, `sec_filing`, `news`, `github`
- Company relationships (`RELATED_TO_TECH`)

**Graph Algorithms**:
- **PageRank** - Prioritizes important technologies based on document connectivity
- **Community Detection** (v0-v5) - Groups related technologies into clusters
- **Degree Centrality** (implicit) - Measured via total document count per technology

**Variables Calculated**:
| Variable | Formula/Source | Purpose |
|----------|----------------|---------|
| `document_count` | Count of all related documents | Overall activity indicator |
| `doc_type_breakdown` | Count by type (patents, papers, contracts, news, SEC, GitHub) | Source diversity measure |
| `pagerank` | Neo4j PageRank algorithm | Technology importance score |
| `community_id` | Community detection algorithm | Cluster assignment for stratified sampling |
| `quality_score` | Internal LLM-based quality filter | Filters low-quality/spam technologies |

**Usage Logic**:
1. Query all technologies with `quality_score >= 0.75`
2. Classify community maturity using:
   - `patent:news ratio > 2` + `contracts > 5` = Late-stage
   - `patent:news ratio > 1` + `contracts 2-5` = Mid-stage
   - `patent:news ratio < 1` + `contracts 0-2` = Early-stage/Hype
3. Order by: `PageRank DESC → doc_type_diversity DESC → total_docs DESC`
4. Stratified sampling across maturity stages (ensures diverse tech portfolio)

**Output**: List of technologies with metadata for downstream agents

---

### Agent 2: Innovation Scorer (Layer 1: Leading 18-24 months)

**File**: `agent_02_innovation/agent.py`

**Purpose**: Score innovation signals from patents, papers, and GitHub activity

**Data Sources**:
| Document Type | Relationship Role | Time Window |
|---------------|-------------------|-------------|
| `patent` | `invented` | 2 years back |
| `technical_paper` | `invented`, `studied` | 2 years back |
| `github` | *(not yet implemented)* | 2 years back |

**Graph Algorithms**:
- **PageRank (weighted)** - Weights patents by importance (foundational vs incremental)
- **Citation Count** - Quality indicator for patents and papers
- **Community Detection** - Contextualizes activity within innovation cluster
- **Temporal Trend Analysis** - Compares recent (6 months) vs historical rates

**Variables Calculated**:
| Variable | Formula | Purpose |
|----------|---------|---------|
| `innovation_score` | LLM-calculated (0-100) | Final score |
| `patent_count_2yr` | `COUNT(patents)` | Raw volume indicator |
| `patent_pagerank_weighted` | `SUM(1.0 + pagerank*100)` | Weighted patent importance |
| `avg_patent_pagerank` | `patent_pagerank_weighted / patent_count` | Average patent quality |
| `patent_citations` | `SUM(citation_count)` | Total citations received |
| `paper_count_2yr` | `COUNT(papers)` | Raw paper volume |
| `paper_citations` | `SUM(paper.citations)` | Total paper citations |
| `community_patent_count` | Count in same cluster | Contextual benchmark |
| `temporal_trend` | "growing"/"stable"/"declining" | Activity momentum |

**Usage Logic** (LLM-based scoring):
```
IF patent_pagerank_weighted > 150 AND patent_count > 30:
    Score 70-90 (High innovation)
ELSE IF patent_count < 5 AND paper_count < 15:
    Score 0-30 (Minimal innovation)
ELSE:
    Score 30-70 (Moderate, consider citations + temporal trend)
```

**Key Insight**: PageRank weighting prioritizes foundational patents over incremental ones. A tech with 10 high-PageRank patents can outscore one with 50 low-PageRank patents.

**Output**: `innovation_score`, detailed metrics, reasoning

---

### Agent 3: Adoption Scorer (Layer 2: Leading 12-18 months)

**File**: `agent_03_adoption/agent.py`

**Purpose**: Score commercial adoption signals from contracts, regulations, and revenue

**Data Sources**:
| Document Type | Relationship Role | Time Window |
|---------------|-------------------|-------------|
| `government_contract` | `deployed`, `funded`, `researched` | 1 year back |
| `regulation` | `regulated` | 1 year back |
| `sec_filing` | Evidence contains "revenue"/"sales" | 1 year back |
| Company nodes | `RELATED_TO_TECH` relationships | All time |

**Graph Algorithms**:
- **PageRank (companies)** - Prioritizes established companies over startups
- **Relationship Strength** - Uses `evidence_confidence` scores from extraction
- None (primarily count aggregations)

**Variables Calculated**:
| Variable | Formula | Purpose |
|----------|---------|---------|
| `adoption_score` | LLM-calculated (0-100) | Final score |
| `gov_contract_count_1yr` | `COUNT(contracts)` | Deployment activity |
| `gov_contract_total_value` | `SUM(contract.value_usd)` | Market size indicator |
| `gov_contract_avg_value` | `total_value / count` | Deal quality (avg > $1M = serious) |
| `regulatory_approval_count` | `COUNT(regulations)` | FAA/FDA/EPA certifications |
| `companies_developing` | `COUNT(DISTINCT companies)` | Ecosystem breadth |
| `top_companies` | Order by `company.pagerank DESC` | Key players list |
| `revenue_mentions` | SEC filings with "revenue" in evidence | Commercial traction |

**Usage Logic** (LLM-based scoring):
```
IF gov_contracts >= 20 AND regulatory_approvals >= 5 AND companies > 30:
    Score 60-80 (High adoption)
ELSE IF gov_contracts < 3 AND regulatory_approvals <= 1:
    Score 0-30 (Pre-commercial)
ELSE:
    Score 30-60 (Early-to-moderate, weight contract values heavily)
```

**Key Insight**: Government validation precedes private-sector adoption by 12-18 months. High-value contracts ($5M+) signal serious deployment readiness.

**Output**: `adoption_score`, detailed metrics, reasoning

---

### Agent 4: Narrative Scorer (Layer 4: Lagging Indicator)

**File**: `agent_04_narrative/agent.py`

**Purpose**: Score media narrative signals and detect hype saturation

**Data Sources**:
| Data Source | Type | Time Window |
|-------------|------|-------------|
| Neo4j News Articles | `doc_type='news'`, `role='subject'` | 6 months back |
| Tavily Web Search | Real-time search API | Last 30 days |
| Outlet Classification | Industry Authority / Financial Authority / Mainstream / Other | All time |

**Graph Algorithms**:
- **Outlet Tier Hierarchy** - Prioritizes Industry Authority > Financial > Mainstream
- **Temporal Momentum** - Compares last 30 days vs previous 30 days
- **Freshness Score** - `recent_count / (historical_count + recent_count)`

**Variables Calculated**:
| Variable | Formula | Purpose |
|----------|---------|---------|
| `narrative_score` | LLM-calculated (0-100) | Final score |
| `news_count_3mo` | `COUNT(news articles from graph)` | Historical coverage |
| `tier1_count` | Industry Authority outlets | Highest credibility |
| `tier2_count` | Financial Authority outlets | Investment-focused |
| `tier3_count` | Mainstream outlets | Public awareness |
| `avg_sentiment` | Currently 0.0 (not implemented) | Sentiment analysis |
| `sentiment_trend` | "positive"/"neutral"/"negative" | Directional sentiment |
| `freshness_score` | `tavily_count / (news_count_3mo + tavily_count)` | **CRITICAL METRIC** |
| `tavily_relevant_count` | LLM-filtered relevant results | Real-time activity |
| `tavily_relevance_ratio` | `relevant / total_results` | Search precision |

**Usage Logic** (LLM-based with freshness adjustments):
```
Base Score Calculation:
IF news_count > 120 AND tier1_count > 10:
    Base = 70-90 (Media saturation)
ELSE IF news_count < 10:
    Base = 0-25 (Minimal coverage)

Freshness Adjustments:
IF freshness_score > 3.0:
    Final = Base + 30 (SPIKING - Peak hype signal!)
ELSE IF freshness_score > 1.5:
    Final = Base + 15 (Accelerating coverage)
ELSE IF freshness_score < 0.5:
    Final = Base - 20 (Declining narrative - bearish)
```

**Key Insight**: Freshness score is a **contrarian indicator**. `freshness > 3.0` signals narrative peak, often coinciding with valuation peak (sell signal). `freshness < 0.5` signals narrative trough (potential buy signal).

**Output**: `narrative_score`, detailed metrics, reasoning

---

### Agent 5: Risk Scorer (Layer 3: Coincident 0-6 months)

**File**: `agent_05_risk/agent.py`

**Purpose**: Score financial risk signals from SEC filings and insider activity

**Data Sources**:
| Data Source | Type | Time Window |
|-------------|------|-------------|
| SEC Filings (Neo4j) | `doc_type='sec_filing'` with risk keywords | 6 months back |
| Insider Trading (DuckDB) | Forms 3/4/5 - buy/sell transactions | 6 months back |
| Institutional Holdings (DuckDB) | Form 13F - ownership percentages | Latest quarter |

**Graph Algorithms**:
- None (uses count aggregations from Neo4j)
- References external DuckDB for detailed financial analytics

**Variables Calculated**:
| Variable | Formula | Purpose |
|----------|---------|---------|
| `risk_score` | LLM-calculated (0-100) | Final score |
| `sec_risk_mentions_6mo` | `COUNT(risk disclosures)` | Regulatory concerns |
| `institutional_holdings_pct` | `SUM(holdings) / float` | Smart money confidence |
| `insider_buy_count` | `COUNT(buy transactions)` | Management confidence |
| `insider_sell_count` | `COUNT(sell transactions)` | Exit signals |
| `insider_net_position` | "buying"/"neutral"/"selling" | Directional signal |

**Usage Logic** (LLM-based scoring):
```
IF sec_risk_mentions > 40 AND insider_sell_count > insider_buy_count*3:
    Score 70-90 (High risk - executives exiting)
ELSE IF sec_risk_mentions < 5 AND institutional_holdings > 35%:
    Score 0-25 (Low risk - strong fundamentals)
ELSE:
    Score 30-60 (Moderate risk)

Anchor: Score 50 = ~15-20 SEC mentions, ~15% holdings, balanced insider activity
```

**Key Insight**: Insider selling at narrative peaks (when Agent 4 scores > 70) is a strong sell signal. Insider buying during narrative troughs is a strong buy signal.

**Output**: `risk_score`, detailed metrics, reasoning

---

### Agent 6: Hype Scorer

**File**: `agent_06_hype/agent.py`

**Purpose**: Calculate hype from layer score divergence

**Data Sources**:
- Uses scores from Agents 2, 3, 4, 5 (no direct graph queries)

**Graph Algorithms**:
- **Standard Deviation** - Measures divergence across 4 layer scores
- **Narrative Premium** - How much narrative exceeds average
- **Substance Deficit** - Gap between narrative and fundamentals

**Variables Calculated**:
| Variable | Formula | Purpose |
|----------|---------|---------|
| `hype_score` | Rule-based (0-100) | Final score |
| `layer_divergence` | `STDEV(innovation, adoption, narrative, risk)` | Score spread |
| `narrative_premium` | `narrative - AVG(all 4 scores)` | Narrative excess |
| `substance_deficit` | `AVG(all) - AVG(innovation, adoption)` | Fundamentals gap |
| `avg_score` | `(innovation + adoption + narrative + (100-risk)) / 4` | Overall average |

**Usage Logic** (Rule-based):
```python
# High Hype Condition
IF narrative > 60 AND (innovation < 40 OR adoption < 40):
    hype_score = min(100, 50 + narrative_premium*2 + substance_deficit*1.5)
    # Example: narrative=80, innovation=30, adoption=35
    # → narrative_premium = 80-48.75 = 31.25
    # → substance_deficit = 48.75-32.5 = 16.25
    # → hype = 50 + 31.25*2 + 16.25*1.5 = 136.875 → capped at 100

# Low Hype Condition
ELSE IF layer_divergence < 15:
    hype_score = max(0, 50 - divergence*2)
    # Example: divergence=10 → hype = 30

# Moderate Hype
ELSE:
    hype_score = 50 + (divergence - 15)*1.5
    # Example: divergence=25 → hype = 65
```

**Confidence Calculation**:
```python
IF layer_divergence > 20 OR abs(narrative - innovation) > 30:
    confidence = "high"
ELSE:
    confidence = "medium"
```

**Key Insight**: Hype is **divergence**, not absolute values. A tech with all scores at 70 has LOW hype (aligned). A tech with narrative=80, innovation=20 has EXTREME hype (misaligned).

**Output**: `hype_score`, divergence metrics, confidence

---

### Agent 7: Phase Detector

**File**: `agent_07_phase/agent.py`

**Purpose**: Determine hype cycle phase position

**Data Sources**:
- Uses scores from Agents 2, 3, 4, 5, 6 (no direct graph queries)

**Graph Algorithms**:
- **Spread Analysis** - `max(scores) - min(scores)` determines confidence
- **Rule-based Classification** - Threshold-based phase assignment

**Variables Calculated**:
| Variable | Values | Purpose |
|----------|--------|---------|
| `hype_cycle_phase` | "innovation_trigger" / "peak" / "trough" / "slope" / "plateau" | Phase code |
| `phase_reasoning` | Free text | Explanation |
| `phase_confidence` | 0.0 - 1.0 | Confidence score |

**Phase Detection Logic** (Rule-based, recalibrated v7):

| Phase | Conditions | Reasoning |
|-------|------------|-----------|
| **Innovation Trigger** | `innovation > 20` AND `adoption < 25` AND `narrative < 45` | Early innovation, minimal commercialization, low media |
| **Peak** | `narrative > 45` AND `hype > 40` AND `adoption < 25` | High media, high divergence, still pre-commercial |
| **Plateau** | `adoption >= 10` AND `innovation >= 5` AND `narrative <= 45` AND `risk <= 20` | Stable fundamentals, moderate adoption, low hype |
| **Slope** | `adoption > 20` AND `innovation > 12` AND `narrative > 20` AND `hype < 50` | Growing adoption, ongoing innovation, aligned narrative |
| **Trough (Tier 1)** | `innovation < 5` AND `adoption < 5` AND `narrative < 20` | Dead/abandoned technology |
| **Trough (Tier 2)** | 3+ metrics below thresholds: `narrative < 35`, `adoption < 18`, `innovation < 18`, `hype < 28` | Underperforming, disillusionment |
| **Default** | None of above | Slope (mixed signals) |

**Confidence Calculation**:
```python
spread = max(innovation, adoption, narrative) - min(innovation, adoption, narrative)

IF spread > 30:
    confidence = 0.85  # High confidence (clear divergence)
ELSE IF spread > 15:
    confidence = 0.65  # Medium confidence
ELSE:
    confidence = 0.45  # Low confidence (scores aligned = ambiguous phase)
```

**Key Insight**: Phase is determined by **score patterns**, not absolute values. A tech with innovation=60, adoption=10, narrative=70 is at **Peak** (not Slope) due to high narrative + low adoption.

**Output**: `hype_cycle_phase`, reasoning, confidence

---

### Agent 8: LLM Analyst

**File**: `agent_08_analyst/agent.py`

**Purpose**: Generate executive narrative summary

**Data Sources**:
- All scores from Agents 2-7 (no direct graph queries)

**Graph Algorithms**:
- None (LLM synthesis using GPT-4o-mini)

**Variables Used**:
| Input Variable | Source | Purpose |
|----------------|--------|---------|
| `innovation_score` | Agent 2 | Layer 1 fundamentals |
| `adoption_score` | Agent 3 | Layer 2 commercialization |
| `narrative_score` | Agent 4 | Layer 4 media attention |
| `risk_score` | Agent 5 | Layer 3 financial risk |
| `hype_score` | Agent 6 | Divergence signal |
| `hype_cycle_phase` | Agent 7 | Lifecycle position |
| `layer_divergence` | Agent 6 | Score spread metric |

**Output Variables**:
| Variable | Format | Purpose |
|----------|--------|---------|
| `executive_summary` | 3-4 sentences | High-level overview for C-suite |
| `key_insight` | 1 sentence | Single most important takeaway |
| `recommendation` | "invest" / "monitor" / "avoid" / "caution" | Strategic action |

**Usage Logic**:
```
LLM Prompt Template:
"You are a strategic technology analyst. Synthesize the following scores into executive guidance:
- Innovation: {score} (Layer 1)
- Adoption: {score} (Layer 2)
- Narrative: {score} (Layer 4)
- Risk: {score} (Layer 3)
- Hype: {score} (Divergence)
- Phase: {phase} (Lifecycle)

Provide:
1. Executive Summary (3-4 sentences, focus on 'so what')
2. Key Insight (single most important point)
3. Recommendation (invest/monitor/avoid)

Be direct. Avoid jargon. Focus on capital deployment implications."
```

**Output**: Executive summary, key insight, recommendation

---

### Agent 9: Ensemble

**File**: `agent_09_ensemble/agent.py`

**Purpose**: Calculate chart positioning per hype cycle specification

**Data Sources**:
- All scores from Agents 2-7 (no direct graph queries)

**Graph Algorithms**:
- **Weighted Average** - Combines layer scores with predefined weights
- **Phase Multipliers** - Adjusts Y-axis based on phase

**Variables Calculated**:
| Variable | Range | Purpose |
|----------|-------|---------|
| `chart_x` | 0.0 - 5.0 | Maturity axis (left to right) |
| `chart_y` | 0 - 100 | Expectations/visibility axis (bottom to top) |
| `phase_position` | "early" / "mid" / "late" | Position within phase |
| `weighted_score` | 0 - 100 | Overall weighted score |

**Chart X Logic** (Maturity by Phase):
| Phase | X Range | Position Calculation |
|-------|---------|---------------------|
| Innovation Trigger | 0.0 - 0.7 | `0.0 + (innovation/100)*0.7` |
| Peak | 0.7 - 1.4 | `0.7 + (hype/100)*0.7` |
| Trough | 1.4 - 2.7 | `1.4 + min(1.3, narrative_drop*0.01)` |
| Slope | 2.7 - 4.2 | `2.7 + (adoption/100)*1.5` |
| Plateau | 4.2 - 5.0 | `4.2 + min(0.8, adoption/100)` |

**Chart Y Logic** (Expectations/Visibility):
```python
# Base calculation
base_y = narrative*0.7 + innovation*0.2 + adoption*0.1

# Phase multipliers
multipliers = {
    "innovation_trigger": 0.8,   # Lower expectations
    "peak": 1.3,                  # Inflated expectations
    "trough": 0.5,                # Crashed expectations
    "slope": 0.9,                 # Recovering expectations
    "plateau": 0.85               # Stable expectations
}

chart_y = base_y * multipliers[phase]
```

**Weighted Score Formula**:
```python
from constants import LAYER_WEIGHTS

weighted_score = (
    innovation * LAYER_WEIGHTS['innovation'] +
    adoption * LAYER_WEIGHTS['adoption'] +
    narrative * LAYER_WEIGHTS['narrative'] +
    (100 - risk) * LAYER_WEIGHTS['risk']
)
```

**Key Insight**: Chart positioning reflects BOTH phase (X-axis) and visibility (Y-axis). Technologies can have same phase but different Y positions based on media attention.

**Output**: `chart_x`, `chart_y`, `phase_position`, `weighted_score`

---

### Agent 10: Chart Generator

**File**: `agent_10_chart/agent.py`

**Purpose**: Format data for D3.js visualization

**Data Sources**:
- All scores, metadata, and positioning from Agents 1-9

**Graph Algorithms**:
- None (pure data formatting and aggregation)

**Variables Used**:
| Input Variable | Source | Purpose |
|----------------|--------|---------|
| All scores | Agents 2-6 | Data layer |
| All positioning | Agent 9 | Visual layer |
| Phase + confidence | Agent 7 | Classification layer |
| Summary + insight | Agent 8 | Narrative layer |
| Document counts | Agent 1 | Evidence layer |

**Output Format** (per HYPE_CYCLE.md spec):
```json
{
  "technologies": [
    {
      "id": "tech_slug",
      "name": "Display Name",
      "domain": "Industry",
      "phase": {
        "code": "peak",
        "position": "mid",
        "confidence": 0.85
      },
      "scores": {
        "innovation": 75,
        "adoption": 30,
        "narrative": 85,
        "risk": 60,
        "hype": 80,
        "overall_weighted": 62.5
      },
      "position": {
        "x": 1.1,
        "y": 78.5
      },
      "summary": "...",
      "key_insight": "...",
      "evidence_counts": {...}
    }
  ],
  "metadata": {
    "phase_distribution": {...}
  }
}
```

**Output**: JSON formatted for React + D3.js consumption

---

### Agent 11: Evidence Compiler

**File**: `agent_11_evidence/agent.py`

**Purpose**: Collect supporting evidence for all scores

**Data Sources**:
- Metrics and reasoning from Agents 2, 3, 4, 5, 6, 7

**Graph Algorithms**:
- None (pure aggregation)

**Output Structure**:
```json
{
  "innovation_evidence": {
    "metrics": {
      "patent_count_2yr": 45,
      "patent_pagerank_weighted": 187.5,
      "paper_count_2yr": 23,
      "temporal_trend": "growing"
    },
    "reasoning": "High PageRank-weighted patent activity..."
  },
  "adoption_evidence": {
    "metrics": {...},
    "reasoning": "..."
  },
  "narrative_evidence": {
    "metrics": {...},
    "reasoning": "..."
  },
  "risk_evidence": {
    "metrics": {...},
    "reasoning": "..."
  },
  "hype_analysis": {
    "score": 78,
    "reasoning": "...",
    "layer_divergence": 32.5,
    "narrative_premium": 28.3
  },
  "phase_analysis": {
    "phase": "peak",
    "reasoning": "..."
  }
}
```

**Output**: Evidence bundle for all scores (used by frontend for drill-down)

---

### Agent 12: Output Validator

**File**: `agent_12_validator/agent.py`

**Purpose**: Validate final output against specification

**Data Sources**:
- All state fields from LangGraph pipeline

**Validation Rules**:
| Check | Condition | Error Message |
|-------|-----------|---------------|
| Required fields | All fields present | "Missing required field: {field}" |
| Score ranges | 0 <= score <= 100 | "Score out of range: {field}={value}" |
| chart_x range | 0.0 <= x <= 5.0 | "chart_x out of range: {value}" |
| chart_x/phase alignment | X matches phase range | "chart_x {value} incompatible with phase {phase}" |
| phase_position | "early"/"mid"/"late" | "Invalid phase_position: {value}" |
| phase_confidence | 0.0 <= conf <= 1.0 | "phase_confidence out of range: {value}" |
| Phase code | Valid phase string | "Invalid phase code: {value}" |

**Output**: `validation_status` ("pass"/"fail"), `validation_errors` (list)

---

## Cross-Reference Tables

### Graph Algorithms by Agent

| Algorithm | Agent 1 | Agent 2 | Agent 3 | Agent 4 | Agent 5 | Agent 6 | Agent 7 | Agents 8-12 |
|-----------|---------|---------|---------|---------|---------|---------|---------|-------------|
| **PageRank** | ✓ (tech) | ✓ (patents) | ✓ (companies) | - | - | - | - | - |
| **Community Detection** | ✓ | ✓ | - | - | - | - | - | - |
| **Citation Analysis** | - | ✓ | - | - | - | - | - | - |
| **Degree Centrality** | ✓ (implicit) | - | - | - | - | - | - | - |
| **Temporal Trends** | - | ✓ | - | ✓ | - | - | - | - |
| **Standard Deviation** | - | - | - | - | - | ✓ | - | - |
| **Spread Analysis** | - | - | - | - | - | - | ✓ | - |
| **Weighted Average** | - | - | - | - | - | - | - | Agent 9 |
| **LLM Synthesis** | - | ✓ | ✓ | ✓ | ✓ | - | - | Agent 8 |

### Data Sources by Intelligence Layer

| Intelligence Layer | Document Types | Agent(s) | Leading/Lagging | Time Window |
|-------------------|----------------|----------|-----------------|-------------|
| **Layer 1: Innovation** | Patents, Research Papers, GitHub | Agent 2 | Leading 18-24 months | 2 years |
| **Layer 2: Market Formation** | Gov Contracts, Regulations, SEC Revenue | Agent 3 | Leading 12-18 months | 1 year |
| **Layer 3: Financial Reality** | SEC Risk Filings, Insider Trading, Holdings | Agent 5 | Coincident 0-6 months | 6 months |
| **Layer 4: Narrative** | News Articles, Real-time Web Search | Agent 4 | Lagging indicator | 6 months + 30 days |

### Variable Dependencies (Agent Pipeline Flow)

```
Agent 1 (Discovery)
  ↓ technology_id, document_counts
Agent 2 (Innovation) ──┐
  ↓ innovation_score   │
Agent 3 (Adoption) ────┤
  ↓ adoption_score     │
Agent 4 (Narrative) ───┤→ Agent 6 (Hype) ──┐
  ↓ narrative_score    │   ↓ hype_score    │
Agent 5 (Risk) ────────┘                    ├→ Agent 7 (Phase) ──┐
  ↓ risk_score                              │   ↓ phase, conf    │
                                            │                     │
                                            └───────────────────→ Agent 8 (Analyst)
                                                ↓ summary, insight, recommendation
                                                ↓
                                            Agent 9 (Ensemble) ──→ Agent 10 (Chart)
                                                ↓ chart_x, y         ↓ JSON output
                                                ↓                     ↓
                                            Agent 11 (Evidence) ←─────┘
                                                ↓ evidence_bundle
                                                ↓
                                            Agent 12 (Validator)
                                                ↓ validation_status
```

### Key Metrics Summary

| Metric Category | Key Variables | Formula/Source | Used By |
|----------------|---------------|----------------|---------|
| **Innovation** | `patent_pagerank_weighted` | `SUM(1.0 + pagerank*100)` | Agent 2 |
| | `temporal_trend` | Recent vs historical rates | Agent 2 |
| **Adoption** | `gov_contract_total_value` | `SUM(contract.value_usd)` | Agent 3 |
| | `companies_developing` | `COUNT(DISTINCT companies)` | Agent 3 |
| **Narrative** | `freshness_score` | `recent / (historical + recent)` | Agent 4 |
| | `tier1_count` | Industry Authority outlets | Agent 4 |
| **Risk** | `insider_net_position` | Buy vs sell ratio | Agent 5 |
| | `sec_risk_mentions_6mo` | Count of risk disclosures | Agent 5 |
| **Hype** | `layer_divergence` | `STDEV(4 layer scores)` | Agent 6 |
| | `narrative_premium` | `narrative - avg_score` | Agent 6 |
| **Phase** | `hype_cycle_phase` | Rule-based classification | Agent 7 |
| | `phase_confidence` | Spread-based (0.0-1.0) | Agent 7 |
| **Positioning** | `chart_x` | Phase-based (0.0-5.0) | Agent 9 |
| | `chart_y` | Weighted visibility | Agent 9 |

---

## Usage Examples

### Example 1: High Hype Detection

**Input Scores**:
- Innovation: 35
- Adoption: 25
- Narrative: 85
- Risk: 45

**Agent 6 Calculation**:
```python
avg_score = (35 + 25 + 85 + 55) / 4 = 50
narrative_premium = 85 - 50 = 35
substance_deficit = 50 - (35+25)/2 = 20
layer_divergence = STDEV(35, 25, 85, 55) ≈ 25.8

# High Hype Condition (narrative > 60 AND innovation < 40)
hype_score = min(100, 50 + 35*2 + 20*1.5)
            = min(100, 50 + 70 + 30)
            = 100 (capped)
```

**Agent 7 Phase Detection**:
```python
# Checks: narrative=85 > 45 ✓, hype=100 > 40 ✓, adoption=25 < 25 ✓
→ Phase = "peak"
→ Confidence = 0.85 (spread=60 > 30)
```

**Interpretation**: **Peak of Inflated Expectations** - High media attention with weak fundamentals signals maximum hype risk.

---

### Example 2: Slope of Enlightenment

**Input Scores**:
- Innovation: 55
- Adoption: 45
- Narrative: 50
- Risk: 35

**Agent 6 Calculation**:
```python
avg_score = (55 + 45 + 50 + 65) / 4 = 53.75
layer_divergence = STDEV(55, 45, 50, 65) ≈ 8.5

# Low Hype Condition (divergence < 15)
hype_score = max(0, 50 - 8.5*2) = 33
```

**Agent 7 Phase Detection**:
```python
# Checks: adoption=45 > 20 ✓, innovation=55 > 12 ✓, narrative=50 > 20 ✓, hype=33 < 50 ✓
→ Phase = "slope"
→ Confidence = 0.45 (spread=20 < 30, low divergence)
```

**Interpretation**: **Slope of Enlightenment** - Aligned fundamentals with moderate adoption signals healthy growth phase.

---

## Critical Insights

### Why PageRank Matters

**Traditional Approach**: Count patents
- Tech A: 50 patents (40 incremental, 10 foundational) → Score 50
- Tech B: 30 patents (25 foundational, 5 incremental) → Score 30

**PageRank-Weighted Approach**: Weight by importance
- Tech A: `patent_pagerank_weighted = 40*(1.0 + 0.02*100) + 10*(1.0 + 0.15*100) = 256`
- Tech B: `patent_pagerank_weighted = 25*(1.0 + 0.18*100) + 5*(1.0 + 0.03*100) = 488.5`

**Result**: Tech B scores higher despite fewer patents (quality > quantity)

### Why Freshness Score is Critical

**Scenario**: Tech has 200 historical news articles (past 6 months)

- **Case 1**: Tavily finds 5 articles (last 30 days)
  - `freshness = 5 / (200 + 5) = 0.024` (**Declining narrative**)
  - Agent 4 reduces score by ~20 points (media moving on)

- **Case 2**: Tavily finds 100 articles (last 30 days)
  - `freshness = 100 / (200 + 100) = 0.33` (**Stable narrative**)
  - No adjustment

- **Case 3**: Tavily finds 800 articles (last 30 days)
  - `freshness = 800 / (200 + 800) = 0.80` (**Spiking narrative**)
  - Agent 4 increases score by ~30 points (**PEAK SIGNAL**)

**Insight**: Freshness > 0.8 + narrative > 70 = **Media saturation peak** (often coincides with price peak)

### Why Hype is Divergence, Not Absolute Value

**Low Hype Example**:
- All scores near 70 → divergence = 5 → hype = 40 (aligned)

**High Hype Example**:
- Innovation=20, narrative=80 → divergence = 60 → hype = 92 (misaligned)

**Insight**: Investors should **avoid** high-hype peaks and **buy** low-hype troughs with strong fundamentals.

---

**Last Updated**: 2025-11-14
**Maintainer**: Pura Vida Sloth Development Team
