"""
Research Paper Downloader (Enhanced)
=====================================
Downloads academic research papers using CORE API, FRASER API, arXiv, and RSS feeds

Target: 600-800 papers in 30 days
- Primary: CORE API (200M+ papers, 10k requests/day free)
- Secondary: arXiv API (Quantitative Finance)
- Tertiary: FRASER API (Federal Reserve Archive)
- RSS Feeds: Fed Notes, Fed Papers, BIS, NBER
- Fallback: SSRN web scraping

Improvements:
- CORE API integration for massive coverage
- FRASER API for Fed research
- Optimized arXiv queries (batch mode)
- RSS feed parsing
- Retry logic and checkpoints
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
import xml.etree.ElementTree as ET

from src.utils.logger import setup_logger
from src.utils.config import Config
from src.utils.api_client import COREAPIClient
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.retry_handler import retry_on_error
from src.utils.rss_parser import FeedAggregator


class ResearchDownloader:
    """Download research papers with multiple API sources"""

    def __init__(self, output_dir: Path, start_date: datetime, end_date: datetime, keywords: List[str] = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.start_date = start_date
        self.end_date = end_date

        self.logger = setup_logger("ResearchDownloader", self.output_dir / "research.log")

        # Initialize clients
        self.core_client = COREAPIClient() if Config.CORE_API_KEY else None
        self.client = requests.Session()  # Use simple session instead of APIClient
        self.checkpoint = CheckpointManager(self.output_dir, 'research')
        self.rss_aggregator = FeedAggregator(start_date, end_date)

        # Use provided keywords or fall back to Config (backward compatibility)
        self.keywords = keywords if keywords is not None else Config.RESEARCH_KEYWORDS

        self.stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total_size': 0,
            'by_source': {
                'core_api': 0,
                'arxiv': 0,
                'fraser': 0,
                'rss_feeds': 0,
                'ssrn': 0
            }
        }

        resume_info = self.checkpoint.get_resume_info()
        if resume_info:
            self.logger.info(resume_info)

    def download(self) -> Dict:
        """Main download method"""
        self.logger.info(f"Starting research paper download")
        self.logger.info(f"Date range: {self.start_date.date()} to {self.end_date.date()}")
        self.logger.info(f"Keywords: {len(self.keywords)}")

        all_papers = []

        # Method 1: CORE API (primary)
        if self.core_client and Config.CORE_API_KEY:
            self.logger.info("✓ Using CORE API (primary source)")
            core_papers = self._get_core_papers()
            all_papers.extend(core_papers)
            self.logger.info(f"  Found {len(core_papers)} papers from CORE API")
        else:
            self.logger.warning("⚠ CORE API not configured")

        # Method 2: arXiv API (optimized)
        self.logger.info("Fetching from arXiv...")
        arxiv_papers = self._get_arxiv_papers()
        all_papers.extend(arxiv_papers)
        self.logger.info(f"  Found {len(arxiv_papers)} papers from arXiv")

        # Method 3: FRASER API (Fed research)
        self.logger.info("Fetching from FRASER...")
        fraser_papers = self._get_fraser_papers()
        all_papers.extend(fraser_papers)
        self.logger.info(f"  Found {len(fraser_papers)} papers from FRASER")

        # Method 4: RSS Feeds
        self.logger.info("Fetching from RSS feeds...")
        rss_papers = self._get_rss_papers()
        all_papers.extend(rss_papers)
        self.logger.info(f"  Found {len(rss_papers)} papers from RSS")

        # Method 5: SSRN (limited)
        self.logger.info("Fetching from SSRN (limited)...")
        ssrn_papers = self._get_ssrn_papers()
        all_papers.extend(ssrn_papers)
        self.logger.info(f"  Found {len(ssrn_papers)} papers from SSRN")

        # Deduplicate
        unique_papers = self._deduplicate_papers(all_papers)
        self.logger.info(f"Total unique papers to download: {len(unique_papers)}")

        # Download
        self.logger.info("Downloading papers...")
        with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS['research']) as executor:
            futures = {executor.submit(self._download_paper, p): p for p in unique_papers}
            for future in tqdm(as_completed(futures), total=len(futures), desc="Downloading papers"):
                try:
                    future.result()
                except Exception as e:
                    self.logger.error(f"Download error: {e}")

        self.checkpoint.finalize()
        self._save_metadata(unique_papers)
        self._print_summary()

        return self.stats

    @retry_on_error(max_retries=3)
    def _get_core_papers(self) -> List[Dict]:
        """Get papers from CORE API"""
        papers = []

        if not self.core_client:
            return papers

        # Search for each keyword (limit to avoid quota)
        for keyword in self.keywords[:15]:  # First 15 keywords
            item_id = f"core_{keyword.replace(' ', '_')}"

            if self.checkpoint.is_completed(item_id):
                continue

            try:
                results = self.core_client.search_works(keyword, limit=50)

                if results and 'results' in results:
                    for work in results['results']:
                        papers.append({
                            'source': 'core_api',
                            'title': work.get('title', 'Untitled'),
                            'authors': work.get('authors', []),
                            'abstract': work.get('abstract', ''),
                            'year': work.get('yearPublished'),
                            'url': work.get('downloadUrl') or work.get('sourceFulltextUrls', [''])[0],
                            'doi': work.get('doi', ''),
                            'keyword': keyword
                        })

                self.checkpoint.mark_completed(item_id)
                time.sleep(0.5)

            except Exception as e:
                self.logger.error(f"CORE API error for '{keyword}': {e}")
                self.checkpoint.mark_failed(item_id, str(e))

        return papers

    @retry_on_error(max_retries=3)
    def _get_arxiv_papers(self) -> List[Dict]:
        """Get papers from arXiv (optimized batch queries)"""
        papers = []

        # Batch keywords for efficiency
        batch_query = ' OR '.join([f'all:{kw}' for kw in self.keywords[:10]])

        item_id = "arxiv_batch"
        if self.checkpoint.is_completed(item_id):
            return papers

        try:
            url = Config.ARXIV_API_ENDPOINT
            params = {
                'search_query': f'cat:q-fin.* AND ({batch_query})',
                'start': 0,
                'max_results': 200,
                'sortBy': 'submittedDate',
                'sortOrder': 'descending'
            }

            response = self.client.get(url, params=params)
            response.raise_for_status()

            # Parse XML
            root = ET.fromstring(response.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}

            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text.strip() if entry.find('atom:title', ns) is not None else 'Untitled'
                summary = entry.find('atom:summary', ns).text.strip() if entry.find('atom:summary', ns) is not None else ''
                pdf_link = next((link.get('href') for link in entry.findall('atom:link', ns) if link.get('type') == 'application/pdf'), None)
                published = entry.find('atom:published', ns).text if entry.find('atom:published', ns) is not None else None

                papers.append({
                    'source': 'arxiv',
                    'title': title,
                    'abstract': summary,
                    'url': pdf_link or entry.find('atom:id', ns).text,
                    'published': published,
                    'is_pdf': bool(pdf_link)
                })

            self.checkpoint.mark_completed(item_id)

        except Exception as e:
            self.logger.error(f"arXiv API error: {e}")
            self.checkpoint.mark_failed(item_id, str(e))

        return papers

    @retry_on_error(max_retries=3)
    def _get_fraser_papers(self) -> List[Dict]:
        """Get papers from FRASER (Federal Reserve Archive)"""
        papers = []

        item_id = "fraser_oai"
        if self.checkpoint.is_completed(item_id):
            return papers

        try:
            # OAI-PMH ListRecords request
            url = Config.FRASER_OAI_ENDPOINT
            params = {
                'verb': 'ListRecords',
                'metadataPrefix': 'oai_dc',
                'from': self.start_date.strftime('%Y-%m-%d'),
                'until': self.end_date.strftime('%Y-%m-%d')
            }

            response = self.client.get(url, params=params)
            response.raise_for_status()

            # Parse OAI-PMH XML
            root = ET.fromstring(response.content)
            ns = {
                'oai': 'http://www.openarchives.org/OAI/2.0/',
                'dc': 'http://purl.org/dc/elements/1.1/'
            }

            for record in root.findall('.//oai:record', ns):
                metadata = record.find('.//oai:metadata', ns)
                if metadata is not None:
                    dc = metadata.find('oai_dc:dc', {'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/', **ns})
                    if dc is not None:
                        title_elem = dc.find('dc:title', ns)
                        identifier_elem = dc.find('dc:identifier', ns)

                        if title_elem is not None and identifier_elem is not None:
                            papers.append({
                                'source': 'fraser',
                                'title': title_elem.text,
                                'url': identifier_elem.text,
                                'description': dc.find('dc:description', ns).text if dc.find('dc:description', ns) is not None else ''
                            })

            self.checkpoint.mark_completed(item_id)

        except Exception as e:
            self.logger.error(f"FRASER API error: {e}")
            self.checkpoint.mark_failed(item_id, str(e))

        return papers

    def _get_rss_papers(self) -> List[Dict]:
        """Get papers from RSS feeds"""
        papers = []

        # Add all research RSS feeds
        self.rss_aggregator.add_feeds(Config.RESEARCH_RSS_FEEDS)
        entries = self.rss_aggregator.get_entries(sort_by_date=True, deduplicate=True)

        for entry in entries:
            papers.append({
                'source': 'rss_feeds',
                'title': entry['title'],
                'url': entry['link'],
                'summary': entry.get('summary', ''),
                'published': entry['pub_date'].isoformat() if entry.get('pub_date') else None,
                'rss_source': entry['source']
            })

        return papers

    @retry_on_error(max_retries=2)
    def _get_ssrn_papers(self) -> List[Dict]:
        """Get papers from SSRN (limited - abstracts only)"""
        papers = []

        # SSRN requires auth for PDFs, only get abstracts
        for keyword in self.keywords[:5]:  # Very limited
            item_id = f"ssrn_{keyword.replace(' ', '_')}"
            if self.checkpoint.is_completed(item_id):
                continue

            try:
                search_url = f"https://papers.ssrn.com/sol3/results.cfm"
                params = {'npage': '1', 'rpp': '10', 'abstract_id': keyword}

                response = self.client.get(search_url, params=params)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    links = soup.find_all('a', href=lambda x: x and 'abstract_id=' in x)

                    for link in links[:5]:
                        href = link.get('href')
                        if not href.startswith('http'):
                            href = f"https://papers.ssrn.com{href}"

                        papers.append({
                            'source': 'ssrn',
                            'title': link.text.strip() or 'SSRN Paper',
                            'url': href,
                            'keyword': keyword
                        })

                self.checkpoint.mark_completed(item_id)
                time.sleep(2)  # Rate limiting

            except Exception as e:
                self.logger.debug(f"SSRN error for '{keyword}': {e}")
                self.checkpoint.mark_failed(item_id, str(e))

        return papers

    def _deduplicate_papers(self, papers: List[Dict]) -> List[Dict]:
        """Remove duplicate papers"""
        seen = set()
        unique = []

        for paper in papers:
            identifier = paper.get('doi') or paper.get('url') or paper.get('title', '')
            if identifier and identifier not in seen:
                seen.add(identifier)
                unique.append(paper)

        return unique

    def _download_paper(self, paper: Dict):
        """Download a single paper"""
        try:
            source = paper['source']
            title = paper.get('title', 'Untitled')

            # Create filename
            safe_title = self._sanitize_filename(title)[:80]
            timestamp = datetime.now().strftime('%Y%m%d')

            if source == 'arxiv' and paper.get('is_pdf'):
                ext = 'pdf'
            else:
                ext = 'html'

            filename = f"{source}_{timestamp}_{safe_title}.{ext}"
            filepath = self.output_dir / filename

            if filepath.exists():
                self.stats['skipped'] += 1
                return

            # Download
            url = paper.get('url')
            if not url:
                self.stats['failed'] += 1
                return

            response = self.client.get(url, timeout=30)
            response.raise_for_status()

            # Save based on type
            if ext == 'pdf':
                # Validate PDF before saving (check for PDF header)
                if response.content[:4] == b'%PDF':
                    filepath.write_bytes(response.content)
                    # Add delay after arXiv PDF download to avoid rate limiting
                    if source == 'arxiv':
                        time.sleep(3)  # arXiv rate limit: 1 request per 3 seconds
                else:
                    # Not a valid PDF - likely CAPTCHA or error page
                    self.logger.warning(f"Invalid PDF response for {title} - likely CAPTCHA or rate limit")
                    self.logger.warning(f"Response starts with: {response.content[:100]}")
                    self.stats['failed'] += 1
                    return
            else:
                # Create formatted HTML/text
                output = [
                    f"Title: {title}",
                    f"Source: {source}",
                    f"URL: {url}",
                    f"Downloaded: {datetime.now().isoformat()}",
                    "=" * 80,
                    ""
                ]

                if paper.get('abstract'):
                    output.append(f"Abstract: {paper['abstract']}")
                    output.append("")

                if paper.get('authors'):
                    # Handle authors as list of strings or list of dicts
                    authors = paper['authors']
                    if authors and isinstance(authors[0], dict):
                        author_names = [a.get('name', str(a)) for a in authors if a]
                    else:
                        author_names = [str(a) for a in authors]
                    output.append(f"Authors: {', '.join(author_names)}")
                    output.append("")

                # Parse content
                soup = BeautifulSoup(response.content, 'html.parser')
                for elem in soup(['script', 'style', 'nav', 'footer']):
                    elem.decompose()

                output.append(soup.get_text(separator='\n', strip=True))

                filepath.write_text('\n'.join(output), encoding='utf-8')

            self.stats['success'] += 1
            self.stats['by_source'][source] += 1
            self.stats['total_size'] += filepath.stat().st_size

        except Exception as e:
            self.logger.error(f"Failed to download paper: {e}")
            self.stats['failed'] += 1

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename"""
        import re
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        return filename.replace(' ', '_')

    def _save_metadata(self, papers: List[Dict]):
        """Save metadata"""
        metadata_path = self.output_dir / "metadata.json"
        metadata = {
            'download_date': datetime.now().isoformat(),
            'date_range': {'start': self.start_date.isoformat(), 'end': self.end_date.isoformat()},
            'total_papers': len(papers),
            'stats': self.stats,
            'papers': papers
        }
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def _print_summary(self):
        """Print summary"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("RESEARCH DOWNLOAD SUMMARY")
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
        """Cleanup"""
        if hasattr(self, 'core_client') and self.core_client:
            self.core_client.close()
        if hasattr(self, 'client'):
            self.client.close()
