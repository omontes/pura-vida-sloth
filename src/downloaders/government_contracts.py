"""
Government Contracts Downloader
================================
Downloads federal government contract awards using USASpending.gov API

Target: All companies in config + keyword searches
Primary Source: USASpending.gov API v2 (FREE, unlimited)
Data: Contract awards, grants, loans from federal agencies

Business Value:
- Government validation (DoD, NASA, FAA contracts)
- Revenue visibility (contract amounts and timelines)
- R&D funding (grants from government agencies)
- Strategic partnerships (which agencies are investing)
"""

import requests
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from tqdm import tqdm

from src.utils.logger import setup_logger
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.retry_handler import retry_on_error


class GovernmentContractsDownloader:
    """Download government contract data using USASpending.gov API"""

    USA_SPENDING_API = "https://api.usaspending.gov/api/v2"

    def __init__(self, output_dir: Path, companies: Dict[str, str],
                 keywords: List[str] = None, agencies: List[str] = None,
                 years_back: int = 5, min_contract_value: int = 0):
        """
        Initialize government contracts downloader

        Args:
            output_dir: Directory to save downloaded data
            companies: Dict of {ticker/name: company_name}
            keywords: Optional list of keywords to search (e.g., "eVTOL", "electric VTOL")
            agencies: Optional list of agency codes (e.g., "DOD", "NASA", "FAA")
            years_back: How many years back to search
            min_contract_value: Minimum contract value in dollars
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.companies = companies
        self.keywords = keywords or []
        self.agencies = agencies or []
        self.years_back = years_back
        self.min_contract_value = min_contract_value

        self.logger = setup_logger("GovernmentContracts", self.output_dir / "gov_contracts.log")
        self.checkpoint = CheckpointManager(self.output_dir, 'gov_contracts')

        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })

        self.stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total_contracts': 0,
            'total_value': 0
        }

        resume_info = self.checkpoint.get_resume_info()
        if resume_info:
            self.logger.info(resume_info)

    def download(self) -> Dict:
        """Main download method"""
        self.logger.info("Starting government contracts download")
        self.logger.info(f"Companies: {list(self.companies.values())}")
        self.logger.info(f"Keywords: {self.keywords}")
        self.logger.info(f"Agencies: {self.agencies}")
        self.logger.info(f"Years back: {self.years_back}")

        all_contracts = []

        # Search by company name
        for company_id, company_name in tqdm(self.companies.items(), desc="Searching by company"):
            try:
                # Check if already processed
                if self.checkpoint.is_completed(f"company_{company_id}"):
                    self.logger.info(f"Skipping {company_name} (already completed)")
                    self.stats['skipped'] += 1
                    continue

                contracts = self._search_by_company(company_name)
                if contracts:
                    all_contracts.extend(contracts)
                    self.checkpoint.mark_completed(f"company_{company_id}")
                    self.stats['success'] += 1
                else:
                    self.logger.info(f"No contracts found for {company_name}")
                    self.checkpoint.mark_completed(f"company_{company_id}")
                    self.stats['success'] += 1

            except Exception as e:
                self.logger.error(f"Error searching for {company_name}: {str(e)}")
                self.checkpoint.mark_failed(f"company_{company_id}", str(e))
                self.stats['failed'] += 1

        # Search by keywords
        for keyword in tqdm(self.keywords, desc="Searching by keyword"):
            try:
                keyword_id = keyword.replace(" ", "_")
                if self.checkpoint.is_completed(f"keyword_{keyword_id}"):
                    self.logger.info(f"Skipping keyword '{keyword}' (already completed)")
                    self.stats['skipped'] += 1
                    continue

                contracts = self._search_by_keyword(keyword)
                if contracts:
                    all_contracts.extend(contracts)
                    self.checkpoint.mark_completed(f"keyword_{keyword_id}")
                else:
                    self.logger.info(f"No contracts found for keyword '{keyword}'")
                    self.checkpoint.mark_completed(f"keyword_{keyword_id}")

            except Exception as e:
                self.logger.error(f"Error searching for keyword '{keyword}': {str(e)}")
                self.checkpoint.mark_failed(f"keyword_{keyword_id}", str(e))

        # Deduplicate contracts
        unique_contracts = self._deduplicate_contracts(all_contracts)
        self.logger.info(f"Found {len(unique_contracts)} unique contracts (deduplicated from {len(all_contracts)})")

        # Filter by min value
        if self.min_contract_value > 0:
            filtered_contracts = [c for c in unique_contracts
                                if c.get('Award Amount', 0) >= self.min_contract_value]
            self.logger.info(f"Filtered to {len(filtered_contracts)} contracts >= ${self.min_contract_value:,}")
            unique_contracts = filtered_contracts

        # Save contracts
        if unique_contracts:
            self._save_contracts(unique_contracts)
            self._calculate_stats(unique_contracts)

        # Save summary
        self._save_metadata(len(unique_contracts))

        # Finalize checkpoint
        self.checkpoint.finalize()

        # Print summary
        self._print_summary()

        return self.stats

    @retry_on_error(max_retries=3)
    def _search_by_company(self, company_name: str) -> List[Dict]:
        """Search for contracts by company name"""
        self.logger.info(f"Searching contracts for: {company_name}")

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * self.years_back)

        # Build search payload with REQUIRED fields per USASpending API v2 spec
        payload = {
            "filters": {
                "award_type_codes": ["A", "B", "C", "D"],  # REQUIRED: Purchase Orders, Delivery Orders, Definitive Contracts
                "recipient_search_text": [company_name],
                "time_period": [{
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d")
                }]
            },
            "fields": [  # REQUIRED: Specify which columns to return
                "Award ID",
                "Recipient Name",
                "Award Amount",
                "Start Date",
                "End Date",
                "Description",
                "Awarding Agency",
                "Awarding Sub Agency",
                "Award Type"
            ],
            "limit": 100,
            "page": 1
        }

        contracts = []
        try:
            response = self.session.post(
                f"{self.USA_SPENDING_API}/search/spending_by_award/",
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            results = data.get('results', [])

            for result in results:
                contract = self._parse_contract_result(result, company_name)
                contracts.append(contract)

            self.logger.info(f"Found {len(contracts)} contracts for {company_name}")

        except Exception as e:
            self.logger.error(f"Failed to search for {company_name}: {str(e)}")

        return contracts

    @retry_on_error(max_retries=3)
    def _search_by_keyword(self, keyword: str) -> List[Dict]:
        """Search for contracts by keyword in description"""
        self.logger.info(f"Searching contracts for keyword: {keyword}")

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * self.years_back)

        # Build search payload with REQUIRED fields per USASpending API v2 spec
        payload = {
            "filters": {
                "award_type_codes": ["A", "B", "C", "D"],  # REQUIRED: Purchase Orders, Delivery Orders, Definitive Contracts
                "keywords": [keyword],
                "time_period": [{
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d")
                }]
            },
            "fields": [  # REQUIRED: Specify which columns to return
                "Award ID",
                "Recipient Name",
                "Award Amount",
                "Start Date",
                "End Date",
                "Description",
                "Awarding Agency",
                "Awarding Sub Agency",
                "Award Type"
            ],
            "limit": 100,
            "page": 1
        }

        contracts = []
        try:
            response = self.session.post(
                f"{self.USA_SPENDING_API}/search/spending_by_award/",
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            results = data.get('results', [])

            for result in results:
                contract = self._parse_contract_result(result, f"keyword:{keyword}")
                contracts.append(contract)

            self.logger.info(f"Found {len(contracts)} contracts for keyword '{keyword}'")

        except Exception as e:
            self.logger.error(f"Failed to search for keyword '{keyword}': {str(e)}")

        return contracts

    def _parse_contract_result(self, result: Dict, search_term: str) -> Dict:
        """Parse contract result from API (uses field names from fields array in payload)"""
        # When using 'fields' parameter, API returns exactly those field names as keys
        award_id = result.get('Award ID')

        # Parse Award Amount - handle string values with dollar signs
        award_amount_raw = result.get('Award Amount', 0)
        if isinstance(award_amount_raw, str):
            # Remove $ and commas, convert to float
            award_amount = float(award_amount_raw.replace('$', '').replace(',', '')) if award_amount_raw else 0
        else:
            award_amount = float(award_amount_raw) if award_amount_raw else 0

        return {
            'Award ID': award_id,
            'Award Type': result.get('Award Type'),
            'Recipient Name': result.get('Recipient Name'),
            'Award Amount': award_amount,
            'Start Date': result.get('Start Date'),
            'End Date': result.get('End Date'),
            'Description': result.get('Description'),
            'Awarding Agency': result.get('Awarding Agency'),
            'Awarding Sub-Agency': result.get('Awarding Sub Agency'),
            'Search Term': search_term,
            'URL': f"https://www.usaspending.gov/award/{award_id}" if award_id else None
        }

    def _deduplicate_contracts(self, contracts: List[Dict]) -> List[Dict]:
        """Remove duplicate contracts based on Award ID"""
        seen = set()
        unique = []
        for contract in contracts:
            award_id = contract.get('Award ID')
            if award_id and award_id not in seen:
                seen.add(award_id)
                unique.append(contract)
        return unique

    def _save_contracts(self, contracts: List[Dict]):
        """Save contracts to JSON and CSV"""
        # Save as JSON
        json_file = self.output_dir / "contracts.json"
        with open(json_file, 'w') as f:
            json.dump(contracts, f, indent=2, default=str)
        self.logger.info(f"Saved {len(contracts)} contracts to {json_file}")

        # Save as CSV for easy viewing
        try:
            import pandas as pd
            df = pd.DataFrame(contracts)
            csv_file = self.output_dir / "contracts.csv"
            df.to_csv(csv_file, index=False)
            self.logger.info(f"Saved contracts to {csv_file}")
        except Exception as e:
            self.logger.warning(f"Could not save CSV: {e}")

    def _calculate_stats(self, contracts: List[Dict]):
        """Calculate statistics from contracts"""
        self.stats['total_contracts'] = len(contracts)
        total_value = sum(c.get('Award Amount', 0) for c in contracts)
        self.stats['total_value'] = total_value

        # Count by agency
        agency_counts = {}
        for contract in contracts:
            agency = contract.get('Awarding Agency', 'Unknown')
            agency_counts[agency] = agency_counts.get(agency, 0) + 1

        self.stats['contracts_by_agency'] = agency_counts

    def _save_metadata(self, total_contracts: int):
        """Save metadata and summary"""
        metadata = {
            'download_date': datetime.now().isoformat(),
            'years_back': self.years_back,
            'companies_searched': list(self.companies.values()),
            'keywords_searched': self.keywords,
            'agencies_filtered': self.agencies,
            'min_contract_value': self.min_contract_value,
            'total_contracts': total_contracts,
            'stats': self.stats
        }

        metadata_file = self.output_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)

        self.logger.info(f"Metadata saved to {metadata_file}")

    def _print_summary(self):
        """Print download summary"""
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("GOVERNMENT CONTRACTS DOWNLOAD SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Total Contracts Found: {self.stats['total_contracts']}")
        self.logger.info(f"Total Contract Value: ${self.stats['total_value']:,.2f}")
        self.logger.info(f"Companies Searched: {self.stats['success']}")
        self.logger.info(f"Failed Searches: {self.stats['failed']}")
        self.logger.info(f"Skipped: {self.stats['skipped']}")

        if 'contracts_by_agency' in self.stats:
            self.logger.info("\nContracts by Agency:")
            for agency, count in sorted(self.stats['contracts_by_agency'].items(),
                                       key=lambda x: x[1], reverse=True)[:10]:
                self.logger.info(f"  {agency}: {count}")

        self.logger.info("=" * 60)


def main():
    """Test the downloader standalone"""
    # Test with eVTOL companies
    test_companies = {
        'JOBY': 'Joby Aviation',
        'ACHR': 'Archer Aviation',
        'LILM': 'Lilium'
    }

    test_keywords = ['eVTOL', 'electric VTOL', 'urban air mobility']
    test_agencies = ['DOD', 'NASA', 'FAA']

    output_dir = Path("test_gov_contracts_output")
    downloader = GovernmentContractsDownloader(
        output_dir=output_dir,
        companies=test_companies,
        keywords=test_keywords,
        agencies=test_agencies,
        years_back=5,
        min_contract_value=50000
    )

    results = downloader.download()
    print(f"\nDownload complete! Results: {results}")


if __name__ == "__main__":
    main()
