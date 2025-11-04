"""
Example Usage of Financial Document Harvester
==============================================
This script demonstrates various ways to use the harvester
"""

from pathlib import Path
from datetime import datetime, timedelta

from sec_downloader import *
from earnings_downloader import *
from research_downloader import *
from regulatory_downloader import *
from press_release_downloader import *


def example_1_basic_usage():
    """Example 1: Basic usage - download SEC filings for last 30 days"""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Basic SEC Download")
    print("=" * 60)
    
    output_dir = Path("./data/example1")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)
    
    downloader = SECDownloader(output_dir, start_date, end_date)
    results = downloader.download()
    
    print(f"\nResults:")
    print(f"  Success: {results['success']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Skipped: {results['skipped']}")
    print(f"  Total Size: {results['total_size'] / 1024 / 1024:.1f} MB")


def example_2_custom_date_range():
    """Example 2: Custom date range - download earnings for Q3 2024"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Q3 2024 Earnings Calls")
    print("=" * 60)
    
    output_dir = Path("./data/example2")
    
    # Q3 2024: October-November earnings season
    start_date = datetime(2024, 11, 1)
    end_date = datetime(2024, 11, 30)
    
    downloader = EarningsDownloader(output_dir, start_date, end_date)
    results = downloader.download()
    
    print(f"\nResults:")
    print(f"  Transcripts Downloaded: {results['success']}")


def example_3_research_papers():
    """Example 3: Download FinTech research papers"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: FinTech Research Papers")
    print("=" * 60)
    
    output_dir = Path("./data/example3")
    
    # Last 60 days of research
    end_date = datetime.now()
    start_date = end_date - timedelta(days=10)
    
    downloader = ResearchDownloader(output_dir, start_date, end_date)
    results = downloader.download()
    
    print(f"\nResults:")
    print(f"  Papers Downloaded: {results['success']}")

def example_5_specific_companies():
    """Example 5: Focus on specific companies (modify downloader)"""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Specific Companies (JPM, BAC, GS)")
    print("=" * 60)
    
    output_dir = Path("./data/example5")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)
    
    # Create downloader
    downloader = SECDownloader(output_dir, start_date, end_date)
    
    # Modify target companies (optional)
    downloader.TARGET_COMPANIES = {
        'JPM': 'JPMorgan Chase & Co.',
        'BAC': 'Bank of America Corp',
        'GS': 'Goldman Sachs Group Inc.'
    }
    
    results = downloader.download()
    
    print(f"\nResults:")
    print(f"  Documents from 3 companies: {results['success']}")


def main():
    """Run all examples (comment out as needed)"""
    
    print("\n" + "=" * 80)
    print(" FINANCIAL DOCUMENT HARVESTER - USAGE EXAMPLES")
    print("=" * 80)
    
    # Uncomment to run specific examples:
    
    example_1_basic_usage()
    example_2_custom_date_range()
    example_3_research_papers()
    example_5_specific_companies()
    
    print("\n" + "=" * 80)
    print("To run examples, uncomment them in the main() function")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
