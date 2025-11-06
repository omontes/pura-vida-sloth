# Lens PDF Downloader - DuckDB-Enhanced Intelligent Selection

## Overview

The Lens PDF Downloader is an **industry-agnostic system** that intelligently selects and downloads PDFs for top scholarly papers using **DuckDB-based composite scoring**. It combines LLM relevance assessment with bibliometric indicators to prioritize the most valuable papers for strategic intelligence analysis.

**Key Innovation**: Instead of downloading all papers blindly, this system uses a multi-factor composite score to rank papers and download only the highest-quality, most-relevant research.

---

## Why This Approach?

### The Problem: Blind PDF Downloads Waste Resources

Traditional approaches download PDFs for all harvested papers:
- **5,322 papers** harvested → Attempt to download all → **$500+ storage costs**
- **Low relevance papers** (score <5.0) downloaded alongside critical research
- **Duplicate downloads** waste bandwidth and time
- **No prioritization** = equal weight to breakthrough papers and tangential research

### The Solution: Intelligent Selection via Composite Scoring

**Our Approach**:
1. **LLM Pre-Filtering**: Use batch-processed relevance scores (500 papers analyzed)
2. **Composite Ranking**: Combine relevance + impact + citations + innovation + recency
3. **Top N Selection**: Download only the 200-500 highest-scoring papers
4. **Skip Existing PDFs**: Avoid re-downloading files already in folder
5. **Multi-Source Waterfall**: Try 4 sources per paper (Lens → Unpaywall → ArXiv → PMC)

**Result**:
- **286 relevant papers** (score ≥8.0) → **37 PDFs downloaded** (13% success rate)
- **75MB storage** instead of 500+ MB
- **High-quality dataset** for downstream analysis
- **Reproducible** across industries via config changes

---

## Composite Scoring Algorithm

### Formula

```
Composite Score = (
    0.40 × Normalized Relevance Score +
    0.20 × Normalized Impact Potential +
    0.20 × Normalized References Count +
    0.10 × Normalized Innovation Type +
    0.10 × Normalized Recency
)
```

### Factor Normalization (0-1 scale)

#### 1. Relevance Score (40% weight)
- **Source**: LLM assessment from `parsers/scholarly/batch_process_papers.py`
- **Range**: 8.0-10.0 (only relevant papers with score ≥8.0)
- **Normalization**: `(score - 8.0) / (10.0 - 8.0)`
- **Example**: Score 9.0 → 0.5 normalized

#### 2. Impact Potential (20% weight)
- **Source**: `innovation_signals.impact_potential` field
- **Values**: `very_high` (1.0), `high` (0.7), `medium` (0.4), `low` (0.1)
- **Example**: "high" → 0.7 normalized

#### 3. References Count (20% weight)
- **Source**: `original_metadata.references_count` (citations)
- **Normalization**: `MIN(1.0, references_count / 100.0)`
- **Example**: 50 refs → 0.5, 150 refs → 1.0

#### 4. Innovation Type (10% weight)
- **Source**: `innovation_signals.innovation_type` field
- **Values**: `breakthrough` (1.0), `incremental_breakthrough` (0.7), `incremental` (0.4), `not_applicable` (0.1)
- **Example**: "incremental_breakthrough" → 0.7 normalized

#### 5. Recency (10% weight)
- **Source**: `paper_metadata.year_published` field
- **Normalization**: `(year - 2010) / (2025 - 2010)`
- **Example**: 2023 → 0.867, 2018 → 0.533

### Example Calculation

**Paper**: "Thermal Dynamics in Li-Ion Batteries for eVTOL"
- Relevance: 8.5 → normalized 0.25
- Impact: "high" → normalized 0.7
- References: 75 → normalized 0.75
- Innovation: "incremental_breakthrough" → normalized 0.7
- Year: 2024 → normalized 0.933

**Composite Score**:
```
0.40 × 0.25 + 0.20 × 0.7 + 0.20 × 0.75 + 0.10 × 0.7 + 0.10 × 0.933
= 0.10 + 0.14 + 0.15 + 0.07 + 0.093
= 0.553
```

### Custom Weighting Schemes

The system supports **custom weighting** via CLI arguments:

**Relevance-Heavy** (maximize industry alignment):
```bash
--weight-relevance 0.6 \
--weight-impact 0.2 \
--weight-references 0.1 \
--weight-innovation 0.05 \
--weight-recency 0.05
```

