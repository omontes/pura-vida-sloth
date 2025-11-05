"""
News Article Full-Text Downloader - Multi-Fallback Strategy

Downloads full-text content for news articles using multiple fallback sources:
1. trafilatura (primary - best for article extraction)
2. Wayback Machine archives (fallback for paywalled/dead links)

Industry-agnostic design - works with any news metadata JSON.
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

try:
    import trafilatura
except ImportError:
    trafilatura = None

from src.utils.checkpoint_manager import CheckpointManager
from src.utils.retry_handler import retry_on_error


class NewsFullTextDownloader:
    """
    Download full-text for news articles using multiple fallback strategies.

    CRITICAL: Industry-agnostic design - accepts any news metadata JSON.
    """

    def __init__(
        self,
        metadata_path: Path,
        output_subdir: str = "articles_fulltext",
        delay_range: tuple = (3, 6),
        batch_size: int = 20,
        batch_pause: int = 60
    ):
        """
        Initialize news full-text downloader.

        Args:
            metadata_path: Path to news metadata JSON file
            output_subdir: Subdirectory name for full-text articles
            delay_range: Random delay range between downloads (seconds)
            batch_size: Number of articles to download before pausing
            batch_pause: Pause duration between batches (seconds)
        """
        self.metadata_path = Path(metadata_path)
        self.output_dir = self.metadata_path.parent / output_subdir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.delay_range = delay_range
        self.batch_size = batch_size
        self.batch_pause = batch_pause

        # Load metadata
        with open(self.metadata_path, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)

        # Checkpoint for resume capability
        checkpoint_name = f"news_fulltext_download"
        self.checkpoint = CheckpointManager(self.output_dir, checkpoint_name)

        # Logger
        self.logger = logging.getLogger("NewsFullTextDownloader")
        handler = logging.FileHandler(self.output_dir / "news_fulltext_download.log", encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        # User-Agent
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        # Statistics
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'by_source': {
                'trafilatura': 0,
                'wayback': 0,
                'raw_html': 0
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

    @retry_on_error(max_retries=3, backoff_factor=2)
    def _download_with_trafilatura(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Strategy 1: Download using trafilatura (best for article extraction).

        Returns dict with {'text', 'title', 'date', 'author'} if successful, None otherwise.
        """
        if not trafilatura:
            return None

        try:
            # Download HTML
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return None

            # Extract article content
            text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=True,
                no_fallback=False
            )

            if not text or len(text) < 100:  # Too short
                return None

            # Extract metadata
            metadata = trafilatura.extract_metadata(downloaded)

            result = {
                'text': text,
                'title': metadata.title if metadata and metadata.title else None,
                'date': metadata.date if metadata and metadata.date else None,
                'author': metadata.author if metadata and metadata.author else None,
                'url': url,
                'source': 'trafilatura'
            }

            self.logger.info(f"Extracted {len(text)} chars via trafilatura")
            return result

        except Exception as e:
            self.logger.warning(f"Trafilatura extraction failed for {url}: {e}")
            return None

    @retry_on_error(max_retries=2, backoff_factor=2)
    def _download_via_wayback(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Strategy 2: Try Wayback Machine archived version.

        Returns dict with article content if successful, None otherwise.
        """
        try:
            # Check if URL is archived
            availability_url = f"https://archive.org/wayback/available?url={quote_plus(url)}"
            response = requests.get(availability_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            archived = data.get('archived_snapshots', {}).get('closest')

            if not archived or not archived.get('available'):
                return None

            # Get archived URL
            archived_url = archived.get('url')
            if not archived_url:
                return None

            # Download archived page
            if trafilatura:
                downloaded = trafilatura.fetch_url(archived_url)
                if downloaded:
                    text = trafilatura.extract(downloaded, no_fallback=False)
                    if text and len(text) >= 100:
                        result = {
                            'text': text,
                            'title': None,
                            'date': None,
                            'author': None,
                            'url': url,
                            'archived_url': archived_url,
                            'source': 'wayback'
                        }
                        self.logger.info(f"Extracted {len(text)} chars via Wayback Machine")
                        return result

            return None

        except Exception as e:
            self.logger.warning(f"Wayback Machine failed for {url}: {e}")
            return None

    @retry_on_error(max_retries=3, backoff_factor=2)
    def _download_raw_html(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Strategy 3: Fallback to raw HTML download.

        Returns dict with raw HTML if successful, None otherwise.
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()

            html = response.text

            if len(html) < 500:  # Too short
                return None

            # Try to extract with trafilatura if available
            if trafilatura:
                text = trafilatura.extract(html, no_fallback=False)
                if text and len(text) >= 100:
                    result = {
                        'text': text,
                        'title': None,
                        'date': None,
                        'author': None,
                        'url': url,
                        'source': 'raw_html'
                    }
                    self.logger.info(f"Extracted {len(text)} chars from raw HTML")
                    return result

            # Fallback to saving raw HTML
            result = {
                'text': html,
                'title': None,
                'date': None,
                'author': None,
                'url': url,
                'source': 'raw_html'
            }
            self.logger.info(f"Saved raw HTML ({len(html)} chars)")
            return result

        except Exception as e:
            self.logger.warning(f"Raw HTML download failed for {url}: {e}")
            return None

    def download_all(self) -> Dict[str, Any]:
        """
        Download all available full-text articles using multi-fallback strategy.

        Returns statistics dict.
        """
        self.stats['total'] = len(self.metadata)
        self.logger.info(f"Starting news full-text download for {self.stats['total']} articles")

        for idx, article in enumerate(self.metadata):
            # Generate unique ID
            article_id = hashlib.md5(article.get('url', '').encode()).hexdigest()[:16]

            # Check if already processed
            if self.checkpoint.is_completed(article_id):
                self.stats['skipped'] += 1
                continue

            # Get URL
            url = article.get('url', '')
            if not url:
                self.logger.warning(f"[{idx + 1}/{self.stats['total']}] No URL found")
                self.checkpoint.mark_failed(article_id, "No URL")
                self.stats['failed'] += 1
                continue

            # Generate output filename
            title = article.get('title', f"article_{idx}")
            safe_filename = self._sanitize_filename(title)
            output_path = self.output_dir / f"{safe_filename}.txt"

            # Skip if file already exists
            if output_path.exists():
                self.logger.info(f"Skipping existing file: {output_path.name}")
                self.checkpoint.mark_completed(article_id, metadata={'file_path': str(output_path)})
                self.stats['skipped'] += 1
                continue

            # Try multiple strategies
            content = None
            source = None

            # Strategy 1: trafilatura
            content = self._download_with_trafilatura(url)
            if content:
                source = 'trafilatura'

            # Strategy 2: Wayback Machine
            if not content:
                content = self._download_via_wayback(url)
                if content:
                    source = 'wayback'

            # Strategy 3: Raw HTML
            if not content:
                content = self._download_raw_html(url)
                if content:
                    source = 'raw_html'

            # Save if content found
            if content:
                self.logger.info(f"[{idx + 1}/{self.stats['total']}] Downloaded from {source}: {title[:60]}...")

                # Save to file
                try:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(f"Title: {content.get('title') or article.get('title', 'Unknown')}\n")
                        f.write(f"URL: {content.get('url', url)}\n")
                        f.write(f"Date: {content.get('date') or article.get('seendate', 'Unknown')}\n")
                        f.write(f"Domain: {article.get('domain', 'Unknown')}\n")
                        f.write(f"Source: {content.get('source', 'unknown')}\n")
                        f.write(f"\n{'='*80}\n\n")
                        f.write(content.get('text', ''))

                    self.checkpoint.mark_completed(article_id, metadata={
                        'file_path': str(output_path),
                        'source': source,
                        'char_count': len(content.get('text', ''))
                    })
                    self.stats['success'] += 1
                    self.stats['by_source'][source] += 1

                except Exception as e:
                    self.logger.error(f"Failed to save file {output_path}: {e}")
                    self.checkpoint.mark_failed(article_id, f"Save error: {e}")
                    self.stats['failed'] += 1
            else:
                self.logger.warning(f"[{idx + 1}/{self.stats['total']}] No content found: {title[:60]}...")
                self.checkpoint.mark_failed(article_id, "No content from any source")
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
        total_size = sum(f.stat().st_size for f in self.output_dir.glob('*.txt'))
        self.stats['total_size_mb'] = total_size / (1024 * 1024)

        self.logger.info(f"Full-text download complete: {self.stats['success']} success, {self.stats['failed']} failed, {self.stats['skipped']} skipped")
        self.logger.info(f"Total size: {self.stats['total_size_mb']:.2f} MB")
        self.logger.info(f"By source: {self.stats['by_source']}")

        return self.stats


def main():
    """CLI entry point for news full-text downloader."""
    import argparse

    parser = argparse.ArgumentParser(description='Download full-text for news articles')
    parser.add_argument('--metadata', required=True, help='Path to news metadata JSON file')
    parser.add_argument('--output-subdir', default='articles_fulltext', help='Output subdirectory name')
    parser.add_argument('--delay-min', type=float, default=3, help='Minimum delay (seconds)')
    parser.add_argument('--delay-max', type=float, default=6, help='Maximum delay (seconds)')
    parser.add_argument('--batch-size', type=int, default=20, help='Batch size')
    parser.add_argument('--batch-pause', type=int, default=60, help='Batch pause (seconds)')

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Download full-text
    downloader = NewsFullTextDownloader(
        metadata_path=Path(args.metadata),
        output_subdir=args.output_subdir,
        delay_range=(args.delay_min, args.delay_max),
        batch_size=args.batch_size,
        batch_pause=args.batch_pause
    )

    stats = downloader.download_all()

    print("\n" + "="*60)
    print(" NEWS FULL-TEXT DOWNLOAD COMPLETE")
    print("="*60)
    print(f"Total articles: {stats['total']}")
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
