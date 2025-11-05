"""
PDF Downloader Utility - Industry-Agnostic Design

Downloads PDF files from URLs in metadata JSON files and updates metadata
with local file paths. Supports checkpointing for resume capability.

Usage:
    python -m src.utils.pdf_downloader --metadata data/eVTOL/patents/patents_metadata.json
"""

import json
import requests
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from urllib.parse import urlparse
import hashlib

from src.utils.checkpoint_manager import CheckpointManager
from src.utils.retry_handler import retry_on_error


class PDFDownloader:
    """
    Download PDF files from metadata URLs.

    CRITICAL: Industry-agnostic design - works with any metadata JSON file.
    """

    def __init__(
        self,
        metadata_path: Path,
        output_subdir: str = "pdfs",
        url_field: str = "url",
        pdf_url_field: Optional[str] = None,
        title_field: str = "title",
        max_retries: int = 3,
        delay_seconds: float = 1.0
    ):
        """
        Initialize PDF downloader.

        Args:
            metadata_path: Path to metadata JSON file
            output_subdir: Subdirectory name for PDFs (default: "pdfs")
            url_field: Field name containing URL (default: "url")
            pdf_url_field: Field name for direct PDF URL (optional)
            title_field: Field name for document title (default: "title")
            max_retries: Max retry attempts per download
            delay_seconds: Delay between downloads (rate limiting)
        """
        self.metadata_path = Path(metadata_path)
        self.output_dir = self.metadata_path.parent / output_subdir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.url_field = url_field
        self.pdf_url_field = pdf_url_field
        self.title_field = title_field
        self.max_retries = max_retries
        self.delay_seconds = delay_seconds

        # Load metadata
        with open(self.metadata_path, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)

        # Checkpoint for resume capability
        checkpoint_name = f"pdf_download_{self.metadata_path.stem}"
        self.checkpoint = CheckpointManager(self.output_dir, checkpoint_name)

        # Logger
        self.logger = logging.getLogger("PDFDownloader")
        handler = logging.FileHandler(self.output_dir / "pdf_download.log")
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        # User-Agent to avoid bot detection
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def _sanitize_filename(self, text: str, max_length: int = 100) -> str:
        """
        Sanitize text for use as filename.

        Args:
            text: Input text
            max_length: Maximum filename length

        Returns:
            Sanitized filename
        """
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            text = text.replace(char, '_')

        # Truncate and clean
        text = text[:max_length].strip()
        text = '_'.join(text.split())  # Replace whitespace with underscores

        return text

    def _generate_pdf_url(self, item: Dict[str, Any]) -> Optional[str]:
        """
        Generate PDF URL from item metadata.

        Tries multiple strategies:
        1. Direct PDF URL field (if specified)
        2. Google Patents PDF URL construction
        3. Original URL with .pdf extension

        Args:
            item: Metadata item

        Returns:
            PDF URL or None
        """
        # Strategy 1: Direct PDF URL field
        if self.pdf_url_field and self.pdf_url_field in item:
            pdf_url = item[self.pdf_url_field]
            if pdf_url:
                return pdf_url

        # Strategy 2: Google Patents PDF URL
        url = item.get(self.url_field, '')
        if 'patents.google.com/patent/' in url:
            # Extract patent number (e.g., US20250166517A1)
            parts = url.rstrip('/').split('/')
            if len(parts) >= 2:
                patent_num = parts[-2] if parts[-1] in ['en', 'fr', 'de'] else parts[-1]
                # Google Patents PDF URL format
                pdf_url = f"https://patentimages.storage.googleapis.com/{patent_num}/{patent_num}.pdf"
                return pdf_url

        # Strategy 3: Try adding .pdf extension
        if url.endswith('.html') or url.endswith('.htm'):
            return url.replace('.html', '.pdf').replace('.htm', '.pdf')

        # Strategy 4: Direct URL if it's already a PDF
        if url.endswith('.pdf'):
            return url

        return None

    @retry_on_error(max_retries=3, backoff_factor=2)
    def _download_pdf(self, url: str, output_path: Path) -> bool:
        """
        Download PDF from URL.

        Args:
            url: PDF URL
            output_path: Local output path

        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=30, stream=True)
            response.raise_for_status()

            # Check if content is actually PDF
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
            if file_size < 1024:  # Less than 1KB probably not a valid PDF
                self.logger.warning(f"Downloaded file too small ({file_size} bytes): {output_path}")
                output_path.unlink()  # Delete invalid file
                return False

            self.logger.info(f"Downloaded PDF ({file_size / 1024:.1f} KB): {output_path.name}")
            return True

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to download {url}: {e}")
            return False

    def download_all(self) -> Dict[str, Any]:
        """
        Download all PDFs from metadata.

        Returns:
            Statistics dict with success/failed counts
        """
        success_count = 0
        failed_count = 0
        skipped_count = 0

        total_items = len(self.metadata)
        self.logger.info(f"Starting PDF download for {total_items} items")

        for idx, item in enumerate(self.metadata):
            # Generate unique ID for checkpoint
            item_id = item.get('patent_number') or item.get('id') or hashlib.md5(
                item.get(self.url_field, '').encode()
            ).hexdigest()[:16]

            # Check if already processed
            if self.checkpoint.is_completed(item_id):
                skipped_count += 1
                if item.get('file_path'):  # Already has file_path
                    continue

            # Generate PDF URL
            pdf_url = self._generate_pdf_url(item)
            if not pdf_url:
                self.logger.warning(f"Cannot generate PDF URL for: {item.get(self.title_field, 'Unknown')}")
                self.checkpoint.mark_failed(item_id, "No PDF URL available")
                failed_count += 1
                continue

            # Generate output filename
            title = item.get(self.title_field, f"document_{idx}")
            safe_filename = self._sanitize_filename(title)

            # Add patent number if available for uniqueness
            if 'patent_number' in item:
                patent_num = item['patent_number'].split('/')[-1].replace('en', '').replace('fr', '').replace('de', '')
                safe_filename = f"{patent_num}_{safe_filename}"

            output_path = self.output_dir / f"{safe_filename}.pdf"

            # Skip if file already exists
            if output_path.exists():
                self.logger.info(f"Skipping existing file: {output_path.name}")
                item['file_path'] = str(output_path)
                self.checkpoint.mark_completed(item_id, metadata={'file_path': str(output_path)})
                skipped_count += 1
                continue

            # Download PDF
            self.logger.info(f"[{idx + 1}/{total_items}] Downloading: {item.get(self.title_field, 'Unknown')}")
            success = self._download_pdf(pdf_url, output_path)

            if success:
                # Update metadata with file path
                item['file_path'] = str(output_path)
                self.checkpoint.mark_completed(item_id, metadata={'file_path': str(output_path)})
                success_count += 1
            else:
                self.checkpoint.mark_failed(item_id, f"Failed to download from {pdf_url}")
                failed_count += 1

            # Rate limiting
            time.sleep(self.delay_seconds)

        # Save updated metadata
        self._save_updated_metadata()

        # Finalize checkpoint
        self.checkpoint.finalize()

        stats = {
            'success': success_count,
            'failed': failed_count,
            'skipped': skipped_count,
            'total': total_items,
            'total_size_mb': self._calculate_total_size()
        }

        self.logger.info(f"PDF download complete: {success_count} success, {failed_count} failed, {skipped_count} skipped")
        return stats

    def _save_updated_metadata(self):
        """Save updated metadata with file_path fields."""
        backup_path = self.metadata_path.with_suffix('.backup.json')

        # Create backup of original
        if not backup_path.exists():
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                original = f.read()
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original)
            self.logger.info(f"Created metadata backup: {backup_path}")

        # Save updated metadata
        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Updated metadata saved: {self.metadata_path}")

    def _calculate_total_size(self) -> float:
        """Calculate total size of downloaded PDFs in MB."""
        total_bytes = sum(
            f.stat().st_size for f in self.output_dir.glob('*.pdf')
        )
        return total_bytes / (1024 * 1024)


def main():
    """CLI entry point for PDF downloader."""
    import argparse

    parser = argparse.ArgumentParser(description='Download PDFs from metadata JSON')
    parser.add_argument('--metadata', required=True, help='Path to metadata JSON file')
    parser.add_argument('--output-subdir', default='pdfs', help='Output subdirectory name')
    parser.add_argument('--url-field', default='url', help='URL field name in metadata')
    parser.add_argument('--pdf-url-field', default=None, help='Direct PDF URL field name (optional)')
    parser.add_argument('--title-field', default='title', help='Title field name in metadata')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between downloads (seconds)')

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Download PDFs
    downloader = PDFDownloader(
        metadata_path=Path(args.metadata),
        output_subdir=args.output_subdir,
        url_field=args.url_field,
        pdf_url_field=args.pdf_url_field,
        title_field=args.title_field,
        delay_seconds=args.delay
    )

    stats = downloader.download_all()

    print("\n" + "="*60)
    print(" PDF DOWNLOAD COMPLETE")
    print("="*60)
    print(f"Total items:    {stats['total']}")
    print(f"Success:        {stats['success']}")
    print(f"Failed:         {stats['failed']}")
    print(f"Skipped:        {stats['skipped']}")
    print(f"Total size:     {stats['total_size_mb']:.2f} MB")
    print("="*60)


if __name__ == '__main__':
    main()
