"""
Lens Patent Downloader - Using Lens.org Patent API
====================================================
Comprehensive patent downloader using the Lens.org Patent API.

Advantages:
- Global patent database (100M+ patents from 95+ countries)
- Full-text search with advanced query capabilities
- Comprehensive metadata (claims, citations, legal status, CPC codes)
- Cursor-based pagination for large datasets
- Rich filtering options (assignee, date range, patent type)
- Well-documented REST API

Target: 300 patents per company (12,000+ total for 40+ companies)
Primary Source: Lens.org (https://www.lens.org)
API Docs: https://docs.api.lens.org/

API Features:
- Flexible search syntax (Elasticsearch-based)
- Rate limits tracked via response headers
- Cursor-based pagination (scroll) for large result sets
- Multiple date fields (filing, publication, grant)
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
from tqdm import tqdm
import time
import requests
import os

from src.utils.logger import setup_logger
from src.utils.checkpoint_manager import CheckpointManager


class LensPatentDownloader:
    """
    Download patent data using Lens.org Patent API.
    CRITICAL: Industry-agnostic design - accepts assignee list from config.
    """

    # Lens API endpoints
    BASE_URL = "https://api.lens.org/patent/search"

    def __init__(
        self,
        output_dir: Path,
        start_date: str,
        end_date: str,
        assignees: Dict[str, str],  # From config.companies
        limit: int = 300,  # Increased for comprehensive coverage
        **optional_params
    ):
        """
        Initialize Lens Patent downloader

        Args:
            output_dir: Directory to save patents
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            assignees: Dict of company names {ticker/id: name} from config
            limit: Maximum patents to download per assignee (default 300)
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

        self.start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        self.end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        self.assignees = list(assignees.values())  # Extract company names
        self.limit = limit

        self.logger = setup_logger("LensPatents", self.output_dir / "patents.log")
        self.checkpoint = CheckpointManager(self.output_dir, 'lens_patents')

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
            'by_assignee': {}
        }

    def download(self) -> Dict[str, Any]:
        """
        Main download method with incremental saving.

        CRITICAL: Saves patents after each company to prevent data loss on interruption.

        Returns:
            {
                'success': int,
                'failed': int,
                'skipped': int,
                'total_size': float,
                'by_assignee': dict
            }
        """
        self.logger.info(f"Starting Lens Patent API download")
        self.logger.info(f"Date range: {self.start_date.date()} to {self.end_date.date()}")
        self.logger.info(f"Assignees: {len(self.assignees)} companies")
        self.logger.info(f"Limit per assignee: {self.limit}")

        # INCREMENTAL SAVING: Load existing patents if resuming
        all_patents = self._load_existing_patents()
        existing_count = len(all_patents)
        if existing_count > 0:
            self.logger.info(f"Loaded {existing_count} existing patents from previous run")

        # Search by assignee (company name)
        for assignee in self.assignees:
            self.logger.info(f"Searching patents for: {assignee}")

            try:
                patents = self._search_by_assignee(assignee)

                # INCREMENTAL SAVING: Append new patents immediately
                if patents:
                    all_patents.extend(patents)
                    # Save after each company to prevent data loss
                    self._save_patents_incremental(all_patents)

                self.stats['by_assignee'][assignee] = len(patents)
                self.logger.info(f"  Found {len(patents)} patents for {assignee}")

            except Exception as e:
                self.logger.error(f"Error searching patents for {assignee}: {e}")
                self.stats['by_assignee'][assignee] = 0

        # Final deduplication and save
        unique_patents = self._deduplicate_patents(all_patents)
        self.logger.info(f"Total unique patents: {len(unique_patents)}")

        # Final save with deduplicated data
        if unique_patents:
            self._save_patents(unique_patents)
            self._save_metadata(unique_patents)

        # Finalize checkpoint
        self.checkpoint.finalize()

        self._print_summary()

        return self.stats

    def _search_by_assignee(self, assignee: str) -> List[Dict]:
        """
        Search patents by assignee (company) using Lens Patent API.
        Uses cursor-based pagination (scroll) for large result sets.
        """
        patents = []

        try:
            # Build Lens API query (Elasticsearch-based)
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "match": {
                                    "applicant.name": assignee
                                }
                            },
                            {
                                "range": {
                                    "date_published": {
                                        "gte": self.start_date.strftime("%Y-%m-%d"),
                                        "lte": self.end_date.strftime("%Y-%m-%d")
                                    }
                                }
                            }
                        ]
                    }
                },
                "include": [
                    # === EXISTING CORE FIELDS (14) ===
                    "lens_id",
                    "doc_number",
                    "jurisdiction",
                    "kind",
                    "date_published",
                    "biblio.invention_title",
                    "abstract",
                    "biblio.parties.applicants",
                    "biblio.parties.inventors",
                    "biblio.application_reference.date",
                    "legal_status.grant_date",
                    "legal_status.granted",
                    "legal_status.patent_status",
                    "biblio.classifications_cpc",
                    "biblio.references_cited",

                    # === NEW CRITICAL FIELDS (PDF Access + 3 fields) ===
                    "doc_key",                              # For PDF URL construction
                    "publication_type",                     # GRANTED_PATENT vs PATENT_APPLICATION
                    "lang",                                 # Filter English patents

                    # === NEW CRITICAL FIELDS (Strategic Intelligence + 5 fields) ===
                    "families.simple_family.size",          # Patent family breadth
                    "families.extended_family.size",        # Global coverage
                    "biblio.cited_by",                      # Forward citations (impact)
                    "biblio.parties.owners_all",            # Current ownership (M&A tracking)
                    "biblio.priority_claims",               # Priority claims with earliest date

                    # === NEW CRITICAL FIELDS (Legal Status + 3 fields) ===
                    "legal_status.anticipated_term_date",   # Patent expiry date
                    "legal_status.discontinuation_date",    # Abandonment/lapse date
                    "legal_status.has_disclaimer",          # Terminal disclaimer (US)

                    # === NEW HIGH-VALUE FIELDS (Classifications + 1 field) ===
                    "biblio.classifications_ipcr",          # International classification

                    # === NEW MUST-HAVE FIELDS (Full Text + 2 fields) ===
                    "description",                          # Full technical specification (CRITICAL)
                    "claims"                                # Full claims text (legal scope)
                ],
                "size": 100,  # Max 100 per page
                "scroll": "1m"  # Keep scroll context alive for 1 minute
            }

            self.logger.debug(f"  Query: match applicant.name: {assignee}")
            self.logger.debug(f"  Date range: {self.start_date.date()} to {self.end_date.date()}")

            # Initial request
            response = self._make_request(query)

            if not response:
                return patents

            # Process initial results
            data = response.json()
            total_available = data.get('total', 0)
            self.logger.info(f"  Total available: {total_available} patents")

            # Process first batch
            results = data.get('data', [])
            patents.extend(self._process_results(results, assignee))

            # Pagination using scroll
            scroll_id = data.get('scroll_id')

            while scroll_id and len(patents) < self.limit and len(patents) < total_available:
                # Get next batch using scroll_id
                scroll_query = {
                    "scroll_id": scroll_id,
                    "scroll": "1m"
                }

                response = self._make_request(scroll_query)
                if not response:
                    break

                data = response.json()
                results = data.get('data', [])

                if not results:
                    # No more results
                    break

                patents.extend(self._process_results(results, assignee))
                scroll_id = data.get('scroll_id')

                # Update progress bar
                self.logger.debug(f"  Fetched {len(patents)}/{min(self.limit, total_available)} patents")

            # Rate limiting: be conservative
            time.sleep(2)  # 2 second delay between searches

        except Exception as e:
            self.logger.error(f"Error in search for '{assignee}': {e}")
            import traceback
            self.logger.error(traceback.format_exc())

        return patents[:self.limit]  # Ensure we don't exceed limit

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
                remaining = response.headers.get('x-rate-limit-remaining-request-per-minute')
                if remaining:
                    self.logger.debug(f"  Rate limit remaining: {remaining} requests/minute")

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

    def _process_results(self, results: List[Dict], assignee: str) -> List[Dict]:
        """
        Process a batch of results from Lens API.
        """
        patents = []

        for result in results:
            try:
                # Get patent ID (lens_id)
                lens_id = result.get('lens_id')

                if not lens_id:
                    self.logger.debug("  Skipping result with no lens_id")
                    continue

                # Check checkpoint (skip if already processed)
                if self.checkpoint.is_completed(lens_id):
                    self.stats['skipped'] += 1
                    continue

                # Extract patent data
                patent_data = self._extract_patent_data(result, assignee)

                patents.append(patent_data)
                self.stats['success'] += 1

                # Mark as completed in checkpoint
                self.checkpoint.mark_completed(lens_id, metadata={
                    'title': patent_data.get('title'),
                    'assignee': patent_data.get('assignee')
                })

            except Exception as e:
                self.logger.error(f"  Error processing patent {lens_id}: {e}")
                self.stats['failed'] += 1
                if lens_id:
                    self.checkpoint.mark_failed(lens_id, str(e))

        return patents

    def _extract_patent_data(self, result: Dict, assignee: str) -> Dict:
        """
        Extract patent data from Lens API response.

        Lens API response format:
        {
            "lens_id": "123-456-789-012-345",
            "doc_number": "US1234567890B2",
            "jurisdiction": "US",
            "kind": "B2",
            "date_published": "2024-01-15",
            "biblio": {
                "invention_title": [{"lang": "en", "text": "Patent Title"}],
                "parties": {
                    "applicants": [{"name": "Company Name", ...}],
                    "inventors": [{"name": "John Doe", ...}]
                },
                "application_reference": {"date": "2022-06-10"},
                "classifications_cpc": [{"symbol": "B64C39/02"}],
                "references_cited": {"patent_count": 12, "npl_count": 5}
            },
            "abstract": [{"lang": "en", "text": "Abstract text..."}],
            "legal_status": {
                "granted": true,
                "grant_date": "2024-01-15",
                "patent_status": "ACTIVE"
            }
        }
        """
        lens_id = result.get('lens_id', '')
        doc_number = result.get('doc_number', '')
        jurisdiction = result.get('jurisdiction', '')
        kind = result.get('kind', '')

        # Extract title (handle multiple languages, prefer English)
        title = ''
        invention_titles = result.get('biblio', {}).get('invention_title', [])
        if invention_titles:
            # Try to find English title first
            for title_obj in invention_titles:
                if title_obj.get('lang') == 'en':
                    title = title_obj.get('text', '')
                    break
            # If no English title, use first available
            if not title and invention_titles:
                title = invention_titles[0].get('text', '')

        # Extract abstract (handle multiple languages, prefer English)
        abstract = ''
        abstract_list = result.get('abstract', [])
        if abstract_list:
            # Try to find English abstract first
            for abstract_obj in abstract_list:
                if abstract_obj.get('lang') == 'en':
                    abstract = abstract_obj.get('text', '')
                    break
            # If no English abstract, use first available
            if not abstract and abstract_list:
                abstract = abstract_list[0].get('text', '')

        # Extract applicants (assignees)
        biblio = result.get('biblio', {})
        parties = biblio.get('parties', {})
        applicants = parties.get('applicants', [])

        # Get primary assignee name
        assignee_name = assignee  # Default to search assignee
        if applicants:
            assignee_name = applicants[0].get('name', assignee)

        # Extract inventors
        inventors = parties.get('inventors', [])
        inventor_names = [inv.get('name', '') for inv in inventors if inv.get('name')]

        # Extract dates
        date_published = result.get('date_published', '')

        filing_date = ''
        app_ref = biblio.get('application_reference', {})
        if isinstance(app_ref, dict):
            filing_date = app_ref.get('date', '')
        elif isinstance(app_ref, list) and app_ref:
            filing_date = app_ref[0].get('date', '')

        grant_date = ''
        legal_status = result.get('legal_status', {})
        if isinstance(legal_status, dict):
            grant_date = legal_status.get('grant_date', '')
            is_granted = legal_status.get('granted', False)
        else:
            is_granted = False

        # If no grant date, use publication date for granted patents
        if not grant_date and is_granted:
            grant_date = date_published

        # Extract CPC codes
        cpc_classifications = biblio.get('classifications_cpc', [])
        cpc_codes = []
        if isinstance(cpc_classifications, list):
            cpc_codes = [cpc.get('symbol', '') for cpc in cpc_classifications if cpc.get('symbol')]

        # Extract citation counts
        refs_cited = biblio.get('references_cited', {})
        patent_citations = 0
        npl_citations = 0
        npl_resolved_count = 0
        detailed_citations = []
        if isinstance(refs_cited, dict):
            patent_citations = refs_cited.get('patent_count', 0)
            npl_citations = refs_cited.get('npl_count', 0)
            npl_resolved_count = refs_cited.get('npl_resolved_count', 0)
            # Extract detailed citation list
            detailed_citations = refs_cited.get('citations', [])

        # === NEW: PDF ACCESS FIELDS ===
        doc_key = result.get('doc_key', '')
        publication_type = result.get('publication_type', 'UNKNOWN')
        lang = result.get('lang', '')

        # === NEW: FAMILY DATA ===
        families = result.get('families', {})
        simple_family_size = 0
        extended_family_size = 0
        if isinstance(families, dict):
            simple_family = families.get('simple_family', {})
            if isinstance(simple_family, dict):
                simple_family_size = simple_family.get('size', 0)
            extended_family = families.get('extended_family', {})
            if isinstance(extended_family, dict):
                extended_family_size = extended_family.get('size', 0)

        # === NEW: FORWARD CITATIONS (IMPACT) ===
        cited_by = biblio.get('cited_by', {})
        forward_citation_count = 0
        forward_citation_lens_ids = []
        if isinstance(cited_by, dict):
            citing_patents = cited_by.get('patents', [])
            if isinstance(citing_patents, list):
                forward_citation_count = len(citing_patents)
                forward_citation_lens_ids = [p.get('lens_id', '') for p in citing_patents if isinstance(p, dict)]

        # === NEW: OWNERSHIP DATA (M&A TRACKING) ===
        owners_all = parties.get('owners_all', [])
        current_owners = []
        if isinstance(owners_all, list):
            for owner in owners_all:
                if isinstance(owner, dict):
                    extracted_name = owner.get('extracted_name', {})
                    owner_name = ''
                    if isinstance(extracted_name, dict):
                        owner_name = extracted_name.get('value', '')
                    current_owners.append({
                        'name': owner_name,
                        'recorded_date': owner.get('recorded_date', ''),
                        'execution_date': owner.get('execution_date', ''),
                        'country': owner.get('extracted_country', '')
                    })

        # === NEW: PRIORITY DATA ===
        priority_claims = biblio.get('priority_claims', {})
        earliest_priority_date = ''
        if isinstance(priority_claims, dict):
            earliest_claim = priority_claims.get('earliest_claim', {})
            if isinstance(earliest_claim, dict):
                earliest_priority_date = earliest_claim.get('date', '')

        # === NEW: LEGAL STATUS DETAILS ===
        anticipated_term_date = ''
        discontinuation_date = ''
        has_disclaimer = False
        if isinstance(legal_status, dict):
            anticipated_term_date = legal_status.get('anticipated_term_date', '')
            discontinuation_date = legal_status.get('discontinuation_date', '')
            has_disclaimer = legal_status.get('has_disclaimer', False)

        # === NEW: IPCR CLASSIFICATIONS ===
        ipcr_classifications = biblio.get('classifications_ipcr', [])
        ipcr_codes = []
        if isinstance(ipcr_classifications, list):
            for cls in ipcr_classifications:
                if isinstance(cls, dict):
                    symbol = cls.get('symbol', '')
                    if symbol:
                        ipcr_codes.append(symbol)

        # === NEW: FULL TEXT CONTENT (MUST-HAVE) ===
        # Description - may be list of dicts with lang/text or string
        description = ''
        description_raw = result.get('description', '')
        if isinstance(description_raw, list):
            # Prefer English description
            for desc_obj in description_raw:
                if isinstance(desc_obj, dict) and desc_obj.get('lang') == 'en':
                    description = desc_obj.get('text', '')
                    break
            # If no English, use first available
            if not description and description_raw:
                first_desc = description_raw[0]
                if isinstance(first_desc, dict):
                    description = first_desc.get('text', '')
        elif isinstance(description_raw, str):
            description = description_raw

        # Claims - may be list of dicts with lang/text or string
        claims = ''
        claims_raw = result.get('claims', '')
        if isinstance(claims_raw, list):
            # Prefer English claims
            for claim_obj in claims_raw:
                if isinstance(claim_obj, dict) and claim_obj.get('lang') == 'en':
                    claims = claim_obj.get('text', '')
                    break
            # If no English, use first available
            if not claims and claims_raw:
                first_claim = claims_raw[0]
                if isinstance(first_claim, dict):
                    claims = first_claim.get('text', '')
        elif isinstance(claims_raw, str):
            claims = claims_raw

        # Calculate claims count from extracted claims text
        claims_count = 0
        if claims:
            # Rough estimate: count numbered claims (e.g., "1.", "2.", etc.)
            import re
            claim_matches = re.findall(r'\n\s*\d+\.', claims)
            claims_count = len(claim_matches)

        # Construct patent URL
        patent_url = f"https://link.lens.org/{lens_id}"

        return {
            # === EXISTING FIELDS (19) ===
            'patent_number': doc_number,
            'lens_id': lens_id,
            'jurisdiction': jurisdiction,
            'kind': kind,
            'title': title,
            'abstract': abstract,
            'assignee': assignee_name,
            'inventors': inventor_names,
            'filing_date': filing_date,
            'grant_date': grant_date,
            'publication_date': date_published,
            'claims_count': claims_count,  # Now calculated from actual claims text
            'cpc_codes': cpc_codes,
            'citation_count': patent_citations,  # Backward citations
            'npl_citation_count': npl_citations,
            'type': 'granted' if is_granted else 'application',
            'url': patent_url,
            'source': 'Lens.org Patent API',

            # === NEW FIELDS (18) ===
            # PDF Access
            'doc_key': doc_key,
            'publication_type': publication_type,
            'lang': lang,

            # Strategic Intelligence - Family Data
            'simple_family_size': simple_family_size,
            'extended_family_size': extended_family_size,

            # Strategic Intelligence - Forward Citations (Impact)
            'forward_citation_count': forward_citation_count,
            'forward_citation_lens_ids': forward_citation_lens_ids,

            # Strategic Intelligence - Ownership (M&A Tracking)
            'current_owners': current_owners,

            # Strategic Intelligence - Priority Data
            'earliest_priority_date': earliest_priority_date,

            # Legal Status Details
            'anticipated_term_date': anticipated_term_date,
            'discontinuation_date': discontinuation_date,
            'has_terminal_disclaimer': has_disclaimer,

            # Classifications
            'ipcr_codes': ipcr_codes,

            # Citation Details
            'npl_resolved_count': npl_resolved_count,
            'detailed_citations': detailed_citations,

            # Full Text Content (CRITICAL)
            'description': description,
            'claims': claims
        }

    def _deduplicate_patents(self, patents: List[Dict]) -> List[Dict]:
        """Remove duplicate patents based on lens_id"""
        seen = set()
        unique = []

        for patent in patents:
            lens_id = patent.get('lens_id')
            if lens_id and lens_id not in seen:
                seen.add(lens_id)
                unique.append(patent)

        return unique

    def _load_existing_patents(self) -> List[Dict]:
        """
        Load existing patents from file if resuming.
        Returns empty list if no existing file found.
        """
        patents_file = self.output_dir / "patents.json"
        if patents_file.exists():
            try:
                with open(patents_file, 'r', encoding='utf-8') as f:
                    patents = json.load(f)
                return patents if isinstance(patents, list) else []
            except Exception as e:
                self.logger.warning(f"Could not load existing patents: {e}")
                return []
        return []

    def _save_patents_incremental(self, patents: List[Dict]):
        """
        Save patents incrementally (after each company).
        CRITICAL: This prevents data loss if harvest is interrupted.
        """
        patents_file = self.output_dir / "patents.json"
        try:
            with open(patents_file, 'w', encoding='utf-8') as f:
                json.dump(patents, f, indent=2, ensure_ascii=False)
            self.logger.debug(f"  Incremental save: {len(patents)} total patents")
        except Exception as e:
            self.logger.error(f"  Incremental save failed: {e}")

    def _save_patents(self, patents: List[Dict]):
        """Save final deduplicated patents to JSON file"""
        patents_file = self.output_dir / "patents.json"
        with open(patents_file, 'w', encoding='utf-8') as f:
            json.dump(patents, f, indent=2, ensure_ascii=False)

        file_size = patents_file.stat().st_size / (1024 * 1024)  # MB
        self.stats['total_size'] = file_size

        self.logger.info(f"Saved {len(patents)} patents to {patents_file} ({file_size:.2f} MB)")

    def _save_metadata(self, patents: List[Dict]):
        """Save metadata JSON (REQUIRED format)"""
        metadata = []

        for patent in patents:
            metadata.append({
                'title': patent.get('title'),
                'date': patent.get('grant_date') or patent.get('publication_date'),
                'source': 'Lens.org Patent API',
                'url': patent.get('url'),
                'patent_number': patent.get('patent_number'),
                'lens_id': patent.get('lens_id'),
                'assignee': patent.get('assignee'),
                'file_path': None  # No PDF download in this version
            })

        metadata_path = self.output_dir / "patents_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Metadata saved to {metadata_path}")

    def _print_summary(self):
        """Print download summary"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("LENS PATENT DOWNLOAD SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Success: {self.stats['success']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        self.logger.info(f"Skipped: {self.stats['skipped']}")
        self.logger.info(f"Total Size: {self.stats['total_size']:.2f} MB")
        self.logger.info("\nBy Assignee:")
        for assignee, count in sorted(self.stats['by_assignee'].items(), key=lambda x: x[1], reverse=True):
            self.logger.info(f"  {assignee}: {count} patents")
        self.logger.info("=" * 60)
