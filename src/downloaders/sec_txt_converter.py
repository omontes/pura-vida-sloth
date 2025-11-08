"""
SEC Filing TXT Converter
========================
Converts HTML SEC filings to raw text (.txt) format organized by form type.

Reads existing HTML filings from harvest and downloads corresponding .txt versions
from SEC EDGAR, organizing them into folders by form type (8-K, 10-K, etc.)
"""

import requests
import time
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from tqdm import tqdm

from src.utils.logger import setup_logger
from src.utils.rate_limiter import RateLimiter
from src.utils.config import Config
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.retry_handler import retry_on_error


class SECTxtConverter:
    """Convert HTML SEC filings to raw text format"""

    BASE_URL = "https://www.sec.gov"

    def __init__(self, html_dir: Path, output_dir: Path):
        """
        Initialize SEC TXT converter

        Args:
            html_dir: Directory containing HTML filings and metadata.json
            output_dir: Base directory for organized .txt files (e.g., data/eVTOL/sec_filings/txt)
        """
        self.html_dir = Path(html_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load metadata for CIK mappings
        metadata_path = self.html_dir / "metadata.json"
        if not metadata_path.exists():
            raise FileNotFoundError(f"metadata.json not found in {self.html_dir}")

        with open(metadata_path, 'r') as f:
            metadata = json.load(f)

        # Build ticker -> CIK mapping from filings metadata
        self.ticker_to_cik = {}
        for filing in metadata.get('filings', []):
            ticker = filing.get('ticker')
            cik = filing.get('cik')
            if ticker and cik:
                self.ticker_to_cik[ticker] = cik

        self.logger = setup_logger("SECTxtConverter", self.output_dir / "sec_txt_converter.log")
        self.logger.info(f"Loaded CIK mappings for {len(self.ticker_to_cik)} tickers")

        self.rate_limiter = RateLimiter(requests_per_second=9)  # SEC limit is 10, use 9 to be safe
        self.checkpoint = CheckpointManager(self.output_dir, 'sec_txt_converter')

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': Config.SEC_USER_AGENT,
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.sec.gov'
        })

        self.stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total_size': 0
        }

        # Check for resume
        resume_info = self.checkpoint.get_resume_info()
        if resume_info:
            self.logger.info(resume_info)

    def convert_all(self) -> Dict:
        """Convert all HTML filings to TXT format"""
        self.logger.info(f"Starting SEC TXT conversion")
        self.logger.info(f"HTML directory: {self.html_dir}")
        self.logger.info(f"Output directory: {self.output_dir}")

        # Find all HTML files
        html_files = list(self.html_dir.glob("*.html"))
        self.logger.info(f"Found {len(html_files)} HTML files to convert")

        if not html_files:
            self.logger.warning("No HTML files found. Exiting.")
            return self.stats

        # Convert each file
        for html_file in tqdm(html_files, desc="Converting to TXT"):
            try:
                self._convert_file(html_file)
            except Exception as e:
                self.logger.error(f"Error converting {html_file.name}: {e}")
                self.stats['failed'] += 1

        # Finalize checkpoint
        self.checkpoint.finalize()

        # Print summary
        self._print_summary()

        return self.stats

    def _convert_file(self, html_file: Path):
        """Convert a single HTML file to TXT"""
        # Parse filename
        filing_info = self._parse_filename(html_file.name)
        if not filing_info:
            self.logger.warning(f"Could not parse filename: {html_file.name}")
            self.stats['failed'] += 1
            return

        # Check if already completed
        item_id = filing_info['item_id']
        if self.checkpoint.is_completed(item_id):
            self.stats['skipped'] += 1
            return

        # Get CIK
        ticker = filing_info['ticker']
        cik = self.ticker_to_cik.get(ticker)
        if not cik:
            self.logger.error(f"CIK not found for ticker {ticker}")
            self.checkpoint.mark_failed(item_id, f"CIK not found for {ticker}")
            self.stats['failed'] += 1
            return

        # Create form type directory
        form_dir = self.output_dir / filing_info['form_type']
        form_dir.mkdir(parents=True, exist_ok=True)

        # Build output filename
        txt_filename = filing_info['base_name'] + '.txt'
        txt_filepath = form_dir / txt_filename

        # Skip if already exists
        if txt_filepath.exists():
            self.checkpoint.mark_completed(item_id)
            self.stats['skipped'] += 1
            return

        # Download TXT version
        try:
            self._download_txt_filing(cik, filing_info['accession'], txt_filepath)
            self.checkpoint.mark_completed(item_id)
            self.stats['success'] += 1
        except Exception as e:
            self.logger.error(f"Failed to download {txt_filename}: {e}")
            self.checkpoint.mark_failed(item_id, str(e))
            self.stats['failed'] += 1

    def _parse_filename(self, filename: str) -> Optional[Dict]:
        """
        Parse SEC filing filename to extract metadata

        Expected format: {TICKER}_{FORM_TYPE}_{FILING_DATE}_{ACCESSION}.html
        Example: JOBY_8-K_2025-11-05T00-00-00_000181984825000594.html

        Returns:
            Dict with: ticker, form_type, filing_date, accession, base_name, item_id
        """
        try:
            # Remove .html extension
            if not filename.endswith('.html'):
                return None

            base_name = filename[:-5]  # Remove .html

            # Split by underscore
            parts = base_name.split('_')

            if len(parts) < 4:
                return None

            ticker = parts[0]
            form_type = parts[1]
            filing_date = parts[2]
            accession = '_'.join(parts[3:])  # In case accession has underscores

            return {
                'ticker': ticker,
                'form_type': form_type,
                'filing_date': filing_date,
                'accession': accession,
                'base_name': base_name,
                'item_id': base_name  # Use base_name as unique item ID
            }
        except Exception as e:
            self.logger.error(f"Error parsing filename {filename}: {e}")
            return None

    def _format_accession_with_dashes(self, accession: str) -> str:
        """
        Format accession number with dashes for SEC URLs

        Input: "000181984825000597" (18 digits)
        Output: "0001819848-25-000597"

        SEC accession format: {10-digit CIK}-{2-digit year}-{6-digit sequence}
        """
        if len(accession) == 18:
            return f"{accession[:10]}-{accession[10:12]}-{accession[12:]}"
        else:
            # Fallback for non-standard formats
            return accession

    @retry_on_error(max_retries=3)
    def _download_txt_filing(self, cik: str, accession: str, output_path: Path):
        """
        Download raw text version of SEC filing

        Args:
            cik: Company CIK (e.g., "0001819848")
            accession: Filing accession number without dashes (e.g., "000181984825000594")
            output_path: Where to save the .txt file
        """
        # Remove leading zeros from CIK for URL
        cik_for_url = cik.lstrip('0')

        # Format accession with dashes
        accession_with_dashes = self._format_accession_with_dashes(accession)

        # Construct TXT URL
        # Format: /Archives/edgar/data/{CIK}/{ACCESSION}/{ACCESSION-WITH-DASHES}.txt
        txt_url = f"{self.BASE_URL}/Archives/edgar/data/{cik_for_url}/{accession}/{accession_with_dashes}.txt"

        # Download with rate limiting
        self.rate_limiter.wait()
        response = self.session.get(txt_url, timeout=30)
        response.raise_for_status()

        # Save to file
        output_path.write_bytes(response.content)

        self.stats['total_size'] += len(response.content)

        self.logger.debug(f"Downloaded: {output_path.name} ({len(response.content)} bytes)")

    def _print_summary(self):
        """Print conversion summary"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("SEC TXT CONVERSION SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Success: {self.stats['success']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        self.logger.info(f"Skipped: {self.stats['skipped']}")
        self.logger.info(f"Total Size: {self.stats['total_size'] / 1024 / 1024:.2f} MB")
        self.logger.info("=" * 60)

        # Print form type breakdown
        self.logger.info("\nFiles by form type:")
        for form_dir in sorted(self.output_dir.iterdir()):
            if form_dir.is_dir():
                file_count = len(list(form_dir.glob("*.txt")))
                self.logger.info(f"  {form_dir.name}: {file_count} files")


def main():
    """Main entry point for standalone execution"""
    import argparse

    parser = argparse.ArgumentParser(description="Convert SEC HTML filings to TXT format")
    parser.add_argument("--html-dir", type=str, default="data/eVTOL/sec_filings",
                       help="Directory containing HTML filings and metadata.json")
    parser.add_argument("--output-dir", type=str, default="data/eVTOL/sec_filings/txt",
                       help="Output directory for organized TXT files")
    parser.add_argument("--test", action="store_true",
                       help="Test mode: only convert first 5 files")

    args = parser.parse_args()

    html_dir = Path(args.html_dir)
    output_dir = Path(args.output_dir)

    converter = SECTxtConverter(html_dir, output_dir)

    if args.test:
        print("=== TEST MODE: Converting first 5 files ===")
        # Limit to 5 files for testing
        html_files = list(html_dir.glob("*.html"))[:5]
        for html_file in html_files:
            converter._convert_file(html_file)
        converter._print_summary()
    else:
        converter.convert_all()


if __name__ == "__main__":
    main()
