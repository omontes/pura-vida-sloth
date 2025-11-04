"""
Press Release Downloader (Enhanced)
====================================
Downloads press releases using company RSS feeds with web scraping fallbacks

Target: 250-350 press releases in 30 days
- Primary: Company RSS feeds (6 major companies)
- Fallback: Web scraping company newsrooms
- Optional: NewsAPI.org integration

Improvements:
- RSS feed parsing for reliable updates
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


class PressReleaseDownloader:
    """Download company press releases with RSS feeds and fallbacks"""

    def __init__(self, output_dir: Path, start_date: datetime, end_date: datetime,
                 companies: Optional[Dict[str, str]] = None):
        """
        Initialize Press Release downloader

        Args:
            output_dir: Directory to save press releases
            start_date: Start date for press releases
            end_date: End date for press releases
            companies: Dict of ticker symbols to company names (e.g. {'JOBY': 'Joby Aviation'})
                      If None, uses Config.TARGET_COMPANIES for backward compatibility
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.start_date = start_date
        self.end_date = end_date

        self.logger = setup_logger("PressReleaseDownloader", self.output_dir / "press.log")

        # Initialize clients
        self.client = requests.Session()  # Use simple session instead of APIClient
        self.checkpoint = CheckpointManager(self.output_dir, 'press')
        self.rss_aggregator = FeedAggregator(start_date, end_date)

        # Use provided companies or fall back to config (backward compatibility)
        self.companies = companies if companies is not None else Config.TARGET_COMPANIES

        self.stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total_size': 0,
            'by_source': {
                'rss_feeds': 0,
                'web_scraping': 0,
                'newsapi': 0
            }
        }

        resume_info = self.checkpoint.get_resume_info()
        if resume_info:
            self.logger.info(resume_info)

    def download(self) -> Dict:
        """Main download method"""
        self.logger.info(f"Starting press release download")
        self.logger.info(f"Date range: {self.start_date.date()} to {self.end_date.date()}")
        self.logger.info(f"Target companies: {len(self.companies)}")

        all_releases = []

        # Method 1: Company RSS feeds (primary)
        self.logger.info("✓ Using company RSS feeds (primary source)")
        rss_releases = self._get_rss_releases()
        all_releases.extend(rss_releases)
        self.logger.info(f"  Found {len(rss_releases)} releases from RSS feeds")

        # Method 2: Web scraping (fallback for companies without RSS)
        self.logger.info("Fetching from company newsrooms (fallback)...")
        web_releases = self._get_web_releases()
        all_releases.extend(web_releases)
        self.logger.info(f"  Found {len(web_releases)} releases from web scraping")

        # Method 3: NewsAPI (optional)
        if Config.NEWSAPI_KEY:
            self.logger.info("Fetching from NewsAPI (supplementary)...")
            news_releases = self._get_newsapi_releases()
            all_releases.extend(news_releases)
            self.logger.info(f"  Found {len(news_releases)} releases from NewsAPI")

        # Deduplicate
        unique_releases = self._deduplicate_releases(all_releases)
        self.logger.info(f"Total unique releases to download: {len(unique_releases)}")

        # Download
        self.logger.info("Downloading press releases...")
        with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS['press']) as executor:
            futures = {executor.submit(self._download_release, r): r for r in unique_releases}
            for future in tqdm(as_completed(futures), total=len(futures), desc="Downloading releases"):
                try:
                    future.result()
                except Exception as e:
                    self.logger.error(f"Download error: {e}")

        self.checkpoint.finalize()
        self._save_metadata(unique_releases)
        self._print_summary()

        return self.stats

    def _get_rss_releases(self) -> List[Dict]:
        """Get press releases from company RSS feeds"""
        releases = []

        # Add all company RSS feeds
        feed_counts = self.rss_aggregator.add_feeds(Config.COMPANY_RSS_FEEDS)

        for source, count in feed_counts.items():
            self.logger.debug(f"RSS: {source} - {count} entries")

        # Get all entries
        entries = self.rss_aggregator.get_entries(sort_by_date=True, deduplicate=True)

        # Convert to release format
        for entry in entries:
            releases.append({
                'source': 'rss_feeds',
                'company': entry['source'],
                'title': entry['title'],
                'url': entry['link'],
                'published': entry['pub_date'].isoformat() if entry.get('pub_date') else None,
                'summary': entry.get('summary', '')
            })

        return releases

    @retry_on_error(max_retries=3)
    def _get_web_releases(self) -> List[Dict]:
        """Get press releases from web scraping (companies without RSS)"""
        releases = []

        # Companies without RSS feeds
        companies_without_rss = {
            ticker: name for ticker, name in self.companies.items()
            if ticker not in Config.COMPANY_RSS_FEEDS
        }

        # Hardcoded newsroom URLs for major companies
        newsroom_urls = {
            'GS': 'https://www.goldmansachs.com/media-relations/press-releases',
            'MS': 'https://www.morganstanley.com/press-releases',
            'WFC': 'https://newsroom.wf.com/English/news-releases',
            'C': 'https://www.citigroup.com/global/news',
            'SCHW': 'https://pressroom.aboutschwab.com/',
            'BLK': 'https://www.blackrock.com/corporate/newsroom',
            'AIG': 'https://www.aig.com/about-us/media-center/news-releases',
            'HOOD': 'https://newsroom.aboutrobinhood.com/',
            'SOFI': 'https://www.sofi.com/press/',
            'AFRM': 'https://www.affirm.com/press'
        }

        for ticker, url in newsroom_urls.items():
            item_id = f"web_{ticker}"

            if self.checkpoint.is_completed(item_id):
                continue

            try:
                response = self.client.get(url)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'html.parser')

                # Generic link finding (pattern varies by site)
                links = soup.find_all('a', href=True)

                for link in links[:20]:  # Limit to recent 20
                    href = link.get('href', '')
                    text = link.text.strip()

                    # Filter for press release-like links
                    if not text or len(text) < 20:
                        continue

                    # Check if it looks like a press release
                    if any(keyword in text.lower() for keyword in
                           ['announce', 'launch', 'report', 'release', 'news', 'update']):

                        if not href.startswith('http'):
                            from urllib.parse import urljoin
                            href = urljoin(url, href)

                        releases.append({
                            'source': 'web_scraping',
                            'company': ticker,
                            'title': text,
                            'url': href,
                            'published': None
                        })

                self.checkpoint.mark_completed(item_id)
                time.sleep(1)  # Rate limiting

            except Exception as e:
                self.logger.debug(f"Web scraping error for {ticker}: {e}")
                self.checkpoint.mark_failed(item_id, str(e))

        return releases

    @retry_on_error(max_retries=2)
    def _get_newsapi_releases(self) -> List[Dict]:
        """Get press releases from NewsAPI (optional)"""
        releases = []

        if not Config.NEWSAPI_KEY:
            return releases

        # Search for press releases from major companies
        for ticker, name in list(self.companies.items())[:10]:  # Limit to 10 to save quota
            item_id = f"newsapi_{ticker}"

            if self.checkpoint.is_completed(item_id):
                continue

            try:
                url = 'https://newsapi.org/v2/everything'
                params = {
                    'q': f'"{name}" press release',
                    'from': self.start_date.strftime('%Y-%m-%d'),
                    'to': self.end_date.strftime('%Y-%m-%d'),
                    'language': 'en',
                    'sortBy': 'publishedAt',
                    'pageSize': 10,
                    'apiKey': Config.NEWSAPI_KEY
                }

                response = self.client.get(url, params=params)
                response.raise_for_status()

                data = response.json()

                if data.get('status') == 'ok' and data.get('articles'):
                    for article in data['articles']:
                        releases.append({
                            'source': 'newsapi',
                            'company': ticker,
                            'title': article.get('title', 'Untitled'),
                            'url': article.get('url', ''),
                            'published': article.get('publishedAt'),
                            'summary': article.get('description', '')
                        })

                self.checkpoint.mark_completed(item_id)
                time.sleep(1)  # Rate limiting

            except Exception as e:
                self.logger.debug(f"NewsAPI error for {ticker}: {e}")
                self.checkpoint.mark_failed(item_id, str(e))

        return releases

    def _deduplicate_releases(self, releases: List[Dict]) -> List[Dict]:
        """Remove duplicate releases based on URL"""
        seen = set()
        unique = []

        for release in releases:
            url = release.get('url', '')
            if url and url not in seen:
                seen.add(url)
                unique.append(release)

        return unique

    def _download_release(self, release: Dict):
        """Download a single press release"""
        try:
            source = release['source']
            company = release.get('company', 'Unknown')
            title = release.get('title', 'Untitled')

            # Create filename
            safe_title = self._sanitize_filename(title)[:80]
            pub_date = release.get('published', '')

            if pub_date:
                safe_date = pub_date.replace(':', '-').replace('/', '-')[:10]
                filename = f"{company}_{safe_date}_{safe_title}.html"
            else:
                timestamp = datetime.now().strftime('%Y%m%d')
                filename = f"{company}_{timestamp}_{safe_title}.html"

            filepath = self.output_dir / filename

            # Skip if exists
            if filepath.exists():
                self.stats['skipped'] += 1
                return

            # Download
            url = release.get('url')
            if not url:
                self.stats['failed'] += 1
                return

            response = self.client.get(url, timeout=30)
            response.raise_for_status()

            # Create formatted output
            output = []
            output.append(f"Company: {company}")
            output.append(f"Title: {title}")
            output.append(f"URL: {url}")
            output.append(f"Source: {source}")

            if release.get('published'):
                output.append(f"Published: {release['published']}")

            output.append(f"Downloaded: {datetime.now().isoformat()}")
            output.append("=" * 80)
            output.append("")

            if release.get('summary'):
                output.append("SUMMARY:")
                output.append(release['summary'])
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

            self.stats['success'] += 1
            self.stats['by_source'][source] += 1
            self.stats['total_size'] += len(full_text.encode('utf-8'))

            self.logger.debug(f"Downloaded: {filename}")

        except Exception as e:
            self.logger.error(f"Failed to download release: {e}")
            self.stats['failed'] += 1

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename"""
        import re
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        return filename.replace(' ', '_')

    def _save_metadata(self, releases: List[Dict]):
        """Save metadata"""
        metadata_path = self.output_dir / "metadata.json"
        metadata = {
            'download_date': datetime.now().isoformat(),
            'date_range': {
                'start': self.start_date.isoformat(),
                'end': self.end_date.isoformat()
            },
            'total_releases': len(releases),
            'stats': self.stats,
            'releases': releases
        }
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Metadata saved to {metadata_path}")

    def _print_summary(self):
        """Print summary"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("PRESS RELEASE DOWNLOAD SUMMARY")
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
        if hasattr(self, 'client'):
            self.client.close()
