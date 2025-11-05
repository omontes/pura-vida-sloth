# Lens Scholarly Works Downloader - Implementation Guide

**Status**: Pending Implementation (Access Requested)
**Priority**: High - Fills Layer 2 (Market Formation) funding data gap
**Created**: 2025-11-04
**API Token Status**: Scholarly Works access requested, awaiting approval

---

## Table of Contents
1. [Strategic Context](#strategic-context)
2. [API Documentation](#api-documentation)
3. [Implementation Tasks](#implementation-tasks)
4. [Code Structure](#code-structure)
5. [Testing Strategy](#testing-strategy)
6. [Integration Steps](#integration-steps)
7. [Expected Output](#expected-output)

---

## Strategic Context

### Why Lens Scholarly Works?

**Current Gap in Layer 2 (Market Formation)**:
- ✅ Government contracts (USASpending.gov)
- ✅ Regulatory filings
- ✅ Job postings
- ❌ **Missing**: Research funding trends

**What Lens Scholarly Adds**:
1. **Funding/Grant Data** - Track which organizations fund research (NASA, DARPA, DOE, NSF, NIH)
2. **Research Volume Trends** - Measure publication activity over time
3. **Patent-Paper Citations** - Link innovation (patents) to research (papers)
4. **Broader Coverage** - 200M+ papers vs arXiv's narrow physics/CS/math focus

**Strategic Intelligence Value**:
- "NASA eVTOL funding peaked 2021 → dropped 2024 = government reducing bets"
- "Battery research papers increased 300% (2020-2024) = enabling technology maturing"
- "Patent citing paper by 18 months on average = research → commercialization timeline"

### Data Silo Focus

**What to Harvest**:
- Research papers matching industry keywords
- Funding organization names and grant IDs
- Author affiliations (academic vs corporate research)
- Field of study classifications
- Citation counts (scholarly + patent citations)
- Publication dates for trend analysis

**What to Ignore** (not relevant for strategic intelligence):
- Full-text content (abstracts sufficient)
- Detailed author biographies
- Conference presentation details

---

## API Documentation

### Endpoint
```
POST https://api.lens.org/scholar/search
```

### Authentication
```http
Authorization: Bearer {LENS_API_TOKEN}
Content-Type: application/json
Accept: application/json
```

**Token Requirements**:
- Must have "Scholarly Works API" access enabled
- Same token can support both Patent + Scholarly access
- Request access at: https://www.lens.org/lens/user/subscriptions

### Rate Limits
```
x-rate-limit-remaining-request-per-minute: <count>
x-rate-limit-remaining-request-per-day: <count>
```

**Best Practices**:
- Check headers after each request
- If remaining < 10, sleep for 60 seconds
- Implement exponential backoff on rate limit errors (HTTP 429)

### Pagination

**Cursor-based (for >10,000 results)**:
```json
{
  "scroll": "5m",
  "size": 100
}
```

**Scroll continuation**:
```json
{
  "scroll_id": "<returned_scroll_id>",
  "size": 100
}
```

**Note**: Unlike patents, scholarly works may use offset-based pagination for smaller result sets. Test both approaches.

---

## Query Structure

### Basic Keyword Search
```json
{
  "query": {
    "bool": {
      "must": [
        {
          "match": {
            "title": "electric vertical takeoff"
          }
        }
      ]
    }
  },
  "size": 100,
  "scroll": "5m"
}
```

### Multi-Keyword Search (OR logic)
```json
{
  "query": {
    "bool": {
      "should": [
        {"match": {"title": "eVTOL"}},
        {"match": {"title": "electric vertical takeoff"}},
        {"match": {"title": "urban air mobility"}},
        {"match": {"abstract": "eVTOL"}}
      ],
      "minimum_should_match": 1
    }
  }
}
```

### Date Range Filter
```json
{
  "query": {
    "bool": {
      "must": [
        {"match": {"title": "eVTOL"}},
        {
          "range": {
            "year_published": {
              "gte": 2020,
              "lte": 2024
            }
          }
        }
      ]
    }
  }
}
```

### Include Fields (Optimize Response)
```json
{
  "include": [
    "lens_id",
    "title",
    "year_published",
    "date_published",
    "abstract",
    "authors",
    "funding",
    "fields_of_study",
    "scholarly_citations_count",
    "patent_citations_count",
    "source.title",
    "source.publisher",
    "source.type",
    "external_ids"
  ]
}
```

---

## Response Structure

### Example Response
```json
{
  "total": 1247,
  "results": 100,
  "scroll_id": "abc123...",
  "data": [
    {
      "lens_id": "001-234-567-890-123",
      "title": "Battery optimization for eVTOL aircraft",
      "year_published": 2023,
      "date_published": "2023-06-15",
      "abstract": "This paper presents...",
      "authors": [
        {
          "display_name": "John Smith",
          "affiliations": [
            {
              "name": "MIT",
              "country_code": "US"
            }
          ]
        }
      ],
      "funding": [
        {
          "organisation": "NASA",
          "funding_id": "NNX16AL96A",
          "country": "United States"
        }
      ],
      "fields_of_study": ["Aerospace Engineering", "Battery Technology"],
      "scholarly_citations_count": 42,
      "patent_citations_count": 3,
      "source": {
        "title": "Journal of Aerospace Technology",
        "publisher": "IEEE",
        "type": "journal"
      },
      "external_ids": {
        "doi": "10.1109/example.2023.123456",
        "pmid": null,
        "arxiv": null
      }
    }
  ]
}
```

### Key Fields for Strategic Intelligence

**Funding Data** (CRITICAL - fills Layer 2 gap):
```python
funding = paper.get('funding', [])
for grant in funding:
    org = grant.get('organisation')      # "NASA", "DARPA", "NSF"
    grant_id = grant.get('funding_id')   # "NNX16AL96A"
    country = grant.get('country')       # "United States"
```

**Author Affiliations** (academic vs corporate):
```python
authors = paper.get('authors', [])
for author in authors:
    affiliations = author.get('affiliations', [])
    for affil in affiliations:
        org_name = affil.get('name')     # "MIT", "Boeing", "NASA"
        org_type = affil.get('type')     # "Education", "Company", "Government"
```

**Citation Metrics**:
```python
scholarly_cites = paper.get('scholarly_citations_count', 0)  # Academic impact
patent_cites = paper.get('patent_citations_count', 0)        # Commercial impact
```

**Publication Metadata**:
```python
year = paper.get('year_published')        # Trend analysis
source_type = paper.get('source', {}).get('type')  # "journal", "conference"
fields = paper.get('fields_of_study', []) # Topic classification
```

---

## Implementation Tasks

### Phase 1: Create lens_scholarly.py Downloader

**File**: `src/downloaders/lens_scholarly.py`

**Task Checklist**:
- [ ] Copy structure from `lens_patents.py` as template
- [ ] Update class name: `LensScholarlyDownloader`
- [ ] Update endpoint: `https://api.lens.org/scholar/search`
- [ ] Modify query builder for keyword-based search (not assignee-based)
- [ ] Update field mapping for scholarly response structure
- [ ] Implement funding data extraction
- [ ] Implement author affiliation extraction
- [ ] Add citation metrics extraction
- [ ] Implement incremental saving pattern (save after each keyword)
- [ ] Add checkpoint/resume capability
- [ ] Implement cursor-based pagination
- [ ] Add rate limit handling
- [ ] Create standardized output contract

**Code Template**:
```python
"""
Lens Scholarly Works API Downloader

Downloads research papers with funding data from Lens.org Scholarly Works API.
Fills Layer 2 (Market Formation) gap with research funding trends.

API Docs: https://docs.api.lens.org/scholar.html
Coverage: 200M+ scholarly works
Rate Limits: Check x-rate-limit-* headers
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

from src.utils.checkpoint_manager import CheckpointManager

class LensScholarlyDownloader:
    """
    Download scholarly works from Lens.org Scholarly Works API.

    Mandatory Design Patterns Implemented:
    1. Incremental Persistence - Save after each keyword
    2. Graceful Degradation - Continue on single keyword failure
    3. Rate Limit Handling - Exponential backoff
    4. Standardized Output Contract - Same stats dict as other downloaders
    5. Checkpoint/Resume - Track completed keywords
    6. Industry-Agnostic Parameters - All keywords from config
    """

    def __init__(
        self,
        output_dir: Path,
        start_date: str,  # ISO format: "2024-05-01"
        end_date: str,
        keywords: List[str],  # ["eVTOL", "electric vertical takeoff", ...]
        limit: int = 500
    ):
        """
        Initialize Lens Scholarly Works downloader.

        Args:
            output_dir: Where to save papers.json and metadata
            start_date: Start date for year_published filter (YYYY-MM-DD)
            end_date: End date for year_published filter (YYYY-MM-DD)
            keywords: List of keywords to search (from config)
            limit: Max papers per keyword (default 500)
        """
        # Setup
        load_dotenv()
        self.api_token = os.getenv('LENS_API_TOKEN')
        if not self.api_token:
            raise ValueError("LENS_API_TOKEN not found in environment")

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Parse dates to year-only for year_published filter
        self.start_year = datetime.fromisoformat(start_date).year
        self.end_year = datetime.fromisoformat(end_date).year

        self.keywords = keywords
        self.limit = limit

        # API configuration
        self.base_url = "https://api.lens.org/scholar/search"
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        # Checkpoint manager
        self.checkpoint = CheckpointManager(
            self.output_dir / "checkpoint_lens_scholarly.json"
        )

        # Logging
        self.logger = logging.getLogger(__name__)

        # Stats
        self.stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total_size': 0,
            'by_keyword': {}
        }

    def download(self) -> Dict[str, Any]:
        """
        Main download method with incremental saving.

        Returns standardized stats dict.
        """
        self.logger.info(f"Starting Lens Scholarly Works download")
        self.logger.info(f"Year range: {self.start_year} to {self.end_year}")
        self.logger.info(f"Keywords: {len(self.keywords)}")
        self.logger.info(f"Limit per keyword: {self.limit}")

        # INCREMENTAL SAVING: Load existing papers
        all_papers = self._load_existing_papers()
        existing_count = len(all_papers)
        if existing_count > 0:
            self.logger.info(f"Loaded {existing_count} existing papers")

        # Search by keyword
        for keyword in self.keywords:
            # Skip if already completed
            if self.checkpoint.is_completed(keyword):
                self.logger.info(f"Skipping {keyword} (already completed)")
                self.stats['skipped'] += 1
                continue

            self.logger.info(f"Searching papers for: {keyword}")

            try:
                papers = self._search_by_keyword(keyword)

                # INCREMENTAL SAVING: Append and save
                if papers:
                    all_papers.extend(papers)
                    self._save_papers_incremental(all_papers)

                self.stats['by_keyword'][keyword] = len(papers)
                self.checkpoint.mark_completed(keyword)
                self.logger.info(f"  Found {len(papers)} papers for {keyword}")

            except Exception as e:
                self.logger.error(f"Error searching for {keyword}: {e}")
                self.stats['by_keyword'][keyword] = 0
                self.stats['failed'] += 1

        # Final deduplication
        unique_papers = self._deduplicate_papers(all_papers)
        self.logger.info(f"Total unique papers: {len(unique_papers)}")

        # Final save
        if unique_papers:
            self._save_papers(unique_papers)
            self._save_metadata(unique_papers)

        self.checkpoint.finalize()
        self._print_summary()

        return self.stats

    def _search_by_keyword(self, keyword: str) -> List[Dict]:
        """Search papers by keyword with pagination."""
        # TODO: Implement query builder
        # TODO: Implement pagination loop
        # TODO: Implement rate limit handling
        pass

    def _extract_paper_data(self, raw_paper: Dict) -> Dict:
        """Extract and normalize paper data from API response."""
        # TODO: Extract funding data
        # TODO: Extract author affiliations
        # TODO: Extract citation metrics
        pass

    def _load_existing_papers(self) -> List[Dict]:
        """Load existing papers for resume capability."""
        papers_file = self.output_dir / "papers.json"
        if papers_file.exists():
            try:
                with open(papers_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load existing papers: {e}")
        return []

    def _save_papers_incremental(self, papers: List[Dict]):
        """Save after each keyword (prevent data loss)."""
        papers_file = self.output_dir / "papers.json"
        try:
            with open(papers_file, 'w', encoding='utf-8') as f:
                json.dump(papers, f, indent=2, ensure_ascii=False)
            self.logger.debug(f"  Incremental save: {len(papers)} total papers")
        except Exception as e:
            self.logger.error(f"  Incremental save failed: {e}")

    def _deduplicate_papers(self, papers: List[Dict]) -> List[Dict]:
        """Deduplicate by lens_id."""
        seen = set()
        unique = []
        for paper in papers:
            lens_id = paper.get('lens_id')
            if lens_id and lens_id not in seen:
                seen.add(lens_id)
                unique.append(paper)
        return unique

    def _save_papers(self, papers: List[Dict]):
        """Save final deduplicated papers."""
        papers_file = self.output_dir / "papers.json"
        with open(papers_file, 'w', encoding='utf-8') as f:
            json.dump(papers, f, indent=2, ensure_ascii=False)

        file_size = papers_file.stat().st_size / (1024 * 1024)
        self.stats['total_size'] = file_size
        self.stats['success'] = len(papers)

        self.logger.info(f"Saved {len(papers)} papers ({file_size:.2f} MB)")

    def _save_metadata(self, papers: List[Dict]):
        """Save standardized metadata."""
        metadata = {
            'source': 'lens_scholarly',
            'timestamp': datetime.now().isoformat(),
            'year_range': f"{self.start_year}-{self.end_year}",
            'keywords': self.keywords,
            'total_papers': len(papers),
            'stats': self.stats
        }

        metadata_file = self.output_dir / "papers_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def _print_summary(self):
        """Print download summary."""
        self.logger.info("=" * 60)
        self.logger.info("Lens Scholarly Works Download Summary")
        self.logger.info("=" * 60)
        self.logger.info(f"Successful: {self.stats['success']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        self.logger.info(f"Skipped: {self.stats['skipped']}")
        self.logger.info(f"Total size: {self.stats['total_size']:.2f} MB")
```

---

### Phase 2: Update Configuration

**File**: `configs/evtol_config.json`

**Task Checklist**:
- [ ] Add `lens_scholarly` to `data_sources`
- [ ] Set `enabled: true` after token is ready
- [ ] Set appropriate `limit` (recommend 500 papers per keyword)
- [ ] Set `priority: 3` (after patents, before news)

**Config Addition**:
```json
{
  "data_sources": {
    "lens_scholarly": {
      "enabled": true,
      "limit": 500,
      "priority": 3,
      "comment": "Lens.org Scholarly Works API - research papers with funding data. Fills Layer 2 funding gap. ~5,000+ papers expected from keyword searches."
    }
  }
}
```

**Note**: Use existing `keywords.core` array from config:
```json
{
  "keywords": {
    "core": [
      "eVTOL",
      "electric vertical takeoff",
      "electric VTOL",
      "urban air mobility",
      "air taxi",
      "flying car"
    ]
  }
}
```

---

### Phase 3: Orchestrator Integration

**File**: `src/core/orchestrator.py`

**Task Checklist**:
- [ ] Import `LensScholarlyDownloader`
- [ ] Add initialization block after `lens_patents`
- [ ] Pass keywords from `config['keywords']['core']`
- [ ] Add to downloaders dict with priority 3

**Code Addition** (insert after line ~182, after lens_patents block):
```python
# 1c. Lens Scholarly Works (NEW - research papers with funding data)
if self.config['data_sources'].get('lens_scholarly', {}).get('enabled'):
    from src.downloaders.lens_scholarly import LensScholarlyDownloader

    # Get keywords from config
    keywords = []
    if 'keywords' in self.config:
        if 'core' in self.config['keywords']:
            keywords.extend(self.config['keywords']['core'])
        # Optionally add secondary keywords
        if 'secondary' in self.config['keywords']:
            keywords.extend(self.config['keywords']['secondary'])

    if not keywords:
        self.logger.warning("No keywords found in config for lens_scholarly")
    else:
        downloaders['lens_scholarly'] = LensScholarlyDownloader(
            output_dir=self.industry_root / folder_map.get('lens_scholarly', 'lens_scholarly'),
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            keywords=keywords,
            limit=self.config['data_sources']['lens_scholarly'].get('limit', 500)
        )
        self.logger.info(f"Initialized: LensScholarlyDownloader ({len(keywords)} keywords)")
```

**Config Update** (add to `output_config.folder_structure`):
```json
{
  "output_config": {
    "folder_structure": {
      "lens_scholarly": "lens_scholarly"
    }
  }
}
```

---

## Testing Strategy

### Phase 1: Token Validation Test

**File**: `test_lens_scholarly_api.py` (already created)

**Tasks**:
- [x] Test script created
- [x] Verified current token lacks access
- [ ] After access granted, verify HTTP 200 response
- [ ] Verify funding data in response
- [ ] Verify response structure matches expectations

**Run**:
```bash
python test_lens_scholarly_api.py
```

**Expected Output (after access granted)**:
```
[SUCCESS] Token works for scholarly works API
Total results: 127
Results in response: 5

First scholarly work:
Lens ID: 001-234-567-890-123
Title: Battery optimization for eVTOL aircraft
Year: 2023

Funding: 2 grants found!
  - Organization: NASA
    Grant ID: NNX16AL96A
  - Organization: DOE
    Grant ID: DE-SC0012345

Authors: 4 authors
  - John Smith
  - Jane Doe
  - ...
```

---

### Phase 2: Single Keyword Test

**Create**: `configs/evtol_test_scholarly.json`

```json
{
  "industry": "eVTOL",
  "industry_name": "eVTOL - Scholarly Works Test",
  "description": "Single keyword test for Lens Scholarly API",

  "date_range": {
    "days_back": 365
  },

  "output_config": {
    "base_dir": "./data",
    "industry_folder": "eVTOL_SCHOLARLY_TEST",
    "create_timestamp_subfolder": false,
    "folder_structure": {
      "lens_scholarly": "lens_scholarly"
    }
  },

  "keywords": {
    "core": ["eVTOL"]
  },

  "data_sources": {
    "lens_scholarly": {
      "enabled": true,
      "limit": 50,
      "priority": 1,
      "comment": "TEST - Single keyword with 50 papers limit"
    }
  }
}
```

**Run**:
```bash
python -m src.core.orchestrator --config configs/evtol_test_scholarly.json
```

**Validate**:
- [ ] Check `data/eVTOL_SCHOLARLY_TEST/lens_scholarly/papers.json` exists
- [ ] Verify ~50 papers downloaded
- [ ] Verify funding data extracted correctly
- [ ] Check incremental saves worked (interrupt and resume test)
- [ ] Verify metadata file created

---

### Phase 3: Full Keyword Harvest

**Run**:
```bash
python -m src.core.orchestrator --config configs/evtol_config.json
```

**Expected Results**:
- Keywords: 6 core keywords
- Papers per keyword: ~500-1,000
- Total papers: ~3,000-5,000 (after deduplication)
- File size: ~15-30 MB
- Funding records: ~40-60% of papers have funding data

**Validate**:
- [ ] All keywords processed
- [ ] Checkpoint tracking works
- [ ] Incremental saves prevented data loss
- [ ] Deduplication removed duplicates
- [ ] Rate limits respected
- [ ] Stats dict matches standardized contract

---

## Expected Output

### Directory Structure
```
data/eVTOL/lens_scholarly/
├── papers.json                          # 3,000-5,000 papers (~15-30 MB)
├── papers_metadata.json                 # Standardized metadata
├── checkpoint_lens_scholarly.json       # Resume tracking
└── papers.log                          # Download log
```

### papers.json Structure
```json
[
  {
    "lens_id": "001-234-567-890-123",
    "title": "Battery optimization for eVTOL aircraft",
    "year_published": 2023,
    "date_published": "2023-06-15",
    "abstract": "This paper presents...",
    "authors": [
      {
        "display_name": "John Smith",
        "affiliations": [
          {
            "name": "MIT",
            "country_code": "US",
            "type": "Education"
          }
        ]
      }
    ],
    "funding": [
      {
        "organisation": "NASA",
        "funding_id": "NNX16AL96A",
        "country": "United States"
      }
    ],
    "fields_of_study": ["Aerospace Engineering", "Battery Technology"],
    "scholarly_citations_count": 42,
    "patent_citations_count": 3,
    "source": {
      "title": "Journal of Aerospace Technology",
      "publisher": "IEEE",
      "type": "journal"
    },
    "external_ids": {
      "doi": "10.1109/example.2023.123456",
      "pmid": null,
      "arxiv": null
    },
    "harvested_at": "2025-11-04T10:30:00Z",
    "matched_keyword": "eVTOL"
  }
]
```

### papers_metadata.json Structure
```json
{
  "source": "lens_scholarly",
  "timestamp": "2025-11-04T10:35:00.123456",
  "year_range": "2024-2025",
  "keywords": ["eVTOL", "electric vertical takeoff", "..."],
  "total_papers": 4827,
  "stats": {
    "success": 4827,
    "failed": 0,
    "skipped": 0,
    "total_size": 23.45,
    "by_keyword": {
      "eVTOL": 1234,
      "electric vertical takeoff": 987,
      "electric VTOL": 654,
      "urban air mobility": 1203,
      "air taxi": 521,
      "flying car": 228
    }
  },
  "funding_coverage": {
    "papers_with_funding": 2891,
    "percentage": 59.9,
    "top_organizations": [
      {"name": "NASA", "count": 456},
      {"name": "European Commission", "count": 234},
      {"name": "NSF", "count": 189}
    ]
  }
}
```

---

## Strategic Intelligence Use Cases

Once implemented, this data enables:

### 1. Research Funding Trend Analysis
**Question**: "Is government research investment increasing or decreasing?"

**Query**:
```python
import json
from collections import Counter

with open('data/eVTOL/lens_scholarly/papers.json') as f:
    papers = json.load(f)

# Group by year and funding org
funding_by_year = {}
for paper in papers:
    year = paper.get('year_published')
    for grant in paper.get('funding', []):
        org = grant.get('organisation')
        if org:
            funding_by_year.setdefault(year, Counter())[org] += 1

# NASA funding trend
nasa_trend = {year: counts.get('NASA', 0) for year, counts in sorted(funding_by_year.items())}
print(f"NASA eVTOL Funding Trend: {nasa_trend}")
# Output: {2020: 12, 2021: 45, 2022: 67, 2023: 54, 2024: 23}
# Interpretation: Peaked 2022, declining = reducing bets
```

### 2. Academic vs Corporate Research Balance
**Question**: "Is research shifting from academia to industry?"

**Query**:
```python
academic_count = 0
corporate_count = 0

for paper in papers:
    for author in paper.get('authors', []):
        for affil in author.get('affiliations', []):
            org_type = affil.get('type', '').lower()
            if 'education' in org_type or 'university' in org_type:
                academic_count += 1
            elif 'company' in org_type or 'corporate' in org_type:
                corporate_count += 1

ratio = corporate_count / academic_count if academic_count > 0 else 0
print(f"Corporate/Academic Ratio: {ratio:.2f}")
# >1.0 = commercialization phase, <0.5 = early research phase
```

### 3. Patent-Paper Citation Lag
**Question**: "How long from research → commercialization?"

**Query**:
```python
papers_cited_by_patents = [p for p in papers if p.get('patent_citations_count', 0) > 0]

avg_lag = []
for paper in papers_cited_by_patents:
    pub_year = paper.get('year_published')
    # Cross-reference with patent data to find citing patents' dates
    # Calculate avg lag: patent_year - paper_year

print(f"Average research → patent lag: {sum(avg_lag)/len(avg_lag):.1f} years")
# eVTOL expected: 2-3 years (fast commercialization)
# Compare to mature fields: 5-7 years
```

### 4. Enabling Technology Maturity
**Question**: "Are enabling technologies (batteries, materials) advancing?"

**Query**:
```python
battery_papers = [p for p in papers if 'battery' in ' '.join(p.get('fields_of_study', [])).lower()]

battery_by_year = Counter(p.get('year_published') for p in battery_papers)
print(f"Battery Research Trend: {dict(battery_by_year)}")
# Growing = enabling tech maturing, shrinking = diminishing returns
```

---

## Success Criteria

### Functional Requirements
- [ ] Downloads 3,000+ papers for eVTOL test case
- [ ] Extracts funding data from 50%+ of papers
- [ ] Incremental saving prevents data loss
- [ ] Resume capability works after interruption
- [ ] Rate limits respected (no 429 errors)
- [ ] Deduplication removes cross-keyword duplicates
- [ ] Standardized output contract matches other downloaders

### Data Quality Requirements
- [ ] All papers have `lens_id` (unique identifier)
- [ ] Funding organizations normalized (NASA, not "NASA Ames", "NASA JPL")
- [ ] Author affiliations include organization type (education/company/government)
- [ ] Date fields valid (year_published matches date_published)
- [ ] Fields of study populated for topic analysis

### Integration Requirements
- [ ] Orchestrator integration seamless
- [ ] Config-driven (no hardcoded keywords)
- [ ] Logging follows established patterns
- [ ] Error handling graceful (single keyword failure doesn't stop harvest)
- [ ] Compatible with existing checkpoint system

---

## Known Challenges & Solutions

### Challenge 1: Keyword Overlap
**Problem**: "eVTOL" and "electric VTOL" return overlapping papers

**Solution**: Deduplication by `lens_id` at end (already implemented in template)

### Challenge 2: Funding Organization Name Variations
**Problem**: "NASA", "NASA Ames Research Center", "National Aeronautics and Space Administration"

**Solution**: Add normalization function:
```python
def normalize_funding_org(org_name: str) -> str:
    """Normalize funding organization names."""
    org_name = org_name.upper()

    # NASA variations
    if 'NASA' in org_name or 'AERONAUTICS AND SPACE' in org_name:
        return 'NASA'

    # NSF variations
    if 'NSF' in org_name or 'NATIONAL SCIENCE FOUNDATION' in org_name:
        return 'NSF'

    # DOE variations
    if 'DOE' in org_name or 'DEPARTMENT OF ENERGY' in org_name:
        return 'DOE'

    # DARPA variations
    if 'DARPA' in org_name or 'DEFENSE ADVANCED RESEARCH' in org_name:
        return 'DARPA'

    # Keep as-is if no match
    return org_name.title()
```

### Challenge 3: Year vs Date Filtering
**Problem**: API may support `year_published` (int) or `date_published` (string) filters

**Solution**: Test both in initial implementation:
```python
# Try year-based first (simpler)
"range": {
    "year_published": {
        "gte": 2020,
        "lte": 2024
    }
}

# Fallback to date-based if year not supported
"range": {
    "date_published": {
        "gte": "2020-01-01",
        "lte": "2024-12-31"
    }
}
```

### Challenge 4: Abstract vs Full Text
**Problem**: Some papers may not have abstracts

**Solution**: Use `title` + `abstract` for keyword matching, gracefully handle missing abstracts:
```python
abstract = paper.get('abstract') or paper.get('title') or "No abstract available"
```

---

## Post-Implementation Validation

### Data Sanity Checks

**Run these queries after harvest**:

1. **Check for duplicates**:
```python
lens_ids = [p['lens_id'] for p in papers]
duplicates = len(lens_ids) - len(set(lens_ids))
assert duplicates == 0, f"Found {duplicates} duplicate lens_ids!"
```

2. **Check funding coverage**:
```python
with_funding = len([p for p in papers if p.get('funding')])
coverage = with_funding / len(papers) * 100
assert coverage > 40, f"Only {coverage:.1f}% have funding data (expected >40%)"
```

3. **Check year distribution**:
```python
years = [p.get('year_published') for p in papers if p.get('year_published')]
min_year, max_year = min(years), max(years)
assert min_year >= 2020, f"Papers older than expected: {min_year}"
assert max_year <= 2025, f"Papers newer than expected: {max_year}"
```

4. **Check keyword match distribution**:
```python
from collections import Counter
matches = Counter(p.get('matched_keyword') for p in papers)
print(f"Papers per keyword: {dict(matches)}")
# Should be relatively balanced, not 99% from one keyword
```

---

## Timeline Estimate

**After Lens grants Scholarly Works access**:

1. **Phase 1 - Implementation**: 2-3 hours
   - Copy template from lens_patents.py
   - Adapt for keyword-based search
   - Implement funding extraction
   - Add incremental saving

2. **Phase 2 - Testing**: 1-2 hours
   - Token validation test
   - Single keyword test (50 papers)
   - Validate output structure
   - Fix any issues

3. **Phase 3 - Integration**: 30 minutes
   - Update evtol_config.json
   - Update orchestrator.py
   - Verify initialization

4. **Phase 4 - Full Harvest**: 30-60 minutes
   - Run full keyword harvest
   - Validate data quality
   - Check stats and logs

**Total**: ~4-6 hours from token ready to full harvest complete

---

## Next Session Checklist

**Before Starting**:
- [ ] Verify `LENS_API_TOKEN` has Scholarly Works access
- [ ] Run `python test_lens_scholarly_api.py` → expect HTTP 200
- [ ] Review this document

**Implementation Order**:
1. [ ] Create `src/downloaders/lens_scholarly.py` from template
2. [ ] Implement `_search_by_keyword()` method
3. [ ] Implement `_extract_paper_data()` method
4. [ ] Implement pagination loop
5. [ ] Add rate limit handling
6. [ ] Test with `configs/evtol_test_scholarly.json`
7. [ ] Validate output structure
8. [ ] Update `configs/evtol_config.json`
9. [ ] Update `src/core/orchestrator.py`
10. [ ] Run full harvest
11. [ ] Validate data quality
12. [ ] Update todo list and mark complete

---

**Document Status**: Ready for implementation
**Blockers**: Awaiting Lens Scholarly Works API access approval
**Contact**: https://www.lens.org/lens/user/subscriptions (request access)

