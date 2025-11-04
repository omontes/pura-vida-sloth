#!/usr/bin/env python3
"""
Company Fundamentals Downloader - FMP API Free Tier
Downloads company profiles, financial statements, key metrics, and news
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import requests
from tqdm import tqdm
from dotenv import load_dotenv

from src.utils.rate_limiter import RateLimiter
from src.utils.api_client import FMPAPIClient

load_dotenv()


class CompanyFundamentalsDownloader:
    """Download company fundamentals using FMP API free tier (250 calls/day)"""

    # FMP Free Tier Endpoints
    PROFILE_ENDPOINT = "profile"
    INCOME_STATEMENT = "income-statement"
    BALANCE_SHEET = "balance-sheet-statement"
    CASH_FLOW = "cash-flow-statement"
    KEY_METRICS = "key-metrics"
    COMPANY_NEWS = "stock_news"
    EARNINGS_CALENDAR = "earnings_calendar"

    def __init__(self, output_dir: Path, tickers: Dict[str, str], start_date: datetime, end_date: datetime):
        """
        Initialize company fundamentals downloader

        Args:
            output_dir: Directory to save company data
            tickers: Dict of ticker symbols to company names
            start_date: Start date for news/calendar
            end_date: End date for news/calendar
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date

        # Initialize FMP client
        self.fmp_client = FMPAPIClient()

        # Rate limiter: 250 calls/day = ~10 calls/hour to be safe
        # Each company uses ~7 API calls (profile, 3 financials, metrics, news, calendar)
        # 10 calls/hour = 10/3600 = 0.00278 requests/second
        self.rate_limiter = RateLimiter(requests_per_second=10/3600)

        # Stats
        self.stats = {
            'companies_processed': 0,
            'profiles_downloaded': 0,
            'financials_downloaded': 0,
            'metrics_downloaded': 0,
            'news_articles': 0,
            'earnings_dates': 0,
            'api_calls_made': 0,
            'errors': []
        }

    def download(self) -> Dict:
        """Download fundamentals for all companies (interface method for initial_harvest.py)"""
        print(f"\n{'='*60}")
        print(f"COMPANY FUNDAMENTALS DOWNLOADER - FMP Free Tier")
        print(f"{'='*60}")
        print(f"Output: {self.output_dir}")
        print(f"Companies: {len(self.tickers)}")
        print(f"Date Range: {self.start_date.date()} to {self.end_date.date()}")
        print(f"{'='*60}\n")

        for ticker, company_name in tqdm(self.tickers.items(), desc="Processing companies"):
            try:
                self._download_company_data(ticker, company_name)
                self.stats['companies_processed'] += 1

                # Small delay between companies to respect rate limits
                time.sleep(1)

            except Exception as e:
                error_msg = f"Error processing {ticker} ({company_name}): {str(e)}"
                print(f"\n  [ERROR] {error_msg}")
                self.stats['errors'].append(error_msg)

        self._save_summary()
        self._print_summary()

        # Calculate total documents downloaded
        total_docs = (
            self.stats['profiles_downloaded'] +
            self.stats['financials_downloaded'] +
            self.stats['metrics_downloaded'] +
            self.stats['news_articles'] +
            self.stats['earnings_dates']
        )

        # Return format expected by initial_harvest.py
        return {
            'success': total_docs,
            'failed': len(self.stats['errors']),
            'stats': self.stats
        }

    def _download_company_data(self, ticker: str, company_name: str):
        """Download all available data for a single company"""
        company_dir = self.output_dir / ticker
        company_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n  Processing {ticker} - {company_name}")

        # 1. Company Profile
        profile = self._get_company_profile(ticker)
        if profile:
            self._save_json(company_dir / "profile.json", profile)
            self.stats['profiles_downloaded'] += 1
            print(f"    ✓ Profile")

        # 2. Income Statement (last 5 quarters)
        income = self._get_financial_statement(ticker, self.INCOME_STATEMENT, limit=5)
        if income:
            self._save_json(company_dir / "income_statement.json", income)
            self.stats['financials_downloaded'] += 1
            print(f"    ✓ Income Statement ({len(income)} periods)")

        # 3. Balance Sheet (last 5 quarters)
        balance = self._get_financial_statement(ticker, self.BALANCE_SHEET, limit=5)
        if balance:
            self._save_json(company_dir / "balance_sheet.json", balance)
            self.stats['financials_downloaded'] += 1
            print(f"    ✓ Balance Sheet ({len(balance)} periods)")

        # 4. Cash Flow (last 5 quarters)
        cash_flow = self._get_financial_statement(ticker, self.CASH_FLOW, limit=5)
        if cash_flow:
            self._save_json(company_dir / "cash_flow.json", cash_flow)
            self.stats['financials_downloaded'] += 1
            print(f"    ✓ Cash Flow ({len(cash_flow)} periods)")

        # 5. Key Metrics (last 5 quarters)
        metrics = self._get_key_metrics(ticker, limit=5)
        if metrics:
            self._save_json(company_dir / "key_metrics.json", metrics)
            self.stats['metrics_downloaded'] += 1
            print(f"    ✓ Key Metrics ({len(metrics)} periods)")

        # 6. Company News (date-filtered)
        news = self._get_company_news(ticker, limit=50)
        if news:
            # Filter by date range
            filtered_news = [
                article for article in news
                if self._is_in_date_range(article.get('publishedDate', ''))
            ]
            if filtered_news:
                self._save_json(company_dir / "news.json", filtered_news)
                self.stats['news_articles'] += len(filtered_news)
                print(f"    ✓ News ({len(filtered_news)} articles)")

        # 7. Earnings Calendar
        calendar = self._get_earnings_calendar(ticker)
        if calendar:
            # Filter by date range
            filtered_calendar = [
                event for event in calendar
                if self._is_in_date_range(event.get('date', ''))
            ]
            if filtered_calendar:
                self._save_json(company_dir / "earnings_calendar.json", filtered_calendar)
                self.stats['earnings_dates'] += len(filtered_calendar)
                print(f"    ✓ Earnings Calendar ({len(filtered_calendar)} events)")

    def _get_company_profile(self, ticker: str) -> Optional[List[Dict]]:
        """Get company profile"""
        with self.rate_limiter:
            self.stats['api_calls_made'] += 1
            return self.fmp_client.get_company_profile(ticker)

    def _get_financial_statement(self, ticker: str, statement_type: str, limit: int = 5) -> Optional[List[Dict]]:
        """Get financial statement (income, balance, cash flow)"""
        with self.rate_limiter:
            self.stats['api_calls_made'] += 1
            params = {
                'limit': limit,
                'period': 'quarter'  # Quarterly data
            }
            return self.fmp_client.fetch_endpoint(statement_type, ticker, params=params)

    def _get_key_metrics(self, ticker: str, limit: int = 5) -> Optional[List[Dict]]:
        """Get key metrics"""
        with self.rate_limiter:
            self.stats['api_calls_made'] += 1
            params = {
                'limit': limit,
                'period': 'quarter'
            }
            return self.fmp_client.fetch_endpoint(self.KEY_METRICS, ticker, params=params)

    def _get_company_news(self, ticker: str, limit: int = 50) -> Optional[List[Dict]]:
        """Get company news"""
        with self.rate_limiter:
            self.stats['api_calls_made'] += 1
            params = {
                'tickers': ticker,
                'limit': limit
            }
            return self.fmp_client.fetch_endpoint(self.COMPANY_NEWS, params=params)

    def _get_earnings_calendar(self, ticker: str) -> Optional[List[Dict]]:
        """Get earnings calendar"""
        with self.rate_limiter:
            self.stats['api_calls_made'] += 1
            # Format dates for API
            from_date = self.start_date.strftime('%Y-%m-%d')
            to_date = self.end_date.strftime('%Y-%m-%d')

            params = {
                'symbol': ticker,
                'from': from_date,
                'to': to_date
            }
            return self.fmp_client.fetch_endpoint(self.EARNINGS_CALENDAR, params=params)

    def _is_in_date_range(self, date_str: str) -> bool:
        """Check if date string is within start_date and end_date"""
        if not date_str:
            return False

        try:
            # Parse date (handles various formats)
            if 'T' in date_str:
                article_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                article_date = datetime.strptime(date_str, '%Y-%m-%d')

            return self.start_date <= article_date <= self.end_date
        except Exception:
            return False

    def _save_json(self, filepath: Path, data: any):
        """Save data as JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _save_summary(self):
        """Save harvest summary"""
        summary_path = self.output_dir / "harvest_summary.json"

        summary = {
            'harvest_date': datetime.now().isoformat(),
            'date_range': {
                'start': self.start_date.isoformat(),
                'end': self.end_date.isoformat()
            },
            'statistics': self.stats,
            'companies': list(self.tickers.keys())
        }

        self._save_json(summary_path, summary)

    def _print_summary(self):
        """Print harvest summary"""
        print(f"\n{'='*60}")
        print(f"COMPANY FUNDAMENTALS HARVEST COMPLETE")
        print(f"{'='*60}")
        print(f"Companies Processed:     {self.stats['companies_processed']}/{len(self.tickers)}")
        print(f"Profiles Downloaded:     {self.stats['profiles_downloaded']}")
        print(f"Financial Statements:    {self.stats['financials_downloaded']}")
        print(f"Key Metrics:             {self.stats['metrics_downloaded']}")
        print(f"News Articles:           {self.stats['news_articles']}")
        print(f"Earnings Events:         {self.stats['earnings_dates']}")
        print(f"Total API Calls:         {self.stats['api_calls_made']}")

        if self.stats['errors']:
            print(f"\nErrors: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:  # Show first 5
                print(f"  • {error}")

        print(f"{'='*60}\n")


def main():
    """Test standalone execution"""
    # Test configuration
    output_dir = Path("./data/test_company_fundamentals")

    # Test with a few eVTOL companies
    test_tickers = {
        "JOBY": "Joby Aviation",
        "ACHR": "Archer Aviation",
        "LILM": "Lilium N.V."
    }

    # Last 180 days
    from datetime import timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)

    print("Testing Company Fundamentals Downloader...")
    print(f"Output: {output_dir}")
    print(f"Tickers: {list(test_tickers.keys())}")

    downloader = CompanyFundamentalsDownloader(
        output_dir=output_dir,
        tickers=test_tickers,
        start_date=start_date,
        end_date=end_date
    )

    stats = downloader.download()

    print("\n[SUCCESS] Test download complete!")
    print(f"Check output in: {output_dir}")


if __name__ == "__main__":
    main()
