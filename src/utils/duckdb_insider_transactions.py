"""
DuckDB Manager for Insider Transactions (Forms 3/4/5)

Loads SEC Forms 3/4/5 TSV files into DuckDB for fast SQL analytics.
Provides 10-100x performance improvement over Pandas for large datasets.

Usage:
    from src.utils.duckdb_insider_transactions import InsiderTransactionsDatabase

    db = InsiderTransactionsDatabase()
    db.initialize()  # One-time setup

    # Query transactions by ticker
    results = db.query_transactions_by_ticker(['ACHR', 'JOBY'], start_date='2024-01-01')
"""

import duckdb
import logging
from pathlib import Path
from typing import List, Optional
import pandas as pd


class InsiderTransactionsDatabase:
    """
    Manages DuckDB database for Forms 3/4/5 insider transactions.

    Provides fast SQL queries over ~60MB TSV data per quarter.
    """

    def __init__(self, data_dir: str = "data/insider_transactions", db_path: Optional[str] = None):
        """
        Initialize insider transactions database manager.

        Args:
            data_dir: Directory containing TSV files (NONDERIV_TRANS.tsv, etc.)
            db_path: Path to DuckDB file. If None, creates in data_dir/insider_transactions.duckdb
        """
        self.data_dir = Path(data_dir)
        self.db_path = db_path or str(self.data_dir / "insider_transactions.duckdb")
        self.con = None
        self.logger = logging.getLogger(__name__)

        # TSV file paths (only 3 core files needed)
        self.tsv_files = {
            'nonderiv_trans': self.data_dir / "NONDERIV_TRANS.tsv",
            'reportingowner': self.data_dir / "REPORTINGOWNER.tsv",
            'submission': self.data_dir / "SUBMISSION.tsv"
        }

    def connect(self):
        """Open connection to DuckDB database."""
        if self.con is None:
            self.con = duckdb.connect(self.db_path)
            self.logger.info(f"Connected to DuckDB: {self.db_path}")
        return self.con

    def close(self):
        """Close DuckDB connection."""
        if self.con:
            self.con.close()
            self.con = None
            self.logger.info("Closed DuckDB connection")

    def initialize(self, force_reload: bool = False):
        """
        Initialize DuckDB database from TSV files.

        Loads all 3 TSV tables and creates indexes for fast queries.
        Only runs once unless force_reload=True.

        Args:
            force_reload: If True, drops existing tables and reloads
        """
        self.connect()

        # Check if already initialized
        tables = self.con.execute("SHOW TABLES").fetchdf()
        if not tables.empty and not force_reload:
            self.logger.info("Database already initialized. Use force_reload=True to reload.")
            return

        self.logger.info("Initializing Insider Transactions database from TSV files...")

        # Drop existing tables if force reload
        if force_reload:
            for table_name in ['nonderiv_trans', 'reportingowner', 'submission']:
                try:
                    self.con.execute(f"DROP TABLE IF EXISTS {table_name}")
                except:
                    pass

        # Load TSV files into DuckDB
        for table_name, file_path in self.tsv_files.items():
            if not file_path.exists():
                self.logger.warning(f"Skipping {table_name}: file not found at {file_path}")
                continue

            self.logger.info(f"Loading {table_name} from {file_path.name}...")

            try:
                # DuckDB can read TSV directly with auto schema detection
                self.con.execute(f"""
                    CREATE TABLE {table_name} AS
                    SELECT * FROM read_csv_auto('{file_path}',
                        delim='\t',
                        header=true,
                        nullstr='',
                        ignore_errors=false
                    )
                """)

                # Get row count
                count = self.con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                self.logger.info(f"  Loaded {count:,} rows into {table_name}")

            except Exception as e:
                self.logger.error(f"  Error loading {table_name}: {e}")
                raise

        # Create indexes for fast queries
        self.logger.info("Creating indexes...")
        self._create_indexes()

        self.logger.info("Database initialization complete!")
        self._print_database_stats()

    def _create_indexes(self):
        """Create indexes on frequently queried columns."""
        try:
            # Primary keys
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_submission_accession ON submission(ACCESSION_NUMBER)")
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_submission_ticker ON submission(ISSUERTRADINGSYMBOL)")
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_submission_cik ON submission(ISSUERCIK)")

            # Nonderiv_trans indexes (most queried table)
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_nonderiv_accession ON nonderiv_trans(ACCESSION_NUMBER)")
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_nonderiv_transcode ON nonderiv_trans(TRANS_CODE)")
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_nonderiv_transdate ON nonderiv_trans(TRANS_DATE)")

            # Reportingowner indexes
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_reportingowner_accession ON reportingowner(ACCESSION_NUMBER)")
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_reportingowner_cik ON reportingowner(RPTOWNERCIK)")

            self.logger.info("  Created 8 indexes for query optimization")

        except Exception as e:
            self.logger.warning(f"  Index creation warning: {e}")

    def _print_database_stats(self):
        """Print database statistics."""
        self.logger.info("=" * 60)
        self.logger.info("Insider Transactions Database Statistics")
        self.logger.info("=" * 60)

        # Table sizes
        for table_name in ['submission', 'nonderiv_trans', 'reportingowner']:
            try:
                count = self.con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                self.logger.info(f"{table_name:20s}: {count:>10,} rows")
            except:
                pass

        # Date range
        try:
            date_range = self.con.execute("""
                SELECT MIN(TRANS_DATE) as min_date,
                       MAX(TRANS_DATE) as max_date
                FROM nonderiv_trans
            """).fetchone()
            self.logger.info(f"\nDate Range: {date_range[0]} to {date_range[1]}")
        except:
            pass

        # Transaction code distribution
        try:
            codes = self.con.execute("""
                SELECT TRANS_CODE, COUNT(*) as count
                FROM nonderiv_trans
                GROUP BY TRANS_CODE
                ORDER BY count DESC
                LIMIT 10
            """).fetchdf()
            self.logger.info(f"\nTop Transaction Codes:")
            for _, row in codes.iterrows():
                code = row['TRANS_CODE'] if pd.notna(row['TRANS_CODE']) else 'NULL'
                self.logger.info(f"  {code:5s}: {row['count']:>10,}")
        except:
            pass

        self.logger.info("=" * 60)

    def query_transactions_by_ticker(
        self,
        tickers: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        transaction_codes: List[str] = ['P', 'S']  # Purchase and Sale only
    ) -> pd.DataFrame:
        """
        Query insider transactions for given ticker symbols.

        Joins NONDERIV_TRANS + SUBMISSION + REPORTINGOWNER tables.

        Args:
            tickers: List of ticker symbols (e.g., ['ACHR', 'JOBY'])
            start_date: Filter by transaction_date >= start_date (format: 'YYYY-MM-DD')
            end_date: Filter by transaction_date <= end_date (format: 'YYYY-MM-DD')
            transaction_codes: List of codes to include (default: ['P', 'S'])

        Returns:
            DataFrame with columns: ticker, insider_name, transaction_date, transaction_code,
                                   shares, price, role, etc.
        """
        self.connect()

        if not tickers:
            return pd.DataFrame()

        # Build ticker filter
        ticker_list = "', '".join([t.upper() for t in tickers])
        ticker_filter = f"s.ISSUERTRADINGSYMBOL IN ('{ticker_list}')"

        # Build date filters (parse DD-MON-YYYY format using STRPTIME)
        date_filters = []
        if start_date:
            date_filters.append(f"STRPTIME(n.TRANS_DATE, '%d-%b-%Y') >= DATE '{start_date}'")
        if end_date:
            date_filters.append(f"STRPTIME(n.TRANS_DATE, '%d-%b-%Y') <= DATE '{end_date}'")

        # Build transaction code filter
        code_list = "', '".join(transaction_codes)
        code_filter = f"n.TRANS_CODE IN ('{code_list}')"

        where_clause = ticker_filter + " AND " + code_filter
        if date_filters:
            where_clause += " AND " + " AND ".join(date_filters)

        # Main query with joins
        query = f"""
        SELECT
            s.ISSUERTRADINGSYMBOL as ticker,
            s.ISSUERNAME as company_name,
            s.ISSUERCIK as company_cik,
            r.RPTOWNERNAME as insider_name,
            r.RPTOWNERCIK as insider_cik,
            r.RPTOWNER_RELATIONSHIP as insider_relationship,
            r.RPTOWNER_TITLE as insider_title,
            n.TRANS_DATE as transaction_date,
            n.TRANS_CODE as transaction_code,
            n.TRANS_SHARES as shares,
            n.TRANS_PRICEPERSHARE as price_per_share,
            n.TRANS_ACQUIRED_DISP_CD as acquired_disposed,
            n.SHRS_OWND_FOLWNG_TRANS as shares_owned_after,
            n.DIRECT_INDIRECT_OWNERSHIP as ownership_type,
            n.TRANS_TIMELINESS as timeliness,
            s.FILING_DATE as filing_date,
            s.DOCUMENT_TYPE as form_type,
            n.ACCESSION_NUMBER as accession_number
        FROM nonderiv_trans n
        JOIN submission s ON n.ACCESSION_NUMBER = s.ACCESSION_NUMBER
        JOIN reportingowner r ON n.ACCESSION_NUMBER = r.ACCESSION_NUMBER
        WHERE {where_clause}
        ORDER BY n.TRANS_DATE DESC, n.TRANS_SHARES DESC
        """

        try:
            df = self.con.execute(query).fetchdf()
            self.logger.debug(f"Query returned {len(df)} transaction records for {len(tickers)} tickers")
            return df

        except Exception as e:
            self.logger.error(f"Query failed: {e}")
            raise


