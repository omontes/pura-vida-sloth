"""
Validate SEC Insider Transactions dataset structure (2025 Q2).

Purpose: Inspect TSV files to verify field names, data types, and content
before implementing DuckDB manager and downloader.
"""
import pandas as pd
from pathlib import Path

data_dir = Path("data/insider_transactions")

print("=" * 70)
print("SEC INSIDER TRANSACTIONS DATASET VALIDATION (2025 Q2)")
print("=" * 70)

# Load TSV files
print("\n1. Loading TSV files...")
try:
    nonderiv_trans = pd.read_csv(data_dir / "NONDERIV_TRANS.tsv", sep='\t', low_memory=False)
    reportingowner = pd.read_csv(data_dir / "REPORTINGOWNER.tsv", sep='\t', low_memory=False)
    submission = pd.read_csv(data_dir / "SUBMISSION.tsv", sep='\t', low_memory=False)

    print(f"   [OK] NONDERIV_TRANS: {len(nonderiv_trans):,} rows")
    print(f"   [OK] REPORTINGOWNER: {len(reportingowner):,} rows")
    print(f"   [OK] SUBMISSION: {len(submission):,} rows")
except Exception as e:
    print(f"   [ERROR] Error loading files: {e}")
    exit(1)

# Check column names
print("\n2. Verifying column names...")
print(f"\n   NONDERIV_TRANS columns ({len(nonderiv_trans.columns)}):")
for col in nonderiv_trans.columns[:15]:  # Show first 15
    print(f"      - {col}")
print(f"      ... and {len(nonderiv_trans.columns) - 15} more")

print(f"\n   REPORTINGOWNER columns ({len(reportingowner.columns)}):")
for col in reportingowner.columns:
    print(f"      - {col}")

print(f"\n   SUBMISSION columns ({len(submission.columns)}):")
for col in submission.columns:
    print(f"      - {col}")

# Check transaction codes distribution
print("\n3. Transaction codes distribution (NONDERIV_TRANS):")
trans_codes = nonderiv_trans['TRANS_CODE'].value_counts().head(10)
for code, count in trans_codes.items():
    print(f"   {code}: {count:>10,}")

# Find eVTOL companies in dataset
print("\n4. Searching for eVTOL companies...")
evtol_tickers = ['ACHR', 'JOBY', 'BLDE', 'EVEX', 'EVTL', 'BA', 'LMT']
found_tickers = submission[submission['ISSUERTRADINGSYMBOL'].isin(evtol_tickers)]['ISSUERTRADINGSYMBOL'].unique()
print(f"   Found {len(found_tickers)} eVTOL companies:")
for ticker in found_tickers:
    count = submission[submission['ISSUERTRADINGSYMBOL'] == ticker].shape[0]
    print(f"      - {ticker}: {count} filings")

# Test JOIN operation
print("\n5. Testing JOIN operations...")
try:
    # Join NONDERIV_TRANS + SUBMISSION + REPORTINGOWNER
    test_join = nonderiv_trans.merge(submission, on='ACCESSION_NUMBER', how='left')
    test_join = test_join.merge(reportingowner, on='ACCESSION_NUMBER', how='left')
    print(f"   [OK] JOIN successful: {len(test_join):,} records")
except Exception as e:
    print(f"   [ERROR] JOIN failed: {e}")

# Show sample transaction for ACHR (if available)
print("\n6. Sample transaction (ACHR if available)...")
achr_filings = submission[submission['ISSUERTRADINGSYMBOL'] == 'ACHR']
if not achr_filings.empty:
    achr_accession = achr_filings['ACCESSION_NUMBER'].iloc[0]
    sample_trans = nonderiv_trans[nonderiv_trans['ACCESSION_NUMBER'] == achr_accession]

    if not sample_trans.empty:
        row = sample_trans.iloc[0]
        print(f"   Accession: {achr_accession}")
        print(f"   Security: {row.get('SECURITY_TITLE', 'N/A')}")
        print(f"   Trans Date: {row.get('TRANS_DATE', 'N/A')}")
        print(f"   Trans Code: {row.get('TRANS_CODE', 'N/A')}")
        print(f"   Shares: {row.get('TRANS_SHARES', 'N/A')}")
        print(f"   Price: ${row.get('TRANS_PRICEPERSHARE', 'N/A')}")
        print(f"   Acquired/Disposed: {row.get('TRANS_ACQUIRED_DISP_CD', 'N/A')}")
    else:
        print(f"   No transactions found for accession {achr_accession}")
else:
    print("   ACHR not found in dataset (Q2 2025 may have no filings)")

# Date range analysis
print("\n7. Date range analysis...")
try:
    nonderiv_trans['TRANS_DATE'] = pd.to_datetime(nonderiv_trans['TRANS_DATE'], errors='coerce')
    min_date = nonderiv_trans['TRANS_DATE'].min()
    max_date = nonderiv_trans['TRANS_DATE'].max()
    print(f"   Transaction dates: {min_date} to {max_date}")
except Exception as e:
    print(f"   Date parsing error: {e}")

# Check REPORTINGOWNER relationship field
print("\n8. Reporting owner relationships...")
if 'RPTOWNER_RELATIONSHIP' in reportingowner.columns:
    relationships = reportingowner['RPTOWNER_RELATIONSHIP'].value_counts().head(10)
    print(f"   RPTOWNER_RELATIONSHIP values ({len(relationships)}):")
    for rel, count in relationships.items():
        print(f"      {rel}: {count:>10,}")
else:
    print("   [ERROR] RPTOWNER_RELATIONSHIP column not found!")

# Check for price data availability
print("\n9. Price data availability...")
prices_available = nonderiv_trans['TRANS_PRICEPERSHARE'].notna().sum()
total_trans = len(nonderiv_trans)
price_pct = (prices_available / total_trans * 100) if total_trans > 0 else 0
print(f"   Transactions with price: {prices_available:,}/{total_trans:,} ({price_pct:.1f}%)")

# Filter to P and S transactions only
print("\n10. Purchase (P) and Sale (S) transactions...")
ps_trans = nonderiv_trans[nonderiv_trans['TRANS_CODE'].isin(['P', 'S'])]
print(f"   Total P/S transactions: {len(ps_trans):,}")
print(f"   Purchase (P): {len(ps_trans[ps_trans['TRANS_CODE'] == 'P']):,}")
print(f"   Sale (S): {len(ps_trans[ps_trans['TRANS_CODE'] == 'S']):,}")

print("\n" + "=" * 70)
print("VALIDATION COMPLETE")
print("=" * 70)
print("\nNext steps:")
print("1. Create src/utils/duckdb_insider_transactions.py")
print("2. Create src/downloaders/insider_transactions.py")
print("3. Test with 3 eVTOL companies")
print("4. Full harvest 17 companies")
