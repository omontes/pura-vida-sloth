"""
SEC EDGAR Downloader
====================
Downloads SEC filings (8-K, 10-Q, 10-K, etc.) from EDGAR database

Target: 400-500 documents in 30 days
- 8-K: ~300 docs (most frequent, filed within 4 days of events)
- 10-Q: ~100 docs (quarterly reports)
- 10-K: ~20 docs (annual reports)
- Other: ~50 docs (S-1, proxy statements, etc.)
"""

import requests
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from src.utils.logger import setup_logger
from src.utils.rate_limiter import RateLimiter
from src.utils.config import Config
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.retry_handler import retry_on_error

import logging


class SECDownloader:
    """Download SEC EDGAR filings"""
    
    # SEC EDGAR API endpoints
    BASE_URL = "https://www.sec.gov"
    SUBMISSIONS_URL = f"{BASE_URL}/cgi-bin/browse-edgar"
    
    # Top financial companies to track
    TARGET_COMPANIES = {
        # Major Banks
        'JPM': 'JPMorgan Chase & Co.',
        'BAC': 'Bank of America Corp',
        'WFC': 'Wells Fargo & Company',
        'C': 'Citigroup Inc.',
        'GS': 'Goldman Sachs Group Inc.',
        'MS': 'Morgan Stanley',
        'USB': 'U.S. Bancorp',
        'PNC': 'PNC Financial Services',
        'TFC': 'Truist Financial Corp',
        'COF': 'Capital One Financial',
        
        # Payment & FinTech
        'V': 'Visa Inc.',
        'MA': 'Mastercard Inc.',
        'PYPL': 'PayPal Holdings Inc.',
        'SQ': 'Block Inc. (Square)',
        'FIS': 'Fidelity National Info Services',
        'FISV': 'Fiserv Inc.',
        'AXP': 'American Express',
        
        # Investment & Trading
        'SCHW': 'Charles Schwab Corp',
        'BLK': 'BlackRock Inc.',
        'TROW': 'T. Rowe Price Group',
        'BK': 'Bank of New York Mellon',
        'STT': 'State Street Corp',
        
        # Insurance & Financial Services
        'BRK.B': 'Berkshire Hathaway',
        'AIG': 'American International Group',
        'MET': 'MetLife Inc.',
        'PRU': 'Prudential Financial',
        'ALL': 'Allstate Corp',
        
        # Crypto & Emerging FinTech
        'COIN': 'Coinbase Global Inc.',
        'HOOD': 'Robinhood Markets Inc.',
        'SOFI': 'SoFi Technologies Inc.',
        'AFRM': 'Affirm Holdings Inc.',
        'UPST': 'Upstart Holdings Inc.',
        
        # Additional FinTech
        'INTU': 'Intuit Inc.',
        'ADYEN': 'Adyen N.V.',
    }
    
    # Filing types to download
    FILING_TYPES = ['8-K', '10-Q', '10-K', 'S-1', 'DEF 14A', 'D', '4']  # Added Form D for funding, Form 4 for insider transactions
    
    def __init__(self, output_dir: Path, start_date: datetime, end_date: datetime,
                 tickers: Optional[Dict[str, str]] = None):
        """
        Initialize SEC downloader

        Args:
            output_dir: Directory to save filings
            start_date: Start date for filings
            end_date: End date for filings
            tickers: Dict of ticker symbols to company names (e.g. {'JOBY': 'Joby Aviation'})
                    If None, uses Config.TARGET_COMPANIES for backward compatibility
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.start_date = start_date
        self.end_date = end_date

        # Use provided tickers or fall back to hardcoded list (backward compatibility)
        self.companies = tickers if tickers is not None else self.TARGET_COMPANIES

        self.logger = setup_logger("SECDownloader", self.output_dir / "sec.log")
        self.rate_limiter = RateLimiter(requests_per_second=Config.RATE_LIMITS['sec'])
        self.checkpoint = CheckpointManager(self.output_dir, 'sec')

        self.session = requests.Session()
        # SEC requires User-Agent header
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
    
    def download(self) -> Dict:
        """Main download method"""
        self.logger.info(f"Starting SEC EDGAR download")
        self.logger.info(f"Date range: {self.start_date.date()} to {self.end_date.date()}")
        self.logger.info(f"Target companies: {len(self.companies)}")
        self.logger.info(f"Filing types: {self.FILING_TYPES}")

        # Get all filings metadata
        all_filings = []

        self.logger.info("Fetching filings metadata...")
        for ticker, company_name in tqdm(self.companies.items(),
                                         desc="Companies"):
            try:
                filings = self._get_company_filings(ticker, company_name)
                all_filings.extend(filings)
                time.sleep(0.1)  # Rate limiting
            except Exception as e:
                self.logger.error(f"Error fetching {ticker}: {e}")
        
        self.logger.info(f"Found {len(all_filings)} filings to download")
        
        # Download filings in parallel
        self.logger.info("Downloading filings...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self._download_filing, filing): filing 
                for filing in all_filings
            }
            
            for future in tqdm(as_completed(futures), 
                             total=len(futures),
                             desc="Downloading"):
                filing = futures[future]
                try:
                    future.result()
                except Exception as e:
                    self.logger.error(f"Error downloading {filing['accession']}: {e}")
                    self.stats['failed'] += 1
        
        # Finalize checkpoint
        self.checkpoint.finalize()

        # Save metadata
        metadata_path = self.output_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump({
                'download_date': datetime.now().isoformat(),
                'date_range': {
                    'start': self.start_date.isoformat(),
                    'end': self.end_date.isoformat()
                },
                'companies': self.TARGET_COMPANIES,
                'filings': all_filings,
                'stats': self.stats
            }, f, indent=2)

        self.logger.info(f"Metadata saved to {metadata_path}")

        # Print summary
        self._print_summary()

        return self.stats
    
    @retry_on_error(max_retries=3)
    def _get_company_filings(self, ticker: str, company_name: str) -> List[Dict]:
        """Get recent filings for a company using SEC EDGAR API"""
        filings = []

        # Check if already completed
        item_id = f"company_{ticker}"
        if self.checkpoint.is_completed(item_id):
            return []

        # Use SEC's newer JSON API
        # First get CIK from ticker
        cik = self._get_cik_from_ticker(ticker)
        if not cik:
            self.logger.warning(f"Could not find CIK for {ticker}")
            self.checkpoint.mark_failed(item_id, "Could not find CIK")
            return []
        
        # Get company submissions
        submissions_url = f"{self.BASE_URL}/cgi-bin/browse-edgar"

        self.logger.debug(f"  Fetching filings for {ticker} (CIK: {cik})")
        self.logger.debug(f"  Date range: {self.start_date.date()} to {self.end_date.date()}")

        for filing_type in self.FILING_TYPES:
            try:
                params = {
                    'action': 'getcompany',
                    'CIK': cik,
                    'type': filing_type,
                    'dateb': self.end_date.strftime('%Y%m%d'),
                    'datea': self.start_date.strftime('%Y%m%d'),
                    'owner': 'exclude',
                    'output': 'atom',
                    'count': 100
                }

                self.rate_limiter.wait()
                response = self.session.get(submissions_url, params=params)
                response.raise_for_status()

                # Parse ATOM feed
                from xml.etree import ElementTree as ET
                root = ET.fromstring(response.content)

                # Extract entries
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                entries = root.findall('.//atom:entry', ns)

                self.logger.debug(f"    Form {filing_type}: Found {len(entries)} entries in ATOM feed")

                entries_in_range = 0
                for entry in entries:
                    filing_date_str = entry.find('.//atom:filing-date', ns).text
                    filing_date = datetime.strptime(filing_date_str, '%Y-%m-%d')

                    if self.start_date <= filing_date <= self.end_date:
                        accession = entry.find('.//atom:accession-number', ns).text
                        filing_url = entry.find('.//atom:filing-href', ns).text

                        filings.append({
                            'ticker': ticker,
                            'company_name': company_name,
                            'cik': cik,
                            'filing_type': filing_type,
                            'filing_date': filing_date.isoformat(),
                            'accession': accession.replace('-', ''),
                            'url': filing_url
                        })
                        entries_in_range += 1

                if entries_in_range > 0:
                    self.logger.debug(f"    Form {filing_type}: {entries_in_range} filings in date range")

                time.sleep(0.15)  # Rate limiting

            except Exception as e:
                self.logger.error(f"  ERROR - Form {filing_type} for {ticker}: {e}", exc_info=True)

        # Mark company as completed
        self.checkpoint.mark_completed(item_id, {'count': len(filings)})

        return filings
    
    def _get_cik_from_ticker(self, ticker: str) -> Optional[str]:
        """Get CIK number from ticker symbol using SEC's official ticker mapping"""
        try:
            # Use SEC's official company_tickers.json mapping (more reliable than search)
            # This file is updated nightly by the SEC
            url = f"{self.BASE_URL}/files/company_tickers.json"

            self.rate_limiter.wait()
            response = self.session.get(url)
            response.raise_for_status()

            ticker_data = response.json()

            # Search for matching ticker (case-insensitive)
            ticker_upper = ticker.upper().strip()

            for item in ticker_data.values():
                if item.get('ticker', '').upper() == ticker_upper:
                    cik = str(item['cik_str']).zfill(10)  # Pad with zeros to 10 digits
                    self.logger.debug(f"  Found CIK {cik} for ticker {ticker}")
                    return cik

            # Fallback: Try company name search (less reliable)
            self.logger.warning(f"  Ticker {ticker} not found in company_tickers.json, trying name search...")

            search_url = f"{self.BASE_URL}/cgi-bin/browse-edgar"
            params = {
                'action': 'getcompany',
                'company': ticker,
                'output': 'atom',
                'count': 1
            }

            self.rate_limiter.wait()
            response = self.session.get(search_url, params=params)
            response.raise_for_status()

            from xml.etree import ElementTree as ET
            root = ET.fromstring(response.content)

            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            cik_element = root.find('.//atom:cik', ns)

            if cik_element is not None:
                cik = cik_element.text.zfill(10)  # Pad with zeros
                self.logger.debug(f"  Found CIK {cik} for {ticker} via name search")
                return cik

        except Exception as e:
            self.logger.error(f"Error getting CIK for {ticker}: {e}")

        return None
    
    @retry_on_error(max_retries=3)
    def _download_filing(self, filing: Dict):
        """Download a single filing"""
        try:
            # Create filename (replace colons for Windows compatibility)
            safe_date = filing['filing_date'].replace(':', '-')
            filename = (f"{filing['ticker']}_{filing['filing_type']}_"
                       f"{safe_date}_{filing['accession']}.html")
            filepath = self.output_dir / filename

            # Skip if already exists
            if filepath.exists():
                self.stats['skipped'] += 1
                return

            # Download
            self.rate_limiter.wait()
            response = self.session.get(filing['url'], timeout=30)
            response.raise_for_status()

            # Save
            filepath.write_bytes(response.content)

            self.stats['success'] += 1
            self.stats['total_size'] += len(response.content)

            self.logger.debug(f"Downloaded: {filename}")

        except Exception as e:
            self.logger.error(f"Failed to download {filing['accession']}: {e}")
            self.stats['failed'] += 1
            raise

    def _print_summary(self):
        """Print download summary"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("SEC EDGAR DOWNLOAD SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Success: {self.stats['success']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        self.logger.info(f"Skipped: {self.stats['skipped']}")
        self.logger.info(f"Total Size: {self.stats['total_size'] / 1024 / 1024:.2f} MB")
        self.logger.info("=" * 60)
