"""
DuckDB Manager for Form 13F Data

Loads SEC Form 13F TSV files into DuckDB for fast SQL analytics.
Provides 10-100x performance improvement over Pandas for large datasets.

Usage:
    from src.utils.duckdb_manager import Form13FDatabase

    db = Form13FDatabase()
    db.initialize()  # One-time setup

    # Query holdings
    results = db.query_holdings_by_cusip(['03945R102'])
"""

import duckdb
import logging
from pathlib import Path
from typing import List, Optional
import pandas as pd


class Form13FDatabase:
    """
    Manages DuckDB database for Form 13F institutional holdings data.

    Provides fast SQL queries over 331MB of TSV data (3.36M records).
    """

    def __init__(self, data_dir: str = "data/form13f", db_path: Optional[str] = None):
        """
        Initialize Form 13F database manager.

        Args:
            data_dir: Directory containing TSV files (INFOTABLE.tsv, SUBMISSION.tsv, etc.)
            db_path: Path to DuckDB file. If None, creates in data_dir/13f_data.duckdb
        """
        self.data_dir = Path(data_dir)
        self.db_path = db_path or str(self.data_dir / "13f_data.duckdb")
        self.con = None
        self.logger = logging.getLogger(__name__)

        # TSV file paths
        self.tsv_files = {
            'infotable': self.data_dir / "INFOTABLE.tsv",
            'submission': self.data_dir / "SUBMISSION.tsv",
            'coverpage': self.data_dir / "COVERPAGE.tsv",
            'summarypage': self.data_dir / "SUMMARYPAGE.tsv",
            'signature': self.data_dir / "SIGNATURE.tsv",
            'othermanager': self.data_dir / "OTHERMANAGER.tsv",
            'othermanager2': self.data_dir / "OTHERMANAGER2.tsv"
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

        Loads all 7 TSV tables and creates indexes for fast queries.
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

        self.logger.info("Initializing Form 13F database from TSV files...")

        # Drop existing tables if force reload
        if force_reload:
            for table_name in ['infotable', 'submission', 'coverpage', 'summarypage', 'signature', 'othermanager', 'othermanager2']:
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
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_coverpage_accession ON coverpage(ACCESSION_NUMBER)")

            # Infotable indexes (most queried table)
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_infotable_accession ON infotable(ACCESSION_NUMBER)")
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_infotable_cusip ON infotable(CUSIP)")

            # Date index for filtering
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_submission_period ON submission(PERIODOFREPORT)")
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_submission_type ON submission(SUBMISSIONTYPE)")

            self.logger.info("  Created 7 indexes for query optimization")

        except Exception as e:
            self.logger.warning(f"  Index creation warning: {e}")

    def _print_database_stats(self):
        """Print database statistics."""
        self.logger.info("=" * 60)
        self.logger.info("Form 13F Database Statistics")
        self.logger.info("=" * 60)

        # Table sizes
        for table_name in ['submission', 'coverpage', 'infotable']:
            try:
                count = self.con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                self.logger.info(f"{table_name:15s}: {count:>10,} rows")
            except:
                pass

        # Date range
        try:
            date_range = self.con.execute("""
                SELECT MIN(PERIODOFREPORT) as min_date,
                       MAX(PERIODOFREPORT) as max_date,
                       COUNT(DISTINCT PERIODOFREPORT) as num_quarters
                FROM submission
            """).fetchone()
            self.logger.info(f"\nDate Range: {date_range[0]} to {date_range[1]}")
            self.logger.info(f"Quarters: {date_range[2]}")
        except:
            pass

        # Submission types
        try:
            types = self.con.execute("""
                SELECT SUBMISSIONTYPE, COUNT(*) as count
                FROM submission
                GROUP BY SUBMISSIONTYPE
                ORDER BY count DESC
            """).fetchdf()
            self.logger.info(f"\nSubmission Types:")
            for _, row in types.head(5).iterrows():
                self.logger.info(f"  {row['SUBMISSIONTYPE']:15s}: {row['count']:>6,}")
        except:
            pass

        self.logger.info("=" * 60)

    def query_holdings_by_cusip(
        self,
        cusips: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Query institutional holdings for given CUSIPs.

        Joins INFOTABLE + SUBMISSION + COVERPAGE tables to get complete data.

        Args:
            cusips: List of 9-digit CUSIP identifiers
            start_date: Filter by period >= start_date (format: 'YYYY-MM-DD')
            end_date: Filter by period <= end_date (format: 'YYYY-MM-DD')

        Returns:
            DataFrame with columns: cusip, company_name, shares, value, quarter,
                                   filing_date, institution, cik, etc.
        """
        self.connect()

        if not cusips:
            return pd.DataFrame()

        # Build CUSIP filter
        cusip_list = "', '".join(cusips)
        cusip_filter = f"i.CUSIP IN ('{cusip_list}')"

        # Build date filters
        # Note: PERIODOFREPORT is in DD-MON-YYYY format, need to convert for comparison
        date_filters = []
        if start_date:
            date_filters.append(f"strptime(s.PERIODOFREPORT, '%d-%b-%Y') >= strptime('{start_date}', '%Y-%m-%d')")
        if end_date:
            date_filters.append(f"strptime(s.PERIODOFREPORT, '%d-%b-%Y') <= strptime('{end_date}', '%Y-%m-%d')")

        where_clause = cusip_filter
        if date_filters:
            where_clause += " AND " + " AND ".join(date_filters)

        # Main query with joins
        query = f"""
        SELECT
            i.CUSIP as cusip,
            i.NAMEOFISSUER as company_name,
            i.VALUE as value,
            i.SSHPRNAMT as shares,
            i.SSHPRNAMTTYPE as share_type,
            i.PUTCALL as put_call,
            i.INVESTMENTDISCRETION as investment_discretion,
            i.VOTING_AUTH_SOLE as voting_sole,
            i.VOTING_AUTH_SHARED as voting_shared,
            i.VOTING_AUTH_NONE as voting_none,
            s.PERIODOFREPORT as quarter,
            s.FILING_DATE as filing_date,
            s.CIK as cik,
            s.SUBMISSIONTYPE as submission_type,
            c.FILINGMANAGER_NAME as institution,
            c.FILINGMANAGER_CITY as institution_city,
            c.FILINGMANAGER_STATEORCOUNTRY as institution_state,
            i.ACCESSION_NUMBER as accession_number
        FROM infotable i
        JOIN submission s ON i.ACCESSION_NUMBER = s.ACCESSION_NUMBER
        JOIN coverpage c ON i.ACCESSION_NUMBER = c.ACCESSION_NUMBER
        WHERE {where_clause}
            AND s.SUBMISSIONTYPE = '13F-HR'  -- Only holdings reports (exclude notices)
            AND i.CUSIP != '000000000'       -- Exclude invalid CUSIPs
        ORDER BY s.PERIODOFREPORT DESC, i.VALUE DESC
        """

        try:
            df = self.con.execute(query).fetchdf()
            self.logger.debug(f"Query returned {len(df)} holdings records for {len(cusips)} CUSIPs")
            return df

        except Exception as e:
            self.logger.error(f"Query failed: {e}")
            raise

    def get_quarters(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[str]:
        """
        Get list of available quarters in the database.

        Args:
            start_date: Filter >= start_date (format: 'YYYY-MM-DD')
            end_date: Filter <= end_date (format: 'YYYY-MM-DD')

        Returns:
            List of quarter dates (e.g., ['2025-06-30', '2025-03-31', ...])
        """
        self.connect()

        query = "SELECT DISTINCT PERIODOFREPORT FROM submission"

        filters = []
        if start_date:
            filters.append(f"PERIODOFREPORT >= '{start_date}'")
        if end_date:
            filters.append(f"PERIODOFREPORT <= '{end_date}'")

        if filters:
            query += " WHERE " + " AND ".join(filters)

        query += " ORDER BY PERIODOFREPORT DESC"

        quarters = self.con.execute(query).fetchdf()['PERIODOFREPORT'].tolist()
        return quarters

    def normalize_value(self, value: float, filing_date: str) -> float:
        """
        Normalize value field based on filing date.

        Pre-Jan 3, 2023: Values are in thousands (multiply by 1000)
        Post-Jan 3, 2023: Values are in actual dollars

        Args:
            value: Raw value from INFOTABLE
            filing_date: Filing date from SUBMISSION

        Returns:
            Normalized value in dollars
        """
        if pd.isna(value):
            return 0.0

        # Parse filing date
        try:
            filing_dt = pd.to_datetime(filing_date)
            cutoff_dt = pd.to_datetime('2023-01-03')

            if filing_dt < cutoff_dt:
                return value * 1000  # Convert thousands to dollars
            return value

        except:
            # If date parsing fails, assume post-2023 format
            return value


# Convenience function for quick access
def get_form13f_database(data_dir: str = "data/form13f") -> Form13FDatabase:
    """
    Get initialized Form 13F database connection.

    Args:
        data_dir: Directory containing TSV files

    Returns:
        Form13FDatabase instance (connected and initialized)
    """
    db = Form13FDatabase(data_dir=data_dir)
    db.initialize()  # Initialize if not already done
    return db


if __name__ == "__main__":
    # Test database initialization
    logging.basicConfig(level=logging.INFO)

    print("Initializing Form 13F database...")
    db = Form13FDatabase()
    db.initialize()

    # Test query
    print("\nTesting query for Archer Aviation (CUSIP: 03945R102)...")
    holdings = db.query_holdings_by_cusip(['03945R102'], start_date='2024-01-01')

    if not holdings.empty:
        print(f"\nFound {len(holdings)} holding records")
        print(f"Quarters: {holdings['quarter'].unique()}")
        print(f"Institutions: {holdings['institution'].nunique()}")
        print(f"\nTop 5 holders in latest quarter:")
        latest_quarter = holdings['quarter'].max()
        latest = holdings[holdings['quarter'] == latest_quarter].head(5)
        for _, row in latest.iterrows():
            print(f"  {row['institution'][:50]:50s} {row['shares']:>12,.0f} shares  ${row['value']:>15,.0f}")

    db.close()
