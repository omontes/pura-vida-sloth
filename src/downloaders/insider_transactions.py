"""
Insider Transactions (Forms 3/4/5) Downloader

Downloads insider transactions from SEC Forms 3/4/5 dataset.
Provides Layer 3 (Financial Reality) intelligence on executive confidence signals.

Mandatory Design Patterns Implemented:
1. Incremental Persistence - Save after each company
2. Graceful Degradation - Continue on single company failure
3. Checkpoint/Resume - Track completed companies
4. Standardized Output Contract - Same stats dict as other downloaders
5. Industry-Agnostic Parameters - All companies from config
6. Rate Limit Handling - N/A (local database query)

Usage:
    from src.downloaders.insider_transactions import InsiderTransactionsDownloader

    downloader = InsiderTransactionsDownloader(
        output_dir=Path('./data/eVTOL/insider_transactions'),
        companies={'ACHR': 'Archer Aviation Inc', 'JOBY': 'Joby Aero, Inc.'},
        start_date='2024-01-01',
        end_date='2025-11-05'
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

from src.utils.duckdb_insider_transactions import InsiderTransactionsDatabase
from src.utils.checkpoint_manager import CheckpointManager


class InsiderTransactionsDownloader:
    """
    Download insider transactions from SEC Forms 3/4/5 dataset.

    Industry-agnostic: Works with any config file (eVTOL, quantum, biotech, etc.)
    """

    def __init__(
        self,
        output_dir: Path,
        companies: Dict[str, str],  # {ticker: company_name}
        start_date: str,  # ISO format: "2024-01-01"
        end_date: str,
        duckdb_path: str = "data/insider_transactions/insider_transactions.duckdb"
    ):
        """
        Initialize Insider Transactions downloader.

        Args:
            output_dir: Where to save transactions.json and metadata
            companies: Dict of {ticker: company_name} from config
            start_date: Start date for filtering (YYYY-MM-DD)
            end_date: End date for filtering (YYYY-MM-DD)
            duckdb_path: Path to insider transactions DuckDB database
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.companies = companies
        self.tickers = list(companies.keys())
        self.start_date = datetime.fromisoformat(start_date)
        self.end_date = datetime.fromisoformat(end_date)

        # Initialize utilities
        self.db = InsiderTransactionsDatabase()
        self.db.initialize()  # Ensure database is ready

        self.checkpoint = CheckpointManager(
            output_dir=self.output_dir,
            downloader_name="insider_transactions"
        )

        # Logging
        self.logger = logging.getLogger(__name__)
        log_file = self.output_dir / "transactions.log"
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

    def download(self) -> Dict[str, Any]:
        """
        Main download method with incremental saving.

        CRITICAL: Saves transactions after each company to prevent data loss.

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
        self.logger.info(f"Starting Insider Transactions download")
        self.logger.info(f"Date range: {self.start_date.date()} to {self.end_date.date()}")
        self.logger.info(f"Companies: {len(self.companies)}")

        # INCREMENTAL SAVING: Load existing transactions
        all_transactions = self._load_existing_transactions()
        existing_count = len(all_transactions)
        if existing_count > 0:
            self.logger.info(f"Loaded {existing_count} existing company transactions")

        # Process each company
        for ticker, company_name in self.companies.items():
            # Skip if already completed
            if self.checkpoint.is_completed(ticker):
                self.logger.info(f"Skipping {ticker} (already completed)")
                self.stats['skipped'] += 1
                continue

            self.logger.info(f"Processing {company_name} ({ticker})")

            try:
                # Query transactions for this company
                company_transactions = self._process_company(ticker, company_name)

                if company_transactions:
                    # Remove existing entry if present (for resume)
                    all_transactions = [t for t in all_transactions if t['ticker'] != ticker]
                    # Add new entry
                    all_transactions.append(company_transactions)

                    # INCREMENTAL SAVING: Save after each company
                    self._save_transactions_incremental(all_transactions)

                    trans_count = len(company_transactions.get('transactions', []))
                    self.stats['success'] += 1
                    self.stats['by_company'][ticker] = trans_count
                    self.checkpoint.mark_completed(ticker)
                    self.logger.info(f"  Completed {ticker}: {trans_count} transactions")
                else:
                    self.stats['failed'] += 1
                    self.stats['by_company'][ticker] = 0
                    self.logger.warning(f"  No transactions found for {ticker}")

            except Exception as e:
                self.logger.error(f"Error processing {ticker}: {e}", exc_info=True)
                self.stats['failed'] += 1
                self.stats['by_company'][ticker] = 0

        # Final save with all transactions
        if all_transactions:
            self._save_transactions(all_transactions)
            self._save_metadata(all_transactions)

        # Finalize checkpoint
        self.checkpoint.finalize()

        # Close database connection
        self.db.close()

        self._print_summary()

        return self.stats

    def _process_company(self, ticker: str, company_name: str) -> Optional[Dict]:
        """
        Process insider transactions for a single company.

        Returns dict with company info, monthly aggregated transactions, and individual transaction details.
        """
        # Query database by ticker for P and S transactions only
        transactions_df = self.db.query_transactions_by_ticker(
            tickers=[ticker],
            start_date=self.start_date.strftime('%Y-%m-%d'),
            end_date=self.end_date.strftime('%Y-%m-%d'),
            transaction_codes=['P', 'S']  # Purchase and Sale only
        )

        if transactions_df.empty:
            self.logger.warning(f"  No transactions found for {ticker}")
            return None

        # Parse dates
        transactions_df['transaction_date'] = pd.to_datetime(transactions_df['transaction_date'], errors='coerce')
        transactions_df['filing_date'] = pd.to_datetime(transactions_df['filing_date'], errors='coerce')

        # Parse insider roles
        transactions_df['parsed_roles'] = transactions_df['insider_relationship'].apply(self._parse_insider_role)
        transactions_df['is_officer'] = transactions_df['parsed_roles'].apply(lambda x: x['is_officer'])
        transactions_df['is_director'] = transactions_df['parsed_roles'].apply(lambda x: x['is_director'])
        transactions_df['is_10pct_owner'] = transactions_df['parsed_roles'].apply(lambda x: x['is_10pct_owner'])

        # Get company CIK
        company_cik = transactions_df['company_cik'].iloc[0] if 'company_cik' in transactions_df else ''

        # Calculate summary stats
        summary = self._calculate_summary(transactions_df)

        # Aggregate by month
        monthly_data = self._aggregate_by_month(transactions_df)

        # Rank top insiders
        top_sellers = self._rank_top_insiders(transactions_df[transactions_df['transaction_code'] == 'S'], 'seller')
        top_buyers = self._rank_top_insiders(transactions_df[transactions_df['transaction_code'] == 'P'], 'buyer')

        # Extract transaction details
        transaction_details = self._extract_transaction_details(transactions_df)

        return {
            'company': company_name,
            'ticker': ticker,
            'cik': company_cik,
            'date_range': {
                'start': self.start_date.strftime('%Y-%m-%d'),
                'end': self.end_date.strftime('%Y-%m-%d')
            },
            'summary': summary,
            'months': monthly_data,
            'top_sellers': top_sellers,
            'top_buyers': top_buyers,
            'transactions': transaction_details
        }

    def _parse_insider_role(self, relationship: str) -> Dict[str, bool]:
        """
        Parse RPTOWNER_RELATIONSHIP field to extract roles.

        Format: "Director,Officer,TenPercentOwner" (comma-separated)

        Returns:
            {
                'is_officer': bool,
                'is_director': bool,
                'is_10pct_owner': bool,
                'role_summary': str
            }
        """
        if pd.isna(relationship):
            return {
                'is_officer': False,
                'is_director': False,
                'is_10pct_owner': False,
                'role_summary': 'Unknown'
            }

        relationship_upper = str(relationship).upper()

        is_officer = 'OFFICER' in relationship_upper
        is_director = 'DIRECTOR' in relationship_upper
        is_10pct = 'TENPERCENTOWNER' in relationship_upper

        # Build role summary
        roles = []
        if is_officer:
            roles.append('Officer')
        if is_director:
            roles.append('Director')
        if is_10pct:
            roles.append('10% Owner')

        role_summary = ', '.join(roles) if roles else 'Other'

        return {
            'is_officer': is_officer,
            'is_director': is_director,
            'is_10pct_owner': is_10pct,
            'role_summary': role_summary
        }

    def _calculate_summary(self, df: pd.DataFrame) -> Dict:
        """Calculate overall summary statistics for the company."""
        total_trans = len(df)
        purchase_trans = len(df[df['transaction_code'] == 'P'])
        sale_trans = len(df[df['transaction_code'] == 'S'])

        # Calculate share totals
        purchase_shares = df[df['transaction_code'] == 'P']['shares'].sum()
        sale_shares = df[df['transaction_code'] == 'S']['shares'].sum()
        net_shares = purchase_shares - sale_shares

        # Calculate value totals
        df_with_price = df[df['price_per_share'].notna() & (df['price_per_share'] > 0)]
        df_with_price_purchase = df_with_price[df_with_price['transaction_code'] == 'P']
        df_with_price_sale = df_with_price[df_with_price['transaction_code'] == 'S']

        purchase_value = (df_with_price_purchase['shares'] * df_with_price_purchase['price_per_share']).sum()
        sale_value = (df_with_price_sale['shares'] * df_with_price_sale['price_per_share']).sum()
        net_value = purchase_value - sale_value

        # Calculate average prices
        avg_purchase_price = df_with_price_purchase['price_per_share'].mean() if not df_with_price_purchase.empty else 0
        avg_sale_price = df_with_price_sale['price_per_share'].mean() if not df_with_price_sale.empty else 0

        # Count unique insiders
        total_insiders = df['insider_cik'].nunique()

        # Count insiders by role
        officers_count = df[df['is_officer']]['insider_cik'].nunique()
        directors_count = df[df['is_director']]['insider_cik'].nunique()
        owners_count = df[df['is_10pct_owner']]['insider_cik'].nunique()

        # Date range
        date_range_days = (df['transaction_date'].max() - df['transaction_date'].min()).days

        return {
            'total_transactions': int(total_trans),
            'total_insiders': int(total_insiders),
            'date_range_days': int(date_range_days),
            'purchase_transactions': int(purchase_trans),
            'sale_transactions': int(sale_trans),
            'net_transactions': int(purchase_trans - sale_trans),
            'total_purchase_value_usd': float(purchase_value),
            'total_sale_value_usd': float(sale_value),
            'net_value_usd': float(net_value),
            'total_purchase_shares': int(purchase_shares),
            'total_sale_shares': int(sale_shares),
            'net_shares': int(net_shares),
            'avg_purchase_price_per_share': float(avg_purchase_price),
            'avg_sale_price_per_share': float(avg_sale_price),
            'officers_count': int(officers_count),
            'directors_count': int(directors_count),
            'tenpercentowners_count': int(owners_count)
        }

    def _aggregate_by_month(self, df: pd.DataFrame) -> List[Dict]:
        """
        Aggregate transactions by month.

        Returns list of monthly summaries with transaction counts, values, and insider activity.
        """
        # Group by year-month
        df['year_month'] = df['transaction_date'].dt.to_period('M')

        monthly_data = []
        for period, group in df.groupby('year_month', sort=False):
            # Separate purchases and sales
            purchases = group[group['transaction_code'] == 'P']
            sales = group[group['transaction_code'] == 'S']

            # Calculate share totals
            purchase_shares = purchases['shares'].sum()
            sale_shares = sales['shares'].sum()
            net_shares = purchase_shares - sale_shares

            # Calculate value totals (only for transactions with valid prices)
            purchases_with_price = purchases[purchases['price_per_share'].notna() & (purchases['price_per_share'] > 0)]
            sales_with_price = sales[sales['price_per_share'].notna() & (sales['price_per_share'] > 0)]

            purchase_value = (purchases_with_price['shares'] * purchases_with_price['price_per_share']).sum()
            sale_value = (sales_with_price['shares'] * sales_with_price['price_per_share']).sum()
            net_value = purchase_value - sale_value

            # Calculate average prices
            avg_purchase_price = purchases_with_price['price_per_share'].mean() if not purchases_with_price.empty else 0
            avg_sale_price = sales_with_price['price_per_share'].mean() if not sales_with_price.empty else 0

            # Count unique buyers/sellers
            num_buyers = purchases['insider_cik'].nunique()
            num_sellers = sales['insider_cik'].nunique()

            # Count transactions by role
            officer_trans = group[group['is_officer']].shape[0]
            director_trans = group[group['is_director']].shape[0]
            owner_trans = group[group['is_10pct_owner']].shape[0]

            monthly_data.append({
                'period': str(period),
                'transactions_count': int(len(group)),
                'purchase_shares': int(purchase_shares),
                'sale_shares': int(sale_shares),
                'net_shares': int(net_shares),
                'purchase_value_usd': float(purchase_value),
                'sale_value_usd': float(sale_value),
                'net_value_usd': float(net_value),
                'avg_purchase_price': float(avg_purchase_price),
                'avg_sale_price': float(avg_sale_price),
                'num_buyers': int(num_buyers),
                'num_sellers': int(num_sellers),
                'officer_transactions': int(officer_trans),
                'director_transactions': int(director_trans),
                'tenpercentowner_transactions': int(owner_trans)
            })

        # Sort by period (most recent first)
        return sorted(monthly_data, key=lambda x: x['period'], reverse=True)

    def _rank_top_insiders(self, df: pd.DataFrame, insider_type: str) -> List[Dict]:
        """
        Rank top insiders by transaction value.

        Args:
            df: DataFrame filtered to either purchases or sales
            insider_type: 'seller' or 'buyer'
        """
        if df.empty:
            return []

        # Group by insider
        grouped = df.groupby('insider_cik').agg({
            'insider_name': 'first',
            'insider_relationship': 'first',
            'shares': 'sum',
            'price_per_share': 'mean',  # Average price
            'transaction_code': 'count'  # Transaction count
        }).reset_index()

        # Calculate total value (only for transactions with valid prices)
        df_with_price = df[df['price_per_share'].notna() & (df['price_per_share'] > 0)]
        value_by_insider = df_with_price.groupby('insider_cik').apply(
            lambda x: (x['shares'] * x['price_per_share']).sum()
        ).to_dict()

        grouped['total_value'] = grouped['insider_cik'].map(value_by_insider).fillna(0)

        # Calculate total value across all insiders
        total_value_all = grouped['total_value'].sum()

        # Parse roles
        grouped['parsed_roles'] = grouped['insider_relationship'].apply(self._parse_insider_role)

        # Sort by total value
        grouped = grouped.sort_values('total_value', ascending=False).head(10)

        # Build ranking
        rankings = []
        for rank, (_, row) in enumerate(grouped.iterrows(), start=1):
            parsed_role = row['parsed_roles']
            pct_of_total = (row['total_value'] / total_value_all * 100) if total_value_all > 0 else 0

            rankings.append({
                'rank': rank,
                'insider_name': str(row['insider_name']),
                'insider_cik': str(row['insider_cik']),
                'insider_role': parsed_role['role_summary'],
                'is_officer': parsed_role['is_officer'],
                'is_director': parsed_role['is_director'],
                'is_10pct_owner': parsed_role['is_10pct_owner'],
                f'total_{"sale" if insider_type == "seller" else "purchase"}_shares': int(row['shares']),
                f'total_{"sale" if insider_type == "seller" else "purchase"}_value_usd': float(row['total_value']),
                'transactions_count': int(row['transaction_code']),
                f'avg_{"sale" if insider_type == "seller" else "purchase"}_price': float(row['price_per_share']),
                'pct_of_total_sales' if insider_type == 'seller' else 'pct_of_total_purchases': float(pct_of_total)
            })

        return rankings

    def _extract_transaction_details(self, df: pd.DataFrame) -> List[Dict]:
        """
        Extract individual transaction details.

        Returns list of all transactions sorted by date (most recent first).
        """
        transactions = []

        for _, row in df.iterrows():
            parsed_role = row['parsed_roles']

            # Construct SEC URL
            accession_number = str(row['accession_number'])
            insider_cik = str(row['insider_cik'])
            sec_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={insider_cik}&type=4&dateb=&owner=include&count=100"

            # Transaction type label
            trans_type = "Purchase" if row['transaction_code'] == 'P' else "Sale"

            # Timeliness label
            timeliness_raw = row.get('timeliness', '')
            if pd.isna(timeliness_raw) or timeliness_raw == '':
                timeliness = 'On-time'
            elif timeliness_raw == 'E':
                timeliness = 'Early'
            elif timeliness_raw == 'L':
                timeliness = 'Late'
            else:
                timeliness = 'On-time'

            transactions.append({
                'transaction_date': row['transaction_date'].strftime('%Y-%m-%d') if pd.notna(row['transaction_date']) else None,
                'filing_date': row['filing_date'].strftime('%Y-%m-%d') if pd.notna(row['filing_date']) else None,
                'insider_name': str(row['insider_name']),
                'insider_cik': str(row['insider_cik']),
                'insider_role': parsed_role['role_summary'],
                'is_officer': parsed_role['is_officer'],
                'is_director': parsed_role['is_director'],
                'is_10pct_owner': parsed_role['is_10pct_owner'],
                'transaction_code': str(row['transaction_code']),
                'transaction_type': trans_type,
                'shares': float(row['shares']) if pd.notna(row['shares']) else 0,
                'price_per_share': float(row['price_per_share']) if pd.notna(row['price_per_share']) else 0,
                'value_usd': float(row['shares'] * row['price_per_share']) if pd.notna(row['shares']) and pd.notna(row['price_per_share']) else 0,
                'shares_owned_after': float(row['shares_owned_after']) if pd.notna(row['shares_owned_after']) else 0,
                'ownership_type': str(row['ownership_type']) if pd.notna(row['ownership_type']) else 'Unknown',
                'timeliness': timeliness,
                'form_type': str(row['form_type']) if pd.notna(row['form_type']) else 'Unknown',
                'accession_number': accession_number,
                'sec_url': sec_url
            })

        # Sort by transaction_date (most recent first)
        return sorted(transactions, key=lambda x: x['transaction_date'] or '1900-01-01', reverse=True)

    def _load_existing_transactions(self) -> List[Dict]:
        """Load existing transactions.json if it exists (for resume)."""
        transactions_file = self.output_dir / "transactions.json"
        if transactions_file.exists():
            try:
                with open(transactions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load existing transactions: {e}")
                return []
        return []

    def _save_transactions_incremental(self, transactions: List[Dict]):
        """Save transactions.json after each company (incremental saving)."""
        output_file = self.output_dir / "transactions.json"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(transactions, f, indent=2, ensure_ascii=False)
            self.logger.debug(f"Saved {len(transactions)} company transactions (incremental)")
        except Exception as e:
            self.logger.error(f"Failed to save transactions (incremental): {e}")

    def _save_transactions(self, transactions: List[Dict]):
        """Final save of transactions.json."""
        output_file = self.output_dir / "transactions.json"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(transactions, f, indent=2, ensure_ascii=False)

            # Calculate file size
            file_size_mb = output_file.stat().st_size / (1024 * 1024)
            self.stats['total_size'] = file_size_mb

            self.logger.info(f"Saved transactions.json ({file_size_mb:.2f} MB)")
        except Exception as e:
            self.logger.error(f"Failed to save transactions: {e}")

    def _save_metadata(self, transactions: List[Dict]):
        """Save transactions_metadata.json."""
        # Count total transactions across all companies
        total_transactions = sum(
            len(company.get('transactions', []))
            for company in transactions
        )

        metadata = {
            'source': 'insider_transactions',
            'timestamp': datetime.now().isoformat(),
            'date_range': f"{self.start_date.date()} to {self.end_date.date()}",
            'total_companies': len(transactions),
            'total_transactions': total_transactions,
            'stats': self.stats
        }

        metadata_file = self.output_dir / "transactions_metadata.json"
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Saved transactions_metadata.json")
        except Exception as e:
            self.logger.error(f"Failed to save metadata: {e}")

    def _print_summary(self):
        """Print download summary."""
        self.logger.info("=" * 60)
        self.logger.info("INSIDER TRANSACTIONS DOWNLOAD COMPLETE")
        self.logger.info("=" * 60)
        self.logger.info(f"Success: {self.stats['success']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        self.logger.info(f"Skipped: {self.stats['skipped']}")
        self.logger.info(f"Total Size: {self.stats['total_size']:.2f} MB")
        self.logger.info("\nBy Company:")
        for ticker, count in sorted(self.stats['by_company'].items()):
            self.logger.info(f"  {ticker}: {count} transactions")
        self.logger.info("=" * 60)


if __name__ == "__main__":
    # Standalone test - 3 companies
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print("=" * 70)
    print("INSIDER TRANSACTIONS DOWNLOADER - STANDALONE TEST")
    print("=" * 70)
    print("\nTesting with 3 eVTOL companies (ACHR, JOBY, BLDE)")
    print("Output: data/eVTOL_INSIDER_STANDALONE_TEST/insider_transactions/")
    print()

    downloader = InsiderTransactionsDownloader(
        output_dir=Path("data/eVTOL_INSIDER_STANDALONE_TEST/insider_transactions"),
        companies={
            'ACHR': 'Archer Aviation Inc',
            'JOBY': 'Joby Aero, Inc.',
            'BLDE': 'Blade Air Mobility'
        },
        start_date='2024-01-01',
        end_date='2025-11-05'
    )

    stats = downloader.download()

    print("\n" + "=" * 70)
    print("STANDALONE TEST COMPLETE")
    print("=" * 70)
    print(f"Success: {stats['success']}/{len(downloader.companies)}")
    print(f"Failed: {stats['failed']}")
    print(f"File size: {stats['total_size']:.2f} MB")
    print("\nBy Company:")
    for ticker, count in stats['by_company'].items():
        print(f"  {ticker}: {count} transactions")
    print("=" * 70)
