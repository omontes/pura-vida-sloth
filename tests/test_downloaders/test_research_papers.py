"""
Unit test for Research Papers Downloader

Tests the research_papers.py downloader in isolation.
Run this test directly: python tests/test_downloaders/test_research_papers.py

This provides fast feedback (10 seconds) vs running the entire test_system.py (5 minutes).
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import shutil

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.downloaders.research_papers import ResearchDownloader


def test_research_downloader():
    """Test Research Papers Downloader with eVTOL keywords"""

    print("\n" + "="*60)
    print("RESEARCH PAPERS DOWNLOADER TEST")
    print("="*60)

    # Test configuration
    test_output = project_root / "data" / "test_research_papers"

    # Clean previous test data
    if test_output.exists():
        shutil.rmtree(test_output)

    # eVTOL keywords for testing
    keywords = ["eVTOL", "urban air mobility", "VTOL aircraft", "electric aircraft"]

    print(f"\nTest Output: {test_output}")
    print(f"Keywords: {keywords}")
    print(f"Date Range: Last 90 days")

    try:
        # Initialize downloader
        downloader = ResearchDownloader(
            output_dir=test_output,
            start_date=datetime.now() - timedelta(days=90),
            end_date=datetime.now(),
            keywords=keywords
        )

        # Download papers
        print("\nDownloading papers...")
        result = downloader.download()

        # Check results
        print("\n" + "-"*60)
        print("RESULTS:")
        print("-"*60)
        print(f"Success: {result.get('success', 0)}")
        print(f"Failed: {result.get('failed', 0)}")
        print(f"Total Size: {result.get('total_size', 0) / (1024*1024):.2f} MB")

        if result.get('by_source'):
            print("\nBy Source:")
            for source, count in result.get('by_source', {}).items():
                print(f"  {source}: {count}")

        # Test assertion
        if result.get('success', 0) >= 1:
            print("\n" + "="*60)
            print("TEST: PASSED ✓")
            print("="*60)
            return True
        else:
            print("\n" + "="*60)
            print("TEST: FAILED ✗ - No papers downloaded")
            print("="*60)
            return False

    except Exception as e:
        print(f"\n" + "="*60)
        print(f"TEST: FAILED ✗ - Error: {e}")
        print("="*60)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_research_downloader()
    sys.exit(0 if success else 1)
