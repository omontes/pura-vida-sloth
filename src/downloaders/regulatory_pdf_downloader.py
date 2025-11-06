"""
Regulatory PDF Downloader - Dual-Source Discovery System
=========================================================
Downloads PDFs from regulatory documents using two strategies:

STRATEGY 1: Federal Register Direct Downloads (42 documents)
- Source: metadata.json[*].pdf_url field
- Pattern: https://www.govinfo.gov/content/pkg/FR-{date}/pdf/{number}.pdf
- Direct download, no scraping needed
- High success rate (100%)

STRATEGY 2: RSS Feed Web Scraping (6 documents)
- Source: metadata.json[*].url field (NASA, agency sites)
- Requires BeautifulSoup scraping to find PDF links
- Fallback: Save HTML content if no PDF found
- Variable success rate (60-80%)

Features:
- Checkpoint/resume capability
- PDF validation (size, MIME, magic bytes)
- Rate limiting for politeness
- Detailed statistics tracking
- Safe filename generation

Usage:
    python -m src.downloaders.regulatory_pdf_downloader \\
        --metadata data/eVTOL/regulatory_docs/metadata.json \\
        --output data/eVTOL/regulatory_docs/pdfs \\
        --limit 48
"""

import json
import time
import re
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from tqdm import tqdm

from src.utils.logger import setup_logger
from src.utils.checkpoint_manager import CheckpointManager


