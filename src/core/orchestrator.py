"""
Initial Harvest - Industry-Specific Data Collection
====================================================
JSON-driven multi-source data harvester for Gartner-style hype cycle analysis

Features:
- Industry-specific configuration via JSON
- Automatic folder structure organization
- Multi-source data collection (10 sources)
- Free-tier API limit management
- Consolidated cross-source analytics
- Resume capability via checkpoints

Usage:
    python initial_harvest.py --config configs/evtol_config.json
    python initial_harvest.py --config configs/evtol_config.json --dry-run
    python initial_harvest.py --config configs/evtol_config.json --resume
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
import jsonschema

from src.utils.logger import setup_logger


class InitialHarvest:
    """Main orchestrator for industry-specific data harvesting"""

    def __init__(self, config_path: str, dry_run: bool = False, resume: bool = False):
        self.config_path = config_path
        self.dry_run = dry_run
        self.resume = resume

        # Load and validate configuration
        self.config = self._load_and_validate_config()

        # Setup paths
        self.industry_root = None
        self.logger = None

    def _load_and_validate_config(self) -> Dict:
        """Load and validate JSON configuration"""
        print(f"Loading configuration from: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Validate against schema
        try:
            # Schema is in project root/configs, not src/core/configs
            project_root = Path(__file__).parent.parent.parent
            schema_path = project_root / 'configs' / 'config_schema.json'
            if schema_path.exists():
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema = json.load(f)
                jsonschema.validate(config, schema)
                print("[OK] Configuration validated successfully")
            else:
                print("[WARN] Schema file not found - skipping validation")
        except jsonschema.ValidationError as e:
            print(f"[FAIL] Configuration validation error: {e.message}")
            sys.exit(1)

        return config

    def setup_folders(self) -> Path:
        """Create organized folder structure for industry"""
        base = Path(self.config['output_config']['base_dir'])
        industry = self.config['output_config']['industry_folder']

        # Create industry root
        industry_root = base / industry

        if self.dry_run:
            print(f"[DRY-RUN] Would create: {industry_root}")
            return industry_root

        industry_root.mkdir(parents=True, exist_ok=True)
        print(f"[OK] Created industry root: {industry_root}")

        # Create source subfolders
        folder_map = self.config['output_config']['folder_structure']
        for source, folder_name in folder_map.items():
            folder_path = industry_root / folder_name
            folder_path.mkdir(exist_ok=True)
            print(f"  - Created: {folder_name}/")

        # Create consolidated folder
        consolidated = industry_root / '_consolidated'
        consolidated.mkdir(exist_ok=True)
        print(f"  - Created: _consolidated/")

        # Save config copy
        config_copy = industry_root / 'harvest_config.json'
        with open(config_copy, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2)
        print(f"  - Saved config copy: harvest_config.json")

        # Setup logger
        self.logger = setup_logger("InitialHarvest", industry_root / "harvest.log")

        return industry_root

    def initialize_downloaders(self) -> Dict:
        """Initialize all enabled downloaders"""
        if self.dry_run:
            print("[DRY-RUN] Would initialize downloaders for enabled sources")
            return {}

        downloaders = {}
        folder_map = self.config['output_config']['folder_structure']

        # Calculate date range
        if self.config['date_range'].get('days_back'):
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.config['date_range']['days_back'])
        else:
            start_date = datetime.fromisoformat(self.config['date_range']['start_date'])
            end_date = datetime.fromisoformat(self.config['date_range']['end_date'])

        self.logger.info(f"Date range: {start_date.date()} to {end_date.date()}")

        # Combine all keywords
        all_keywords = []
        for keyword_group in self.config['keywords'].values():
            all_keywords.extend(keyword_group)

        # Combine all company tickers
        all_tickers = {}
        if 'companies' in self.config:
            for company_type in ['public', 'private']:
                if company_type in self.config['companies']:
                    all_tickers.update(self.config['companies'][company_type])

        # 0. Company Fundamentals (FMP API)
        if self.config['data_sources'].get('company_fundamentals', {}).get('enabled'):
            from src.downloaders.company_fundamentals import CompanyFundamentalsDownloader
            downloaders['company_fundamentals'] = CompanyFundamentalsDownloader(
                output_dir=self.industry_root / folder_map['company_fundamentals'],
                tickers=self.config['companies'].get('public', {}),  # Only public companies have stock data
                start_date=start_date,
                end_date=end_date
            )
            self.logger.info("Initialized: CompanyFundamentalsDownloader")

        # 1. Patents
        if self.config['data_sources'].get('patents', {}).get('enabled'):
            from src.downloaders.patents import PatentDownloader
            downloaders['patents'] = PatentDownloader(
                output_dir=self.industry_root / folder_map['patents'],
                start_date=start_date,
                end_date=end_date,
                keywords=self.config['keywords']['core'] + self.config['keywords'].get('technology', []),
                cpc_codes=self.config['data_sources']['patents'].get('cpc_codes', []),
                limit=self.config['data_sources']['patents'].get('limit', 1000)
            )
            self.logger.info("Initialized: PatentDownloader")

        # 2. GitHub
        if self.config['data_sources'].get('github', {}).get('enabled'):
            from src.downloaders.github_tracker import GitHubTracker
            downloaders['github'] = GitHubTracker(
                output_dir=self.industry_root / folder_map['github'],
                keywords=self.config['keywords']['core'],
                limit=self.config['data_sources']['github'].get('limit', 100),
                min_stars=self.config['data_sources']['github'].get('min_stars', 5)
            )
            self.logger.info("Initialized: GitHubTracker")

        # 3. SEC Filings
        if self.config['data_sources'].get('sec_filings', {}).get('enabled'):
            from src.downloaders.sec_filings import SECDownloader
            downloaders['sec'] = SECDownloader(
                output_dir=self.industry_root / folder_map['sec'],
                start_date=start_date,
                end_date=end_date,
                tickers=all_tickers  # Pass eVTOL companies from config
            )
            self.logger.info("Initialized: SECDownloader")

        # 4. Earnings
        if self.config['data_sources'].get('earnings', {}).get('enabled'):
            from src.downloaders.earnings import EarningsDownloader
            downloaders['earnings'] = EarningsDownloader(
                output_dir=self.industry_root / folder_map['earnings'],
                start_date=start_date,
                end_date=end_date,
                tickers=all_tickers  # Pass eVTOL companies from config
            )
            self.logger.info("Initialized: EarningsDownloader")

        # 5. Research Papers
        if self.config['data_sources'].get('research', {}).get('enabled'):
            from src.downloaders.research_papers import ResearchDownloader
            downloaders['research'] = ResearchDownloader(
                output_dir=self.industry_root / folder_map['research'],
                start_date=start_date,
                end_date=end_date,
                keywords=all_keywords  # Pass eVTOL keywords from config
            )
            self.logger.info("Initialized: ResearchDownloader")

        # 6. Regulatory
        if self.config['data_sources'].get('regulatory', {}).get('enabled'):
            from src.downloaders.regulatory import RegulatoryDownloader
            # Get regulatory-specific config
            agencies = self.config['data_sources']['regulatory'].get('agencies', None)
            rss_feeds = self.config['data_sources']['regulatory'].get('rss_feeds', None)
            downloaders['regulatory'] = RegulatoryDownloader(
                output_dir=self.industry_root / folder_map['regulatory'],
                start_date=start_date,
                end_date=end_date,
                agencies=agencies,  # Pass FAA agencies from config
                rss_feeds=rss_feeds  # Pass regulatory RSS feeds from config
            )
            self.logger.info("Initialized: RegulatoryDownloader")

        # 7. Press Releases
        if self.config['data_sources'].get('press', {}).get('enabled'):
            from src.downloaders.press_releases import PressReleaseDownloader
            downloaders['press'] = PressReleaseDownloader(
                output_dir=self.industry_root / folder_map['press'],
                start_date=start_date,
                end_date=end_date,
                companies=all_tickers  # Pass eVTOL companies from config
            )
            self.logger.info("Initialized: PressReleaseDownloader")

        # 8. News Sentiment
        if self.config['data_sources'].get('news_sentiment', {}).get('enabled'):
            from src.downloaders.news_sentiment import NewsSentimentDownloader
            downloaders['news'] = NewsSentimentDownloader(
                output_dir=self.industry_root / folder_map['news'],
                start_date=start_date,
                end_date=end_date,
                keywords=self.config['keywords']['core'],
                limit=self.config['data_sources']['news_sentiment'].get('limit', 2000),
                max_per_query=self.config['data_sources']['news_sentiment'].get('max_records_per_query', 250)
            )
            self.logger.info("Initialized: NewsSentimentDownloader")

        # 9. Citations
        if self.config['data_sources'].get('citations', {}).get('enabled'):
            from src.downloaders.citation_tracker import CitationTracker
            downloaders['citations'] = CitationTracker(
                output_dir=self.industry_root / folder_map['citations'],
                start_date=start_date,
                end_date=end_date,
                keywords=self.config['keywords']['core'] + self.config['keywords'].get('technology', []),
                limit=self.config['data_sources']['citations'].get('limit', 500)
            )
            self.logger.info("Initialized: CitationTracker")

        # 10. Job Postings
        if self.config['data_sources'].get('jobs', {}).get('enabled'):
            from src.downloaders.job_market_tracker import JobMarketTracker
            downloaders['jobs'] = JobMarketTracker(
                output_dir=self.industry_root / folder_map['jobs'],
                keywords=self.config['keywords']['core'],
                limit=self.config['data_sources']['jobs'].get('limit', 500),
                locations=self.config['data_sources']['jobs'].get('locations', ["United States"])
            )
            self.logger.info("Initialized: JobMarketTracker")

        # 11. Stock Market Data (NEW - Yahoo Finance)
        if self.config['data_sources'].get('stock_market', {}).get('enabled'):
            from src.downloaders.stock_market import StockMarketDownloader
            downloaders['stock_market'] = StockMarketDownloader(
                output_dir=self.industry_root / folder_map['stock_market'],
                tickers=all_tickers,  # Public companies only
                history_period=self.config['data_sources']['stock_market'].get('history_period', '6mo'),
                download_options=self.config['data_sources']['stock_market'].get('download_options', True)
            )
            self.logger.info("Initialized: StockMarketDownloader")

        # 12. Government Contracts (NEW - USASpending.gov)
        if self.config['data_sources'].get('government_contracts', {}).get('enabled'):
            from src.downloaders.government_contracts import GovernmentContractsDownloader
            downloaders['gov_contracts'] = GovernmentContractsDownloader(
                output_dir=self.industry_root / folder_map['gov_contracts'],
                companies=all_tickers,
                keywords=self.config['keywords']['core'],
                agencies=self.config['data_sources']['government_contracts'].get('agencies', []),
                years_back=self.config['data_sources']['government_contracts'].get('years_back', 5),
                min_contract_value=self.config['data_sources']['government_contracts'].get('min_contract_value', 0)
            )
            self.logger.info("Initialized: GovernmentContractsDownloader")

        # 13. Institutional Holdings (NEW - 13F Filings)
        if self.config['data_sources'].get('institutional_holdings', {}).get('enabled'):
            from src.downloaders.institutional_holdings import InstitutionalHoldingsDownloader
            public_tickers = list(self.config['companies'].get('public', {}).keys())
            downloaders['institutional_holdings'] = InstitutionalHoldingsDownloader(
                output_dir=self.industry_root / folder_map['institutional_holdings'],
                target_tickers=public_tickers,
                quarters_back=self.config['data_sources']['institutional_holdings'].get('quarters_back', 4)
            )
            self.logger.info("Initialized: InstitutionalHoldingsDownloader")

        return downloaders

    def execute_harvest(self, downloaders: Dict) -> Dict:
        """Execute downloads for all enabled sources"""
        if self.dry_run:
            print(f"[DRY-RUN] Would execute {len(downloaders)} downloaders")
            return {}

        results = {}

        # Sort by priority
        sorted_sources = sorted(
            downloaders.items(),
            key=lambda x: self.config['data_sources'].get(x[0], {}).get('priority', 999)
        )

        print("\n" + "=" * 60)
        print(f" HARVESTING: {self.config['industry_name']}")
        print("=" * 60)

        for idx, (source_name, downloader) in enumerate(sorted_sources, 1):
            print(f"\n[{idx}/{len(sorted_sources)}] {source_name.upper()}")
            print("-" * 60)

            try:
                result = downloader.download()
                results[source_name] = result

                print(f"  [OK] Success: {result.get('success', 0)} documents")
                self.logger.info(f"{source_name}: {result.get('success', 0)} documents downloaded")

            except Exception as e:
                print(f"  [FAIL] Error: {e}")
                results[source_name] = {'success': 0, 'failed': 1, 'error': str(e)}
                self.logger.error(f"{source_name} failed: {e}")

        return results

    def generate_consolidated_analytics(self, results: Dict):
        """Generate cross-source analytics"""
        if self.dry_run:
            print("[DRY-RUN] Would generate consolidated analytics")
            return

        print("\n" + "=" * 60)
        print(" GENERATING CONSOLIDATED ANALYTICS")
        print("=" * 60)

        consolidated_dir = self.industry_root / '_consolidated'

        # 1. Harvest Summary
        harvest_summary = {
            'industry': self.config['industry'],
            'industry_name': self.config['industry_name'],
            'harvest_date': datetime.now().isoformat(),
            'date_range': self.config['date_range'],
            'total_documents': sum(r.get('success', 0) for r in results.values()),
            'by_source': {source: r.get('success', 0) for source, r in results.items()},
            'total_size_mb': sum(r.get('total_size', 0) for r in results.values()) / 1024 / 1024
        }

        with open(consolidated_dir / 'harvest_summary.json', 'w') as f:
            json.dump(harvest_summary, f, indent=2)
        print("  [OK] Saved: harvest_summary.json")

        # 2. Quick Stats for Hype Cycle (basic version)
        hype_cycle_data = {
            'innovation_signals': {
                'patents_count': results.get('patents', {}).get('success', 0),
                'research_papers': results.get('citations', {}).get('success', 0),
                'github_repos': results.get('github', {}).get('repositories_tracked', 0)
            },
            'market_signals': {
                'news_articles': results.get('news', {}).get('success', 0),
                'job_postings': results.get('jobs', {}).get('postings_tracked', 0),
                'sec_filings': results.get('sec', {}).get('success', 0)
            },
            'preliminary_assessment': 'Data collected - ready for hype cycle analysis'
        }

        with open(consolidated_dir / 'hype_cycle_data.json', 'w') as f:
            json.dump(hype_cycle_data, f, indent=2)
        print("  [OK] Saved: hype_cycle_data.json")

        self.logger.info("Consolidated analytics generated")

    def print_final_summary(self, results: Dict):
        """Print final harvest summary"""
        print("\n" + "=" * 60)
        print(" HARVEST COMPLETE")
        print("=" * 60)

        total_docs = sum(r.get('success', 0) for r in results.values())
        total_size = sum(r.get('total_size', 0) for r in results.values())

        print(f"\nDocuments Collected:")
        for source, result in sorted(results.items()):
            count = result.get('success', 0)
            print(f"  {source:20s} {count:6d}")
        print(f"  {'-'*28}")
        print(f"  {'TOTAL':20s} {total_docs:6d}")

        print(f"\nStorage:")
        print(f"  Location: {self.industry_root}")
        print(f"  Total Size: {total_size / 1024 / 1024:.2f} MB")

        print(f"\nConsolidated Analytics:")
        print(f"  Location: {self.industry_root / '_consolidated'}/")

        print(f"\nNext Steps:")
        print(f"  1. Review data: ls -R {self.industry_root}")
        print(f"  2. Check analytics: cat {self.industry_root}/_consolidated/harvest_summary.json")
        print(f"  3. Run analysis: python analyze_hype_cycle.py --industry {self.config['industry']}")

    def run(self):
        """Main execution flow"""
        print("\n" + "=" * 60)
        print(" FINANCIAL DOCUMENT HARVESTER - INITIAL HARVEST")
        print(f" Industry: {self.config.get('industry_name', self.config['industry'])}")
        print("=" * 60)

        # 1. Setup folder structure
        self.industry_root = self.setup_folders()

        if self.dry_run:
            print("\n[DRY-RUN] Configuration valid - ready to harvest!")
            return

        # 2. Initialize downloaders
        print(f"\nInitializing downloaders...")
        downloaders = self.initialize_downloaders()
        print(f"[OK] Initialized {len(downloaders)} downloaders")

        # 3. Execute harvest
        results = self.execute_harvest(downloaders)

        # 4. Generate consolidated analytics
        self.generate_consolidated_analytics(results)

        # 5. Print final summary
        self.print_final_summary(results)

        print(f"\nHarvest completed successfully!")


def main():
    parser = argparse.ArgumentParser(
        description='Initial Harvest - Multi-source Data Collection for Hype Cycle Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run eVTOL harvest
  python initial_harvest.py --config configs/evtol_config.json

  # Validate configuration only
  python initial_harvest.py --config configs/evtol_config.json --dry-run

  # Resume from checkpoint
  python initial_harvest.py --config configs/evtol_config.json --resume
        """
    )

    parser.add_argument(
        '--config',
        required=True,
        help='Path to industry configuration JSON file'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate configuration without downloading data'
    )

    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from checkpoint (if available)'
    )

    args = parser.parse_args()

    # Run harvest
    try:
        harvester = InitialHarvest(
            config_path=args.config,
            dry_run=args.dry_run,
            resume=args.resume
        )
        harvester.run()

    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Harvest interrupted by user")
        print("Run with --resume to continue from checkpoint")
        sys.exit(1)

    except Exception as e:
        print(f"\n[ERROR] Harvest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
