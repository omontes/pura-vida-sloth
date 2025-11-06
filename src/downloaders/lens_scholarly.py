"""
Lens Scholarly Works Downloader - Using Lens.org Scholarly Works API
====================================================================
Comprehensive scholarly works downloader using the Lens.org Scholarly Works API.

Strategic Value:
- Fills Layer 2 (Market Formation) gap with research funding data
- Tracks government/institutional research investment trends
- Identifies academic vs corporate research balance
- Measures research impact via citation metrics

Coverage:
- 200M+ scholarly works (global academic database)
- Funding data (NASA, DARPA, NSF, DOE, EU Commission, etc.)
- Author affiliations (academic vs corporate research institutions)
- Citation metrics (scholarly citations + patent citations)
- Full-text search with keyword matching

Target: 1,000 papers per keyword (~4,000-6,000 total for 6 keywords)
Primary Source: Lens.org (https://www.lens.org)
API Docs: https://docs.api.lens.org/scholar.html

API Features:
- Elasticsearch-based query syntax
- Cursor-based pagination (scroll) for large result sets
- Rich metadata (funding, affiliations, citations)
- Rate limits: 10 requests/minute (Institutional User tier)
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
import time
import requests
import os

from src.utils.logger import setup_logger
from src.utils.checkpoint_manager import CheckpointManager


class LensScholarlyDownloader:
    """
    Download scholarly works using Lens.org Scholarly Works API.
    CRITICAL: Industry-agnostic design - accepts keyword list from config.

    Mandatory Design Patterns:
    1. Incremental Persistence - Save after each keyword
    2. Graceful Degradation - Continue on single keyword failure
    3. Rate Limit Handling - Exponential backoff + header monitoring
    4. Standardized Output Contract - Stats dict format
    5. Checkpoint/Resume - Track completed keywords
    6. Industry-Agnostic - All keywords from config
    """

    # Lens API endpoints
    BASE_URL = "https://api.lens.org/scholarly/search"

    # Rate limiting (Institutional User tier)
    RATE_LIMIT_RPM = 10  # Requests per minute
    RATE_LIMIT_DELAY = 6  # Seconds between requests (conservative)
    RECORDS_PER_REQUEST = 500  # Max for free/institutional tier

    # Optimized include fields for strategic intelligence + PDF access
    INCLUDE_FIELDS = [
        # === CORE IDENTIFICATION ===
        "lens_id",
        "title",
        "date_published",
        "year_published",
        "publication_type",
        "publication_supplementary_type",  # NEW: Reviews, clinical trials, meta-analyses

        # === CRITICAL: CONTENT ACCESS (PDF Download) ===
        "external_ids",  # NEW: DOI, PubMed, PMC, ArXiv IDs
        "open_access",   # NEW: License, OA status, PDF URLs, landing pages
        "source_urls",   # NEW: Direct content URLs (html, pdf)

        # === FUNDING (Layer 2 - Market Formation) ===
        "funding",

        # === CITATIONS (Cross-Layer Analysis) ===
        "scholarly_citations_count",
        "scholarly_citations",      # NEW: List of citing works
        "patent_citations_count",
        "patent_citations",         # NEW: List of citing patents (Layer 1 link)
        "references_count",
        "references",               # NEW: Full reference list

        # === AUTHORS & AFFILIATIONS ===
        "authors",
        "author_count",

        # === CLASSIFICATION & KEYWORDS ===
        "fields_of_study",
        "keywords",
        "mesh_terms",   # NEW: Medical Subject Headings

        # === RESEARCH CONTEXT ===
        "clinical_trials",  # NEW: Clinical trial registries
        "chemicals",        # NEW: Chemical substances (biotech/materials)

        # === SOURCE PUBLICATION ===
        "source",
        "abstract"
    ]

    def __init__(
        self,
        output_dir: Path,
        start_date: str,
        end_date: str,
        keywords: List[str],  # From config.keywords
        limit: int = 1000,  # Papers per keyword
        **optional_params
    ):
        """
        Initialize Lens Scholarly Works downloader

        Args:
            output_dir: Directory to save papers
            start_date: Start date (ISO format YYYY-MM-DD)
            end_date: End date (ISO format YYYY-MM-DD)
            keywords: List of keywords from config (scholarly-optimized)
            limit: Maximum papers to download per keyword (default 1000)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Get API token from environment
        self.api_token = os.getenv('LENS_API_TOKEN')
        if not self.api_token:
            raise ValueError(
                "LENS_API_TOKEN not found in environment. "
                "Please add it to your .env file. "
                "Get your free API key at: https://www.lens.org/lens/user/subscriptions"
            )

        # Parse dates to year for year_published filter
        self.start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        self.end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        self.start_year = self.start_date.year
        self.end_year = self.end_date.year

        self.keywords = keywords
        self.limit = limit

        self.logger = setup_logger("LensScholarly", self.output_dir / "scholarly.log")
        self.checkpoint = CheckpointManager(self.output_dir, 'lens_scholarly')

        # Setup session for Lens API
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Strategic Intelligence Harvester/1.0'
        })

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

        CRITICAL: Saves papers after each keyword to prevent data loss on interruption.

        Returns:
            {
                'success': int,
                'failed': int,
                'skipped': int,
                'total_size': float,
                'by_keyword': dict
            }
        """
        self.logger.info(f"Starting Lens Scholarly Works API download")
        self.logger.info(f"Year range: {self.start_year} to {self.end_year}")
        self.logger.info(f"Keywords: {len(self.keywords)}")
        self.logger.info(f"Limit per keyword: {self.limit}")

        # INCREMENTAL SAVING: Load existing papers if resuming
        all_papers = self._load_existing_papers()
        existing_count = len(all_papers)
        if existing_count > 0:
            self.logger.info(f"Loaded {existing_count} existing papers from previous run")

        # Search by keyword
        for keyword in self.keywords:
            # Skip if already completed
            checkpoint_key = f"keyword_{keyword}"
            if self.checkpoint.is_completed(checkpoint_key):
                self.logger.info(f"Skipping {keyword} (already completed)")
                self.stats['skipped'] += 1
                continue

            self.logger.info(f"Searching papers for: {keyword}")

            try:
                papers = self._search_by_keyword(keyword)

                # INCREMENTAL SAVING: Append new papers immediately
                if papers:
                    all_papers.extend(papers)
                    # Save after each keyword to prevent data loss
                    self._save_papers_incremental(all_papers)

                self.stats['by_keyword'][keyword] = len(papers)
                self.logger.info(f"  Found {len(papers)} papers for {keyword}")

                # Mark keyword as completed
                self.checkpoint.mark_completed(checkpoint_key, metadata={
                    'keyword': keyword,
                    'papers_count': len(papers)
                })

            except Exception as e:
                self.logger.error(f"Error searching papers for {keyword}: {e}")
                self.stats['by_keyword'][keyword] = 0
                self.stats['failed'] += 1

        # Final deduplication and save
        unique_papers = self._deduplicate_papers(all_papers)
        self.logger.info(f"Total unique papers: {len(unique_papers)}")

        # Final save with deduplicated data
        if unique_papers:
            self._save_papers(unique_papers)
            self._save_metadata(unique_papers)

        # Finalize checkpoint
        self.checkpoint.finalize()

        self._print_summary()

        return self.stats

    def _search_by_keyword(self, keyword: str) -> List[Dict]:
        """
        Search scholarly works by keyword using Lens Scholarly API.
        Uses cursor-based pagination (scroll) for large result sets.
        """
        papers = []

        try:
            # Build Lens API query (Elasticsearch-based)
            query = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "match": {
                                    "title": keyword
                                }
                            },
                            {
                                "match": {
                                    "abstract": keyword
                                }
                            }
                        ],
                        "minimum_should_match": 1,
                        "filter": {
                            "range": {
                                "year_published": {
                                    "gte": self.start_year,
                                    "lte": self.end_year
                                }
                            }
                        }
                    }
                },
                "include": self.INCLUDE_FIELDS,
                "size": self.RECORDS_PER_REQUEST,  # 500 records per request
                "scroll": "5m"  # Keep scroll context alive for 5 minutes
            }

            self.logger.debug(f"  Query: match title/abstract: {keyword}")
            self.logger.debug(f"  Year range: {self.start_year} to {self.end_year}")

            # Initial request
            response = self._make_request(query)

            if not response:
                return papers

            # Process initial results
            data = response.json()
            total_available = data.get('total', 0)
            self.logger.info(f"  Total available: {total_available} papers")

            # Process first batch
            results = data.get('data', [])
            papers.extend(self._process_results(results, keyword))

            # Pagination using scroll
            scroll_id = data.get('scroll_id')

            while scroll_id and len(papers) < self.limit and len(papers) < total_available:
                # Get next batch using scroll_id
                scroll_query = {
                    "scroll_id": scroll_id,
                    "scroll": "5m"
                }

                response = self._make_request(scroll_query)
                if not response:
                    break

                data = response.json()
                results = data.get('data', [])

                if not results:
                    # No more results
                    break

                papers.extend(self._process_results(results, keyword))
                scroll_id = data.get('scroll_id')

                # Update progress
                self.logger.debug(f"  Fetched {len(papers)}/{min(self.limit, total_available)} papers")

            # Rate limiting: conservative delay between keywords
            time.sleep(self.RATE_LIMIT_DELAY)

        except Exception as e:
            self.logger.error(f"Error in search for '{keyword}': {e}")
            import traceback
            self.logger.error(traceback.format_exc())

        return papers[:self.limit]  # Ensure we don't exceed limit

    def _make_request(self, query: Dict) -> Optional[requests.Response]:
        """
        Make a request to Lens API with retry logic and rate limit handling.
        """
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                response = self.session.post(
                    self.BASE_URL,
                    json=query,
                    timeout=30
                )

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('x-rate-limit-retry-after-seconds', 60))
                    self.logger.warning(f"  Rate limit hit, waiting {retry_after}s...")
                    time.sleep(retry_after)
                    retry_count += 1
                    continue

                # Handle end of scroll (no more results)
                if response.status_code == 204:
                    self.logger.debug("  End of results (HTTP 204)")
                    return None

                # Handle errors
                if response.status_code != 200:
                    # Log the full error response for debugging
                    try:
                        error_detail = response.json()
                        self.logger.error(f"  API Error Response: {error_detail}")
                    except:
                        self.logger.error(f"  API Error Response: {response.text}")

                response.raise_for_status()

                # Check rate limit headers
                remaining_minute = response.headers.get('x-rate-limit-remaining-request-per-minute')
                remaining_month = response.headers.get('x-rate-limit-remaining-request-per-month')
                if remaining_minute:
                    self.logger.debug(f"  Rate limit remaining: {remaining_minute} requests/minute")
                if remaining_month:
                    self.logger.debug(f"  Monthly quota remaining: {remaining_month} requests")

                return response

            except requests.exceptions.RequestException as e:
                self.logger.error(f"  Request error: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # Exponential backoff
                    self.logger.warning(f"  Retrying in {wait_time}s... (attempt {retry_count}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"  Max retries exceeded")
                    return None

        return None

    def _process_results(self, results: List[Dict], keyword: str) -> List[Dict]:
        """
        Process a batch of results from Lens API.
        """
        papers = []

        for result in results:
            try:
                # Get paper ID (lens_id)
                lens_id = result.get('lens_id')

                if not lens_id:
                    self.logger.debug("  Skipping result with no lens_id")
                    continue

                # Check checkpoint (skip if already processed)
                if self.checkpoint.is_completed(lens_id):
                    self.stats['skipped'] += 1
                    continue

                # Extract paper data
                paper_data = self._extract_paper_data(result, keyword)

                papers.append(paper_data)
                self.stats['success'] += 1

                # Mark as completed in checkpoint
                self.checkpoint.mark_completed(lens_id, metadata={
                    'title': paper_data.get('title'),
                    'keyword': keyword
                })

            except Exception as e:
                self.logger.error(f"  Error processing paper {lens_id}: {e}")
                self.stats['failed'] += 1
                if lens_id:
                    self.checkpoint.mark_failed(lens_id, str(e))

        return papers

    def _extract_paper_data(self, result: Dict, keyword: str) -> Dict:
        """
        Extract scholarly work data from Lens API response.

        Lens Scholarly API response format:
        {
            "lens_id": "001-234-567-890-123",
            "title": "Paper Title",
            "year_published": 2023,
            "date_published": "2023-06-15",
            "abstract": "Abstract text...",
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
            "fields_of_study": ["Aerospace Engineering"],
            "scholarly_citations_count": 42,
            "patent_citations_count": 3,
            "source": {
                "title": "Journal Name",
                "publisher": "IEEE",
                "country": "US"
            }
        }
        """
        lens_id = result.get('lens_id', '')
        title = result.get('title', 'Untitled')
        year_published = result.get('year_published', 0)
        date_published = result.get('date_published', '')
        publication_type = result.get('publication_type', 'unknown')

        # Extract abstract (handle different formats)
        abstract = ''
        abstract_data = result.get('abstract')
        if isinstance(abstract_data, str):
            abstract = abstract_data
        elif isinstance(abstract_data, list) and abstract_data:
            # Handle list of abstracts (multiple languages)
            for abs_obj in abstract_data:
                if isinstance(abs_obj, dict):
                    if abs_obj.get('lang') == 'en':
                        abstract = abs_obj.get('text', '')
                        break
            # If no English abstract, use first available
            if not abstract and abstract_data:
                if isinstance(abstract_data[0], dict):
                    abstract = abstract_data[0].get('text', '')

        # Extract funding data (CRITICAL for Layer 2 analysis)
        funding = []
        for grant in result.get('funding', []):
            org_name = grant.get('organisation', 'Unknown')
            # Normalize funding organization names
            normalized_org = self._normalize_funding_org(org_name)
            funding.append({
                'organisation': normalized_org,
                'organisation_raw': org_name,  # Keep original for reference
                'funding_id': grant.get('funding_id', ''),
                'country': grant.get('country', '')
            })

        # Extract authors and affiliations
        authors = []
        for author in result.get('authors', []):
            author_data = {
                'display_name': author.get('display_name', ''),
                'affiliations': []
            }

            for affil in author.get('affiliations', []):
                author_data['affiliations'].append({
                    'name': affil.get('name', ''),
                    'country_code': affil.get('country_code', '')
                })

            authors.append(author_data)

        # Extract citation metrics
        scholarly_citations = result.get('scholarly_citations_count', 0)
        patent_citations = result.get('patent_citations_count', 0)
        references_count = result.get('references_count', 0)

        # Extract fields of study
        fields_of_study = result.get('fields_of_study', [])
        paper_keywords = result.get('keywords', [])

        # Extract source metadata
        source_data = result.get('source', {})
        source = {
            'title': source_data.get('title', ''),
            'publisher': source_data.get('publisher', ''),
            'country': source_data.get('country', '')
        }

        # NEW: Extract external IDs (DOI, ArXiv, PubMed, etc.)
        external_ids = result.get('external_ids', [])

        # NEW: Extract open access information
        open_access = result.get('open_access', {})

        # NEW: Extract source URLs
        source_urls = result.get('source_urls', [])

        # NEW: Extract publication supplementary type
        publication_supplementary_type = result.get('publication_supplementary_type', [])

        # NEW: Extract clinical trials
        clinical_trials = result.get('clinical_trials', [])

        # NEW: Extract chemicals
        chemicals = result.get('chemicals', [])

        # NEW: Extract MeSH terms
        mesh_terms = result.get('mesh_terms', [])

        # NEW: Extract scholarly citations list
        scholarly_citations_list = result.get('scholarly_citations', [])

        # NEW: Extract patent citations list
        patent_citations_list = result.get('patent_citations', [])

        # NEW: Extract references list
        references = result.get('references', [])

        # Construct paper URL
        paper_url = f"https://link.lens.org/{lens_id}"

        return {
            'lens_id': lens_id,
            'title': title,
            'year_published': year_published,
            'date_published': date_published,
            'publication_type': publication_type,
            'publication_supplementary_type': publication_supplementary_type,  # NEW
            'abstract': abstract,
            'external_ids': external_ids,  # NEW
            'open_access': open_access,  # NEW
            'source_urls': source_urls,  # NEW
            'funding': funding,
            'authors': authors,
            'author_count': len(authors),
            'scholarly_citations_count': scholarly_citations,
            'scholarly_citations': scholarly_citations_list,  # NEW
            'patent_citations_count': patent_citations,
            'patent_citations': patent_citations_list,  # NEW
            'references_count': references_count,
            'references': references,  # NEW
            'fields_of_study': fields_of_study,
            'keywords': paper_keywords,
            'mesh_terms': mesh_terms,  # NEW
            'clinical_trials': clinical_trials,  # NEW
            'chemicals': chemicals,  # NEW
            'source': source,
            'matched_keyword': keyword,
            'harvested_at': datetime.now().isoformat(),
            'url': paper_url
        }

    def _normalize_funding_org(self, org_name: str) -> str:
        """
        Normalize funding organization names for consistent analysis.

        Examples:
        - "NASA Ames Research Center" → "NASA"
        - "National Science Foundation" → "NSF"
        - "European Commission" → "European Commission"
        """
        if not org_name:
            return 'Unknown'

        org_upper = org_name.upper()

        # NASA variations
        if 'NASA' in org_upper or 'AERONAUTICS AND SPACE' in org_upper:
            return 'NASA'

        # NSF variations
        if 'NSF' in org_upper or 'NATIONAL SCIENCE FOUNDATION' in org_upper:
            return 'NSF'

        # DOE variations
        if 'DOE' in org_upper or 'DEPARTMENT OF ENERGY' in org_upper:
            return 'DOE'

        # DARPA variations
        if 'DARPA' in org_upper or 'DEFENSE ADVANCED RESEARCH' in org_upper:
            return 'DARPA'

        # NIH variations
        if 'NIH' in org_upper or 'NATIONAL INSTITUTES OF HEALTH' in org_upper:
            return 'NIH'

        # DOD variations
        if 'DEPARTMENT OF DEFENSE' in org_upper or org_upper.startswith('DOD'):
            return 'DOD'

        # European Commission
        if 'EUROPEAN COMMISSION' in org_upper or 'EC ' in org_upper:
            return 'European Commission'

        # Keep original if no match (title case)
        return org_name.title()

    def _deduplicate_papers(self, papers: List[Dict]) -> List[Dict]:
        """Remove duplicate papers based on lens_id"""
        seen = set()
        unique = []

        for paper in papers:
            lens_id = paper.get('lens_id')
            if lens_id and lens_id not in seen:
                seen.add(lens_id)
                unique.append(paper)

        return unique

    def _load_existing_papers(self) -> List[Dict]:
        """
        Load existing papers from file if resuming.
        Returns empty list if no existing file found.
        """
        papers_file = self.output_dir / "papers.json"
        if papers_file.exists():
            try:
                with open(papers_file, 'r', encoding='utf-8') as f:
                    papers = json.load(f)
                return papers if isinstance(papers, list) else []
            except Exception as e:
                self.logger.warning(f"Could not load existing papers: {e}")
                return []
        return []

    def _save_papers_incremental(self, papers: List[Dict]):
        """
        Save papers incrementally (after each keyword).
        CRITICAL: This prevents data loss if harvest is interrupted.
        """
        papers_file = self.output_dir / "papers.json"
        try:
            with open(papers_file, 'w', encoding='utf-8') as f:
                json.dump(papers, f, indent=2, ensure_ascii=False)
            self.logger.debug(f"  Incremental save: {len(papers)} total papers")
        except Exception as e:
            self.logger.error(f"  Incremental save failed: {e}")

    def _save_papers(self, papers: List[Dict]):
        """Save final deduplicated papers to JSON file"""
        papers_file = self.output_dir / "papers.json"
        with open(papers_file, 'w', encoding='utf-8') as f:
            json.dump(papers, f, indent=2, ensure_ascii=False)

        file_size = papers_file.stat().st_size / (1024 * 1024)  # MB
        self.stats['total_size'] = file_size

        self.logger.info(f"Saved {len(papers)} papers to {papers_file} ({file_size:.2f} MB)")

    def _save_metadata(self, papers: List[Dict]):
        """Save metadata JSON with funding coverage analysis"""
        # Calculate funding coverage
        papers_with_funding = len([p for p in papers if p.get('funding')])
        funding_coverage_pct = (papers_with_funding / len(papers) * 100) if papers else 0

        # Get top funding organizations
        from collections import Counter
        funding_orgs = []
        for paper in papers:
            for grant in paper.get('funding', []):
                org = grant.get('organisation')
                if org:
                    funding_orgs.append(org)

        top_orgs = Counter(funding_orgs).most_common(10)

        metadata = {
            'source': 'lens_scholarly',
            'timestamp': datetime.now().isoformat(),
            'year_range': f"{self.start_year}-{self.end_year}",
            'keywords': self.keywords,
            'total_papers': len(papers),
            'stats': self.stats,
            'funding_coverage': {
                'papers_with_funding': papers_with_funding,
                'percentage': round(funding_coverage_pct, 2),
                'top_organizations': [
                    {'name': org, 'count': count} for org, count in top_orgs
                ]
            }
        }

        metadata_path = self.output_dir / "papers_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Metadata saved to {metadata_path}")
        self.logger.info(f"Funding coverage: {funding_coverage_pct:.1f}% ({papers_with_funding}/{len(papers)} papers)")

    def _print_summary(self):
        """Print download summary"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("LENS SCHOLARLY WORKS DOWNLOAD SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Success: {self.stats['success']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        self.logger.info(f"Skipped: {self.stats['skipped']}")
        self.logger.info(f"Total Size: {self.stats['total_size']:.2f} MB")
        self.logger.info("\nBy Keyword:")
        for keyword, count in sorted(self.stats['by_keyword'].items(), key=lambda x: x[1], reverse=True):
            self.logger.info(f"  {keyword}: {count} papers")
        self.logger.info("=" * 60)


# Standalone test block
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(" LENS SCHOLARLY WORKS API - STANDALONE TEST")
    print("=" * 60)
    print("\nTest Configuration:")
    print("  Keywords: 2 (eVTOL, urban air mobility)")
    print("  Limit: 1,000 papers per keyword")
    print("  Expected: ~1,500-2,000 papers (after dedup)")
    print("  Runtime: ~1-2 minutes")
    print("\n" + "=" * 60 + "\n")

    from pathlib import Path

    # Test output directory
    test_output = Path("data/eVTOL_SCHOLARLY_TEST")

    # Initialize downloader with test configuration
    downloader = LensScholarlyDownloader(
        output_dir=test_output / "lens_scholarly",
        start_date="2024-01-01",
        end_date="2025-01-01",
        keywords=["eVTOL", "urban air mobility"],  # 2 keywords for intermediate test
        limit=1000  # INTERMEDIATE test: 1,000 papers per keyword
    )

    # Run download
    results = downloader.download()

    # Print final results
    print("\n" + "=" * 60)
    print(" TEST COMPLETE")
    print("=" * 60)
    print(f"\nResults: {results}")
    print(f"\nOutput location: {test_output / 'lens_scholarly'}")
    print("\nNext steps:")
    print("  1. Review papers.json for keyword relevance")
    print("  2. Check papers_metadata.json for funding coverage")
    print("  3. Verify scholarly.log for rate limit monitoring")
    print("  4. If successful, enable in configs/evtol_config.json")
    print("\n" + "=" * 60 + "\n")