# Convenience function for quick access
def get_insider_transactions_database(data_dir: str = "data/insider_transactions") -> InsiderTransactionsDatabase:
    """
    Get initialized Insider Transactions database connection.

    Args:
        data_dir: Directory containing TSV files

    Returns:
        InsiderTransactionsDatabase instance (connected and initialized)
    """
    db = InsiderTransactionsDatabase(data_dir=data_dir)
    db.initialize()  # Initialize if not already done
    return db


if __name__ == "__main__":
    # Test database initialization
    logging.basicConfig(level=logging.INFO)

    print("Initializing Insider Transactions database...")
    db = InsiderTransactionsDatabase()
    db.initialize()

    # Test query
    print("\nTesting query for Archer Aviation (ACHR)...")
    transactions = db.query_transactions_by_ticker(['ACHR'], start_date='2024-01-01')

    if not transactions.empty:
        print(f"\nFound {len(transactions)} transaction records")
        print(f"Date range: {transactions['transaction_date'].min()} to {transactions['transaction_date'].max()}")
        print(f"\nTop 5 transactions:")
        for _, row in transactions.head(5).iterrows():
            action = "BOUGHT" if row['transaction_code'] == 'P' else "SOLD"
            shares = row['shares'] if pd.notna(row['shares']) else 0
            price = row['price_per_share'] if pd.notna(row['price_per_share']) else 0
            insider_name = row['insider_name'][:30] if pd.notna(row['insider_name']) else 'N/A'
            print(f"  {row['transaction_date']} | {insider_name:30s} | {action:5s} {shares:>10,.0f} @ ${price:>7.2f}")
    else:
        print("\nNo transactions found for ACHR in dataset")

    db.close()
