"""
Earnings Call Transcript Downloader (Enhanced)
===============================================
Downloads earnings call transcripts using FMP API with web scraping fallbacks

Target: 300-400 transcripts in 30 days
- Primary source: Financial Modeling Prep API
- Fallback 1: SeekingAlpha (web scraping)
- Fallback 2: Company investor relations pages

Improvements:
- FMP API integration for reliable transcript access
- Retry logic with exponential backoff
- 429 rate limit detection
- Resume capability with checkpoints
- Multi-level fallback system
"""

import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import logging

from src.utils.logger import setup_logger
from src.utils.config import Config
from src.utils.api_client import FMPAPIClient
import requests
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.retry_handler import retry_on_error


class EarningsDownloader:
    """Download earnings call transcripts with FMP API and fallbacks"""

    def __init__(self, output_dir: Path, start_date: datetime, end_date: datetime):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.start_date = start_date
        self.end_date = end_date

        self.logger = setup_logger("EarningsDownloader", self.output_dir / "earnings.log")

        # Initialize API client and checkpoint manager
        self.fmp_client = FMPAPIClient() if Config.FMP_API_KEY else None
        self.scraper_client = requests.Session()  # Use simple session instead of APIClient
        self.checkpoint = CheckpointManager(self.output_dir, 'earnings')

        # Get target companies from config
        self.companies = Config.TARGET_COMPANIES

        self.stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total_size': 0,
            'by_source': {
                'fmp_api': 0,
                'seekingalpha': 0,
                'company_ir': 0
            }
        }

        # Check resume info
        resume_info = self.checkpoint.get_resume_info()
        if resume_info:
            self.logger.info(resume_info)

    def download(self) -> Dict:
        """Main download method with multi-source approach"""
        self.logger.info(f"Starting earnings transcript download")
        self.logger.info(f"Date range: {self.start_date.date()} to {self.end_date.date()}")
        self.logger.info(f"Target companies: {len(self.companies)}")

        all_transcripts = []

        # Method 1: FMP API (if configured)
        if self.fmp_client and Config.FMP_API_KEY:
            self.logger.info("✓ Using FMP API (primary source)")
            fmp_transcripts = self._get_fmp_transcripts()
            all_transcripts.extend(fmp_transcripts)
            self.logger.info(f"  Found {len(fmp_transcripts)} transcripts from FMP API")
        else:
            self.logger.warning("⚠ FMP API not configured, using fallback methods only")

        # Method 2: SeekingAlpha scraping (fallback)
        self.logger.info("Fetching from SeekingAlpha (fallback)...")
        sa_transcripts = self._get_seekingalpha_transcripts()
        all_transcripts.extend(sa_transcripts)
        self.logger.info(f"  Found {len(sa_transcripts)} transcripts from SeekingAlpha")

        # Method 3: Company IR pages (fallback)
        self.logger.info("Fetching from company IR pages (fallback)...")
        ir_transcripts = self._get_company_ir_transcripts()
        all_transcripts.extend(ir_transcripts)
        self.logger.info(f"  Found {len(ir_transcripts)} transcripts from company IR")

        # Remove duplicates (by URL)
        unique_transcripts = self._deduplicate_transcripts(all_transcripts)
        self.logger.info(f"Total unique transcripts to download: {len(unique_transcripts)}")

        # Download transcripts with progress bar
        self.logger.info("Downloading transcripts...")
        with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS['earnings']) as executor:
            futures = {
                executor.submit(self._download_transcript, t): t
                for t in unique_transcripts
            }

            for future in tqdm(as_completed(futures),
                             total=len(futures),
                             desc="Downloading transcripts"):
                try:
                    future.result()
                except Exception as e:
                    self.logger.error(f"Download error: {e}")

        # Finalize checkpoint
        self.checkpoint.finalize()

        # Save metadata
        self._save_metadata(unique_transcripts)

        # Print summary
        self._print_summary()

        return self.stats

    def _get_fmp_transcripts(self) -> List[Dict]:
        """Get transcripts from Financial Modeling Prep API"""
        transcripts = []

        if not self.fmp_client:
            return transcripts

        # Calculate quarters to fetch based on date range
        quarters_to_fetch = self._calculate_quarters(self.start_date, self.end_date)

        self.logger.info(f"Fetching transcripts for {len(quarters_to_fetch)} quarters")

        for ticker in self.companies.keys():
            # Check if already completed
            if self.checkpoint.is_completed(f"fmp_{ticker}"):
                continue

            try:
                for quarter, year in quarters_to_fetch:
                    item_id = f"fmp_{ticker}_Q{quarter}_{year}"

                    # Skip if already processed
                    if self.checkpoint.is_completed(item_id):
                        continue

                    # Fetch transcript
                    data = self.fmp_client.get_earnings_transcript(ticker, quarter, year)

                    if data and isinstance(data, list) and len(data) > 0:
                        transcript_data = data[0]

                        transcripts.append({
                            'ticker': ticker,
                            'company': self.companies[ticker],
                            'source': 'fmp_api',
                            'data': transcript_data,
                            'quarter': quarter,
                            'year': year,
                            'title': f"{ticker} Q{quarter} {year} Earnings Call"
                        })

                        self.checkpoint.mark_completed(item_id, {
                            'ticker': ticker,
                            'quarter': quarter,
                            'year': year
                        })

                        self.logger.debug(f"Found: {ticker} Q{quarter} {year}")

                    time.sleep(0.1)  # Small delay between requests

            except Exception as e:
                self.logger.error(f"FMP API error for {ticker}: {e}")
                self.checkpoint.mark_failed(f"fmp_{ticker}", str(e))

        return transcripts

    def _calculate_quarters(self, start_date: datetime, end_date: datetime) -> List[Tuple[int, int]]:
        """
        Calculate quarters to fetch based on date range

        Returns:
            List of (quarter, year) tuples
        """
        quarters = []
        current = start_date

        while current <= end_date:
            quarter = (current.month - 1) // 3 + 1
            year = current.year

            if (quarter, year) not in quarters:
                quarters.append((quarter, year))

            # Move to next quarter
            current = current + timedelta(days=90)

        return quarters

    @retry_on_error(max_retries=3)
    def _get_seekingalpha_transcripts(self) -> List[Dict]:
        """Get transcripts from SeekingAlpha (web scraping fallback)"""
        transcripts = []

        try:
            for ticker in list(self.companies.keys())[:15]:  # Limit to avoid blocking
                item_id = f"sa_{ticker}"

                # Skip if already completed
                if self.checkpoint.is_completed(item_id):
                    continue

                try:
                    search_url = f"https://seekingalpha.com/symbol/{ticker}/earnings/transcripts"

                    response = self.scraper_client.get(search_url)

                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')

                        # Find transcript links
                        transcript_links = soup.find_all('a', href=lambda x: x and '/article/' in x)

                        for link in transcript_links[:3]:  # Limit to recent 3
                            href = link.get('href')
                            if not href.startswith('http'):
                                href = f"https://seekingalpha.com{href}"

                            # Check if earnings-related
                            if 'earnings' in href.lower() or 'transcript' in link.text.lower():
                                transcripts.append({
                                    'ticker': ticker,
                                    'company': self.companies[ticker],
                                    'source': 'seekingalpha',
                                    'url': href,
                                    'title': link.text.strip() or 'Earnings Call Transcript'
                                })

                        self.checkpoint.mark_completed(item_id)

                except Exception as e:
                    self.logger.debug(f"SeekingAlpha error for {ticker}: {e}")
                    self.checkpoint.mark_failed(item_id, str(e))

                time.sleep(1)  # Rate limiting

        except Exception as e:
            self.logger.error(f"SeekingAlpha scraping error: {e}")

        return transcripts

    @retry_on_error(max_retries=3)
    def _get_company_ir_transcripts(self) -> List[Dict]:
        """Get transcripts from company investor relations pages"""
        transcripts = []

        ir_urls = Config.COMPANY_IR_URLS

        for ticker, url in ir_urls.items():
            item_id = f"ir_{ticker}"

            # Skip if already completed
            if self.checkpoint.is_completed(item_id):
                continue

            try:
                response = self.scraper_client.get(url)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Look for transcript links
                    links = soup.find_all('a', href=lambda x: x and
                                         ('transcript' in x.lower() or 'earnings' in x.lower()))

                    for link in links[:2]:  # Limit to 2 most recent
                        href = link.get('href')
                        if not href.startswith('http'):
                            from urllib.parse import urljoin
                            href = urljoin(url, href)

                        transcripts.append({
                            'ticker': ticker,
                            'company': self.companies.get(ticker, ticker),
                            'source': 'company_ir',
                            'url': href,
                            'title': link.text.strip() or 'Earnings Transcript'
                        })

                    self.checkpoint.mark_completed(item_id)

                time.sleep(0.5)

            except Exception as e:
                self.logger.debug(f"Company IR error for {ticker}: {e}")
                self.checkpoint.mark_failed(item_id, str(e))

        return transcripts

    def _deduplicate_transcripts(self, transcripts: List[Dict]) -> List[Dict]:
        """Remove duplicate transcripts based on URL or data content"""
        seen = set()
        unique = []

        for transcript in transcripts:
            # Create unique identifier
            if 'url' in transcript:
                identifier = transcript['url']
            elif 'data' in transcript:
                identifier = f"{transcript['ticker']}_Q{transcript.get('quarter')}_{transcript.get('year')}"
            else:
                identifier = transcript.get('title', str(transcript))

            if identifier not in seen:
                seen.add(identifier)
                unique.append(transcript)

        return unique

    def _download_transcript(self, transcript: Dict):
        """Download a single transcript with multi-source handling"""
        try:
            ticker = transcript['ticker']
            source = transcript['source']

            # Create filename
            if source == 'fmp_api':
                quarter = transcript.get('quarter', '')
                year = transcript.get('year', '')
                filename = f"{ticker}_Q{quarter}_{year}_earnings_fmp.txt"
            else:
                timestamp = datetime.now().strftime('%Y%m%d')
                filename = f"{ticker}_earnings_{source}_{timestamp}.txt"

            filepath = self.output_dir / filename

            # Skip if exists
            if filepath.exists():
                self.stats['skipped'] += 1
                self.logger.debug(f"Skipped (exists): {filename}")
                return

            # Download based on source
            if source == 'fmp_api':
                success = self._save_fmp_transcript(transcript, filepath)
            else:
                success = self._download_web_transcript(transcript, filepath)

            if success:
                self.stats['success'] += 1
                self.stats['by_source'][source] += 1
                self.logger.debug(f"Downloaded: {filename}")
            else:
                self.stats['failed'] += 1

        except Exception as e:
            self.logger.error(f"Failed to download transcript: {e}")
            self.stats['failed'] += 1
            raise

    def _save_fmp_transcript(self, transcript: Dict, filepath: Path) -> bool:
        """Save FMP API transcript data to file"""
        try:
            data = transcript['data']

            # Extract content
            content = data.get('content', '')

            if not content:
                self.logger.warning(f"No content in FMP transcript for {transcript['ticker']}")
                return False

            # Create formatted output
            output = []
            output.append(f"Company: {transcript['company']} ({transcript['ticker']})")
            output.append(f"Quarter: Q{transcript['quarter']} {transcript['year']}")
            output.append(f"Date: {data.get('date', 'Unknown')}")
            output.append(f"Source: Financial Modeling Prep API")
            output.append("=" * 80)
            output.append("")
            output.append(content)

            text = '\n'.join(output)

            # Save to file
            filepath.write_text(text, encoding='utf-8')

            self.stats['total_size'] += len(text.encode('utf-8'))

            return True

        except Exception as e:
            self.logger.error(f"Error saving FMP transcript: {e}")
            return False

    @retry_on_error(max_retries=3)
    def _download_web_transcript(self, transcript: Dict, filepath: Path) -> bool:
        """Download transcript from web URL"""
        try:
            url = transcript['url']

            response = self.scraper_client.get(url, timeout=30)
            response.raise_for_status()

            # Parse content
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove scripts, styles, navigation
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()

            # Extract text
            text = soup.get_text(separator='\n', strip=True)

            # Create header
            header = []
            header.append(f"Company: {transcript['company']} ({transcript['ticker']})")
            header.append(f"Title: {transcript['title']}")
            header.append(f"URL: {url}")
            header.append(f"Source: {transcript['source']}")
            header.append(f"Downloaded: {datetime.now().isoformat()}")
            header.append("=" * 80)
            header.append("")

            full_text = '\n'.join(header) + '\n' + text

            # Save
            filepath.write_text(full_text, encoding='utf-8')

            self.stats['total_size'] += len(full_text.encode('utf-8'))

            return True

        except Exception as e:
            self.logger.error(f"Failed to download from {transcript.get('url')}: {e}")
            return False

    def _save_metadata(self, transcripts: List[Dict]):
        """Save download metadata"""
        metadata_path = self.output_dir / "metadata.json"

        # Remove 'data' field from transcripts for cleaner metadata
        clean_transcripts = []
        for t in transcripts:
            clean_t = {k: v for k, v in t.items() if k != 'data'}
            clean_transcripts.append(clean_t)

        metadata = {
            'download_date': datetime.now().isoformat(),
            'date_range': {
                'start': self.start_date.isoformat(),
                'end': self.end_date.isoformat()
            },
            'total_transcripts': len(transcripts),
            'stats': self.stats,
            'transcripts': clean_transcripts
        }

        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Metadata saved to {metadata_path}")

    def _print_summary(self):
        """Print download summary"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("EARNINGS DOWNLOAD SUMMARY")
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
        if hasattr(self, 'fmp_client') and self.fmp_client:
            self.fmp_client.close()
        if hasattr(self, 'scraper_client'):
            self.scraper_client.close()
