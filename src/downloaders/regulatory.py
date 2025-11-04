"""
Regulatory Announcements Downloader (Enhanced)
===============================================
Downloads regulatory announcements using Federal Register API and RSS feeds

Target: 200-300 documents in 30 days
- Primary source: Federal Register API (comprehensive)
- Secondary source: Agency RSS feeds (Fed, FDIC, OCC, CFPB)
- Fallback: Web scraping (FinCEN only)

Improvements:
- Federal Register API for all federal agencies
- RSS feed parsing for agency-specific content
- Retry logic with exponential backoff
- 429 rate limit detection
- Resume capability with checkpoints
"""

import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import json
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import logging

from src.utils.logger import setup_logger
from src.utils.config import Config
import requests
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.retry_handler import retry_on_error
from src.utils.rss_parser import FeedAggregator


class RegulatoryDownloader:
    """Download regulatory announcements with API and RSS feeds"""

    def __init__(self, output_dir: Path, start_date: datetime, end_date: datetime):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.start_date = start_date
        self.end_date = end_date

        self.logger = setup_logger("RegulatoryDownloader", self.output_dir / "regulatory.log")

        # Initialize clients
        self.client = requests.Session()  # Use simple session instead of APIClient
        self.checkpoint = CheckpointManager(self.output_dir, 'regulatory')
        self.rss_aggregator = FeedAggregator(start_date, end_date)

        self.stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total_size': 0,
            'by_source': {
                'federal_register': 0,
                'rss_feeds': 0,
                'web_scraping': 0
            }
        }

        # Check resume info
        resume_info = self.checkpoint.get_resume_info()
        if resume_info:
            self.logger.info(resume_info)

    def download(self) -> Dict:
        """Main download method"""
        self.logger.info(f"Starting regulatory document download")
        self.logger.info(f"Date range: {self.start_date.date()} to {self.end_date.date()}")

        all_documents = []

        # Method 1: Federal Register API (primary - covers all agencies)
        self.logger.info("✓ Using Federal Register API (primary source)")
        fr_docs = self._get_federal_register_documents()
        all_documents.extend(fr_docs)
        self.logger.info(f"  Found {len(fr_docs)} documents from Federal Register API")

        # Method 2: Agency RSS feeds (secondary - agency-specific)
        self.logger.info("Fetching from agency RSS feeds...")
        rss_docs = self._get_rss_documents()
        all_documents.extend(rss_docs)
        self.logger.info(f"  Found {len(rss_docs)} documents from RSS feeds")

        # Method 3: FinCEN web scraping (fallback - no API/RSS)
        self.logger.info("Fetching from FinCEN (web scraping fallback)...")
        fincen_docs = self._get_fincen_documents()
        all_documents.extend(fincen_docs)
        self.logger.info(f"  Found {len(fincen_docs)} documents from FinCEN")

        # Deduplicate
        unique_documents = self._deduplicate_documents(all_documents)
        self.logger.info(f"Total unique documents to download: {len(unique_documents)}")

        # Download documents
        self.logger.info("Downloading documents...")
        with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS['regulatory']) as executor:
            futures = {
                executor.submit(self._download_document, doc): doc
                for doc in unique_documents
            }

            for future in tqdm(as_completed(futures),
                             total=len(futures),
                             desc="Downloading documents"):
                try:
                    future.result()
                except Exception as e:
                    self.logger.error(f"Download error: {e}")

        # Finalize
        self.checkpoint.finalize()
        self._save_metadata(unique_documents)
        self._print_summary()

        return self.stats

    @retry_on_error(max_retries=3)
    def _get_federal_register_documents(self) -> List[Dict]:
        """Get documents from Federal Register API"""
        documents = []

        # Format dates for API
        start_str = self.start_date.strftime('%Y-%m-%d')
        end_str = self.end_date.strftime('%Y-%m-%d')

        for agency in Config.FEDERAL_AGENCIES:
            item_id = f"fr_api_{agency}"

            # Skip if already completed
            if self.checkpoint.is_completed(item_id):
                continue

            try:
                # Query Federal Register API
                url = Config.FEDERAL_REGISTER_API
                params = {
                    'conditions[agencies][]': agency,
                    'conditions[publication_date][gte]': start_str,
                    'conditions[publication_date][lte]': end_str,
                    'per_page': 100,
                    'page': 1
                }

                response = self.client.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                results = data.get('results', [])

                for result in results:
                    documents.append({
                        'source': 'federal_register',
                        'agency': agency,
                        'title': result.get('title', 'Untitled'),
                        'document_number': result.get('document_number', ''),
                        'publication_date': result.get('publication_date', ''),
                        'document_type': result.get('type', ''),
                        'url': result.get('html_url', ''),
                        'pdf_url': result.get('pdf_url', ''),
                        'abstract': result.get('abstract', '')
                    })

                self.checkpoint.mark_completed(item_id, {'count': len(results)})
                self.logger.debug(f"Federal Register: {agency} - {len(results)} documents")

                time.sleep(0.5)  # Be nice to the API

            except Exception as e:
                self.logger.error(f"Federal Register API error for {agency}: {e}")
                self.checkpoint.mark_failed(item_id, str(e))

        return documents

    def _get_rss_documents(self) -> List[Dict]:
        """Get documents from agency RSS feeds"""
        documents = []

        # Add all RSS feeds
        feed_counts = self.rss_aggregator.add_feeds(Config.REGULATORY_RSS_FEEDS)

        for source, count in feed_counts.items():
            self.logger.debug(f"RSS: {source} - {count} entries")

        # Get all entries
        entries = self.rss_aggregator.get_entries(sort_by_date=True, deduplicate=True)

        # Convert to document format
        for entry in entries:
            documents.append({
                'source': 'rss_feeds',
                'agency': entry['source'],
                'title': entry['title'],
                'url': entry['link'],
                'publication_date': entry['pub_date'].isoformat() if entry.get('pub_date') else None,
                'summary': entry.get('summary', ''),
                'author': entry.get('author', '')
            })

        return documents

    @retry_on_error(max_retries=3)
    def _get_fincen_documents(self) -> List[Dict]:
        """Get documents from FinCEN (web scraping - no API/RSS)"""
        documents = []

        item_id = "fincen_scrape"

        # Skip if already completed
        if self.checkpoint.is_completed(item_id):
            return documents

        try:
            url = 'https://www.fincen.gov/news-room/news-releases'

            response = self.client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find news release links (structure may vary)
            links = soup.find_all('a', href=lambda x: x and '/news/' in x)

            for link in links[:50]:  # Limit to recent 50
                href = link.get('href', '')
                if not href.startswith('http'):
                    href = f"https://www.fincen.gov{href}"

                title = link.text.strip()

                if title and len(title) > 10:
                    documents.append({
                        'source': 'web_scraping',
                        'agency': 'FinCEN',
                        'title': title,
                        'url': href,
                        'publication_date': None  # Not easily extractable
                    })

            self.checkpoint.mark_completed(item_id, {'count': len(documents)})
            self.logger.debug(f"FinCEN scraping: {len(documents)} documents")

        except Exception as e:
            self.logger.error(f"FinCEN scraping error: {e}")
            self.checkpoint.mark_failed(item_id, str(e))

        return documents

    def _deduplicate_documents(self, documents: List[Dict]) -> List[Dict]:
        """Remove duplicate documents based on URL or document number"""
        seen = set()
        unique = []

        for doc in documents:
            # Create unique identifier
            if 'document_number' in doc and doc['document_number']:
                identifier = doc['document_number']
            elif 'url' in doc:
                identifier = doc['url']
            else:
                identifier = doc.get('title', str(doc))

            if identifier not in seen:
                seen.add(identifier)
                unique.append(doc)

        return unique

    def _download_document(self, document: Dict):
        """Download a single regulatory document"""
        try:
            source = document['source']
            agency = document.get('agency', 'Unknown')

            # Create filename
            doc_number = document.get('document_number', '')
            pub_date = document.get('publication_date', '')

            if doc_number:
                filename = f"{agency}_{doc_number}.html"
            elif pub_date:
                safe_date = pub_date.replace(':', '-').replace('/', '-')[:10]
                safe_title = self._sanitize_filename(document['title'])[:50]
                filename = f"{agency}_{safe_date}_{safe_title}.html"
            else:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_title = self._sanitize_filename(document['title'])[:50]
                filename = f"{agency}_{timestamp}_{safe_title}.html"

            filepath = self.output_dir / filename

            # Skip if exists
            if filepath.exists():
                self.stats['skipped'] += 1
                return

            # Download based on source
            if source == 'federal_register':
                success = self._download_federal_register_doc(document, filepath)
            else:
                success = self._download_web_document(document, filepath)

            if success:
                self.stats['success'] += 1
                self.stats['by_source'][source] += 1
                self.logger.debug(f"Downloaded: {filename}")
            else:
                self.stats['failed'] += 1

        except Exception as e:
            self.logger.error(f"Failed to download document: {e}")
            self.stats['failed'] += 1
            raise

    @retry_on_error(max_retries=3)
    def _download_federal_register_doc(self, document: Dict, filepath: Path) -> bool:
        """Download Federal Register document"""
        try:
            # Prefer HTML URL
            url = document.get('html_url') or document.get('url')

            if not url:
                self.logger.warning(f"No URL for document: {document.get('title')}")
                return False

            response = self.client.get(url, timeout=30)
            response.raise_for_status()

            # Create formatted output
            output = []
            output.append(f"Agency: {document.get('agency', 'Unknown')}")
            output.append(f"Title: {document.get('title', 'Untitled')}")
            output.append(f"Document Number: {document.get('document_number', 'N/A')}")
            output.append(f"Publication Date: {document.get('publication_date', 'Unknown')}")
            output.append(f"Document Type: {document.get('document_type', 'Unknown')}")
            output.append(f"URL: {url}")
            output.append(f"PDF URL: {document.get('pdf_url', 'N/A')}")
            output.append(f"Source: Federal Register API")
            output.append("=" * 80)
            output.append("")

            if document.get('abstract'):
                output.append("ABSTRACT:")
                output.append(document['abstract'])
                output.append("")
                output.append("=" * 80)
                output.append("")

            output.append("FULL DOCUMENT:")
            output.append("")

            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove scripts, styles, navigation
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()

            text = soup.get_text(separator='\n', strip=True)
            output.append(text)

            full_text = '\n'.join(output)

            # Save
            filepath.write_text(full_text, encoding='utf-8')
            self.stats['total_size'] += len(full_text.encode('utf-8'))

            return True

        except Exception as e:
            self.logger.error(f"Error downloading Federal Register doc: {e}")
            return False

    @retry_on_error(max_retries=3)
    def _download_web_document(self, document: Dict, filepath: Path) -> bool:
        """Download document from web URL"""
        try:
            url = document.get('url')

            if not url:
                return False

            response = self.client.get(url, timeout=30)
            response.raise_for_status()

            # Create header
            output = []
            output.append(f"Agency: {document.get('agency', 'Unknown')}")
            output.append(f"Title: {document.get('title', 'Untitled')}")
            output.append(f"URL: {url}")
            output.append(f"Source: {document.get('source', 'Unknown')}")

            if document.get('publication_date'):
                output.append(f"Publication Date: {document['publication_date']}")

            output.append(f"Downloaded: {datetime.now().isoformat()}")
            output.append("=" * 80)
            output.append("")

            if document.get('summary'):
                output.append("SUMMARY:")
                output.append(document['summary'])
                output.append("")
                output.append("=" * 80)
                output.append("")

            # Parse content
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()

            text = soup.get_text(separator='\n', strip=True)
            output.append(text)

            full_text = '\n'.join(output)

            # Save
            filepath.write_text(full_text, encoding='utf-8')
            self.stats['total_size'] += len(full_text.encode('utf-8'))

            return True

        except Exception as e:
            self.logger.error(f"Error downloading web document: {e}")
            return False

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename by removing invalid characters"""
        import re
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Replace spaces with underscores
        filename = filename.replace(' ', '_')
        return filename

    def _save_metadata(self, documents: List[Dict]):
        """Save download metadata"""
        metadata_path = self.output_dir / "metadata.json"

        metadata = {
            'download_date': datetime.now().isoformat(),
            'date_range': {
                'start': self.start_date.isoformat(),
                'end': self.end_date.isoformat()
            },
            'total_documents': len(documents),
            'stats': self.stats,
            'documents': documents
        }

        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Metadata saved to {metadata_path}")

    def _print_summary(self):
        """Print download summary"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("REGULATORY DOWNLOAD SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Success: {self.stats['success']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        self.logger.info(f"Skipped: {self.stats['skipped']}")
        self.logger.info(f"Total Size: {self.stats['total_size'] / 1024 / 1024:.2f} MB")
        self.logger.info("\nBy Source:")
        for source, count in self.stats['by_source'].items():
            self.logger.info(f"  {source}: {count}")
        self.logger.info("=" * 60)

    def __del__(self):
        """Cleanup on destruction"""
        if hasattr(self, 'client'):
            self.client.close()
