"""
Form 13F Institutional Holdings Downloader

Downloads institutional investor holdings from SEC Form 13F dataset.
Provides Layer 3 (Financial Reality) intelligence on institutional confidence/risk signals.

Mandatory Design Patterns Implemented:
1. Incremental Persistence - Save after each company
2. Graceful Degradation - Continue on single CUSIP failure
3. Checkpoint/Resume - Track completed companies
4. Standardized Output Contract - Same stats dict as other downloaders
5. Industry-Agnostic Parameters - All companies from config
6. Rate Limit Handling - N/A (local database query)

Usage:
    from src.downloaders.form13f_holdings import Form13FHoldingsDownloader

    downloader = Form13FHoldingsDownloader(
        output_dir=Path('./data/eVTOL/institutional_holdings'),
        companies={'ACHR': 'Archer Aviation Inc', 'JOBY': 'Joby Aero, Inc.'},
        start_date='2024-01-01',
        end_date='2025-06-30'
    )

    stats = downloader.download()
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
import pandas as pd

from src.utils.duckdb_manager import Form13FDatabase
from src.utils.cusip_mapper import CUSIPMapper
from src.utils.checkpoint_manager import CheckpointManager


class Form13FHoldingsDownloader:
    """
    Download institutional holdings from SEC Form 13F dataset.

    Industry-agnostic: Works with any config file (eVTOL, quantum, biotech, etc.)
    """

    def __init__(
        self,
        output_dir: Path,
        companies: Dict[str, str],  # {ticker: company_name}
        start_date: str,  # ISO format: "2024-01-01"
        end_date: str,
        duckdb_path: str = "data/form13f/13f_data.duckdb"
    ):
        """
        Initialize Form 13F Holdings downloader.

        Args:
            output_dir: Where to save holdings.json and metadata
            companies: Dict of {ticker: company_name} from config
            start_date: Start date for filtering (YYYY-MM-DD)
            end_date: End date for filtering (YYYY-MM-DD)
            duckdb_path: Path to Form 13F DuckDB database
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.companies = companies
        self.tickers = list(companies.keys())
        self.start_date = datetime.fromisoformat(start_date)
        self.end_date = datetime.fromisoformat(end_date)

        # Initialize utilities
        self.db = Form13FDatabase()
        self.db.initialize()  # Ensure database is ready

        self.cusip_mapper = CUSIPMapper()

        self.checkpoint = CheckpointManager(
            output_dir=self.output_dir,
            downloader_name="form13f_holdings"
        )

        # Logging
        self.logger = logging.getLogger(__name__)
        log_file = self.output_dir / "holdings.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)

        # Stats tracking
        self.stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total_size': 0,
            'by_company': {}
        }

        # CUSIP mappings cache
        self.ticker_to_cusip = {}

    def download(self) -> Dict[str, Any]:
        """
        Main download method with incremental saving.

        CRITICAL: Saves holdings after each company to prevent data loss.

        Returns:
            Standardized stats dict:
            {
                'success': int,
                'failed': int,
                'skipped': int,
                'total_size': float,
                'by_company': dict
            }
        """
        self.logger.info(f"Starting Form 13F Holdings download")
        self.logger.info(f"Date range: {self.start_date.date()} to {self.end_date.date()}")
        self.logger.info(f"Companies: {len(self.companies)}")

        # Step 1: Map tickers → CUSIPs
        self.logger.info("Mapping tickers to CUSIPs...")
        self.ticker_to_cusip = self.cusip_mapper.map_tickers_simple(self.tickers)

        mapped_count = len(self.ticker_to_cusip)
        self.logger.info(f"Mapped {mapped_count}/{len(self.tickers)} tickers to CUSIPs")

        if mapped_count == 0:
            self.logger.error("No CUSIP mappings found. Cannot proceed.")
            return self.stats

        # INCREMENTAL SAVING: Load existing holdings
        all_holdings = self._load_existing_holdings()
        existing_count = len(all_holdings)
        if existing_count > 0:
            self.logger.info(f"Loaded {existing_count} existing company holdings")

        # Step 2: Process each company
        for ticker, company_name in self.companies.items():
            # Skip if already completed
            if self.checkpoint.is_completed(ticker):
                self.logger.info(f"Skipping {ticker} (already completed)")
                self.stats['skipped'] += 1
                continue

            # Skip if no CUSIP mapping
            if ticker not in self.ticker_to_cusip:
                self.logger.warning(f"Skipping {ticker} (no CUSIP mapping)")
                self.stats['failed'] += 1
                self.stats['by_company'][ticker] = {'quarters': 0, 'error': 'No CUSIP mapping'}
                continue

            cusip = self.ticker_to_cusip[ticker]
            self.logger.info(f"Processing {company_name} ({ticker}) - CUSIP: {cusip}")

            try:
                # Query holdings for this company
                company_holdings = self._process_company(ticker, company_name, cusip)

                if company_holdings:
                    # Remove existing entry if present (for resume)
                    all_holdings = [h for h in all_holdings if h['ticker'] != ticker]
                    # Add new entry
                    all_holdings.append(company_holdings)

                    # INCREMENTAL SAVING: Save after each company
                    self._save_holdings_incremental(all_holdings)

                    self.stats['success'] += 1
                    self.checkpoint.mark_completed(ticker)
                    self.logger.info(f"  Completed {ticker}: {len(company_holdings['quarters'])} quarters")
                else:
                    self.stats['failed'] += 1
                    self.logger.warning(f"  No holdings found for {ticker}")

            except Exception as e:
                self.logger.error(f"Error processing {ticker}: {e}")
                self.stats['failed'] += 1
                self.stats['by_company'][ticker] = {'quarters': 0, 'error': str(e)}

        # Final save with all holdings
        if all_holdings:
            self._save_holdings(all_holdings)
            self._save_metadata(all_holdings)

        # Finalize checkpoint
        self.checkpoint.finalize()

        # Close database connection
        self.db.close()

        self._print_summary()

        return self.stats

    def _process_company(self, ticker: str, company_name: str, cusip: str) -> Optional[Dict]:
        """
        Process holdings for a single company.

        Args:
            ticker: Stock ticker symbol
            company_name: Full company name
            cusip: 9-digit CUSIP identifier

        Returns:
            Dict with company holdings data, or None if no data
        """
        # Query holdings from database
        holdings_df = self.db.query_holdings_by_cusip(
            cusips=[cusip],
            start_date=self.start_date.strftime('%Y-%m-%d'),
            end_date=self.end_date.strftime('%Y-%m-%d')
        )

        if holdings_df.empty:
            self.logger.warning(f"  No holdings found in database for {ticker} (CUSIP: {cusip})")
            return None

        self.logger.info(f"  Found {len(holdings_df)} holding records")

        # Normalize values (pre/post Jan 2023 format change)
        holdings_df['normalized_value'] = holdings_df.apply(
            lambda row: self.db.normalize_value(row['value'], row['filing_date']),
            axis=1
        )

        # Group by quarter
        quarterly_data = self._aggregate_by_quarter(holdings_df)

        if not quarterly_data:
            return None

        # Build output structure
        company_data = {
            'company': company_name,
            'ticker': ticker,
            'cusip': cusip,
            'quarters': quarterly_data,
            'strategic_signals': self._calculate_strategic_signals(quarterly_data)
        }

        # Track stats
        self.stats['by_company'][ticker] = {
            'quarters': len(quarterly_data),
            'total_institutions': quarterly_data[0]['num_institutions'] if quarterly_data else 0
        }

        return company_data

    def _aggregate_by_quarter(self, holdings_df: pd.DataFrame) -> List[Dict]:
        """
        Aggregate holdings by quarter and calculate metrics.

        Args:
            holdings_df: Holdings data from database

        Returns:
            List of quarterly holdings dicts, sorted by date (newest first)
        """
        quarters = []

        # Group by quarter
        grouped = holdings_df.groupby('quarter')

        # Sort quarters descending (newest first)
        quarter_dates = sorted(holdings_df['quarter'].unique(), reverse=True)

        previous_quarter_shares = None

        for quarter_date in quarter_dates:
            quarter_df = grouped.get_group(quarter_date)

            # Calculate metrics
            total_shares = quarter_df['shares'].sum()
            total_value = quarter_df['normalized_value'].sum()
            num_institutions = len(quarter_df)

            # Calculate QoQ change
            qoq_change_shares = None
            qoq_change_pct = None
            if previous_quarter_shares is not None and previous_quarter_shares > 0:
                qoq_change_shares = total_shares - previous_quarter_shares
                qoq_change_pct = (qoq_change_shares / previous_quarter_shares) * 100

            # Get top 10 holders
            top_holders = self._get_top_holders(quarter_df)

            # Calculate concentration (top 10 as % of total)
            top10_shares = sum(h['shares'] for h in top_holders)
            concentration_top10_pct = (top10_shares / total_shares * 100) if total_shares > 0 else 0

            quarter_data = {
                'period': quarter_date,
                'filing_deadline': self._calculate_filing_deadline(quarter_date),
                'total_shares_held': int(total_shares),
                'num_institutions': num_institutions,
                'total_value_usd': int(total_value),
                'qoq_change_shares': int(qoq_change_shares) if qoq_change_shares is not None else None,
                'qoq_change_pct': round(qoq_change_pct, 2) if qoq_change_pct is not None else None,
                'concentration_top10_pct': round(concentration_top10_pct, 2),
                'top_holders': top_holders
            }

            quarters.append(quarter_data)

            # Store for next iteration
            previous_quarter_shares = total_shares

        return quarters

    def _get_top_holders(self, quarter_df: pd.DataFrame, limit: int = 10) -> List[Dict]:
        """
        Get top N institutional holders for a quarter.

        Args:
            quarter_df: Holdings data for single quarter
            limit: Number of top holders to return

        Returns:
            List of top holder dicts
        """
        # Sort by shares descending
        top_df = quarter_df.nlargest(limit, 'shares')

        total_shares = quarter_df['shares'].sum()

        holders = []
        for rank, (_, row) in enumerate(top_df.iterrows(), start=1):
            pct_of_total = (row['shares'] / total_shares * 100) if total_shares > 0 else 0

            holder = {
                'rank': rank,
                'institution': row['institution'],
                'cik': row['cik'],
                'shares': int(row['shares']),
                'value_usd': int(row['normalized_value']),
                'pct_of_total': round(pct_of_total, 2)
            }

            holders.append(holder)

        return holders

    def _calculate_filing_deadline(self, quarter_date: str) -> str:
        """
        Calculate filing deadline (45 days after quarter end).

        Args:
            quarter_date: Quarter end date (e.g., "30-JUN-2025")

        Returns:
            Filing deadline (e.g., "2025-08-14")
        """
        try:
            # Parse quarter date
            quarter_dt = pd.to_datetime(quarter_date)
            # Add 45 days
            deadline = quarter_dt + pd.Timedelta(days=45)
            return deadline.strftime('%Y-%m-%d')
        except:
            return "Unknown"

    def _calculate_strategic_signals(self, quarterly_data: List[Dict]) -> Dict[str, str]:
        """
        Calculate strategic signals based on quarterly trends.

        Args:
            quarterly_data: List of quarterly holdings dicts

        Returns:
            Dict with strategic indicators:
            - trend: "accumulation", "distribution", "stable"
            - smart_money_signal: "bullish", "bearish", "neutral"
            - risk_level: "low", "moderate", "high"
        """
        if len(quarterly_data) < 2:
            return {
                'trend': 'insufficient_data',
                'smart_money_signal': 'neutral',
                'risk_level': 'unknown'
            }

        # Analyze last 3 quarters
        recent_quarters = quarterly_data[:min(3, len(quarterly_data))]

        # Calculate average QoQ change
        qoq_changes = [q['qoq_change_pct'] for q in recent_quarters if q['qoq_change_pct'] is not None]

        if not qoq_changes:
            return {
                'trend': 'stable',
                'smart_money_signal': 'neutral',
                'risk_level': 'moderate'
            }

        avg_qoq_change = sum(qoq_changes) / len(qoq_changes)

        # Determine trend
        if avg_qoq_change > 5:
            trend = 'accumulation'
            smart_money = 'bullish'
            risk = 'low'
        elif avg_qoq_change < -5:
            trend = 'distribution'
            smart_money = 'bearish'
            risk = 'high'
        else:
            trend = 'stable'
            smart_money = 'neutral'
            risk = 'moderate'

        return {
            'trend': trend,
            'smart_money_signal': smart_money,
            'risk_level': risk
        }

    def _load_existing_holdings(self) -> List[Dict]:
        """
        Load existing holdings from file if resuming.

        Returns:
            List of company holdings dicts
        """
        holdings_file = self.output_dir / "holdings.json"
        if holdings_file.exists():
            try:
                with open(holdings_file, 'r', encoding='utf-8') as f:
                    holdings = json.load(f)
                return holdings if isinstance(holdings, list) else []
            except Exception as e:
                self.logger.warning(f"Could not load existing holdings: {e}")
                return []
        return []

    def _save_holdings_incremental(self, holdings: List[Dict]):
        """
        Save holdings incrementally (after each company).

        CRITICAL: This prevents data loss if harvest is interrupted.

        Args:
            holdings: List of company holdings dicts
        """
        holdings_file = self.output_dir / "holdings.json"
        try:
            with open(holdings_file, 'w', encoding='utf-8') as f:
                json.dump(holdings, f, indent=2, ensure_ascii=False)
            self.logger.debug(f"  Incremental save: {len(holdings)} companies")
        except Exception as e:
            self.logger.error(f"  Incremental save failed: {e}")

    def _save_holdings(self, holdings: List[Dict]):
        """
        Save final holdings to JSON file.

        Args:
            holdings: List of company holdings dicts
        """
        holdings_file = self.output_dir / "holdings.json"
        with open(holdings_file, 'w', encoding='utf-8') as f:
            json.dump(holdings, f, indent=2, ensure_ascii=False)

        file_size = holdings_file.stat().st_size / (1024 * 1024)  # MB
        self.stats['total_size'] = file_size

        self.logger.info(f"Saved {len(holdings)} companies to {holdings_file} ({file_size:.2f} MB)")

    def _save_metadata(self, holdings: List[Dict]):
        """
        Save standardized metadata.

        Args:
            holdings: List of company holdings dicts
        """
        # Calculate aggregate stats
        total_quarters = sum(len(h['quarters']) for h in holdings)

        metadata = {
            'source': 'SEC Form 13F',
            'timestamp': datetime.now().isoformat(),
            'date_range': f"{self.start_date.date()} to {self.end_date.date()}",
            'companies_analyzed': len(holdings),
            'total_quarters': total_quarters,
            'cusip_mapping_success': len(self.ticker_to_cusip),
            'cusip_mapping_failed': len(self.companies) - len(self.ticker_to_cusip),
            'stats': self.stats
        }

        metadata_file = self.output_dir / "holdings_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Saved metadata to {metadata_file}")

    def _print_summary(self):
        """Print download summary."""
        self.logger.info("=" * 60)
        self.logger.info("Form 13F Holdings Download Summary")
        self.logger.info("=" * 60)
        self.logger.info(f"Successful: {self.stats['success']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        self.logger.info(f"Skipped: {self.stats['skipped']}")
        self.logger.info(f"Total size: {self.stats['total_size']:.2f} MB")

        if self.stats['by_company']:
            self.logger.info("\nBy Company:")
            for ticker, company_stats in sorted(self.stats['by_company'].items()):
                quarters = company_stats.get('quarters', 0)
                error = company_stats.get('error', '')
                if error:
                    self.logger.info(f"  {ticker:6s}: ERROR - {error}")
                else:
                    institutions = company_stats.get('total_institutions', 0)
                    self.logger.info(f"  {ticker:6s}: {quarters} quarters, {institutions} institutions")

        self.logger.info("=" * 60)


if __name__ == "__main__":
    # Test with single company
    logging.basicConfig(level=logging.INFO)

    print("Testing Form 13F Holdings Downloader...")
    print("=" * 60)

    # Test companies
    test_companies = {
        'ACHR': 'Archer Aviation Inc'
    }

    downloader = Form13FHoldingsDownloader(
        output_dir=Path('./data/form13f_test'),
        companies=test_companies,
        start_date='2024-01-01',
        end_date='2025-06-30'
    )

    stats = downloader.download()

    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    print(f"Success: {stats['success']}")
    print(f"Failed: {stats['failed']}")
    print(f"Total size: {stats['total_size']:.2f} MB")
