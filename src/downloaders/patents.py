"""
Patent Downloader - Using SerpApi Google Patents
=================================================
Industry-agnostic patent downloader using the SerpApi Google Patents API.

Advantages:
- INSTANT access with API key (no approval needed)
- 100 free searches/month (enough for limited patent data)
- Google Patents data (comprehensive, up-to-date)
- Company-based search (assignee) - perfect for industry tracking
- Well-documented REST API

Target: 50-100 patents per harvest (limited by free tier)
Primary Source: SerpApi (https://serpapi.com)
API Docs: https://serpapi.com/google-patents-api

Free Tier Limits:
- 100 searches/month
- Each search returns up to 100 results
- Strategic use: ~20 patents per company for 5 companies
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


class PatentDownloader:
    """
    Download patent data using SerpApi Google Patents.
    CRITICAL: Industry-agnostic design - accepts assignee list from config.
    """

    # SerpApi endpoint
    BASE_URL = "https://serpapi.com/search"

    def __init__(
        self,
        output_dir: Path,
        start_date: str,
        end_date: str,
        assignees: Dict[str, str],  # From config.companies
        limit: int = 20,  # Reduced for free tier (100 searches/month)
        download_pdfs: bool = False,
        **optional_params
    ):
        """
        Initialize SerpApi Patent downloader

        Args:
            output_dir: Directory to save patents
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            assignees: Dict of company names {ticker/id: name} from config
            limit: Maximum patents to download per assignee (default 20 for free tier)
            download_pdfs: Whether to download full patent PDFs (not implemented yet)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Get API token from environment
        self.api_token = os.getenv('SERP_API_KEY')
        if not self.api_token:
            raise ValueError(
                "SERP_API_KEY not found in environment. "
                "Please add it to your .env file. "
                "Get your free API key at: https://serpapi.com/users/sign_up"
            )

        self.start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        self.end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        self.assignees = list(assignees.values())  # Extract company names
        self.limit = limit
        self.download_pdfs = download_pdfs

        self.logger = setup_logger("Patents", self.output_dir / "patents.log")
        self.checkpoint = CheckpointManager(self.output_dir, 'patents')

        # Setup session for SerpApi
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Strategic Intelligence Harvester)'
        })

        # Create PDF directory if needed
        if download_pdfs:
            self.pdf_dir = self.output_dir / "pdfs"
            self.pdf_dir.mkdir(exist_ok=True)

        self.stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total_size': 0,
            'by_assignee': {}
        }

    def download(self) -> Dict[str, Any]:
        """
        Main download method. Returns stats dict with REQUIRED keys.

        Returns:
            {
                'success': int,
                'failed': int,
                'skipped': int,
                'total_size': float,
                'by_assignee': dict
            }
        """
        self.logger.info(f"Starting SerpApi patent download")
        self.logger.info(f"Date range: {self.start_date.date()} to {self.end_date.date()}")
        self.logger.info(f"Assignees: {self.assignees}")
        self.logger.info(f"Limit per assignee: {self.limit} (FREE TIER: conserving searches)")
        self.logger.info(f"Download PDFs: {self.download_pdfs}")

        all_patents = []

        # Search by assignee (company name)
        for assignee in self.assignees:
            self.logger.info(f"Searching patents for: {assignee}")

            try:
                patents = self._search_by_assignee(assignee)
                all_patents.extend(patents)

                self.stats['by_assignee'][assignee] = len(patents)
                self.logger.info(f"  Found {len(patents)} patents for {assignee}")

            except Exception as e:
                self.logger.error(f"Error searching patents for {assignee}: {e}")
                self.stats['by_assignee'][assignee] = 0

        # Deduplicate by patent number
        unique_patents = self._deduplicate_patents(all_patents)
        self.logger.info(f"Total unique patents: {len(unique_patents)}")

        # Save patents
        if unique_patents:
            self._save_patents(unique_patents)
            self._save_metadata(unique_patents)

        # Finalize checkpoint
        self.checkpoint.finalize()

        self._print_summary()

        return self.stats

    def _search_by_assignee(self, assignee: str) -> List[Dict]:
        """
        Search patents by assignee (company) using SerpApi Google Patents.
        Limited to one search per assignee to conserve free tier quota.
        """
        patents = []

        try:
            # Build search query for Google Patents
            # Use assignee: syntax in query (SerpApi supports both parameter and query syntax)
            query = f'assignee:"{assignee}"'

            # SerpApi parameters (official format from docs)
            # Date range uses separate 'before' and 'after' parameters with format: type:YYYYMMDD
            # type can be: priority, filing, or publication
            params = {
                'engine': 'google_patents',  # Use Google Patents engine
                'q': query,
                'api_key': self.api_token,
                'num': max(10, min(self.limit, 100)),  # SerpApi requires Min: 10, Max: 100
                'after': f'publication:{self.start_date.strftime("%Y%m%d")}',  # Format: publication:YYYYMMDD
                'before': f'publication:{self.end_date.strftime("%Y%m%d")}'    # Format: publication:YYYYMMDD
            }

            self.logger.debug(f"  Query: {query}")
            self.logger.debug(f"  Requesting up to {params['num']} results")

            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=30
            )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                self.logger.warning(f"  Rate limit hit, waiting {retry_after}s...")
                time.sleep(retry_after)
                # Retry once
                response = self.session.get(
                    self.BASE_URL,
                    params=params,
                    timeout=30
                )

            response.raise_for_status()
            data = response.json()

            # Check for SerpApi errors
            if 'error' in data:
                self.logger.error(f"  SerpApi error: {data['error']}")
                return patents

            # Extract organic_results from response
            results = data.get('organic_results', [])

            if not results:
                self.logger.warning(f"  No results found for {assignee}")
                return patents

            self.logger.info(f"  Found {len(results)} results")

            # Process each patent
            for result in tqdm(results, desc=f"  Processing {assignee}", leave=False):
                try:
                    # Get patent ID from result
                    patent_id = result.get('patent_id')

                    if not patent_id:
                        self.logger.debug("  Skipping result with no patent_id")
                        continue

                    # Check checkpoint (skip if already processed)
                    if self.checkpoint.is_completed(patent_id):
                        self.stats['skipped'] += 1
                        continue

                    # Extract patent data
                    patent_data = self._extract_patent_data(result, assignee)

                    patents.append(patent_data)
                    self.stats['success'] += 1

                    # Mark as completed in checkpoint
                    self.checkpoint.mark_completed(patent_id, metadata={
                        'title': patent_data.get('title'),
                        'assignee': patent_data.get('assignee')
                    })

                    # Stop if we've reached the limit
                    if len(patents) >= self.limit:
                        break

                except Exception as e:
                    self.logger.error(f"  Error processing patent {patent_id}: {e}")
                    self.stats['failed'] += 1
                    if patent_id:
                        self.checkpoint.mark_failed(patent_id, str(e))

            # Rate limiting: be conservative with free tier
            time.sleep(2)  # 2 second delay between searches

        except Exception as e:
            self.logger.error(f"Error in search for '{assignee}': {e}")
            import traceback
            self.logger.error(traceback.format_exc())

        return patents

    def _extract_patent_data(self, result: Dict, assignee: str) -> Dict:
        """
        Extract patent data from SerpApi Google Patents result.
        Handles various field names and missing data gracefully.

        SerpApi response format:
        {
            "patent_id": "US1234567890B2",
            "title": "Patent Title",
            "snippet": "Abstract snippet...",
            "publication_date": "2024-01-15",
            "filing_date": "2022-06-10",
            "grant_date": "2024-01-15",
            "inventor": "John Doe, Jane Smith",
            "assignee": "Company Name",
            "patent_link": "https://patents.google.com/patent/US1234567890B2",
            "pdf": "https://patentimages.storage.googleapis.com/.../US1234567890B2.pdf"
        }
        """
        patent_id = result.get('patent_id', '')

        # Extract title
        title = result.get('title', '')

        # Extract abstract/snippet
        abstract = result.get('snippet', '')

        # Extract dates
        filing_date = result.get('filing_date', '')
        grant_date = result.get('grant_date') or result.get('publication_date', '')

        # Extract assignee (use provided or from result)
        assignee_name = result.get('assignee', assignee)

        # Extract inventors (SerpApi returns as comma-separated string)
        inventor_str = result.get('inventor', '')
        if inventor_str:
            inventor_names = [name.strip() for name in inventor_str.split(',')]
        else:
            inventor_names = []

        # Extract patent URL
        patent_url = result.get('patent_link', f"https://patents.google.com/patent/{patent_id}")

        # Extract PDF URL if available
        pdf_url = result.get('pdf', '')

        return {
            'patent_number': patent_id,
            'title': title,
            'abstract': abstract,
            'assignee': assignee_name,
            'inventors': inventor_names,
            'filing_date': filing_date,
            'grant_date': grant_date,
            'claims_count': 0,  # SerpApi doesn't provide claims count in search results
            'type': 'granted',
            'url': patent_url,
            'pdf_url': pdf_url if pdf_url else None,
            'source': 'SerpApi (Google Patents)'
        }

    def _deduplicate_patents(self, patents: List[Dict]) -> List[Dict]:
        """Remove duplicate patents based on patent number"""
        seen = set()
        unique = []

        for patent in patents:
            patent_num = patent.get('patent_number')
            if patent_num and patent_num not in seen:
                seen.add(patent_num)
                unique.append(patent)

        return unique

    def _save_patents(self, patents: List[Dict]):
        """Save patents to JSON file"""
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
                'date': patent.get('grant_date'),
                'source': 'SerpApi (Google Patents)',
                'url': patent.get('url'),
                'patent_number': patent.get('patent_number'),
                'assignee': patent.get('assignee'),
                'file_path': patent.get('pdf_file') if self.download_pdfs else None
            })

        metadata_path = self.output_dir / "patents_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Metadata saved to {metadata_path}")

    def _print_summary(self):
        """Print download summary"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("PATENT DOWNLOAD SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Success: {self.stats['success']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        self.logger.info(f"Skipped: {self.stats['skipped']}")
        self.logger.info(f"Total Size: {self.stats['total_size']:.2f} MB")
        self.logger.info("\nBy Assignee:")
        for assignee, count in self.stats['by_assignee'].items():
            self.logger.info(f"  {assignee}: {count} patents")
        self.logger.info("=" * 60)