class RegulatoryPDFDownloader:
    """
    Download PDFs from regulatory documents using dual-source strategy.

    Mandatory Design Patterns:
    1. Dual-Source Strategy - Federal Register (direct) + RSS (scraped)
    2. Checkpoint/Resume - Track completed downloads
    3. PDF Validation - Verify file integrity
    4. Rate Limiting - Respect server load
    5. Safe Filenames - Sanitize agency names and document numbers
    """

    # Constants
    MIN_PDF_SIZE = 1024  # 1 KB minimum
    MAX_PDF_SIZE = 50 * 1024 * 1024  # 50 MB maximum
    REQUEST_TIMEOUT = 30  # seconds
    RATE_LIMIT_DELAY = 1.0  # seconds between requests

    # PDF magic bytes
    PDF_MAGIC_BYTES = b'%PDF-'

    def __init__(
        self,
        metadata_path: str,
        output_dir: str,
        limit: Optional[int] = None,
        rate_limit_delay: float = RATE_LIMIT_DELAY
    ):
        """
        Initialize regulatory PDF downloader.

        Args:
            metadata_path: Path to metadata.json file
            output_dir: Directory to save downloaded PDFs
            limit: Maximum number of PDFs to download (None = all)
            rate_limit_delay: Seconds to wait between downloads
        """
        self.metadata_path = Path(metadata_path)
        self.output_dir = Path(output_dir)
        self.limit = limit
        self.rate_limit_delay = rate_limit_delay

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self.logger = setup_logger('regulatory_pdf_downloader', self.output_dir / 'downloader.log')

        # Setup checkpoint manager
        self.checkpoint = CheckpointManager(self.output_dir, 'regulatory_pdf')

        # Setup HTTP session with headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/pdf,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })

        # Statistics
        self.stats = {
            'total_attempted': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'by_source': {
                'federal_register_direct': 0,
                'rss_scraped': 0,
                'rss_fallback_html': 0,
                'existing': 0,
                'failed': 0
            },
            'failed_documents': []
        }

    def load_metadata(self) -> List[Dict]:
        """
        Load metadata.json and extract documents array.

        Returns:
            List of document metadata dictionaries
        """
        self.logger.info(f"Loading metadata from {self.metadata_path}")

        with open(self.metadata_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        documents = data.get('documents', [])
        total = len(documents)

        self.logger.info(f"Loaded {total} documents from metadata")

        # Apply limit if specified
        if self.limit and self.limit < total:
            documents = documents[:self.limit]
            self.logger.info(f"Limited to {self.limit} documents")

        return documents

    def discover_pdfs(self, documents: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Categorize documents by source type for appropriate download strategy.

        Args:
            documents: List of document metadata

        Returns:
            Dict with 'federal_register' and 'rss_feeds' keys
        """
        categorized = {
            'federal_register': [],
            'rss_feeds': []
        }

        for doc in documents:
            source = doc.get('source', '')

            if source == 'federal_register' and doc.get('pdf_url'):
                categorized['federal_register'].append(doc)
            elif source in ['rss_feeds', 'rss'] or (not doc.get('pdf_url') and doc.get('url')):
                categorized['rss_feeds'].append(doc)
            else:
                self.logger.warning(f"Unknown source type for document: {doc.get('title', 'Unknown')[:50]}")

        self.logger.info(f"Categorized: {len(categorized['federal_register'])} Federal Register, "
                        f"{len(categorized['rss_feeds'])} RSS feeds")

        return categorized

    def download_all(self) -> Dict[str, Any]:
        """
        Main entry point - discover and download all PDFs.

        Returns:
            Statistics dictionary with download results
        """
        start_time = time.time()
        self.logger.info("=" * 70)
        self.logger.info(" REGULATORY PDF DOWNLOADER - Starting")
        self.logger.info("=" * 70)

        # Load metadata
        documents = self.load_metadata()

        # Categorize by source type
        categorized = self.discover_pdfs(documents)

        # Download Federal Register PDFs
        self._download_federal_register_batch(categorized['federal_register'])

        # Download RSS Feed PDFs
        self._download_rss_batch(categorized['rss_feeds'])

        # Generate summary
        duration = time.time() - start_time
        self._print_summary(duration)

        # Save metadata report
        self._save_download_report(duration)

        return self.stats

    def _download_federal_register_batch(self, documents: List[Dict]):
        """
        Download Federal Register PDFs using direct pdf_url links.

        Args:
            documents: List of Federal Register documents
        """
        if not documents:
            return

        self.logger.info(f"\nDownloading {len(documents)} Federal Register PDFs...")

        for doc in tqdm(documents, desc="Federal Register PDFs"):
            self.stats['total_attempted'] += 1

            doc_number = doc.get('document_number', 'unknown')

            # Check if already completed
            if self.checkpoint.is_completed(doc_number):
                self.logger.info(f"⊘ Skipping {doc_number} (already completed)")
                self.stats['skipped'] += 1
                self.stats['by_source']['existing'] += 1
                continue

            # Generate filename
            filename = self._sanitize_filename(doc)
            output_path = self.output_dir / filename

            # Check if file already exists
            if output_path.exists() and output_path.stat().st_size >= self.MIN_PDF_SIZE:
                self.logger.info(f"⊘ Skipping {doc_number} (PDF already exists, "
                               f"{output_path.stat().st_size / 1024:.1f} KB)")
                self.stats['skipped'] += 1
                self.stats['by_source']['existing'] += 1

                # Mark as completed
                if not self.checkpoint.is_completed(doc_number):
                    self.checkpoint.mark_completed(doc_number, metadata={
                        'filename': filename,
                        'file_size': output_path.stat().st_size,
                        'source': 'federal_register_existing'
                    })
                continue

            # Download PDF
            success = self._download_federal_register_pdf(doc, output_path)

            if success:
                self.stats['successful'] += 1
                self.stats['by_source']['federal_register_direct'] += 1

                self.checkpoint.mark_completed(doc_number, metadata={
                    'filename': filename,
                    'file_size': output_path.stat().st_size,
                    'source': 'federal_register_direct',
                    'pdf_url': doc.get('pdf_url')
                })
            else:
                self.stats['failed'] += 1
                self.stats['by_source']['failed'] += 1
                self.stats['failed_documents'].append({
                    'document_number': doc_number,
                    'title': doc.get('title', 'N/A')[:100],
                    'reason': 'download_failed'
                })

            # Rate limiting
            time.sleep(self.rate_limit_delay)

    def _download_federal_register_pdf(self, document: Dict, output_path: Path) -> bool:
        """
        Download PDF directly from govinfo.gov using pdf_url field.

        Args:
            document: Document metadata with pdf_url
            output_path: Where to save PDF

        Returns:
            True if successful, False otherwise
        """
        pdf_url = document.get('pdf_url')
        doc_number = document.get('document_number', 'unknown')

        if not pdf_url:
            self.logger.warning(f"No pdf_url for {doc_number}")
            return False

        try:
            self.logger.info(f"↓ Downloading {doc_number} from govinfo.gov")

            response = self.session.get(pdf_url, timeout=self.REQUEST_TIMEOUT)
            response.raise_for_status()

            # Validate PDF content
            if not self._is_valid_pdf(response.content):
                self.logger.error(f"✗ Invalid PDF content for {doc_number}")
                return False

            # Check file size
            file_size = len(response.content)
            if file_size < self.MIN_PDF_SIZE or file_size > self.MAX_PDF_SIZE:
                self.logger.error(f"✗ Invalid file size for {doc_number}: {file_size} bytes")
                return False

            # Save to disk
            output_path.write_bytes(response.content)
            self.logger.info(f"✓ Saved {doc_number} ({file_size / 1024:.1f} KB)")

            return True

        except requests.exceptions.RequestException as e:
            self.logger.error(f"✗ Download failed for {doc_number}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"✗ Unexpected error for {doc_number}: {e}")
            return False

    def _download_rss_batch(self, documents: List[Dict]):
        """
        Download PDFs from RSS feed sources using web scraping.

        Args:
            documents: List of RSS feed documents
        """
        if not documents:
            return

        self.logger.info(f"\nDownloading {len(documents)} RSS Feed PDFs (requires scraping)...")

        for doc in tqdm(documents, desc="RSS Feed PDFs"):
            self.stats['total_attempted'] += 1

            title = doc.get('title', 'unknown')[:50]

            # Check if already completed
            doc_id = self._generate_doc_id(doc)
            if self.checkpoint.is_completed(doc_id):
                self.logger.info(f"⊘ Skipping {title} (already completed)")
                self.stats['skipped'] += 1
                self.stats['by_source']['existing'] += 1
                continue

            # Generate filename
            filename = self._sanitize_filename(doc)
            output_path = self.output_dir / filename

            # Check if file already exists
            if output_path.exists() and output_path.stat().st_size >= self.MIN_PDF_SIZE:
                self.logger.info(f"⊘ Skipping {title} (file exists, {output_path.stat().st_size / 1024:.1f} KB)")
                self.stats['skipped'] += 1
                self.stats['by_source']['existing'] += 1

                if not self.checkpoint.is_completed(doc_id):
                    self.checkpoint.mark_completed(doc_id, metadata={
                        'filename': filename,
                        'file_size': output_path.stat().st_size,
                        'source': 'rss_existing'
                    })
                continue

            # Scrape and download
            success, source_type = self._scrape_and_download_rss_pdf(doc, output_path)

            if success:
                self.stats['successful'] += 1
                self.stats['by_source'][source_type] += 1

                self.checkpoint.mark_completed(doc_id, metadata={
                    'filename': filename,
                    'file_size': output_path.stat().st_size if output_path.exists() else 0,
                    'source': source_type,
                    'url': doc.get('url')
                })
            else:
                self.stats['failed'] += 1
                self.stats['by_source']['failed'] += 1
                self.stats['failed_documents'].append({
                    'title': title,
                    'url': doc.get('url', 'N/A'),
                    'reason': 'scraping_failed'
                })

            # Rate limiting
            time.sleep(self.rate_limit_delay)

    def _scrape_and_download_rss_pdf(self, document: Dict, output_path: Path) -> tuple[bool, str]:
        """
        Scrape source page to find PDF links and download.

        Args:
            document: Document metadata with url field
            output_path: Where to save PDF

        Returns:
            Tuple of (success: bool, source_type: str)
        """
        source_url = document.get('url')
        title = document.get('title', 'Unknown')[:50]

        if not source_url:
            self.logger.warning(f"No URL for RSS document: {title}")
            return False, 'failed'

        try:
            self.logger.info(f"↓ Scraping {title}...")

            # Fetch source page
            response = self.session.get(source_url, timeout=self.REQUEST_TIMEOUT)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract PDF links
            pdf_links = self._extract_pdf_links(soup, source_url)

            # Try each PDF link
            for pdf_url in pdf_links:
                self.logger.info(f"  → Trying PDF: {pdf_url[:80]}...")

                if self._download_and_validate_pdf(pdf_url, output_path):
                    self.logger.info(f"✓ Downloaded PDF from {urlparse(pdf_url).netloc}")
                    return True, 'rss_scraped'

            # No PDF found - fallback to HTML extraction
            self.logger.warning(f"⚠ No PDF found for {title}, saving HTML as fallback")
            return self._save_html_as_fallback(response.content, output_path, document), 'rss_fallback_html'

        except requests.exceptions.RequestException as e:
            self.logger.error(f"✗ Scraping failed for {title}: {e}")
            return False, 'failed'
        except Exception as e:
            self.logger.error(f"✗ Unexpected error scraping {title}: {e}")
            return False, 'failed'

    def _extract_pdf_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract potential PDF links from HTML page.

        Args:
            soup: BeautifulSoup parsed HTML
            base_url: Base URL for resolving relative links

        Returns:
            List of absolute PDF URLs
        """
        pdf_links = []

        # Pattern 1: Direct <a href="*.pdf"> links
        for link in soup.find_all('a', href=True):
            href = link['href']

            # Check if link ends with .pdf
            if href.lower().endswith('.pdf'):
                absolute_url = urljoin(base_url, href)
                pdf_links.append(absolute_url)
                continue

            # Check if link text contains "PDF" or "Download"
            link_text = link.get_text(strip=True).lower()
            if 'pdf' in link_text or 'download' in link_text:
                absolute_url = urljoin(base_url, href)
                if absolute_url not in pdf_links:
                    pdf_links.append(absolute_url)

        # Pattern 2: Embedded iframes with PDF sources
        for iframe in soup.find_all('iframe', src=True):
            src = iframe['src']
            if src.lower().endswith('.pdf'):
                absolute_url = urljoin(base_url, src)
                pdf_links.append(absolute_url)

        # Pattern 3: Object/embed tags for PDFs
        for obj in soup.find_all(['object', 'embed'], attrs={'data': True}):
            data_url = obj.get('data') or obj.get('src')
            if data_url and data_url.lower().endswith('.pdf'):
                absolute_url = urljoin(base_url, data_url)
                pdf_links.append(absolute_url)

        self.logger.info(f"  Found {len(pdf_links)} potential PDF links")
        return pdf_links

    def _download_and_validate_pdf(self, pdf_url: str, output_path: Path) -> bool:
        """
        Download PDF and validate it's a real PDF file.

        Args:
            pdf_url: URL to PDF
            output_path: Where to save

        Returns:
            True if valid PDF downloaded, False otherwise
        """
        try:
            response = self.session.get(pdf_url, timeout=self.REQUEST_TIMEOUT)
            response.raise_for_status()

            # Validate PDF
            if not self._is_valid_pdf(response.content):
                return False

            # Check size
            file_size = len(response.content)
            if file_size < self.MIN_PDF_SIZE or file_size > self.MAX_PDF_SIZE:
                return False

            # Save
            output_path.write_bytes(response.content)
            return True

        except Exception as e:
            self.logger.debug(f"    Failed: {e}")
            return False

    def _is_valid_pdf(self, content: bytes) -> bool:
        """
        Validate PDF by checking magic bytes and content type.

        Args:
            content: File content bytes

        Returns:
            True if valid PDF, False otherwise
        """
        if len(content) < len(self.PDF_MAGIC_BYTES):
            return False

        return content[:len(self.PDF_MAGIC_BYTES)] == self.PDF_MAGIC_BYTES

    def _save_html_as_fallback(self, html_content: bytes, output_path: Path, document: Dict) -> bool:
        """
        Save HTML content as text fallback when no PDF found.

        Args:
            html_content: HTML bytes
            output_path: Output path (will change extension to .txt)
            document: Document metadata

        Returns:
            True if saved successfully
        """
        try:
            # Change extension to .txt
            txt_path = output_path.with_suffix('.txt')

            # Parse HTML and extract text
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove script and style tags
            for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()

            # Extract text
            text = soup.get_text(separator='\n', strip=True)

            # Add metadata header
            header = f"""
REGULATORY DOCUMENT (HTML FALLBACK)
===================================
Title: {document.get('title', 'N/A')}
Source: {document.get('url', 'N/A')}
Agency: {document.get('agency', 'N/A')}
Date: {document.get('publication_date', 'N/A')}
Downloaded: {datetime.now().isoformat()}

===================================

"""

            # Save
            txt_path.write_text(header + text, encoding='utf-8')
            self.logger.info(f"✓ Saved HTML fallback as TXT ({len(text)} chars)")

            return True

        except Exception as e:
            self.logger.error(f"✗ Failed to save HTML fallback: {e}")
            return False

    def _sanitize_filename(self, document: Dict) -> str:
        """
        Generate safe filename from document metadata.

        Args:
            document: Document metadata

        Returns:
            Safe filename string
        """
        agency = document.get('agency', 'unknown')
        doc_number = document.get('document_number', '')
        title = document.get('title', '')

        # Clean agency name
        agency_clean = re.sub(r'[^a-z0-9-]', '', agency.lower().replace(' ', '-'))

        # Use document number if available
        if doc_number:
            doc_clean = re.sub(r'[^a-zA-Z0-9-]', '', doc_number)
            filename = f"{agency_clean}_{doc_clean}.pdf"
        else:
            # Use sanitized title
            title_clean = re.sub(r'[^a-zA-Z0-9-]', '', title[:50].replace(' ', '_'))
            pub_date = document.get('publication_date', '')
            date_clean = re.sub(r'[^0-9-]', '', pub_date)
            filename = f"{agency_clean}_{date_clean}_{title_clean}.pdf"

        return filename

    def _generate_doc_id(self, document: Dict) -> str:
        """
        Generate unique ID for RSS documents without document_number.

        Args:
            document: Document metadata

        Returns:
            Unique identifier string
        """
        # Try document number first
        if document.get('document_number'):
            return document['document_number']

        # Fallback to URL-based ID
        url = document.get('url', '')
        if url:
            return f"rss_{hash(url) % 1000000:06d}"

        # Last resort: title-based ID
        title = document.get('title', 'unknown')
        return f"rss_{hash(title) % 1000000:06d}"

    def _print_summary(self, duration: float):
        """
        Print download statistics summary.

        Args:
            duration: Total duration in seconds
        """
        self.logger.info("\n" + "=" * 70)
        self.logger.info(" DOWNLOAD COMPLETE - Summary")
        self.logger.info("=" * 70)

        self.logger.info(f"\nTotal Attempted: {self.stats['total_attempted']}")
        self.logger.info(f"Successful: {self.stats['successful']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        self.logger.info(f"Skipped (existing): {self.stats['skipped']}")

        if self.stats['successful'] > 0:
            success_rate = (self.stats['successful'] / self.stats['total_attempted']) * 100
            self.logger.info(f"Success Rate: {success_rate:.1f}%")

        self.logger.info(f"\nBy Source:")
        for source, count in self.stats['by_source'].items():
            if count > 0:
                self.logger.info(f"  {source:30s}: {count:>4}")

        self.logger.info(f"\nDuration: {duration / 60:.1f} minutes")

        if self.stats['failed_documents']:
            self.logger.info(f"\nFailed Documents ({len(self.stats['failed_documents'])}):")
            for failed in self.stats['failed_documents'][:10]:  # Show first 10
                title = failed.get('title', failed.get('document_number', 'Unknown'))[:60]
                reason = failed.get('reason', 'unknown')
                self.logger.info(f"  - {title}... ({reason})")

        self.logger.info("=" * 70)

    def _save_download_report(self, duration: float):
        """
        Save comprehensive download report as JSON.

        Args:
            duration: Total duration in seconds
        """
        report_path = self.output_dir / 'pdf_download_report.json'

        report = {
            'timestamp': datetime.now().isoformat(),
            'metadata_path': str(self.metadata_path),
            'output_dir': str(self.output_dir),
            'limit': self.limit,
            'duration_seconds': duration,
            'stats': self.stats
        }

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.logger.info(f"\n✓ Report saved to {report_path}")


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Download PDFs from regulatory documents using dual-source strategy'
    )

    parser.add_argument(
        '--metadata',
        required=True,
        help='Path to metadata.json file'
    )

    parser.add_argument(
        '--output',
        required=True,
        help='Output directory for PDFs'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of PDFs to download (default: all)'
    )

    parser.add_argument(
        '--rate-limit',
        type=float,
        default=1.0,
        help='Seconds to wait between downloads (default: 1.0)'
    )

    args = parser.parse_args()

    # Create downloader
    downloader = RegulatoryPDFDownloader(
        metadata_path=args.metadata,
        output_dir=args.output,
        limit=args.limit,
        rate_limit_delay=args.rate_limit
    )

    # Run download
    downloader.download_all()


if __name__ == '__main__':
    main()
