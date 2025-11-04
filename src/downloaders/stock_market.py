"""
Stock Market Data Downloader
=============================
Downloads stock market data using Yahoo Finance for financial analysis

Target: All public company tickers in config
Primary Source: Yahoo Finance via yfinance library (FREE, unlimited)
Data: Prices, volumes, options, short interest, analyst recommendations

Business Value:
- Stock price trends and volatility (market sentiment)
- Options data (put/call ratios, implied volatility)
- Short interest (bearish sentiment indicators)
- Analyst consensus (Wall Street expectations)
- Institutional holdings (top 10 holders)
"""

import yfinance as yf
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from tqdm import tqdm

from src.utils.logger import setup_logger
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.retry_handler import retry_on_error


class StockMarketDownloader:
    """Download stock market data using Yahoo Finance"""

    def __init__(self, output_dir: Path, tickers: Dict[str, str],
                 history_period: str = "6mo", download_options: bool = True):
        """
        Initialize stock market downloader

        Args:
            output_dir: Directory to save downloaded data
            tickers: Dict of {ticker: company_name}
            history_period: Historical data period (1mo, 3mo, 6mo, 1y, 2y, 5y, max)
            download_options: Whether to download options chains
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.tickers = tickers
        self.history_period = history_period
        self.download_options = download_options

        self.logger = setup_logger("StockMarket", self.output_dir / "stock_market.log")
        self.checkpoint = CheckpointManager(self.output_dir, 'stock_market')

        self.stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total_size': 0,
            'prices_downloaded': 0,
            'options_downloaded': 0,
            'info_downloaded': 0
        }

        resume_info = self.checkpoint.get_resume_info()
        if resume_info:
            self.logger.info(resume_info)

    def download(self) -> Dict:
        """Main download method"""
        self.logger.info("Starting stock market data download")
        self.logger.info(f"Tickers: {list(self.tickers.keys())}")
        self.logger.info(f"History period: {self.history_period}")
        self.logger.info(f"Download options: {self.download_options}")

        all_data = {}

        for ticker, company_name in tqdm(self.tickers.items(), desc="Downloading stock data"):
            try:
                # Check if already completed
                if self.checkpoint.is_completed(ticker):
                    self.logger.info(f"Skipping {ticker} (already completed)")
                    self.stats['skipped'] += 1
                    continue

                ticker_data = self._download_ticker_data(ticker, company_name)
                if ticker_data:
                    all_data[ticker] = ticker_data
                    self.checkpoint.mark_completed(ticker)
                    self.stats['success'] += 1
                else:
                    self.checkpoint.mark_failed(ticker, "Download failed")
                    self.stats['failed'] += 1

            except Exception as e:
                self.logger.error(f"Error downloading {ticker}: {str(e)}")
                self.stats['failed'] += 1

        # Save summary
        self._save_metadata()

        # Finalize checkpoint
        self.checkpoint.finalize()

        # Print summary
        self._print_summary()

        return self.stats

    @retry_on_error(max_retries=3)
    def _download_ticker_data(self, ticker: str, company_name: str) -> Optional[Dict]:
        """Download all data for a single ticker"""
        self.logger.info(f"Downloading data for {ticker} ({company_name})")

        try:
            # Create ticker object
            stock = yf.Ticker(ticker)

            ticker_data = {
                'ticker': ticker,
                'company_name': company_name,
                'download_date': datetime.now().isoformat()
            }

            # 1. Historical prices
            try:
                hist = stock.history(period=self.history_period)
                if not hist.empty:
                    hist_file = self.output_dir / f"{ticker}_prices.csv"
                    hist.to_csv(hist_file)
                    ticker_data['prices_file'] = str(hist_file)
                    ticker_data['price_records'] = len(hist)
                    self.stats['prices_downloaded'] += 1
                    self.logger.debug(f"Saved {len(hist)} price records for {ticker}")
            except Exception as e:
                self.logger.warning(f"Failed to download prices for {ticker}: {e}")

            # 2. Company info (includes fundamentals, short interest, analyst data)
            try:
                info = stock.info
                if info:
                    info_file = self.output_dir / f"{ticker}_info.json"
                    with open(info_file, 'w') as f:
                        json.dump(info, f, indent=2, default=str)
                    ticker_data['info_file'] = str(info_file)
                    self.stats['info_downloaded'] += 1

                    # Extract key metrics for quick reference
                    ticker_data['metrics'] = {
                        'market_cap': info.get('marketCap'),
                        'pe_ratio': info.get('trailingPE'),
                        'forward_pe': info.get('forwardPE'),
                        'price_to_book': info.get('priceToBook'),
                        'short_percent': info.get('shortPercentOfFloat'),
                        'short_ratio': info.get('shortRatio'),
                        '52_week_high': info.get('fiftyTwoWeekHigh'),
                        '52_week_low': info.get('fiftyTwoWeekLow'),
                        'beta': info.get('beta'),
                        'current_price': info.get('currentPrice')
                    }

                    self.logger.debug(f"Saved company info for {ticker}")
            except Exception as e:
                self.logger.warning(f"Failed to download info for {ticker}: {e}")

            # 3. Options chains (if enabled)
            if self.download_options:
                try:
                    expirations = stock.options
                    if expirations:
                        options_data = []
                        # Limit to next 3 expirations to avoid excessive data
                        for exp_date in expirations[:3]:
                            try:
                                opt_chain = stock.option_chain(exp_date)

                                # Save calls
                                calls_file = self.output_dir / f"{ticker}_calls_{exp_date}.csv"
                                opt_chain.calls.to_csv(calls_file)

                                # Save puts
                                puts_file = self.output_dir / f"{ticker}_puts_{exp_date}.csv"
                                opt_chain.puts.to_csv(puts_file)

                                options_data.append({
                                    'expiration': exp_date,
                                    'calls_file': str(calls_file),
                                    'puts_file': str(puts_file),
                                    'num_calls': len(opt_chain.calls),
                                    'num_puts': len(opt_chain.puts)
                                })

                                self.logger.debug(f"Saved options for {ticker} exp {exp_date}")
                            except Exception as e:
                                self.logger.warning(f"Failed to download options for {ticker} {exp_date}: {e}")

                        if options_data:
                            ticker_data['options'] = options_data
                            self.stats['options_downloaded'] += 1
                except Exception as e:
                    self.logger.warning(f"No options data for {ticker}: {e}")

            # 4. Analyst recommendations
            try:
                recommendations = stock.recommendations
                if recommendations is not None and not recommendations.empty:
                    rec_file = self.output_dir / f"{ticker}_recommendations.csv"
                    recommendations.to_csv(rec_file)
                    ticker_data['recommendations_file'] = str(rec_file)
                    ticker_data['recommendation_count'] = len(recommendations)
                    self.logger.debug(f"Saved {len(recommendations)} recommendations for {ticker}")
            except Exception as e:
                self.logger.warning(f"No recommendations for {ticker}: {e}")

            # 5. Institutional holders (top 10)
            try:
                inst_holders = stock.institutional_holders
                if inst_holders is not None and not inst_holders.empty:
                    inst_file = self.output_dir / f"{ticker}_institutional_holders.csv"
                    inst_holders.to_csv(inst_file)
                    ticker_data['institutional_holders_file'] = str(inst_file)
                    ticker_data['top_holders_count'] = len(inst_holders)
                    self.logger.debug(f"Saved {len(inst_holders)} institutional holders for {ticker}")
            except Exception as e:
                self.logger.warning(f"No institutional holders for {ticker}: {e}")

            # 6. Insider transactions (basic from yfinance)
            try:
                insider_trans = stock.insider_transactions
                if insider_trans is not None and not insider_trans.empty:
                    insider_file = self.output_dir / f"{ticker}_insider_transactions.csv"
                    insider_trans.to_csv(insider_file)
                    ticker_data['insider_transactions_file'] = str(insider_file)
                    ticker_data['insider_transaction_count'] = len(insider_trans)
                    self.logger.debug(f"Saved {len(insider_trans)} insider transactions for {ticker}")
            except Exception as e:
                self.logger.warning(f"No insider transactions for {ticker}: {e}")

            # 7. Earnings estimates
            try:
                earnings_est = stock.earnings_estimate
                if earnings_est is not None and not earnings_est.empty:
                    earn_file = self.output_dir / f"{ticker}_earnings_estimate.csv"
                    earnings_est.to_csv(earn_file)
                    ticker_data['earnings_estimate_file'] = str(earn_file)
                    self.logger.debug(f"Saved earnings estimates for {ticker}")
            except Exception as e:
                self.logger.warning(f"No earnings estimates for {ticker}: {e}")

            # 8. Revenue estimates
            try:
                revenue_est = stock.revenue_estimate
                if revenue_est is not None and not revenue_est.empty:
                    rev_file = self.output_dir / f"{ticker}_revenue_estimate.csv"
                    revenue_est.to_csv(rev_file)
                    ticker_data['revenue_estimate_file'] = str(rev_file)
                    self.logger.debug(f"Saved revenue estimates for {ticker}")
            except Exception as e:
                self.logger.warning(f"No revenue estimates for {ticker}: {e}")

            return ticker_data

        except Exception as e:
            self.logger.error(f"Failed to download data for {ticker}: {str(e)}")
            return None

    def _save_metadata(self):
        """Save metadata and summary"""
        metadata = {
            'download_date': datetime.now().isoformat(),
            'history_period': self.history_period,
            'total_tickers': len(self.tickers),
            'stats': self.stats
        }

        metadata_file = self.output_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        self.logger.info(f"Metadata saved to {metadata_file}")

    def _print_summary(self):
        """Print download summary"""
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("STOCK MARKET DOWNLOAD SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Tickers Processed: {self.stats['success']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        self.logger.info(f"Skipped: {self.stats['skipped']}")
        self.logger.info(f"Prices Downloaded: {self.stats['prices_downloaded']}")
        self.logger.info(f"Company Info Downloaded: {self.stats['info_downloaded']}")
        self.logger.info(f"Options Chains Downloaded: {self.stats['options_downloaded']}")
        self.logger.info("=" * 60)


def main():
    """Test the downloader standalone"""
    # Test with eVTOL companies
    test_tickers = {
        'JOBY': 'Joby Aviation',
        'ACHR': 'Archer Aviation'
    }

    output_dir = Path("test_stock_market_output")
    downloader = StockMarketDownloader(
        output_dir=output_dir,
        tickers=test_tickers,
        history_period="3mo",
        download_options=True
    )

    results = downloader.download()
    print(f"\nDownload complete! Results: {results}")


if __name__ == "__main__":
    main()