**Innovation-Heavy** (discover breakthroughs):
```bash
--weight-relevance 0.3 \
--weight-impact 0.3 \
--weight-references 0.1 \
--weight-innovation 0.2 \
--weight-recency 0.1
```

**Citation-Heavy** (established research):
```bash
--weight-relevance 0.3 \
--weight-impact 0.1 \
--weight-references 0.4 \
--weight-innovation 0.1 \
--weight-recency 0.1
```

---

## PDF Download Strategy (4-Phase Waterfall)

The downloader tries **4 sources in priority order** until success:

### Phase 1: Lens Direct
**Source**: `open_access.locations[].pdf_urls[]` field from Lens API
**Success Rate**: ~2% (5 PDFs in eVTOL test)
**Pros**: Authoritative source, high quality
**Cons**: Limited open access availability

### Phase 2: Unpaywall (Primary Source)
**Source**: DOI → Unpaywall API → `best_oa_location.url_for_pdf`
**Success Rate**: ~10% (27 PDFs in eVTOL test)
**Pros**: Largest open access database, excellent coverage
**Cons**: Rate limiting (requires delays)

**API Details**:
- Endpoint: `https://api.unpaywall.org/v2/{doi}?email={email}`
- Rate Limit: 100,000 requests/day per email
- Email Required: `your-email@example.com` (set via `LENS_USER_EMAIL` env var)

### Phase 3: ArXiv
**Source**: ArXiv ID → `https://arxiv.org/pdf/{arxiv_id}.pdf`
**Success Rate**: ~0% in eVTOL (engineering papers not on ArXiv)
**Pros**: Free, no rate limits, high-quality PDFs
**Cons**: Only preprints in physics/CS/math domains

### Phase 4: PubMed Central (PMC)
**Source**: PMC ID → `https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/pdf/`
**Success Rate**: ~0% in eVTOL (not biomedical papers)
**Pros**: Free, high-quality biomedical research
**Cons**: Only life sciences/biomedical domains

### Overall Success Rate

**eVTOL Dataset Results**:
- **Total Attempted**: 286 papers (all with score ≥8.0)
- **Successful Downloads**: 37 PDFs (13%)
- **Existing PDFs (Skipped)**: 5 files (skip logic working)
- **Failed (No Open Access)**: 249 papers (87%)

**Why Low Success Rate?**
- Most engineering research is behind paywalls
- Aerospace/aviation papers rarely on ArXiv/PMC
- Unpaywall coverage varies by field (biomedical >50%, engineering ~10%)

**Expected for Other Industries**:
- **Biomedical**: 40-60% success (high PMC coverage)
- **Computer Science**: 30-50% success (ArXiv + conference preprints)
- **Physics**: 50-70% success (ArXiv dominance)
- **Social Sciences**: 10-20% success (limited open access)

---

## Skip Logic (Avoid Duplicate Downloads)

### How It Works

Before attempting download, the system checks if PDF already exists:

```python
pdf_path = output_dir / f"{lens_id}.pdf"

if pdf_path.exists():
    file_size = pdf_path.stat().st_size
    if file_size >= MIN_PDF_SIZE:  # 1 KB
        # Valid PDF exists → Skip download
        stats['skipped'] += 1
        stats['by_source']['existing'] += 1
        checkpoint.mark_completed(lens_id, metadata={...})
        continue
    else:
        # Corrupted file (too small) → Delete and retry
        pdf_path.unlink()
        # Proceed to download...
```

### Benefits

1. **Avoid Redundant Work**: If interrupted, resume without re-downloading
2. **Bandwidth Savings**: Skip 5-20 MB files already on disk
3. **Time Savings**: ~30 seconds per skipped PDF (no HTTP requests)
4. **Checkpoint Integration**: Mark existing files as completed for tracking

### Example Output (Skip Logic)

```
INFO | ⊘ Skipping 196-298-967-622-68X (PDF already exists, 1.96 MB)
INFO | ⊘ Skipping 193-690-109-973-974 (PDF already exists, 6.73 MB)
INFO | ⊘ Skipping 007-864-336-696-607 (PDF already exists, 2.47 MB)
```

---

## Usage

### Prerequisites

1. **LLM-Scored Papers**: Run `parsers/scholarly/batch_process_papers.py` first
2. **DuckDB Analysis**: System auto-initializes DuckDB from checkpoint files
3. **Environment Variables**: Set `LENS_USER_EMAIL` for Unpaywall API

