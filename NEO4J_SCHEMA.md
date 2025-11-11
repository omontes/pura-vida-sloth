# KNOWLEDGE GRAPH SCHEMA v2.0
**Last updated:** 2025-11-07
**Status:** COMPLETE AND OPTIMIZED ✅
**Architecture:** Pure GraphRAG Storage (Zero Computed Fields)

---

## ⚠️ CRITICAL ARCHITECTURAL PRINCIPLE

> **"Pure Storage Design: Neo4j Aura contains ZERO derived scores, only raw data + relationships"**
>
> — From README.md Architecture section

**What this means:**
- **Neo4j**: Stores ONLY LLM extraction output (entities, mentions, relations)
- **LangGraph Agents**: Compute ALL scores on-demand by querying the graph
- **No aggregation**: Each document creates separate records (agents aggregate via Cypher)
- **No scoring**: innovation_score, adoption_score, etc. are computed by agents, NOT stored

**Key Principle:** Graph = Dumb Storage | Agents = Smart Computers

---

## TABLE OF CONTENTS

1. [Nodes](#nodes)
2. [Relationships](#relationships)
   - [Entity Mentions](#entity-mentions-technologycompany-mentioned_in-document)
   - [Entity Relations](#entity-relations-aggregated-cross-document)
3. [Document Extraction Format](#document-extraction-format)
4. [Role Definitions Reference](#role-definitions-reference)
5. [Relation Type Reference](#relation-type-reference)
6. [Agent Computation Layer](#agent-computation-layer)
7. [Query Examples](#query-examples-for-agents)
8. [Migration Guide v1.1 → v2.0](#migration-guide-v11--v20)

---

## NODES

### 1. (:Technology)

```cypher
// ============ IDENTITY ============
id: string                    // "evtol", "hydrogen_aviation"
name: string                  // "eVTOL air taxis"
domain: string                // "Aviation", "Energy", "Biotech"
description: string?          // LLM-generated: "Electric vertical takeoff and landing aircraft"
aliases: [string]?            // ["electric VTOL", "urban air mobility", "flying taxis"]

// ============ METADATA ============
updated_at: datetime          // Last update timestamp
```

**Total: 6 fields** ✅

**What's NOT here:**
- ❌ NO `innovation_score`, `adoption_score`, `narrative_score`, `risk_score`, `hype_score`
- ❌ NO `hype_phase`, `llm_phase`, `ensemble_phase`
- ❌ NO computed fields of any kind

**Why:** All scores are computed by LangGraph agents querying the graph, never stored.

**Implementation notes:**
- `description`: Filled with simple LLM prompt: "In 1-2 sentences, describe what {name} is in the context of {domain}"
- `aliases`: Used for entity linking during ingestion and GraphRAG semantic search

---

### 2. (:Company)

```cypher
// ============ IDENTITY ============
id: string                    // "joby", "archer", "toyota"
name: string                  // "Joby Aviation"
aliases: [string]?            // ["Joby", "JOBY", "Joby Aero Inc"]
ticker: string?               // "JOBY"
kind: string?                 // "startup" | "incumbent" | "investor" | "operator" | "oem"
sector: string?               // "Aerospace", "Automotive", "Energy"
country: string?              // "US", "JP", "CN"
description: string?          // LLM-generated: "Electric aircraft manufacturer"

// ============ METADATA ============
updated_at: datetime
```

**Total: 9 fields** ✅

**What's NOT here:**
- ❌ NO financial metrics
- ❌ NO computed scores

**Why:** Company-level analysis is done by agents querying related documents/relations.

---

### 3. (:Document)

#### Common Fields (all doc_type)

```cypher
// ============ IDENTITY ============
doc_id: string                 // "patent_US1234567" | "news_ft_20250512"
doc_type: string              // "patent" | "technical_paper" | "news" | "sec_filing" |
                              // "regulation" | "github" | "government_contract"
source: string                // "USPTO" | "Financial Times" | "SEC" | "FAA"
title: string
url: string?                  // Link to original document
published_at: datetime?       // Publication date (CRITICAL for agent temporal queries)

// ============ CONTENT ============
summary: string?               // LLM-generated summary (200-500 chars)
content: string?               // Content of the document, example Abstract, Document Info ...
quality_score: float          // 0.85-1 relevant to the industry
relevance_score: float?       // 0-1 (relevance to the relations )


// ============ EMBEDDINGS ============
embedding: vector?            // 768-dim for semantic search
```

**Total: 10 common fields** ✅

---

#### Specific Fields by doc_type

### ✅ doc_type = "patent"

```cypher
// ============ IDENTIFIERS ============
patent_number: string         // "US11234567B2"
jurisdiction: string          // "US" | "WO" | "EP" | "CN" | "JP"

// ============ STATUS ============
type: string                  // "application" | "granted"
legal_status: string          // "pending" | "granted" | "expired" | "abandoned"

// ============ DATES ============
filing_date: datetime
grant_date: datetime?

// ============ OWNERSHIP ============
assignee_name: string         // "Joby Aero Inc."

// ============ METRICS (FOR AGENT SCORING) ============
citation_count: int           // Cited by other patents (agents use for innovation_score)
simple_family_size: int       // Patent family size (agents use for IP portfolio strength)
```

**Total: 10 fields** ✅

---

### ✅ doc_type = "technical_paper"

```cypher
// ============ IDENTIFIERS ============
doi: string?                  // "10.1234/example.2025.12345"

// ============ VENUE ============
venue_type: string?           // "journal" | "conference" | "preprint"
peer_reviewed: boolean?       // true/false
source_title: string?         // "Nature Energy" | "AIAA Aviation Conference"

// ============ DATES ============
year_published: int?          // 2025
date_published: datetime?     // 2025-05-12

// ============ METRICS (FOR AGENT SCORING) ============
citation_count: int?          // Cited by other papers
patent_citations_count: int?  // Cited by patents (tech transfer signal)
```

**Total: 9 fields** ✅

---

### ✅ doc_type = "sec_filing"

```cypher
// ============ COMMON ============
filing_type: string           // "Form-4" | "13F" | "10-K" | "10-Q" | "8-K"
cik: string                   // "0001234567"
accession_number: string      // "0001234567-25-000123"
filing_date: datetime

// ============ FISCAL (10-K, 10-Q) ============
fiscal_year: int?             // 2024
fiscal_quarter: string?       // "Q1" | "Q2" | "Q3" | "Q4"

// ============ FINANCIAL DATA (FOR AGENT SCORING) ============
revenue_mentioned: boolean?   // Is tech revenue mentioned? (agents use for adoption_score)
revenue_amount: float?        // USD (if disclosed)
risk_factor_mentioned: boolean?    // In Risk Factors section? (agents use for risk_score)

// ============ INSIDER TRANSACTIONS (Form-4) ============
net_insider_value_usd: float? // Positive=purchases, Negative=sales (agents use for risk_score)

// ============ INSTITUTIONAL HOLDINGS (13F) ============
total_shares_held: int?       // Total institutional shares
qoq_change_pct: float?        // % change quarter-over-quarter
```

**Total: 13 fields** ✅

---

### ✅ doc_type = "regulation"

```cypher
// ============ AGENCY ============
regulatory_body: string       // "FAA" | "FDA" | "EPA" | "SEC"
sub_agency: string?           // "Office of Airspace Operations"

// ============ DOCUMENT TYPE ============
document_type: string         // "notice" | "proposed_rule" | "final_rule" | "guidance"

// ============ DECISION ============
decision_type: string         // "approval" | "denial" | "proposal" | "certification_requirement"

// ============ TIMELINE ============
effective_date: datetime?     // When it takes effect
```

**Total: 6 fields** ✅

---

### ✅ doc_type = "github"

```cypher
// ============ IDENTIFIERS ============
github_id: int                // 123456789
repo_name: string             // "ssripad/evtol"
owner: string                 // "ssripad"

// ============ TIMELINE (FOR AGENT SCORING) ============
created_at: datetime          // When repo was created
last_pushed_at: datetime      // Last REAL activity (agents use for innovation_score)

// ============ ENGAGEMENT (FOR AGENT SCORING) ============
stars: int                    // Community interest
forks: int                    // Usage/adoption
contributor_count: int        // Number of contributors
```

**Total: 8 fields** ✅

---

### ✅ doc_type = "government_contract"

```cypher
// ============ CONTRACT DETAILS ============
award_id: string              // "DTFAWA-21-A-00001"
recipient_name: string        // "Joby Aero Inc."
award_amount: float           // USD (agents use for adoption_score)

// ============ TIMELINE ============
start_date: datetime
end_date: datetime

// ============ AGENCY ============
awarding_agency: string       // "Department of Defense"
awarding_sub_agency: string   // "U.S. Air Force"
```

**Total: 7 fields** ✅

---

### ✅ doc_type = "news"

```cypher
// ============ SOURCE ============
domain: string                // "finance.yahoo.com"
outlet_tier: string?          // "tier1" | "tier2" | "blog"

// ============ DISCOVERY ============
seendate: datetime            // When GDELT saw the article

// ============ TONE (FOR AGENT SCORING) ============
tone: float                   // -1 to 1 (agents use for narrative_score)
```

**Total: 4 fields** ✅

---

## RELATIONSHIPS

### Entity Mentions (Technology/Company) MENTIONED_IN (Document)

**Purpose:** Track how entities appear in documents. Each document-entity pair creates ONE mention record.

#### (:Technology)-[:MENTIONED_IN]->(:Document)

```cypher
// ============ FROM LLM EXTRACTION ============
role: string                   // "subject" | "invented" | "studied" | "commercialized" |
                               // "implemented" | "procured" | "regulated"
strength: float                // 0-1: centrality of tech in document
                               // 1.0 = primary subject, 0.5 = secondary, 0.1 = passing reference
evidence_confidence: float     // 0-1: LLM confidence in this classification
evidence_text: string          // Max 200 chars from doc supporting this role
```

**Total: 4 fields** (4 required)

---

#### (:Company)-[:MENTIONED_IN]->(:Document)

```cypher
// ============ FROM LLM EXTRACTION ============
role: string                   // "owner" | "developer" | "operator" | "contractor" |
                               // "issuer" | "competitor" | "sponsor" |
                               // "investment_target" | "employer"
strength: float                // 0-1
evidence_confidence: float     // 0-1
evidence_text: string          // Max 200 chars
```

**Total: 4 fields** (4 required )

---

### Tech Role → Layer Mapping (for Agent Queries)

| Tech Role        | Layer 1 (Innovation) | Layer 2 (Adoption) | Layer 3 (Risk) | Layer 4 (Narrative) |
|------------------|----------------------|--------------------|----------------|---------------------|
| **subject**      | -                    | -                  | ✓ (Risk docs)  | ✓ (News)            |
| **invented**     | ✓                    | -                  | -              | -                   |
| **studied**      | ✓                    | -                  | -              | -                   |
| **commercialized** | -                  | ✓                  | -              | -                   |
| **implemented**  | -                    | ✓                  | -              | -                   |
| **procured**     | -                    | ✓                  | -              | -                   |
| **regulated**    | -                    | ✓ (approval)       | ✓ (denial)     | -                   |

### Company Role → Layer Mapping (for Agent Queries)

| Company Role        | Layer 1 (Innovation) | Layer 2 (Adoption) | Layer 3 (Risk) | Layer 4 (Narrative) |
|---------------------|----------------------|--------------------|----------------|---------------------|
| **owner**           | ✓                    | -                  | -              | -                   |
| **developer**       | -                    | ✓                  | -              | -                   |
| **operator**        | -                    | ✓                  | -              | -                   |
| **contractor**      | -                    | ✓                  | -              | -                   |
| **issuer**          | -                    | -                  | ✓              | -                   |
| **competitor**      | -                    | -                  | -              | ✓                   |
| **sponsor**         | ✓                    | -                  | -              | -                   |
| **investment_target** | -                 | -                  | ✓              | ✓                   |
| **employer**        | -                    | ✓                  | -              | -                   |

**How Agents Use This:** Innovation Scorer Agent queries `role: "invented"` OR `role: "studied"` to count innovation signals.

---

### Entity Relations (Aggregated Cross-Document)

**Critical Principle:** Each document creates SEPARATE relation records. Agents aggregate via Cypher queries.

**Example:**
- Patent #1 says: "Joby owns_ip for eVTOL" → 1 relation record with doc_ref="patent_1"
- Patent #2 says: "Joby owns_ip for eVTOL" → 1 relation record with doc_ref="patent_2"
- Patent #3 says: "Joby owns_ip for eVTOL" → 1 relation record with doc_ref="patent_3"
- **Total: 3 separate records** (NOT 1 aggregated record)
- **Agent computes:** evidence_count=3, avg_confidence=0.95, sources=["patent"]

---

#### (:Company)-[:RELATED_TO_TECH]->(:Technology)

**Allowed Relation Types:** develops | uses | invests_in | researches | owns_ip

```cypher
// ============ FROM LLM EXTRACTION (PER DOCUMENT) ============
relation_type: string          // "develops" | "uses" | "invests_in" | "researches" | "owns_ip"
evidence_confidence: float     // 0-1: LLM confidence for THIS specific document
evidence_text: string          // Max 200 chars from THIS document
doc_ref: string                // Document ID (critical - links back to source)

```

**Total: 4 fields** (4 required)


---

#### (:Technology)-[:RELATED_TECH]->(:Technology)

**Allowed Relation Types:** competes_with | alternative_to | enables | supersedes | complements | requires | supports | advances_beyond | contradicts | extends_life_of | improves_performance_of | improves_efficiency_of | builds_on | validates

```cypher
// ============ FROM LLM EXTRACTION (PER DOCUMENT) ============
relation_type: string          // One of 14 allowed types (see reference table)
evidence_confidence: float     // 0-1
evidence_text: string          // Max 200 chars
doc_ref: string                // Document ID

```

**Total: 4 fields** (4 required)

---

#### (:Company)-[:RELATED_COMPANY]->(:Company)

**Allowed Relation Types:** partners_with | invests_in | acquires | competes_with | supplies | licenses_from | 



```cypher
// ============ FROM LLM EXTRACTION (PER DOCUMENT) ============
relation_type: string          // One of 6 allowed types
evidence_confidence: float     // 0-1
evidence_text: string          // Max 200 chars
doc_ref: string                // Document ID

```

**Total: 4 fields** (4 required)

---

## DOCUMENT EXTRACTION FORMAT

This is the actual JSON format output by LLM parsers (e.g., `parsers/patents/patents_parser.py`), which is stored directly in Neo4j:

```json
{
  "document": {
    "doc_id": "003-712-519-476-908",
    "doc_type": "patent",
    "title": "ROTOR ASSEMBLY DEPLOYMENT MECHANISM AND AIRCRAFT USING SAME",
    "assignee": "Joby Aero, Inc.",
    "filing_date": "2024-06-21",
    "publication_date": "2025-04-10",
    "patent_number": "2025006314",
    "url": "https://link.lens.org/003-712-519-476-908",
    "citation_count": 5,
    "cpc_codes": [],
    "abstract": "A rotor assembly deployment mechanism..."
  },
  "tech_mentions": [
    {
      "name": "Rotor Assembly Deployment Mechanism",
      "role": "subject",
      "strength": 0.95,
      "evidence_confidence": 0.98,
      "evidence_text": "Primary invention: Mechanism for deploying rotor assembly in VTOL aircraft"
    },
    {
      "name": "Rotor Assembly Deployment Mechanism",
      "role": "invented",
      "strength": 0.90,
      "evidence_confidence": 0.95,
      "evidence_text": "Innovative deployment mechanism designed by Joby for rotor assemblies"
    }
  ],
  "company_mentions": [
    {
      "name": "Joby Aero Inc",
      "role": "owner",
      "strength": 1.0,
      "evidence_confidence": 1.0,
      "evidence_text": "Assignee: Joby Aero, Inc."
    },
    {
      "name": "Joby Aero Inc",
      "role": "developer",
      "strength": 0.98,
      "evidence_confidence": 0.98,
      "evidence_text": "Joby developed the rotor assembly deployment mechanism"
    }
  ],
  "company_tech_relations": [
    {
      "company_name": "Joby Aero Inc",
      "technology_name": "Rotor Assembly Deployment Mechanism",
      "relation_type": "owns_ip",
      "evidence_confidence": 1.0,
      "evidence_text": "Joby Aero filed patent for rotor assembly deployment mechanism",
      "doc_ref": "003-712-519-476-908"
    }
  ],
  "tech_tech_relations": [
    {
      "from_tech_name": "Rotor Assembly Deployment Mechanism",
      "to_tech_name": "Torsion Box Construction",
      "relation_type": "complements",
      "evidence_confidence": 0.95,
      "evidence_text": "Torsion box construction enhances the deployment mechanism's strength",
      "doc_ref": "003-712-519-476-908"
    }
  ],
  "company_company_relations": [
    {
      "from_company_name": "Toyota",
      "to_company_name": "Joby Aviation",
      "relation_type": "partners_with",
      "evidence_confidence": 0.95,
      "evidence_text": "Toyota and Joby announce partnership to develop hydrogen eVTOL",
      "doc_ref": "003-712-519-476-908"
    }
  ]
}
```

**Key Characteristics:**
1. **Document-centric:** All data tied to ONE source document
2. **Minimal fields:** Only 4-6 fields per mention/relation
3. **No aggregation:** Each record is independent
4. **Role granularity:** One mention per entity per role (e.g., "subject" AND "invented" = 2 separate tech_mentions)

---

## ROLE DEFINITIONS REFERENCE

### Technology Roles (7 total)

| Role | Definition | Primary Evidence | Example |
|------|------------|------------------|---------|
| **subject** | Primary topic or focus of the document | All doc types | "eVTOL sector hits new highs" (news) |
| **invented** | Technology was created, designed, or originated | Patents, papers | "Novel magnetic levitation rotor system invented by Joby" (patent) |
| **studied** | Technology is being researched, tested, or validated | Papers | "Study validates eVTOL battery performance" (paper) |
| **commercialized** | Technology is being sold, promoted, or monetized | Contracts, sec_filings, news | "eVTOL air taxi services launched in Dubai" (news) |
| **implemented** | Technology has been built, coded, or deployed | GitHub, contracts, sec_filings | "eVTOL charging system deployed at LAX" (contract) |
| **procured** | Technology was purchased or contracted | Gov contracts | "DoD awards $50M contract for eVTOL platform" (contract) |
| **regulated** | Technology is subject to government oversight | Regulatory filings | "FAA grants type certification for Joby eVTOL" (regulation) |

### Company Roles (9 total)

| Role | Definition | Primary Evidence | Example |
|------|------------|------------------|---------|
| **owner** | Company holds IP rights | Patents | "Assignee: Joby Aero, Inc." (patent) |
| **developer** | Company is building/inventing the technology | Patents, news, contracts | "Joby developed the magnetic levitation rotor" (patent) |
| **operator** | Company uses/deploys the technology | SEC filings, news, contracts | "Joby operates commercial eVTOL services in Dubai" (news) |
| **contractor** | Company receives government funding | Gov contracts | "Joby awarded $50M NASA contract" (contract) |
| **issuer** | Company files SEC reports | SEC filings | "Issuer: Joby Aviation Inc (CIK: 0001856058)" (10-K) |
| **competitor** | Company mentioned as market competitor | News, sec_filings | "Joby competes with Archer in eVTOL market" (news) |
| **sponsor** | Company funds research/development | Papers | "Research funded by Joby Aviation" (paper) |
| **investment_target** | Company receives investment | SEC filings, news | "Toyota invests $394M in Joby" (8-K) |
| **employer** | Company recruits talent | Job postings (future) | "Joby hiring eVTOL flight test engineers" |

---

## RELATION TYPE REFERENCE

### Company → Technology Relations (5 total)

| Relation Type | Definition | Evidence Sources | Example |
|---------------|------------|------------------|---------|
| **develops** | Company is building/engineering the technology | patents, news, contracts | Joby **develops** eVTOL air taxis |
| **uses** | Company operates/deploys the technology | news, contracts, sec_filings | Uber **uses** eVTOL aircraft for air taxi |
| **invests_in** | Company provides financial investment | sec_filings, news | Toyota **invests_in** Joby's eVTOL technology |
| **researches** | Company conducts R&D research | papers, contracts | NASA **researches** eVTOL battery performance |
| **owns_ip** | Company holds patents/IP | patents | Joby **owns_ip** for magnetic levitation rotors |

### Technology → Technology Relations (14 total)

| Relation Type | Definition | Directional? | Example |
|---------------|------------|--------------|---------|
| **competes_with** | Direct competitors solving same problem | No | Hydrogen eVTOL **competes_with** battery eVTOL |
| **alternative_to** | Different approach to same problem | No | Tilt-rotor **alternative_to** lift+cruise design |
| **enables** | Makes another technology possible | Yes | 400Wh/kg batteries **enable** long-range eVTOL |
| **supersedes** | Replaces/improves older technology | Yes | Distributed electric propulsion **supersedes** turbines |
| **complements** | Technologies work together | No | Autonomous flight **complements** urban air mobility |
| **requires** | Hard dependency | Yes | eVTOL **requires** advanced battery management |
| **supports** | Soft dependency | Yes | Lightweight composites **support** eVTOL range |
| **advances_beyond** | Improves over previous technology | Yes | Gen-3 battery **advances_beyond** lithium-ion |
| **contradicts** | Challenges assumptions | Yes | Real-world data **contradicts** hydrogen range claims |
| **extends_life_of** | Improves durability/longevity | Yes | Active cooling **extends_life_of** battery packs |
| **improves_performance_of** | Enhances capability | Yes | Maglev rotors **improve_performance_of** propulsion |
| **improves_efficiency_of** | Reduces losses/waste | Yes | Regenerative braking **improves_efficiency_of** aircraft |
| **builds_on** | Based on prior work | Yes | eVTOL standards **build_on** helicopter regulations |
| **validates** | Testing validates viability | Yes | NASA testing **validates** noise reduction tech |

### Company → Company Relations (6 total)

| Relation Type | Definition | Directional? | Example |
|---------------|------------|--------------|---------|
| **partners_with** | Strategic partnership | No | Joby **partners_with** Uber for air taxi network |
| **invests_in** | Financial investment | Yes | Toyota **invests_in** Joby ($394M) |
| **acquires** | Merger/acquisition | Yes | Boeing **acquires** Aurora Flight Sciences |
| **competes_with** | Business competition | No | Joby **competes_with** Archer in eVTOL market |
| **supplies** | Supply chain relationship | Yes | Honeywell **supplies** avionics to eVTOL manufacturers |
| **licenses_from** | IP licensing agreement | Yes | Wisk **licenses_from** Kitty Hawk (Cora eVTOL IP) |

---

## AGENT COMPUTATION LAYER

**Critical Principle:** Neo4j stores RAW data. LangGraph agents COMPUTE everything by querying the graph.

### How Agents Query the Graph

The 11-agent LangGraph system queries Neo4j to compute scores on-demand. No scores are ever stored in the graph.

#### Innovation Scorer Agent (Layer 1)

**What it computes:** innovation_score (0-100)

**How it queries:**
```cypher
// Count patents mentioning the technology
MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN {role: "invented"}]->(d:Document {doc_type: "patent"})
WHERE date(datetime(d.published_at)) >= date() - duration('P730D')  // Last 2 years
WITH t,
     count(DISTINCT d) as patent_count,
     avg(m.strength) as avg_patent_strength,
     sum(d.citation_count) as total_citations

// Count research papers
MATCH (t)-[m2:MENTIONED_IN {role: "studied"}]->(d2:Document {doc_type: "technical_paper"})
WHERE date(datetime(d2.published_at)) >= date() - duration('P730D')
WITH t, patent_count, avg_patent_strength, total_citations,
     count(DISTINCT d2) as paper_count,
     avg(m2.strength) as avg_paper_strength,
     sum(d2.citation_count) as paper_citations

// Count GitHub repos
MATCH (t)-[m3:MENTIONED_IN]->(d3:Document {doc_type: "github"})
WITH t, patent_count, avg_patent_strength, total_citations, paper_count, avg_paper_strength, paper_citations,
     count(DISTINCT d3) as github_count,
     avg(d3.stars) as avg_stars

RETURN patent_count, paper_count, github_count, total_citations, paper_citations, avg_stars
```

**Then in Python:**
```python
innovation_score = (
    (patent_count * 5) +
    (total_citations * 0.1) +
    (paper_count * 3) +
    (paper_citations * 0.2) +
    (github_count * 2) +
    (avg_stars * 0.05)
)
# Normalize to 0-100 scale
innovation_score = min(100, innovation_score)
```

**Returns:** `{"technology": "evtol", "innovation_score": 78.4, "evidence_count": 23}`

---

#### Adoption Scorer Agent (Layer 2)

**What it computes:** adoption_score (0-100)

**How it queries:**
```cypher
// Count government contracts
MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN {role: "procured"}]->(d:Document {doc_type: "government_contract"})
WHERE date(datetime(d.published_at)) >= date() - duration('P365D')
WITH t,
     count(DISTINCT d) as contract_count,
     sum(d.award_amount) as total_contract_value

// Count regulatory approvals
MATCH (t)-[m2:MENTIONED_IN {role: "regulated"}]->(d2:Document {doc_type: "regulation"})
WHERE d2.decision_type = "approval"
  AND date(datetime(d2.published_at)) >= date() - duration('P365D')
WITH t, contract_count, total_contract_value,
     count(DISTINCT d2) as approval_count

// Check for commercial revenue
MATCH (c:Company)-[rel:RELATED_TO_TECH {relation_type: "develops"}]->(t)
MATCH (c)-[:MENTIONED_IN {role: "issuer"}]->(d3:Document {doc_type: "sec_filing"})
WHERE d3.revenue_mentioned = true
  AND date(datetime(d3.published_at)) >= date() - duration('P365D')
WITH t, contract_count, total_contract_value, approval_count,
     count(DISTINCT c) as companies_with_revenue

RETURN contract_count, total_contract_value, approval_count, companies_with_revenue
```

**Then in Python:**
```python
adoption_score = (
    (contract_count * 8) +
    (total_contract_value / 1000000 * 0.5) +  # $10M = 5 pts
    (approval_count * 12) +
    (companies_with_revenue * 15)
)
adoption_score = min(100, adoption_score)
```

---

#### Risk Scorer Agent (Layer 3)

**What it computes:** risk_score (0-100)

**How it queries:**
```cypher
// Check for risk mentions in SEC filings
MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN {role: "subject"}]->(d:Document {doc_type: "sec_filing"})
WHERE d.risk_factor_mentioned = true
  AND date(datetime(d.published_at)) >= date() - duration('P180D')
WITH t,
     count(DISTINCT d) as risk_mention_count

// Check for insider selling
MATCH (c:Company)-[rel:RELATED_TO_TECH]->(t)
MATCH (c)-[:MENTIONED_IN {role: "investment_target"}]->(d2:Document {doc_type: "sec_filing", filing_type: "Form-4"})
WHERE d2.net_insider_value_usd < 0  // Negative = selling
  AND date(datetime(d2.published_at)) >= date() - duration('P180D')
WITH t, risk_mention_count,
     sum(abs(d2.net_insider_value_usd)) as total_insider_selling

RETURN risk_mention_count, total_insider_selling
```

**Then in Python:**
```python
risk_score = (
    (risk_mention_count * 10) +
    (total_insider_selling / 10000000 * 5)  # $10M selling = 5 pts
)
risk_score = min(100, risk_score)
```

---

#### Narrative Scorer Agent (Layer 4)

**What it computes:** narrative_score (0-100)

**How it queries:**
```cypher
// Count news articles mentioning technology
MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN {role: "subject"}]->(d:Document {doc_type: "news"})
WHERE date(datetime(d.published_at)) >= date() - duration('P90D')
WITH t,
     count(DISTINCT d) as news_count,
     avg(d.tone) as avg_sentiment,
     avg(m.strength) as avg_prominence

RETURN news_count, avg_sentiment, avg_prominence
```

**Then in Python:**
```python
narrative_score = (
    (news_count * 1.5) +  # Volume
    (avg_sentiment * 20) +  # Sentiment (-1 to 1 → -20 to +20)
    (avg_prominence * 30)   # Prominence (0 to 1 → 0 to 30)
)
narrative_score = max(0, min(100, narrative_score))
```

---

#### Hype Scorer Agent (Cross-Layer Contradiction Detection)

**What it computes:** hype_score (0-100), contradiction signals

**How it works:**
1. Gets innovation_score, adoption_score, narrative_score, risk_score from other agents
2. Detects contradictions:
   - High narrative + Low innovation = **Peak phase signal**
   - Low narrative + High innovation = **Trough phase signal**
3. Computes hype_score as ratio of narrative to fundamentals

**Python logic:**
```python
fundamentals_score = (innovation_score + adoption_score) / 2
hype_score = (narrative_score / fundamentals_score) * 50 if fundamentals_score > 0 else 0

# Detect contradictions
if narrative_score > 80 and innovation_score < 30:
    signal = "PEAK_PHASE_SIGNAL"
elif narrative_score < 20 and innovation_score > 70:
    signal = "TROUGH_PHASE_SIGNAL"
else:
    signal = "NO_SIGNAL"
```

---

### Summary: Agent Query Patterns

| Agent | Queries | Aggregates | Computes | Stores |
|-------|---------|------------|----------|--------|
| **Innovation Scorer** | `role: "invented"`, `role: "studied"` | count(patents), sum(citations) | innovation_score | ❌ No |
| **Adoption Scorer** | `role: "procured"`, `role: "commercialized"` | sum(contract_value), count(approvals) | adoption_score | ❌ No |
| **Narrative Scorer** | `role: "subject"` from news | count(news), avg(sentiment) | narrative_score | ❌ No |
| **Risk Scorer** | `role: "subject"` from SEC, insider selling | count(risk_mentions), sum(selling) | risk_score | ❌ No |
| **Hype Scorer** | All other scores | contradiction_count | hype_score | ❌ No |

**Key Takeaway:** Query → Aggregate → Compute → Return (never store)

---

## QUERY EXAMPLES (FOR AGENTS)

### Example 1: Innovation Scorer Agent - Count Patents

```cypher
// Agent queries raw mentions to compute patent_count
MATCH (t:Technology {id: "evtol"})-[m:MENTIONED_IN {role: "invented"}]->(d:Document {doc_type: "patent"})
WHERE date(datetime(d.published_at)) >= date() - duration('P730D')
RETURN count(DISTINCT d) as patent_count,
       avg(m.strength) as avg_strength,
       collect(d.id)[0..10] as sample_patent_ids
```

**Agent Python code:**
```python
result = graph.query(cypher, params={"tech_id": "evtol"})
patent_count = result[0]["patent_count"]
innovation_score = patent_count * 5  # Weight patents heavily
```

---

### Example 2: Adoption Scorer Agent - Aggregate Contract Value

```cypher
// Agent queries documents to compute total government investment
MATCH (t:Technology {id: "evtol"})-[m:MENTIONED_IN {role: "procured"}]->(d:Document {doc_type: "government_contract"})
WHERE date(datetime(d.published_at)) >= date() - duration('P365D')
RETURN count(DISTINCT d) as contract_count,
       sum(d.award_amount) as total_contract_value_usd,
       collect({agency: d.awarding_agency, amount: d.award_amount})[0..5] as top_contracts
```

**Agent Python code:**
```python
result = graph.query(cypher, params={"tech_id": "evtol"})
adoption_score = (result[0]["total_contract_value_usd"] / 1000000) * 0.5
```

---

### Example 3: Evidence Compiler Agent - Trace Provenance

```cypher
// Agent retrieves all evidence for a specific relation
MATCH (c:Company {id: "joby"})-[rel:RELATED_TO_TECH {relation_type: "owns_ip"}]->(t:Technology {id: "evtol"})
MATCH (d:Document {id: rel.doc_ref})
RETURN d.title,
       d.doc_type,
       d.published_at,
       d.url,
       rel.evidence_text,
       rel.evidence_confidence
ORDER BY d.published_at DESC
LIMIT 20
```

**Agent Python code:**
```python
evidence_list = graph.query(cypher, params={"company_id": "joby", "tech_id": "evtol"})
# Returns list of source documents with citations for report
```

---

### Example 4: Hype Scorer Agent - Detect Contradictions

```cypher
// Agent counts Layer 4 (narrative) mentions
MATCH (t:Technology {id: "evtol"})-[m:MENTIONED_IN {role: "subject"}]->(d:Document {doc_type: "news"})
WHERE date(datetime(d.published_at)) >= date() - duration('P90D')
WITH t, count(DISTINCT d) as news_count_90d

// Agent counts Layer 1 (innovation) mentions
MATCH (t)-[m2:MENTIONED_IN {role: "invented"}]->(d2:Document {doc_type: "patent"})
WHERE date(datetime(d2.published_at)) >= date() - duration('P365D')
WITH t, news_count_90d, count(DISTINCT d2) as patent_count_365d

// Agent checks Layer 3 (risk) - insider selling
MATCH (c:Company)-[rel:RELATED_TO_TECH]->(t)
MATCH (c)-[:MENTIONED_IN {role: "investment_target"}]->(d3:Document {doc_type: "sec_filing", filing_type: "Form-4"})
WHERE d3.net_insider_value_usd < 0
  AND date(datetime(d3.published_at)) >= date() - duration('P180D')
WITH t, news_count_90d, patent_count_365d,
     sum(abs(d3.net_insider_value_usd)) as insider_selling_usd

RETURN news_count_90d,
       patent_count_365d,
       insider_selling_usd,
       CASE
         WHEN news_count_90d > 50 AND patent_count_365d < 10 AND insider_selling_usd > 10000000
         THEN "PEAK_PHASE_SIGNAL"
         ELSE "NO_SIGNAL"
       END as contradiction_signal
```

---

### Example 5: Phase Detector Agent - Technology Lifecycle Position

```cypher
// Agent queries multiple layers to determine lifecycle phase
// Layer 1: Innovation
MATCH (t:Technology {id: "evtol"})-[:MENTIONED_IN {role: "invented"}]->(d1:Document {doc_type: "patent"})
WHERE date(datetime(d1.published_at)) >= date() - duration('P730D')
WITH t, count(d1) as patent_count_2yr

// Layer 2: Adoption
MATCH (t)-[:MENTIONED_IN {role: "commercialized"}]->(d2:Document)
WHERE date(datetime(d2.published_at)) >= date() - duration('P365D')
WITH t, patent_count_2yr, count(d2) as adoption_count

// Layer 4: Narrative
MATCH (t)-[:MENTIONED_IN {role: "subject"}]->(d3:Document {doc_type: "news"})
WHERE date(datetime(d3.published_at)) >= date() - duration('P90D')
WITH t, patent_count_2yr, adoption_count, count(d3) as news_count

RETURN patent_count_2yr, adoption_count, news_count
```

**Agent Python logic:**
```python
result = graph.query(cypher, params={"tech_id": "evtol"})
patent_count = result[0]["patent_count_2yr"]
adoption_count = result[0]["adoption_count"]
news_count = result[0]["news_count"]

# Phase detection rules
if patent_count > 50 and adoption_count < 5 and news_count < 10:
    phase = "Technology Trigger"
elif patent_count > 30 and news_count > 100:
    phase = "Peak of Inflated Expectations"
elif patent_count < 10 and news_count < 20:
    phase = "Trough of Disillusionment"
elif adoption_count > 10 and news_count > 20:
    phase = "Slope of Enlightenment"
else:
    phase = "Plateau of Productivity"
```

---

## MIGRATION GUIDE v1.1 → v2.0

### Breaking Changes

1. **Field renames:**
   - `tech_role` → `role` (for Technology MENTIONED_IN)
   - `company_role` → `role` (for Company MENTIONED_IN)

2. **Removed fields (if they exist in v1.1):**
   - All scoring fields from Technology node (innovation_score, adoption_score, etc.)
   - All aggregation fields from relationships (evidence_count, evidence_by_source, etc.)

### Migration Steps

1. **Check current schema:**
```cypher
// Verify what fields exist
MATCH (t:Technology)
RETURN keys(t) LIMIT 1

MATCH ()-[r:MENTIONED_IN]->()
RETURN keys(r) LIMIT 1
```

2. **Rename role fields if needed:**
```cypher
// If using tech_role, rename to role
MATCH (t:Technology)-[r:MENTIONED_IN]->(d:Document)
WHERE EXISTS(r.tech_role)
SET r.role = r.tech_role
REMOVE r.tech_role

// If using company_role, rename to role
MATCH (c:Company)-[r:MENTIONED_IN]->(d:Document)
WHERE EXISTS(r.company_role)
SET r.role = r.company_role
REMOVE r.company_role
```

3. **Remove scoring fields (if they exist):**
```cypher
// Remove scores from Technology nodes
MATCH (t:Technology)
REMOVE t.innovation_score, t.adoption_score, t.narrative_score, t.risk_score, t.hype_score,
       t.hype_phase, t.llm_phase, t.ensemble_phase

// Remove aggregation fields from relations (if they exist)
MATCH ()-[r:RELATED_TO_TECH]->()
REMOVE r.confidence, r.evidence_count, r.evidence_by_source, r.supporting_doc_ids,
       r.first_evidence_date, r.latest_evidence_date
```

4. **Verify doc_ref exists:**
```cypher
// Check if doc_ref is present
MATCH ()-[r:RELATED_TO_TECH]->()
WHERE r.doc_ref IS NULL
RETURN count(r) as missing_doc_ref  // Should be 0
```

### Validation

**After migration, verify:**
```cypher
// 1. No scoring fields
MATCH (t:Technology)
WHERE EXISTS(t.innovation_score) OR EXISTS(t.adoption_score)
RETURN count(t) as nodes_with_scores  // Should be 0

// 2. All mentions use "role" field
MATCH ()-[r:MENTIONED_IN]->()
WHERE NOT EXISTS(r.role)
RETURN count(r) as mentions_without_role  // Should be 0

// 3. All relations have doc_ref
MATCH ()-[r:RELATED_TO_TECH]->()
WHERE r.doc_ref IS NULL
RETURN count(r) as relations_without_doc_ref  // Should be 0
```

---

## APPENDIX

### Config File Reference

See [configs/eVTOL_graph_relations.json](../configs/eVTOL_graph_relations.json) for:
- Complete relation type definitions
- Layer mappings (which relations belong to which layer)
- Data source mappings (which sources provide which relations)
- Extraction notes and validation rules

### Architecture Reference

See [README.md](../README.md) for:
- 6-phase pipeline architecture
- 11-agent LangGraph system design
- Multi-layer intelligence framework (L1-L4)
- GraphRAG principles and usage

---

**END OF SCHEMA v2.0 DOCUMENTATION**

---

## VALIDATION CHECKLIST

After implementing this schema, verify:

- ✅ **No scoring fields** in any node (Technology, Company, Document)
- ✅ **No aggregation fields** in any relationship (MENTIONED_IN, RELATED_TO_TECH, etc.)
- ✅ **All relationships use `role` field** (not `tech_role` or `company_role`)
- ✅ **All relations have `doc_ref`** linking back to source document
- ✅ **Query examples show agent computation** (not stored field queries)
- ✅ **"Pure storage" principle** clearly stated at top of document
- ✅ **Document size reduced** from 1,200 lines → ~800 lines
