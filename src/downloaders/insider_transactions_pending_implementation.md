# Insider Transactions (Forms 3/4/5) Downloader - Implementation Guide

**Status**: Pending Implementation - Ready to Start
**Priority**: High - Fills Layer 3 (Financial Reality) with executive confidence signals
**Created**: 2025-11-04
**Dataset Status**: Bulk data available now, no API token required

---

## Table of Contents
1. [Strategic Context](#strategic-context)
2. [SEC Dataset Documentation](#sec-dataset-documentation)
3. [Implementation Tasks](#implementation-tasks)
4. [Code Structure](#code-structure)
5. [Testing Strategy](#testing-strategy)
6. [Integration Steps](#integration-steps)
7. [Expected Output](#expected-output)
8. [Strategic Intelligence Use Cases](#strategic-intelligence-use-cases)

---

## Strategic Context

### Why Insider Transactions?

**Rating**: 10/10 - Highest priority SEC dataset after Form 13F

**Current Gap in Layer 3 (Financial Reality)**:
- ✅ Institutional holdings (Form 13F)
- ❌ **Missing**: Executive confidence signals (insider buying/selling)

**What Insider Transactions Add**:
1. **Executive Confidence Indicator** - CEOs/CFOs buy before good news, sell before bad news
2. **Leading Signal** - Insiders trade 1-6 months before major events
3. **Contrarian Indicator** - Heavy selling at peaks, buying at troughs
4. **C-Level Validation** - Insiders have non-public information (legally traded)

**Strategic Intelligence Value**:
- "eVTOL executives selling 80% holdings at $16-18 = lack of confidence in near-term prospects"
- "CEO buying $5M of shares = insider sees undervaluation"
- "Wave of Form 4 filings after earnings = insider selling window (planned offload)"

### The Pattern

**Historical Examples**:
1. **Tesla 2018**: Heavy insider buying at $180-220 → Stock climbed to $400+ (2019)
2. **Enron 2001**: Executives sold $1B+ while promoting stock → Bankruptcy
3. **Meta 2022**: Zuckerberg sold $4.5B before metaverse collapse → Stock dropped 70%

**Key Insight**: When insiders' actions contradict their public statements, that's a strategic signal.

### Data Silo Focus

**What to Harvest**:
- Transaction dates and filing dates
- Transaction type (Purchase, Sale, Gift, Exercise Options)
- Share quantities and prices
- Insider role (CEO, CFO, Director, 10% owner)
- Company ticker and CUSIP
- Direct vs indirect ownership
- Transaction codes (P = purchase, S = sale, M = option exercise)

**What to Ignore** (not relevant for strategic intelligence):
- Detailed ownership footnotes
- Legal entity structures
- Minor gift transactions (<$10K)
- Form 3 initial filings (focus on Form 4 transactions)
- Form 5 late filings (prefer timely Form 4)

---

## SEC Dataset Documentation

### Overview

**Forms Covered**:
- **Form 3**: Initial statement of beneficial ownership (new insiders)
- **Form 4**: Statement of changes in beneficial ownership (transactions)
- **Form 5**: Annual statement of changes (late filings)

**Primary Focus**: Form 4 (timely transaction reports)

### Download URLs

**Quarterly Bulk Datasets**:
```
https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets
```

**Direct Download Pattern** (example):
```
https://www.sec.gov/files/dera/data/form-345/2024q3_form345.zip
https://www.sec.gov/files/dera/data/form-345/2024q2_form345.zip
https://www.sec.gov/files/dera/data/form-345/2024q1_form345.zip
```

**File Format**: ZIP containing TSV files

**File Size**: 8-16 MB per quarter (compressed)

**Frequency**: Quarterly updates (Jan/Apr/Jul/Oct)

**Coverage**: 2009-present (~50 quarters of data)

### Dataset Structure

**TSV Files in ZIP**:
1. **REPORTINGOWNER.tsv** - Insider information (name, role, CIK)
2. **NONDERIVATIVETABLE.tsv** - Stock transactions (buy/sell shares)
3. **DERIVATIVETABLE.tsv** - Options/warrants transactions
4. **SUBMISSION.tsv** - Filing metadata (date, type, issuer)
5. **ISSUER.tsv** - Company information (CIK, ticker, name)

**Relationships**:
```
SUBMISSION (accession_number) → REPORTINGOWNER (insider details)
                              → NONDERIVATIVETABLE (stock trades)
                              → DERIVATIVETABLE (option trades)
                              → ISSUER (company details)
```

### Key Fields

**NONDERIVATIVETABLE.tsv** (Primary table for stock transactions):
```
ACCESSION_NUMBER         - Links to SUBMISSION
SECURITY_TITLE           - "Common Stock"
TRANSACTION_DATE         - When trade occurred (YYYY-MM-DD)
TRANSACTION_CODE         - P=Purchase, S=Sale, A=Award, etc.
TRANSACTION_SHARES       - Number of shares
TRANSACTION_PRICEPERSHARE - Price per share
TRANSACTION_ACQUIREDDISPOSEDCODE - A=Acquired, D=Disposed
SHARES_OWNED_FOLLOWING   - Total shares after transaction
DIRECT_INDIRECT          - D=Direct, I=Indirect
```

**REPORTINGOWNER.tsv** (Insider role):
```
ACCESSION_NUMBER         - Links to SUBMISSION
ROWNER_CIK               - Insider CIK
ROWNER_NAME              - Insider name
ROWNER_RELATIONSHIP_OFFICER       - TRUE if officer
ROWNER_RELATIONSHIP_DIRECTOR      - TRUE if director
ROWNER_RELATIONSHIP_TENPERCENTOWNER - TRUE if 10%+ owner
ROWNER_RELATIONSHIP_OTHER         - TRUE if other
```

**SUBMISSION.tsv** (Filing metadata):
```
ACCESSION_NUMBER         - Unique filing ID
ISSUER_CIK               - Company CIK
FILING_DATE              - When form filed with SEC (YYYY-MM-DD)
PERIODOFREPRESENTATION   - Quarter end date
```

**ISSUER.tsv** (Company info):
```
ISSUER_CIK               - Company CIK
ISSUER_NAME              - Company name
ISSUER_TRADING_SYMBOL    - Ticker symbol
```

### Transaction Codes (Critical for Analysis)

**Primary Codes to Track**:
- **P** - Open market purchase (bullish signal)
- **S** - Open market sale (bearish signal)
- **A** - Grant/award (compensation, neutral)
- **M** - Exercise of options (neutral, often followed by sale)
- **G** - Gift (neutral, tax planning)
- **F** - Tax withholding (neutral)

**Strategic Focus**: P (purchases) and S (sales) transactions only

---

## Implementation Tasks

### Phase 1: Download and Analyze SEC Dataset

**Tasks**:
1. [ ] Download latest quarter dataset from SEC
2. [ ] Extract ZIP to `data/insider_transactions/` folder
3. [ ] Load TSV files into Python and inspect structure
4. [ ] Verify field names match documentation
5. [ ] Identify date format (YYYY-MM-DD expected)
6. [ ] Test JOIN operations across tables
7. [ ] Validate CUSIP availability in ISSUER table

**Commands**:
```bash
# Create directory
mkdir -p data/insider_transactions

# Download latest quarter (example: Q3 2024)
curl -o data/insider_transactions/2024q3.zip https://www.sec.gov/files/dera/data/form-345/2024q3_form345.zip

# Extract
unzip data/insider_transactions/2024q3.zip -d data/insider_transactions/
```

**Validation Script** (create `test_insider_data.py`):
```python
import pandas as pd
from pathlib import Path

data_dir = Path("data/insider_transactions")

# Load TSV files
nonderiv = pd.read_csv(data_dir / "NONDERIVATIVETABLE.tsv", sep='\t', low_memory=False)
reportingowner = pd.read_csv(data_dir / "REPORTINGOWNER.tsv", sep='\t', low_memory=False)
submission = pd.read_csv(data_dir / "SUBMISSION.tsv", sep='\t', low_memory=False)
issuer = pd.read_csv(data_dir / "ISSUER.tsv", sep='\t', low_memory=False)

print(f"NONDERIVATIVETABLE: {len(nonderiv):,} rows")
print(f"REPORTINGOWNER: {len(reportingowner):,} rows")
print(f"SUBMISSION: {len(submission):,} rows")
print(f"ISSUER: {len(issuer):,} rows")

print("\nNONDERIVATIVETABLE columns:")
print(nonderiv.columns.tolist())

print("\nSample transaction:")
print(nonderiv.head(1).T)

# Test join
sample = nonderiv.merge(submission, on='ACCESSION_NUMBER', how='left').head(5)
print(f"\nJoin test: {len(sample)} records")
```

---

### Phase 2: Create DuckDB Manager

**File**: `src/utils/duckdb_insider_transactions.py`

**Pattern**: Copy from `duckdb_manager.py` (Form 13F implementation)

**Key Differences from Form 13F**:
1. Load 5 TSV files instead of 7
2. Join NONDERIVATIVETABLE + SUBMISSION + REPORTINGOWNER + ISSUER
3. Query by ticker symbols (not CUSIPs)
4. Filter by transaction code (P/S only)
5. Aggregate by month/quarter (not just quarter)

**Task Checklist**:
- [ ] Copy `duckdb_manager.py` → `duckdb_insider_transactions.py`
- [ ] Update class name: `InsiderTransactionsDatabase`
- [ ] Update TSV file paths (5 files)
- [ ] Update `initialize()` method to load insider tables
- [ ] Create indexes on ACCESSION_NUMBER, ISSUER_CIK, TRANSACTION_DATE
- [ ] Implement `query_transactions_by_ticker()` method
- [ ] Implement `query_transactions_by_cusip()` method (if CUSIP available)
- [ ] Add transaction code filtering
- [ ] Add date range filtering
- [ ] Implement aggregation by insider role
- [ ] Add unit tests

**Code Template**:
```python
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

    Provides fast SQL queries over 8-16 MB TSV data per quarter.
    """

    def __init__(self, data_dir: str = "data/insider_transactions", db_path: Optional[str] = None):
        """
        Initialize insider transactions database manager.

        Args:
            data_dir: Directory containing TSV files (NONDERIVATIVETABLE.tsv, etc.)
            db_path: Path to DuckDB file. If None, creates in data_dir/insider_transactions.duckdb
        """
        self.data_dir = Path(data_dir)
        self.db_path = db_path or str(self.data_dir / "insider_transactions.duckdb")
        self.con = None
        self.logger = logging.getLogger(__name__)

        # TSV file paths
        self.tsv_files = {
            'nonderivativetable': self.data_dir / "NONDERIVATIVETABLE.tsv",
            'reportingowner': self.data_dir / "REPORTINGOWNER.tsv",
            'submission': self.data_dir / "SUBMISSION.tsv",
            'issuer': self.data_dir / "ISSUER.tsv",
            'derivativetable': self.data_dir / "DERIVATIVETABLE.tsv"  # Optional
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

        Loads all 5 TSV tables and creates indexes for fast queries.
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
            for table_name in ['nonderivativetable', 'reportingowner', 'submission', 'issuer', 'derivativetable']:
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
                        delim='\\t',
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
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_issuer_cik ON issuer(ISSUER_CIK)")

            # Nonderivativetable indexes (most queried table)
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_nonderiv_accession ON nonderivativetable(ACCESSION_NUMBER)")
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_nonderiv_transcode ON nonderivativetable(TRANSACTION_CODE)")
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_nonderiv_transdate ON nonderivativetable(TRANSACTION_DATE)")

            # Reportingowner indexes
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_reportingowner_accession ON reportingowner(ACCESSION_NUMBER)")

            # Issuer indexes
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_issuer_ticker ON issuer(ISSUER_TRADING_SYMBOL)")

            self.logger.info("  Created 7 indexes for query optimization")

        except Exception as e:
            self.logger.warning(f"  Index creation warning: {e}")

    def _print_database_stats(self):
        """Print database statistics."""
        self.logger.info("=" * 60)
        self.logger.info("Insider Transactions Database Statistics")
        self.logger.info("=" * 60)

        # Table sizes
        for table_name in ['submission', 'nonderivativetable', 'reportingowner', 'issuer']:
            try:
                count = self.con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                self.logger.info(f"{table_name:20s}: {count:>10,} rows")
            except:
                pass

        # Date range
        try:
            date_range = self.con.execute("""
                SELECT MIN(TRANSACTION_DATE) as min_date,
                       MAX(TRANSACTION_DATE) as max_date
                FROM nonderivativetable
            """).fetchone()
            self.logger.info(f"\\nDate Range: {date_range[0]} to {date_range[1]}")
        except:
            pass

        # Transaction code distribution
        try:
            codes = self.con.execute("""
                SELECT TRANSACTION_CODE, COUNT(*) as count
                FROM nonderivativetable
                GROUP BY TRANSACTION_CODE
                ORDER BY count DESC
                LIMIT 10
            """).fetchdf()
            self.logger.info(f"\\nTop Transaction Codes:")
            for _, row in codes.iterrows():
                self.logger.info(f"  {row['TRANSACTION_CODE']:5s}: {row['count']:>10,}")
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

        Joins NONDERIVATIVETABLE + SUBMISSION + REPORTINGOWNER + ISSUER tables.

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
        ticker_filter = f"i.ISSUER_TRADING_SYMBOL IN ('{ticker_list}')"

        # Build date filters
        date_filters = []
        if start_date:
            date_filters.append(f"n.TRANSACTION_DATE >= '{start_date}'")
        if end_date:
            date_filters.append(f"n.TRANSACTION_DATE <= '{end_date}'")

        # Build transaction code filter
        code_list = "', '".join(transaction_codes)
        code_filter = f"n.TRANSACTION_CODE IN ('{code_list}')"

        where_clause = ticker_filter + " AND " + code_filter
        if date_filters:
            where_clause += " AND " + " AND ".join(date_filters)

        # Main query with joins
        query = f"""
        SELECT
            i.ISSUER_TRADING_SYMBOL as ticker,
            i.ISSUER_NAME as company_name,
            r.ROWNER_NAME as insider_name,
            r.ROWNER_CIK as insider_cik,
            r.ROWNER_RELATIONSHIP_OFFICER as is_officer,
            r.ROWNER_RELATIONSHIP_DIRECTOR as is_director,
            r.ROWNER_RELATIONSHIP_TENPERCENTOWNER as is_10pct_owner,
            n.TRANSACTION_DATE as transaction_date,
            n.TRANSACTION_CODE as transaction_code,
            n.TRANSACTION_SHARES as shares,
            n.TRANSACTION_PRICEPERSHARE as price_per_share,
            n.TRANSACTION_ACQUIREDDISPOSEDCODE as acquired_disposed,
            n.SHARES_OWNED_FOLLOWING as shares_owned_after,
            n.DIRECT_INDIRECT as ownership_type,
            s.FILING_DATE as filing_date,
            n.ACCESSION_NUMBER as accession_number
        FROM nonderivativetable n
        JOIN submission s ON n.ACCESSION_NUMBER = s.ACCESSION_NUMBER
        JOIN reportingowner r ON n.ACCESSION_NUMBER = r.ACCESSION_NUMBER
        JOIN issuer i ON s.ISSUER_CIK = i.ISSUER_CIK
        WHERE {where_clause}
        ORDER BY n.TRANSACTION_DATE DESC, n.TRANSACTION_SHARES DESC
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
    print("\\nTesting query for Archer Aviation (ACHR)...")
    transactions = db.query_transactions_by_ticker(['ACHR'], start_date='2024-01-01')

    if not transactions.empty:
        print(f"\\nFound {len(transactions)} transaction records")
        print(f"Date range: {transactions['transaction_date'].min()} to {transactions['transaction_date'].max()}")
        print(f"\\nTop 5 transactions:")
        for _, row in transactions.head(5).iterrows():
            action = "BOUGHT" if row['transaction_code'] == 'P' else "SOLD"
            print(f"  {row['transaction_date']} | {row['insider_name'][:30]:30s} | {action} {row['shares']:>10,.0f} @ ${row['price_per_share']:>7.2f}")

    db.close()
```

---

### Phase 3: Create Insider Transactions Downloader

**File**: `src/downloaders/insider_transactions.py`

**Pattern**: Copy from `form13f_holdings.py` (proven implementation)

**Task Checklist**:
- [ ] Copy `form13f_holdings.py` → `insider_transactions.py`
- [ ] Update class name: `InsiderTransactionsDownloader`
- [ ] Update database import to use `InsiderTransactionsDatabase`
- [ ] Remove CUSIP mapping (use tickers directly)
- [ ] Update `_process_company()` to query by ticker
- [ ] Implement `_aggregate_by_month()` (insider transactions are monthly, not quarterly)
- [ ] Implement `_calculate_insider_signals()` (net buying/selling, officer vs director)
- [ ] Update incremental saving to use `transactions.json`
- [ ] Update checkpoint tracking
- [ ] Add transaction value calculation
- [ ] Implement role-based aggregation (CEO vs CFO vs Director)
- [ ] Add standardized output contract

**Key Methods to Implement**:

```python
def _process_company(self, ticker: str, company_name: str) -> Dict:
    """
    Process insider transactions for a single company.

    Returns dict with company info and monthly aggregated transactions.
    """
    self.logger.info(f"Processing {ticker} - {company_name}")

    # Query database by ticker
    transactions_df = self.db.query_transactions_by_ticker(
        tickers=[ticker],
        start_date=self.start_date,
        end_date=self.end_date,
        transaction_codes=['P', 'S']  # Purchase and Sale only
    )

    if transactions_df.empty:
        self.logger.warning(f"  No transactions found for {ticker}")
        return None

    # Aggregate by month
    monthly_data = self._aggregate_by_month(transactions_df)

    # Calculate strategic signals
    signals = self._calculate_insider_signals(monthly_data)

    return {
        'company': company_name,
        'ticker': ticker,
        'months': monthly_data,
        'strategic_signals': signals
    }

def _aggregate_by_month(self, transactions_df: pd.DataFrame) -> List[Dict]:
    """
    Aggregate transactions by month.

    Returns list of monthly summaries with:
    - Total shares purchased/sold
    - Total transaction value
    - Number of insiders buying/selling
    - Officer vs director breakdown
    """
    # Group by year-month
    transactions_df['year_month'] = pd.to_datetime(transactions_df['transaction_date']).dt.to_period('M')

    monthly_data = []
    for period, group in transactions_df.groupby('year_month'):
        # Separate purchases and sales
        purchases = group[group['transaction_code'] == 'P']
        sales = group[group['transaction_code'] == 'S']

        # Calculate totals
        purchase_shares = purchases['shares'].sum()
        sale_shares = sales['shares'].sum()
        purchase_value = (purchases['shares'] * purchases['price_per_share']).sum()
        sale_value = (sales['shares'] * sales['price_per_share']).sum()

        # Net buying/selling
        net_shares = purchase_shares - sale_shares
        net_value = purchase_value - sale_value

        # Count unique insiders
        num_buyers = purchases['insider_cik'].nunique()
        num_sellers = sales['insider_cik'].nunique()

        # Officer vs director breakdown
        officer_purchases = purchases[purchases['is_officer']].shape[0]
        officer_sales = sales[sales['is_officer']].shape[0]

        monthly_data.append({
            'period': str(period),
            'purchase_shares': int(purchase_shares),
            'sale_shares': int(sale_shares),
            'net_shares': int(net_shares),
            'purchase_value_usd': float(purchase_value),
            'sale_value_usd': float(sale_value),
            'net_value_usd': float(net_value),
            'num_buyers': int(num_buyers),
            'num_sellers': int(num_sellers),
            'officer_purchases': int(officer_purchases),
            'officer_sales': int(officer_sales)
        })

    return sorted(monthly_data, key=lambda x: x['period'], reverse=True)

def _calculate_insider_signals(self, monthly_data: List[Dict]) -> Dict:
    """
    Calculate strategic signals from insider transaction patterns.

    Returns dict with:
    - trend: 'net_buying', 'net_selling', 'neutral'
    - confidence: 'high', 'medium', 'low' (based on transaction value)
    - officer_sentiment: 'bullish', 'bearish', 'neutral'
    """
    if not monthly_data or len(monthly_data) < 3:
        return {
            'trend': 'insufficient_data',
            'confidence': 'unknown',
            'officer_sentiment': 'unknown'
        }

    # Calculate net value over last 3 months
    recent_3mo = monthly_data[:3]
    total_net_value = sum(m['net_value_usd'] for m in recent_3mo)
    total_purchase_value = sum(m['purchase_value_usd'] for m in recent_3mo)
    total_sale_value = sum(m['sale_value_usd'] for m in recent_3mo)

    # Determine trend
    if total_net_value > 100000:  # Net buying >$100K
        trend = 'net_buying'
    elif total_net_value < -100000:  # Net selling >$100K
        trend = 'net_selling'
    else:
        trend = 'neutral'

    # Determine confidence (based on transaction size)
    max_transaction_value = max(total_purchase_value, total_sale_value)
    if max_transaction_value > 10000000:  # >$10M
        confidence = 'high'
    elif max_transaction_value > 1000000:  # >$1M
        confidence = 'medium'
    else:
        confidence = 'low'

    # Officer sentiment (officers have better info than directors)
    officer_net_trades = sum(
        m['officer_purchases'] - m['officer_sales']
        for m in recent_3mo
    )

    if officer_net_trades > 5:
        officer_sentiment = 'bullish'
    elif officer_net_trades < -5:
        officer_sentiment = 'bearish'
    else:
        officer_sentiment = 'neutral'

    return {
        'trend': trend,
        'confidence': confidence,
        'officer_sentiment': officer_sentiment,
        'net_value_3mo': total_net_value,
        'total_purchase_value_3mo': total_purchase_value,
        'total_sale_value_3mo': total_sale_value
    }
```

---

### Phase 4: Configuration Updates

**File**: `configs/evtol_config.json`

**Add to `data_sources`**:
```json
{
  "data_sources": {
    "insider_transactions": {
      "enabled": true,
      "priority": 13,
      "comment": "SEC Forms 3/4/5 insider transactions from local dataset. Tracks CEO/executive buying/selling patterns."
    }
  }
}
```

**Add to `output_config.folder_structure`**:
```json
{
  "output_config": {
    "folder_structure": {
      "insider_transactions": "insider_transactions"
    }
  }
}
```

---

### Phase 5: Orchestrator Integration

**File**: `src/core/orchestrator.py`

**Add after Form 13F block** (around line 343):

```python
# 15. Insider Transactions (Forms 3/4/5) - Executive confidence signals
if self.config['data_sources'].get('insider_transactions', {}).get('enabled'):
    from src.downloaders.insider_transactions import InsiderTransactionsDownloader

    # Get public companies only
    public_companies = self.config.get('companies', {}).get('public', {})

    if public_companies:
        downloaders['insider_transactions'] = InsiderTransactionsDownloader(
            output_dir=self.industry_root / folder_map.get('insider_transactions', 'insider_transactions'),
            companies=public_companies,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )
        self.logger.info(f"Initialized: InsiderTransactionsDownloader ({len(public_companies)} companies)")
    else:
        self.logger.warning("No public companies found for insider_transactions")
```

---

## Testing Strategy

### Phase 1: Database Setup and Validation

**Create**: `test_insider_transactions_db.py`

```python
"""
Test Insider Transactions DuckDB setup and queries.
"""
import logging
from src.utils.duckdb_insider_transactions import InsiderTransactionsDatabase

logging.basicConfig(level=logging.INFO)

print("=" * 60)
print("Testing Insider Transactions Database")
print("=" * 60)

# Initialize database
db = InsiderTransactionsDatabase()
db.initialize()

# Test query for Archer Aviation
print("\\nQuerying ACHR transactions...")
transactions = db.query_transactions_by_ticker(['ACHR'], start_date='2024-01-01')

if not transactions.empty:
    print(f"\\nFound {len(transactions)} transactions")
    print(f"Date range: {transactions['transaction_date'].min()} to {transactions['transaction_date'].max()}")

    # Show top 5 transactions
    print("\\nTop 5 transactions by share count:")
    for _, row in transactions.head(5).iterrows():
        action = "BOUGHT" if row['transaction_code'] == 'P' else "SOLD"
        role = "Officer" if row['is_officer'] else "Director"
        print(f"  {row['transaction_date']} | {role:8s} | {action:5s} | {row['shares']:>10,.0f} shares @ ${row['price_per_share']:>7.2f}")

    # Calculate net buying/selling
    purchases = transactions[transactions['transaction_code'] == 'P']
    sales = transactions[transactions['transaction_code'] == 'S']

    purchase_shares = purchases['shares'].sum()
    sale_shares = sales['shares'].sum()
    net_shares = purchase_shares - sale_shares

    print(f"\\nNet Activity:")
    print(f"  Purchases: {purchase_shares:>12,.0f} shares")
    print(f"  Sales:     {sale_shares:>12,.0f} shares")
    print(f"  Net:       {net_shares:>12,.0f} shares")

else:
    print("\\nNo transactions found for ACHR")

db.close()
print("\\n" + "=" * 60)
```

**Run**:
```bash
python test_insider_transactions_db.py
```

**Expected Output**:
```
============================================================
Testing Insider Transactions Database
============================================================
Connected to DuckDB: data/insider_transactions/insider_transactions.duckdb
Database already initialized. Use force_reload=True to reload.

Querying ACHR transactions...

Found 47 transactions
Date range: 2024-01-15 to 2024-09-30

Top 5 transactions by share count:
  2024-09-15 | Officer  | SOLD  |    500,000 shares @ $  4.25
  2024-08-20 | Officer  | SOLD  |    350,000 shares @ $  5.10
  2024-07-10 | Director | BOUGHT |     25,000 shares @ $  3.80
  2024-06-05 | Officer  | SOLD  |    200,000 shares @ $  6.20
  2024-05-15 | Officer  | SOLD  |    150,000 shares @ $  7.50

Net Activity:
  Purchases:       50,000 shares
  Sales:        1,250,000 shares
  Net:         -1,200,000 shares

============================================================
```

---

### Phase 2: Downloader Unit Test

**Create**: `configs/evtol_test_insider_transactions.json`

```json
{
  "industry": "eVTOL",
  "industry_name": "eVTOL - Insider Transactions Test",
  "description": "Test insider transactions with 3 companies",

  "date_range": {
    "days_back": 365
  },

  "output_config": {
    "base_dir": "./data",
    "industry_folder": "eVTOL_INSIDER_TEST",
    "create_timestamp_subfolder": false,
    "folder_structure": {
      "insider_transactions": "insider_transactions"
    }
  },

  "companies": {
    "public": {
      "ACHR": "Archer Aviation Inc",
      "JOBY": "Joby Aero, Inc.",
      "BLDE": "Blade Air Mobility"
    }
  },

  "data_sources": {
    "insider_transactions": {
      "enabled": true,
      "priority": 1,
      "comment": "TEST - 3 companies only"
    }
  }
}
```

**Run**:
```bash
python -m src.core.orchestrator --config configs/evtol_test_insider_transactions.json
```

**Validate**:
- [ ] Check `data/eVTOL_INSIDER_TEST/insider_transactions/transactions.json` exists
- [ ] Verify 3 companies processed
- [ ] Verify monthly aggregation works
- [ ] Verify strategic signals calculated
- [ ] Check incremental saves worked
- [ ] Verify checkpoint tracking

---

### Phase 3: Full Harvest

**Run**:
```bash
python -m src.core.orchestrator --config configs/evtol_config.json
```

**Expected Results**:
- Companies: 17 public companies (from eVTOL config)
- Transactions per company: 20-200 (varies by company size)
- Total transactions: ~500-1,500
- File size: ~200-500 KB
- Monthly periods: 12 months (based on `days_back: 365`)

**Validate**:
- [ ] All 17 companies processed
- [ ] Monthly aggregation correct
- [ ] Strategic signals make sense
- [ ] Officer vs director breakdown accurate
- [ ] Net buying/selling trends visible
- [ ] Stats dict matches standardized contract

---

## Expected Output

### Directory Structure
```
data/eVTOL/insider_transactions/
├── transactions.json                    # ~500-1,500 transactions (~200-500 KB)
├── transactions_metadata.json           # Standardized metadata
├── checkpoint_insider_transactions.json # Resume tracking
└── transactions.log                    # Download log
```

### transactions.json Structure
```json
[
  {
    "company": "Archer Aviation Inc",
    "ticker": "ACHR",
    "months": [
      {
        "period": "2024-09",
        "purchase_shares": 25000,
        "sale_shares": 850000,
        "net_shares": -825000,
        "purchase_value_usd": 106250.00,
        "sale_value_usd": 4250000.00,
        "net_value_usd": -4143750.00,
        "num_buyers": 2,
        "num_sellers": 4,
        "officer_purchases": 0,
        "officer_sales": 3
      },
      {
        "period": "2024-08",
        "purchase_shares": 0,
        "sale_shares": 350000,
        "net_shares": -350000,
        "purchase_value_usd": 0.00,
        "sale_value_usd": 1785000.00,
        "net_value_usd": -1785000.00,
        "num_buyers": 0,
        "num_sellers": 2,
        "officer_purchases": 0,
        "officer_sales": 2
      }
    ],
    "strategic_signals": {
      "trend": "net_selling",
      "confidence": "high",
      "officer_sentiment": "bearish",
      "net_value_3mo": -7250000.00,
      "total_purchase_value_3mo": 150000.00,
      "total_sale_value_3mo": 7400000.00
    }
  }
]
```

### transactions_metadata.json Structure
```json
{
  "source": "insider_transactions",
  "timestamp": "2025-11-04T12:00:00.123456",
  "date_range": "2024-11-04 to 2025-11-04",
  "total_companies": 17,
  "total_transactions": 847,
  "stats": {
    "success": 847,
    "failed": 0,
    "skipped": 0,
    "total_size": 0.45,
    "by_company": {
      "ACHR": 47,
      "JOBY": 123,
      "BLDE": 28,
      "BA": 215,
      "LMT": 189
    }
  }
}
```

---

## Strategic Intelligence Use Cases

### 1. Executive Confidence Indicator

**Question**: "Are insiders buying or selling?"

**Analysis**:
```python
import json

with open('data/eVTOL/insider_transactions/transactions.json') as f:
    data = json.load(f)

for company_data in data:
    ticker = company_data['ticker']
    signals = company_data['strategic_signals']

    print(f"{ticker}: {signals['trend']} (confidence: {signals['confidence']})")
    print(f"  Officer sentiment: {signals['officer_sentiment']}")
    print(f"  Net value (3mo): ${signals['net_value_3mo']:,.0f}")
```

**Output**:
```
ACHR: net_selling (confidence: high)
  Officer sentiment: bearish
  Net value (3mo): -$7,250,000

JOBY: net_buying (confidence: medium)
  Officer sentiment: bullish
  Net value (3mo): +$2,100,000
```

**Strategic Insight**: Heavy insider selling at ACHR = executives lack confidence in near-term stock performance.

---

### 2. Insider Activity vs Stock Price

**Question**: "Did insiders sell at the peak?"

**Analysis**: Cross-reference insider transactions with stock price data to identify if executives timed their sales.

```python
# Pseudo-code
insider_sales_dates = [t['transaction_date'] for t in achr_transactions if t['transaction_code'] == 'S']
stock_prices_on_sale_dates = get_stock_prices('ACHR', insider_sales_dates)

avg_sale_price = stock_prices_on_sale_dates.mean()
current_price = get_current_price('ACHR')

if avg_sale_price > current_price * 1.5:
    print("Insiders sold at 50%+ premium to current price = well-timed exit")
```

---

### 3. Officer vs Director Sentiment

**Question**: "Are officers (CEO/CFO) more bearish than directors?"

**Analysis**:
```python
for company_data in data:
    ticker = company_data['ticker']
    months = company_data['months']

    officer_net = sum(m['officer_purchases'] - m['officer_sales'] for m in months)
    total_net = sum(m['net_shares'] for m in months)

    print(f"{ticker}: Officer net trades: {officer_net}, Total net: {total_net}")

    if officer_net < 0 and total_net < 0:
        print("  ⚠️  Officers leading the selling = high conviction bearish signal")
```

---

### 4. Trend Reversal Detection

**Question**: "Has insider sentiment changed recently?"

**Analysis**: Compare last 3 months vs previous 3 months.

```python
for company_data in data:
    ticker = company_data['ticker']
    months = company_data['months']

    if len(months) < 6:
        continue

    recent_3mo = months[:3]
    previous_3mo = months[3:6]

    recent_net = sum(m['net_value_usd'] for m in recent_3mo)
    previous_net = sum(m['net_value_usd'] for m in previous_3mo)

    if previous_net > 100000 and recent_net < -100000:
        print(f"{ticker}: Sentiment reversal detected!")
        print(f"  Previous 3mo: +${previous_net:,.0f} (buying)")
        print(f"  Recent 3mo: ${recent_net:,.0f} (selling)")
        print("  ⚠️  Strategic signal: Insiders changed outlook")
```

---

## Success Criteria

### Functional Requirements
- [ ] Downloads transactions for all public companies
- [ ] Monthly aggregation correct (net buying/selling)
- [ ] Strategic signals calculated accurately
- [ ] Incremental saving prevents data loss
- [ ] Resume capability works after interruption
- [ ] Standardized output contract matches other downloaders
- [ ] Officer vs director breakdown accurate

### Data Quality Requirements
- [ ] All transactions have valid dates
- [ ] Share counts and prices are numeric (not null)
- [ ] Transaction codes filtered to P/S only
- [ ] Insider roles identified correctly
- [ ] Net calculations accurate (purchases - sales)
- [ ] Monthly periods sorted chronologically

### Integration Requirements
- [ ] Orchestrator integration seamless
- [ ] Config-driven (no hardcoded tickers)
- [ ] Logging follows established patterns
- [ ] Error handling graceful (single company failure doesn't stop harvest)
- [ ] Compatible with existing checkpoint system
- [ ] DuckDB database path configurable

---

## Known Challenges & Solutions

### Challenge 1: Ticker Symbol Changes

**Problem**: Companies change tickers after mergers/SPACs (e.g., ACHR was ACIC before merger)

**Solution**: Query by CIK (if available) instead of ticker. Add ticker mapping table.

```python
# Map old tickers to current tickers
ticker_mapping = {
    'ACIC': 'ACHR',  # Archer Aviation SPAC
    'RTP': 'JOBY'    # Joby Aviation SPAC
}
```

---

### Challenge 2: Option Exercises vs Stock Sales

**Problem**: Insiders often exercise options (transaction code M) immediately followed by sale (S). This is neutral (not bearish).

**Solution**: Detect M → S patterns within 3 days and exclude from bearish signals.

```python
# Filter out option exercise + immediate sale patterns
def filter_option_exercises(transactions_df):
    """Remove option exercise sales (neutral signal)."""
    # Group by insider and find M → S within 3 days
    # Mark those S transactions as 'option_exercise_sale'
    # Exclude from strategic signals
    pass
```

---

### Challenge 3: Scheduled Sales (10b5-1 Plans)

**Problem**: Executives set up pre-scheduled selling plans to avoid insider trading accusations. These sales are not strategic signals.

**Solution**: SEC doesn't tag 10b5-1 sales in Forms 3/4/5. Best heuristic: Regular, consistent sales each month = likely scheduled.

```python
# Detect scheduled selling patterns
def detect_scheduled_sales(monthly_data):
    """Identify likely 10b5-1 scheduled sales."""
    sale_amounts = [m['sale_shares'] for m in monthly_data if m['sale_shares'] > 0]

    # If sale amounts are consistent (±20%), likely scheduled
    if len(sale_amounts) >= 3:
        avg_sale = sum(sale_amounts) / len(sale_amounts)
        variance = sum(abs(s - avg_sale) for s in sale_amounts) / len(sale_amounts)
        if variance / avg_sale < 0.2:  # <20% variance
            return True
    return False
```

---

### Challenge 4: Missing Price Data

**Problem**: Some transactions don't have `TRANSACTION_PRICEPERSHARE` (gifts, awards).

**Solution**: Filter to transaction codes P and S only (which always have prices).

---

## Post-Implementation Validation

### Data Sanity Checks

**Run these queries after harvest**:

1. **Check for missing prices**:
```python
missing_prices = [t for company in data for m in company['months']
                  if m['purchase_value_usd'] == 0 and m['purchase_shares'] > 0]
assert len(missing_prices) == 0, f"Found {len(missing_prices)} transactions with missing prices!"
```

2. **Check net calculation accuracy**:
```python
for company in data:
    for month in company['months']:
        expected_net = month['purchase_shares'] - month['sale_shares']
        assert month['net_shares'] == expected_net, f"Net share calculation error for {company['ticker']}"
```

3. **Check date range**:
```python
from datetime import datetime, timedelta

for company in data:
    for month in company['months']:
        period_date = datetime.strptime(month['period'], '%Y-%m')
        assert period_date >= datetime.now() - timedelta(days=400), f"Transaction older than expected"
```

4. **Check strategic signals logic**:
```python
for company in data:
    signals = company['strategic_signals']
    net_value = signals['net_value_3mo']

    if signals['trend'] == 'net_buying':
        assert net_value > 0, f"{company['ticker']}: trend=net_buying but net_value={net_value}"
    elif signals['trend'] == 'net_selling':
        assert net_value < 0, f"{company['ticker']}: trend=net_selling but net_value={net_value}"
```

---

## Timeline Estimate

**Assuming SEC dataset already downloaded**:

1. **Phase 1 - Database Setup**: 1-2 hours
   - Download SEC dataset
   - Create `duckdb_insider_transactions.py`
   - Test database initialization
   - Validate query results

2. **Phase 2 - Downloader Implementation**: 2-3 hours
   - Copy `form13f_holdings.py` structure
   - Adapt for insider transactions
   - Implement monthly aggregation
   - Implement strategic signals
   - Add incremental saving

3. **Phase 3 - Testing**: 1-2 hours
   - Create test config (3 companies)
   - Run unit tests
   - Validate output structure
   - Fix any issues

4. **Phase 4 - Integration**: 30 minutes
   - Update `evtol_config.json`
   - Update `orchestrator.py`
   - Verify initialization

5. **Phase 5 - Full Harvest**: 15-30 minutes
   - Run full harvest (17 companies)
   - Validate data quality
   - Check stats and logs

**Total**: ~5-8 hours from start to full harvest complete

---

## Next Session Checklist

**Before Starting**:
- [ ] Download latest SEC insider transactions dataset
- [ ] Extract ZIP to `data/insider_transactions/` folder
- [ ] Verify TSV files exist (NONDERIVATIVETABLE.tsv, etc.)
- [ ] Review this document

**Implementation Order**:
1. [ ] Run `test_insider_data.py` to validate TSV structure
2. [ ] Create `src/utils/duckdb_insider_transactions.py`
3. [ ] Test database initialization with `test_insider_transactions_db.py`
4. [ ] Create `src/downloaders/insider_transactions.py`
5. [ ] Implement `_aggregate_by_month()` method
6. [ ] Implement `_calculate_insider_signals()` method
7. [ ] Test with `configs/evtol_test_insider_transactions.json`
8. [ ] Validate output structure
9. [ ] Update `configs/evtol_config.json`
10. [ ] Update `src/core/orchestrator.py`
11. [ ] Run full harvest
12. [ ] Validate data quality with sanity checks
13. [ ] Commit and push changes

---

**Document Status**: Ready for implementation
**Blockers**: None (SEC dataset publicly available)
**Download Dataset**: https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets
**Estimated Implementation Time**: 5-8 hours

---

## Additional Resources

### SEC Forms 3/4/5 Documentation
- **Official Guide**: https://www.sec.gov/files/forms-3-4-5.pdf
- **Data Sets**: https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets
- **Transaction Codes**: https://www.sec.gov/about/forms/form4data.pdf

### Insider Trading Research
- **Academic Paper**: "Do Insiders Trade on Information?" (Lakonishok & Lee, 2001)
- **Regulatory Context**: SEC Rule 10b5-1 (scheduled trading plans)
- **Best Practices**: Harvard Law School Forum on Corporate Governance

### Reference Implementation
- **Form 13F Pattern**: `src/downloaders/form13f_holdings.py`
- **DuckDB Pattern**: `src/utils/duckdb_manager.py`
- **Checkpoint Pattern**: `src/utils/checkpoint_manager.py`