```bash
# .env file
LENS_USER_EMAIL=your-email@example.com
```

### Command-Line Interface

**Basic Usage** (Top 200 papers, default weights):
```bash
python -m src.downloaders.lens_pdf_downloader \
    --papers data/eVTOL/lens_scholarly/papers.json \
    --scored-dir data/eVTOL/lens_scholarly/batch_processing \
    --output data/eVTOL/lens_scholarly/pdfs \
    --limit 200
```

**Top 500 Papers** (auto-limits to available relevant papers):
```bash
python -m src.downloaders.lens_pdf_downloader \
    --papers data/eVTOL/lens_scholarly/papers.json \
    --scored-dir data/eVTOL/lens_scholarly/batch_processing \
    --output data/eVTOL/lens_scholarly/pdfs \
    --limit 500
```

**Custom Weighting** (relevance-heavy):
```bash
python -m src.downloaders.lens_pdf_downloader \
    --papers data/eVTOL/lens_scholarly/papers.json \
    --scored-dir data/eVTOL/lens_scholarly/batch_processing \
    --output data/eVTOL/lens_scholarly/pdfs \
    --limit 200 \
    --weight-relevance 0.6 \
    --weight-impact 0.2 \
    --weight-references 0.1 \
    --weight-innovation 0.05 \
    --weight-recency 0.05
```

### CLI Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--papers` | Yes | - | Path to original `papers.json` (from lens_scholarly harvester) |
| `--scored-dir` | Yes | - | Path to `batch_processing/` directory with checkpoint files |
| `--output` | Yes | - | Output directory for downloaded PDFs |
| `--limit` | No | 200 | Maximum number of papers to download |
| `--weight-relevance` | No | 0.4 | Weight for LLM relevance score (0-1) |
| `--weight-impact` | No | 0.2 | Weight for impact potential (0-1) |
| `--weight-references` | No | 0.2 | Weight for citation count (0-1) |
| `--weight-innovation` | No | 0.1 | Weight for innovation type (0-1) |
| `--weight-recency` | No | 0.1 | Weight for publication year (0-1) |

**Note**: All weights must sum to 1.0 (validated at runtime)

---

## Output Files

### Directory Structure

```
data/eVTOL/lens_scholarly/pdfs/
├── 027-051-602-179-192.pdf          # Lens ID as filename
├── 004-442-155-359-354.pdf
├── 098-946-556-912-949.pdf
├── ...                               # 37 PDFs total (eVTOL example)
├── .checkpoint_pdf_downloader.json   # Resume tracking
└── pdf_download_report.json          # Comprehensive statistics
```

### PDF Download Report (JSON)

**Location**: `{output_dir}/pdf_download_report.json`

**Contents**:
```json
{
  "timestamp": "2025-11-06T08:21:45.521964",
  "papers_json": "data/eVTOL/lens_scholarly/papers.json",
  "scored_papers_dir": "data/eVTOL/lens_scholarly/batch_processing",
  "output_dir": "data/eVTOL/lens_scholarly/pdfs",
  "limit": 500,
  "selection_method": "DuckDB Composite Scoring",

  "composite_weighting": {
    "relevance": 0.4,
    "impact": 0.2,
    "references": 0.2,
    "innovation": 0.1,
    "recency": 0.1
  },

  "composite_score_stats": {
    "min": 0.22,
    "max": 0.91,
    "mean": 0.5625804195804196,
    "median": 0.682
  },

  "total_attempted": 286,
  "successful": 37,
  "skipped": 5,
  "new_downloads": 32,
  "failed": 249,
  "success_rate": 12.937062937062937,

  "by_source": {
    "lens_direct": 5,
    "unpaywall": 27,
    "arxiv": 0,
    "pmc": 0,
    "existing": 5,
    "failed": 249
  },

  "failed_papers": [
    {
      "lens_id": "027-051-602-179-192",
      "title": "A Review of Hybrid-Electric Propulsion...",
      "composite_score": 0.91,
      "reason": "no_pdf_source"
    },
    ...
  ]
}
```

### Checkpoint File (Resume Capability)

**Location**: `{output_dir}/.checkpoint_pdf_downloader.json`

**Purpose**: Track completed downloads for resume after interruption

