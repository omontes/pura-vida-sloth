"""
Academic Citation PDF Downloader - Multi-Fallback Strategy

Downloads PDFs for academic papers using multiple fallback sources:
1. OpenAlex open_access URLs (primary)
2. Unpaywall API (fallback #1)
3. Semantic Scholar API (fallback #2)
4. arXiv search (fallback #3)

Industry-agnostic design - works with any citation metadata JSON.
"""

import json
import requests
import time
import random
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import hashlib
from urllib.parse import quote_plus, urlparse
import re

from src.utils.checkpoint_manager import CheckpointManager
from src.utils.retry_handler import retry_on_error


class CitationPDFDownloader:
    """
    Download PDFs for academic citations using multiple fallback strategies.

    CRITICAL: Industry-agnostic design - accepts any citation metadata JSON.
    """

    def __init__(
        self,
        metadata_path: Path,
        output_subdir: str = "pdfs",
        email: str = "researcher@example.com",  # Required for Unpaywall API
        delay_range: tuple = (2, 4),
        batch_size: int = 25,
        batch_pause: int = 30
    ):
        """
        Initialize citation PDF downloader.

        Args:
            metadata_path: Path to citation metadata JSON file
            output_subdir: Subdirectory name for PDFs (default: "pdfs")
            email: Email for Unpaywall API (required, use real email)
            delay_range: Random delay range between downloads (seconds)
            batch_size: Number of papers to download before pausing
            batch_pause: Pause duration between batches (seconds)
        """
        self.metadata_path = Path(metadata_path)
        self.output_dir = self.metadata_path.parent / output_subdir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.email = email
        self.delay_range = delay_range
        self.batch_size = batch_size
        self.batch_pause = batch_pause

        # Load metadata
        with open(self.metadata_path, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)

        # Checkpoint for resume capability
        checkpoint_name = f"citation_pdf_download"
        self.checkpoint = CheckpointManager(self.output_dir, checkpoint_name)

        # Logger
        self.logger = logging.getLogger("CitationPDFDownloader")
        handler = logging.FileHandler(self.output_dir / "citation_pdf_download.log")
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        # User-Agent
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Statistics
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'by_source': {
                'openalex': 0,
                'unpaywall': 0,
                'semantic_scholar': 0,
                'arxiv': 0
            }
        }

    def _sanitize_filename(self, text: str, max_length: int = 100) -> str:
        """Sanitize text for use as filename."""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            text = text.replace(char, '_')

        # Truncate and clean
        text = text[:max_length].strip()
        text = '_'.join(text.split())

        return text

    def _extract_doi(self, paper: Dict[str, Any]) -> Optional[str]:
        """Extract clean DOI from paper metadata."""
        doi = paper.get('doi', '')
        if not doi:
            return None

        # Clean DOI (remove URL prefix if present)
        doi = doi.replace('https://doi.org/', '')
        doi = doi.replace('http://doi.org/', '')
        doi = doi.strip()

        return doi if doi else None

    def _try_openalex_url(self, paper: Dict[str, Any]) -> Optional[str]:
        """
        Strategy 1: Try OpenAlex open_access URL.

        Returns PDF URL if available, None otherwise.
        """
        # Check if open access
        open_access = paper.get('open_access')
        if not open_access:
            return None

        # Check if OA is available
        if isinstance(open_access, dict):
            is_oa = open_access.get('is_oa', False)
            oa_url = open_access.get('oa_url', '')
        elif isinstance(open_access, bool):
            is_oa = open_access
            oa_url = ''
        else:
            return None

        if not is_oa or not oa_url:
            return None

        self.logger.info(f"Found OpenAlex OA URL: {oa_url}")
        return oa_url

    @retry_on_error(max_retries=3, backoff_factor=2)
    def _try_unpaywall_api(self, doi: str) -> Optional[str]:
        """
        Strategy 2: Try Unpaywall API.

        Returns PDF URL if available, None otherwise.
        """
        if not doi:
            return None

        try:
            url = f"https://api.unpaywall.org/v2/{doi}?email={self.email}"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 404:
                # Paper not in Unpaywall database
                return None

            response.raise_for_status()
            data = response.json()

            # Get best OA location
            best_oa = data.get('best_oa_location')
            if best_oa and best_oa.get('url_for_pdf'):
                pdf_url = best_oa['url_for_pdf']
                self.logger.info(f"Found Unpaywall PDF: {pdf_url}")
                return pdf_url

            return None

        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Unpaywall API error for DOI {doi}: {e}")
            return None

    @retry_on_error(max_retries=3, backoff_factor=2)
    def _try_semantic_scholar(self, doi: str) -> Optional[str]:
        """
        Strategy 3: Try Semantic Scholar API.

        Returns PDF URL if available, None otherwise.
        """
        if not doi:
            return None

        try:
            # Semantic Scholar accepts DOI as paper ID
            url = f"https://api.semanticscholar.org/graph/v1/paper/{doi}"
            params = {'fields': 'openAccessPdf'}

            response = requests.get(url, params=params, headers=self.headers, timeout=10)

            if response.status_code == 404:
                return None

            response.raise_for_status()
            data = response.json()

            # Check for open access PDF
            open_access_pdf = data.get('openAccessPdf')
            if open_access_pdf and open_access_pdf.get('url'):
                pdf_url = open_access_pdf['url']
                self.logger.info(f"Found Semantic Scholar PDF: {pdf_url}")
                return pdf_url

            return None

        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Semantic Scholar API error for DOI {doi}: {e}")
            return None

    @retry_on_error(max_retries=3, backoff_factor=2)
    def _try_arxiv_search(self, title: str) -> Optional[str]:
        """
        Strategy 4: Search arXiv for preprint version.

        Returns PDF URL if found, None otherwise.
        """
        if not title or len(title) < 10:
            return None

        try:
            # Clean title for search
            clean_title = re.sub(r'[^\w\s]', '', title).strip()
            query = quote_plus(clean_title[:200])  # Limit query length

            url = f"http://export.arxiv.org/api/query"
            params = {
                'search_query': f'ti:{query}',
                'start': 0,
                'max_results': 3
            }

            response = requests.get(url, params=params, headers=self.headers, timeout=15)
            response.raise_for_status()

            # Parse XML response
            content = response.text

            # Simple XML parsing (looking for <link title="pdf" ...>)
            pdf_links = re.findall(r'<link title="pdf" href="([^"]+)"', content)

            if pdf_links:
                pdf_url = pdf_links[0]
                self.logger.info(f"Found arXiv PDF: {pdf_url}")
                return pdf_url

            return None

        except requests.exceptions.RequestException as e:
            self.logger.warning(f"arXiv search error for title '{title[:50]}...': {e}")
            return None

    @retry_on_error(max_retries=3, backoff_factor=2)
    def _download_pdf(self, url: str, output_path: Path) -> bool:
        """
        Download PDF from URL.

        Returns True if successful, False otherwise.
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=30, stream=True)
            response.raise_for_status()

            # Check if content is PDF
            content_type = response.headers.get('Content-Type', '').lower()
            if 'pdf' not in content_type and 'application/octet-stream' not in content_type:
                self.logger.warning(f"URL does not return PDF: {url} (Content-Type: {content_type})")
                return False

            # Write PDF to file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # Verify file size
            file_size = output_path.stat().st_size
            if file_size < 1024:  # Less than 1KB
                self.logger.warning(f"Downloaded file too small ({file_size} bytes): {output_path}")
                output_path.unlink()
                return False

            self.logger.info(f"Downloaded PDF ({file_size / 1024:.1f} KB): {output_path.name}")
            return True

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to download {url}: {e}")
            return False

    def download_all(self) -> Dict[str, Any]:
        """
        Download all available PDFs using multi-fallback strategy.

        Returns statistics dict.
        """
        self.stats['total'] = len(self.metadata)
        self.logger.info(f"Starting citation PDF download for {self.stats['total']} papers")

        for idx, paper in enumerate(self.metadata):
            # Generate unique ID
            paper_id = paper.get('id', '') or paper.get('doi', '') or hashlib.md5(
                paper.get('title', '').encode()
            ).hexdigest()[:16]

            # Check if already processed
            if self.checkpoint.is_completed(paper_id):
                self.stats['skipped'] += 1
                continue

            # Generate output filename
            title = paper.get('title', f"paper_{idx}")
            safe_filename = self._sanitize_filename(title)
            output_path = self.output_dir / f"{safe_filename}.pdf"

            # Skip if file already exists
            if output_path.exists():
                self.logger.info(f"Skipping existing file: {output_path.name}")
                self.checkpoint.mark_completed(paper_id, metadata={'file_path': str(output_path)})
                self.stats['skipped'] += 1
                continue

            # Try multiple strategies
            pdf_url = None
            source = None

            # Strategy 1: OpenAlex OA URL
            pdf_url = self._try_openalex_url(paper)
            if pdf_url:
                source = 'openalex'

            # Strategy 2: Unpaywall
            if not pdf_url:
                doi = self._extract_doi(paper)
                if doi:
                    pdf_url = self._try_unpaywall_api(doi)
                    if pdf_url:
                        source = 'unpaywall'

            # Strategy 3: Semantic Scholar
            if not pdf_url and doi:
                pdf_url = self._try_semantic_scholar(doi)
                if pdf_url:
                    source = 'semantic_scholar'

            # Strategy 4: arXiv search
            if not pdf_url:
                pdf_url = self._try_arxiv_search(paper.get('title', ''))
                if pdf_url:
                    source = 'arxiv'

            # Download if URL found
            if pdf_url:
                self.logger.info(f"[{idx + 1}/{self.stats['total']}] Downloading from {source}: {title[:60]}...")
                success = self._download_pdf(pdf_url, output_path)

                if success:
                    self.checkpoint.mark_completed(paper_id, metadata={
                        'file_path': str(output_path),
                        'source': source,
                        'pdf_url': pdf_url
                    })
                    self.stats['success'] += 1
                    self.stats['by_source'][source] += 1
                else:
                    self.checkpoint.mark_failed(paper_id, f"Failed to download from {source}: {pdf_url}")
                    self.stats['failed'] += 1
            else:
                self.logger.warning(f"[{idx + 1}/{self.stats['total']}] No PDF found: {title[:60]}...")
                self.checkpoint.mark_failed(paper_id, "No PDF URL found in any source")
                self.stats['failed'] += 1

            # Rate limiting
            delay = random.uniform(*self.delay_range)
            time.sleep(delay)

            # Batch pause
            if (idx + 1) % self.batch_size == 0:
                self.logger.info(f"Batch complete ({idx + 1}/{self.stats['total']}). Pausing for {self.batch_pause} seconds...")
                time.sleep(self.batch_pause)

        # Finalize checkpoint
        self.checkpoint.finalize()

        # Calculate total size
        total_size = sum(f.stat().st_size for f in self.output_dir.glob('*.pdf'))
        self.stats['total_size_mb'] = total_size / (1024 * 1024)

        self.logger.info(f"PDF download complete: {self.stats['success']} success, {self.stats['failed']} failed, {self.stats['skipped']} skipped")
        self.logger.info(f"Total size: {self.stats['total_size_mb']:.2f} MB")
        self.logger.info(f"By source: {self.stats['by_source']}")

        return self.stats


def main():
    """CLI entry point for citation PDF downloader."""
    import argparse

    parser = argparse.ArgumentParser(description='Download PDFs for academic citations')
    parser.add_argument('--metadata', required=True, help='Path to citation metadata JSON file')
    parser.add_argument('--email', required=True, help='Email for Unpaywall API')
    parser.add_argument('--output-subdir', default='pdfs', help='Output subdirectory name')
    parser.add_argument('--delay-min', type=float, default=2, help='Minimum delay (seconds)')
    parser.add_argument('--delay-max', type=float, default=4, help='Maximum delay (seconds)')
    parser.add_argument('--batch-size', type=int, default=25, help='Batch size')
    parser.add_argument('--batch-pause', type=int, default=30, help='Batch pause (seconds)')

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Download PDFs
    downloader = CitationPDFDownloader(
        metadata_path=Path(args.metadata),
        output_subdir=args.output_subdir,
        email=args.email,
        delay_range=(args.delay_min, args.delay_max),
        batch_size=args.batch_size,
        batch_pause=args.batch_pause
    )

    stats = downloader.download_all()

    print("\n" + "="*60)
    print(" CITATION PDF DOWNLOAD COMPLETE")
    print("="*60)
    print(f"Total papers:   {stats['total']}")
    print(f"Success:        {stats['success']}")
    print(f"Failed:         {stats['failed']}")
    print(f"Skipped:        {stats['skipped']}")
    print(f"Total size:     {stats['total_size_mb']:.2f} MB")
    print(f"\nBy source:")
    for source, count in stats['by_source'].items():
        print(f"  {source:20s}: {count}")
    print("="*60)


if __name__ == '__main__':
    main()
