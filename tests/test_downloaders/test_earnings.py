"""
Unit test for Earnings Downloader

Tests the earnings.py downloader in isolation with MINIMAL API calls.
Run this test directly: python tests/test_downloaders/test_earnings.py

EFFICIENT: Only tests with 1 company to minimize API usage.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import shutil

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.downloaders.earnings import EarningsDownloader


def test_earnings_downloader():
    """Test Earnings Downloader with eVTOL company (MINIMAL - 1 company only)"""

    print("\n" + "="*60)
    print("EARNINGS DOWNLOADER TEST")
    print("="*60)

    # Test configuration - ONLY 1 COMPANY for efficiency
    test_output = project_root / "data" / "tests" / "earnings"

    # Clean previous test data
    if test_output.exists():
        shutil.rmtree(test_output)

    # Only test with 1 company
    tickers = {"JOBY": "Joby Aviation"}

    print(f"\nTest Output: {test_output}")
    print(f"Tickers: {tickers}")
    print(f"Date Range: Last 365 days")
    print(f"[!] EFFICIENT MODE: Testing with only 1 company to save API calls")

    try:
        # Initialize downloader
        downloader = EarningsDownloader(
            output_dir=test_output,
            start_date=datetime.now() - timedelta(days=365),
            end_date=datetime.now(),
            tickers=tickers  # Pass custom tickers
        )

        # Download earnings transcripts
        print("\nDownloading earnings transcripts...")
        result = downloader.download()

        # Check results
        print("\n" + "-"*60)
        print("RESULTS:")
        print("-"*60)
        print(f"Success: {result.get('success', 0)}")
        print(f"Failed: {result.get('failed', 0)}")
        print(f"Skipped: {result.get('skipped', 0)}")

        # Test assertion - finding any transcripts is success
        # Note: Some companies may not have recent earnings calls
        if result.get('success', 0) > 0:
            print("\n" + "="*60)
            print("TEST: PASSED [OK]")
            print("="*60)
            print(f"Note: Successfully downloaded {result.get('success', 0)} earnings transcripts")
            return True
        elif result.get('success', 0) == 0 and result.get('failed', 0) == 0:
            print("\n" + "="*60)
            print("TEST: PASSED [OK] (No recent earnings calls found)")
            print("="*60)
            print(f"Note: This is normal if {list(tickers.keys())[0]} had no recent earnings calls")
            return True
        else:
            print("\n" + "="*60)
            print("TEST: FAILED [X] - Errors occurred")
            print("="*60)
            print(f"Note: {result.get('failed', 0)} transcripts failed to download")
            return False

    except Exception as e:
        print(f"\n" + "="*60)
        print(f"TEST: FAILED [X] - Error: {e}")
        print("="*60)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_earnings_downloader()
    sys.exit(0 if success else 1)