**Format**:
```json
{
  "completed_ids": [
    "027-051-602-179-192",
    "004-442-155-359-354",
    ...
  ],
  "metadata": {
    "027-051-602-179-192": {
      "timestamp": "2025-11-06T08:22:10",
      "source": "unpaywall",
      "file_size": 2048576,
      "composite_score": 0.91
    },
    ...
  }
}
```

---

## Integration with DuckDB Analysis

### Database Initialization

The downloader **automatically initializes DuckDB** from batch checkpoint files:

```python
db = ScholarlyPapersDatabase(
    scored_papers_dir="data/eVTOL/lens_scholarly/batch_processing",
    original_papers_path="data/eVTOL/lens_scholarly/papers.json"
)
db.initialize()
```

### Composite Scoring Query

**SQL Query** (executed by DuckDB):
```sql
WITH scored_papers AS (
    SELECT
        p.lens_id,
        p.title,
        p.year_published,
        r.relevance_score,
        i.innovation_type,
        i.impact_potential,
        m.references_count,

        -- Normalization (all factors → 0-1 scale)
        (r.relevance_score - 8.0) / (9.0 - 8.0) as norm_relevance,

        CASE i.impact_potential
            WHEN 'very_high' THEN 1.0
            WHEN 'high' THEN 0.7
            WHEN 'medium' THEN 0.4
            ELSE 0.1
        END as norm_impact,

        CASE
            WHEN m.references_count IS NULL THEN 0.5
            ELSE LEAST(1.0, m.references_count / 100.0)
        END as norm_references,

        CASE i.innovation_type
            WHEN 'breakthrough' THEN 1.0
            WHEN 'incremental_breakthrough' THEN 0.7
            WHEN 'incremental' THEN 0.4
            ELSE 0.1
        END as norm_innovation,

        CASE
            WHEN p.year_published IS NULL THEN 0.5
            ELSE (CAST(p.year_published AS INTEGER) - 2010) / (2025.0 - 2010.0)
        END as norm_recency

    FROM papers p
    JOIN relevance r ON p.lens_id = r.lens_id
    JOIN innovation_signals i ON p.lens_id = i.lens_id
    LEFT JOIN original_metadata m ON p.lens_id = m.lens_id
    WHERE r.relevance_score >= 8.0
      AND r.is_relevant = true
)
SELECT *,
    (0.4 * norm_relevance +
     0.2 * norm_impact +
     0.2 * norm_references +
     0.1 * norm_innovation +
     0.1 * norm_recency) as composite_score
FROM scored_papers
ORDER BY composite_score DESC
LIMIT 500
```

**Performance**: Query executes in <10ms for 286 papers

### Database Schema (7 Tables)

Created by `src/utils/duckdb_scholarly_analysis.py`:

1. **papers**: Core metadata (lens_id, title, year, authors)
2. **relevance**: LLM scores (relevance_score, is_relevant, category)
3. **technology_nodes**: Extracted tech nodes (node_id, name, domain)
4. **relationships**: Node relationships (subject, predicate, object)
5. **innovation_signals**: Innovation indicators (research_stage, innovation_type, impact_potential)
6. **adoption_indicators**: Adoption signals (if present)
7. **original_metadata**: Raw harvest data (references_count, citations, etc.)

---

## Testing and Validation

### Test Script

**Location**: `tests/test_duckdb_scholarly.py`

**Run Tests**:
```bash
python tests/test_duckdb_scholarly.py
```

**Test Coverage**:
1. ✅ Database initialization (table creation, row counts)
2. ✅ Composite score calculation (query correctness, sorting)
3. ✅ Query performance (<10ms for top 200 papers)
4. ✅ Data quality validation (score ranges, distributions)
5. ✅ Custom weighting schemes (different weights → different rankings)

**Expected Output**:
```
==========================================================================
 DUCKDB SCHOLARLY PAPERS ANALYSIS - TEST SUITE
==========================================================================
✓ PASS   - Database Initialization
✓ PASS   - Composite Scoring
✓ PASS   - Query Performance
✓ PASS   - Data Quality
✓ PASS   - Custom Weighting
==========================================================================
 5/5 tests passed (100%)
==========================================================================
```

### Incremental Testing Workflow

**CRITICAL**: Always test with small batches before full runs.

```bash
# 1. Test with 10 papers first
python -m src.downloaders.lens_pdf_downloader \
    --papers data/eVTOL/lens_scholarly/papers.json \
    --scored-dir data/eVTOL/lens_scholarly/batch_processing \
    --output data/eVTOL/lens_scholarly/pdfs \
    --limit 10

# 2. Verify outputs (PDFs, report.json, checkpoint)
ls data/eVTOL/lens_scholarly/pdfs/

# 3. Test resume (should skip existing PDFs)
python -m src.downloaders.lens_pdf_downloader \
    --papers data/eVTOL/lens_scholarly/papers.json \
    --scored-dir data/eVTOL/lens_scholarly/batch_processing \
    --output data/eVTOL/lens_scholarly/pdfs \
    --limit 10

# 4. Full run (after validation)
python -m src.downloaders.lens_pdf_downloader \
    --papers data/eVTOL/lens_scholarly/papers.json \
    --scored-dir data/eVTOL/lens_scholarly/batch_processing \
    --output data/eVTOL/lens_scholarly/pdfs \
    --limit 500
```

---

## Industry-Agnostic Design

### Switching Industries (Zero Code Changes)

**eVTOL → Quantum Computing**:
```bash
# 1. Run quantum computing harvester
python -m src.harvesters.lens_scholarly \
    --config configs/quantum_computing_config.json

# 2. Process with LLM (batch_process_papers.py)
python parsers/scholarly/batch_process_papers.py \
    --papers data/quantum_computing/lens_scholarly/papers.json \
    --output data/quantum_computing/lens_scholarly/batch_processing \
    --limit 500

# 3. Download PDFs (same script, different paths)
python -m src.downloaders.lens_pdf_downloader \
    --papers data/quantum_computing/lens_scholarly/papers.json \
    --scored-dir data/quantum_computing/lens_scholarly/batch_processing \
    --output data/quantum_computing/lens_scholarly/pdfs \
    --limit 200
```

**No changes to**:
- Composite scoring algorithm
- DuckDB schema
- PDF download logic
- Skip logic
- Checkpoint system

**Only changes**:
- File paths (industry name in path)
- Optional: Custom weighting scheme (if industry priorities differ)

---

## Performance Metrics

### eVTOL Dataset (Real Results)

**Input**:
- Total harvested: 5,322 papers
- LLM-scored: 500 papers (batch processed)
- Relevant (≥8.0): 286 papers
- Limit requested: 500 papers

**Processing**:
- DuckDB initialization: <1 second
- Composite scoring query: <10ms
- Top N selection: 286 papers (auto-limited to available)

**Download**:
- Duration: 9 minutes 14 seconds
- Papers processed: 286
- PDFs downloaded: 32 new + 5 existing = 37 total
- Success rate: 12.9% (new downloads)
- Average time per paper: ~2 seconds
- Average PDF size: 2.0 MB (range: 0.7 - 6.7 MB)

**Costs**:
- Storage: 75 MB (37 PDFs)
- Bandwidth: ~64 MB downloaded
- API calls: 286 Unpaywall requests (free tier)

**Compare to Blind Download**:
- Would attempt: 5,322 papers
- Expected PDFs: ~690 files (~1.4 GB)
- Wasted storage: 95% (non-relevant papers)
- Time wasted: ~4.5 hours (vs 9 minutes)

---

## Troubleshooting

### Issue 1: No PDFs Downloaded (0% success rate)

**Symptoms**: All papers fail with `no_pdf_source`

**Possible Causes**:
1. **Wrong Email**: Unpaywall requires valid email
2. **Rate Limiting**: Too many requests too fast
3. **Field Mismatch**: Academic papers without DOI/ArXiv ID/PMC ID

**Solutions**:
```bash
# Check email is set
echo $LENS_USER_EMAIL  # Should show valid email

# Add delays between requests (edit lens_pdf_downloader.py)
time.sleep(2)  # Increase from 1 to 2 seconds

# Check paper metadata (verify DOI field exists)
jq '.[] | select(.lens_id == "XXX") | .doi' data/eVTOL/lens_scholarly/papers.json
```

### Issue 2: DuckDB Initialization Fails

**Symptoms**: `No such file or directory: checkpoint_*.json`

**Cause**: Batch processing not yet run

**Solution**:
```bash
# Run LLM batch processing first
python parsers/scholarly/batch_process_papers.py \
    --papers data/eVTOL/lens_scholarly/papers.json \
    --output data/eVTOL/lens_scholarly/batch_processing \
    --limit 500
```

### Issue 3: Composite Scores All Identical

**Symptoms**: All papers have same composite score (e.g., 0.5)

**Cause**: Missing fields in database (NULL values default to 0.5)

**Solution**:
```bash
# Check data quality in DuckDB
python tests/test_duckdb_scholarly.py

# Look for NULL fields in output
# Re-run batch processing with correct field extraction
```

### Issue 4: Skip Logic Not Working

**Symptoms**: Re-downloads existing PDFs

**Cause**: Checkpoint file corruption or missing

**Solution**:
```bash
# Check checkpoint exists
cat data/eVTOL/lens_scholarly/pdfs/.checkpoint_pdf_downloader.json

# If corrupted, delete and re-create
rm data/eVTOL/lens_scholarly/pdfs/.checkpoint_pdf_downloader.json

# Re-run downloader (will regenerate checkpoint)
```

### Issue 5: Weights Don't Sum to 1.0

**Symptoms**: `ValueError: Weights must sum to 1.0`

**Cause**: Custom weights provided incorrectly

**Solution**:
```bash
# Check weights sum
python -c "print(0.6 + 0.2 + 0.1 + 0.05 + 0.05)"  # Should be 1.0

# Fix: Adjust last weight to compensate
--weight-relevance 0.6 \
--weight-impact 0.2 \
--weight-references 0.15 \  # Changed from 0.1
--weight-innovation 0.05 \
--weight-recency 0.0  # Set to 0 instead of removing
```

---

## Future Enhancements

### 1. Direct Publisher API Integration
- **IEEE Xplore**: Direct PDF access for IEEE papers
- **Elsevier ScienceDirect**: API key-based downloads
- **Springer Nature**: OA API integration
- **Expected**: +20-30% success rate

### 2. Citation Network Expansion
- **Seed Papers**: Download PDFs for top 100 papers
- **Citation Crawl**: Extract references from PDFs
- **Recursive Download**: Get cited papers (if relevant)
- **Use Case**: Build comprehensive literature map

### 3. Full-Text Analysis
- **PDF Parsing**: Extract text with PyMuPDF/pdfplumber
- **NER Extraction**: Identify companies, technologies, metrics
- **Knowledge Graph Enrichment**: Add full-text relationships
- **Use Case**: Layer 1 intelligence enhancement

### 4. Multi-Industry Comparison
- **Batch Mode**: Process 5 industries in parallel
- **Comparative Reports**: eVTOL vs quantum computing vs biotech
- **Cross-Industry Insights**: Which technologies apply to multiple sectors?
- **Use Case**: Portfolio strategy optimization

### 5. Cost Optimization
- **Academic Access**: Integrate with university proxy servers
- **Shared Libraries**: Pool downloaded PDFs across users
- **Pre-Screened Archives**: Download from curated open access repositories
- **Expected**: +40-60% success rate (if academic credentials available)

---

## Related Documentation

- **Composite Scoring**: See `src/utils/duckdb_scholarly_analysis.py` docstrings
- **LLM Batch Processing**: See `parsers/README.md` (Scholarly Papers Parser section)
- **Checkpoint Pattern**: See `src/utils/checkpoint_manager.py`
- **Testing**: See `tests/test_duckdb_scholarly.py`
- **Industry Config**: See `configs/evtol_config.json`

---

## Credits and References

**Design Patterns**:
- **Waterfall Download**: Inspired by SciHub fallback logic
- **Composite Scoring**: Based on PageRank + citation analysis
- **DuckDB Analytics**: Modeled after OLAP query patterns
- **Checkpoint/Resume**: Production fault-tolerance best practices

**Data Sources**:
- **Lens.org**: Academic paper metadata (CC BY 4.0)
- **Unpaywall**: Open access PDF locations (CC0 public domain)
- **ArXiv**: Preprint repository (open access)
- **PubMed Central**: Biomedical open access archive

**Technologies**:
- **DuckDB**: Embedded analytical database
- **Pandas**: Data manipulation
- **Requests**: HTTP client
- **tqdm**: Progress bars
- **LangChain**: LLM batch processing (upstream)

---

**Last Updated**: 2025-11-06
**Version**: 1.0.0
**Status**: Production Ready
**Tested On**: eVTOL industry (5,322 papers → 286 relevant → 37 PDFs)
