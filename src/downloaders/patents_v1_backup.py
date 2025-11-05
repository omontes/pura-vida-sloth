"""
Patent Downloader
==================
Downloads patent data from USPTO PatentsView API for hype cycle analysis

Target: 500-1,000 patents per harvest (configurable)
Primary Source: PatentsView REST API (unlimited, free)
Data: Filing dates, grant dates, assignees, claims, citations, abstracts

Hype Cycle Value:
- Innovation velocity (patents filed per quarter)
- Technology maturity (grant rate, citation counts)
- Market competition (assignee diversity)
- Commercial intent (patent family size)
"""

import requests
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from src.utils.logger import setup_logger
from src.utils.config import Config
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.retry_handler import retry_on_error


class PatentDownloader:
    """Download patent data from PatentsView API"""

    # New PatentSearch API (May 2025 - Legacy API discontinued)
    PATENTS_VIEW_API = "https://search.patentsview.org/api/v1/patent/"

    def __init__(self, output_dir: Path, start_date: datetime, end_date: datetime,
                 keywords: List[str] = None, cpc_codes: List[str] = None, limit: int = 1000):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.start_date = start_date
        self.end_date = end_date
        self.keywords = keywords or []
        self.cpc_codes = cpc_codes or []
        self.limit = limit

        self.logger = setup_logger("PatentDownloader", self.output_dir / "patents.log")
        self.session = requests.Session()  # Use simple session
        self.checkpoint = CheckpointManager(self.output_dir, 'patents')

        # Load API key from config
        self.api_key = Config.PATENTSVIEW_API_KEY
        if not self.api_key:
            self.logger.warning("PatentsView API key not set. Please set PATENTSVIEW_API_KEY in .env file")
            self.logger.warning("Get your API key at: https://search.patentsview.org/")

        self.stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total_size': 0,
            'by_type': {
                'granted': 0,
                'pending': 0
            }
        }

        resume_info = self.checkpoint.get_resume_info()
        if resume_info:
            self.logger.info(resume_info)

    def download(self) -> Dict:
        """Main download method"""
        self.logger.info(f"Starting patent download")
        self.logger.info(f"Date range: {self.start_date.date()} to {self.end_date.date()}")
        self.logger.info(f"Keywords: {len(self.keywords)}")
        self.logger.info(f"CPC codes: {len(self.cpc_codes)}")
        self.logger.info(f"Limit: {self.limit} patents")

        # Search patents
        patents = self._search_patents()
        self.logger.info(f"Found {len(patents)} patents to process")

        # Save patent records
        self._save_patents(patents)

        # Save metadata
        self._save_metadata(patents)

        # Finalize checkpoint
        self.checkpoint.finalize()

        # Print summary
        self._print_summary()

        return self.stats

    @retry_on_error(max_retries=3)
    def _search_patents(self) -> List[Dict]:
        """Search patents using PatentSearch API"""
        all_patents = []

        # Build query
        query_dict = self._build_query()

        # PatentSearch API uses offset/size pagination (not page/per_page)
        page_size = 100  # Max per request
        offset = 0

        self.logger.info(f"Searching up to {self.limit} patents...")

        while len(all_patents) < self.limit:
            try:
                # Update pagination
                query_dict["o"]["size"] = min(page_size, self.limit - len(all_patents))
                query_dict["o"]["from"] = offset

                # Convert query to JSON string for URL parameter
                import urllib.parse
                query_json = json.dumps(query_dict["q"])
                fields_json = json.dumps(query_dict["f"])
                options_json = json.dumps(query_dict["o"])
                sort_json = json.dumps(query_dict["s"])

                # Build GET request with query parameters
                params = {
                    "q": query_json,
                    "f": fields_json,
                    "o": options_json,
                    "s": sort_json
                }

                # Add API key header
                headers = {}
                if self.api_key:
                    headers["X-Api-Key"] = self.api_key

                # Make GET request
                response = self.session.get(
                    self.PATENTS_VIEW_API,
                    params=params,
                    headers=headers,
                    timeout=30
                )
                response.raise_for_status()

                data = response.json()

                # New API returns patents in different structure
                if 'patents' in data and data['patents']:
                    patents = data['patents']
                    all_patents.extend(patents)
                    self.logger.debug(f"Retrieved {len(patents)} patents (total: {len(all_patents)})")

                    # Check if we got fewer results than requested (end of results)
                    if len(patents) < page_size:
                        self.logger.info(f"Retrieved all available patents ({len(all_patents)} total)")
                        break

                    offset += len(patents)
                else:
                    self.logger.info(f"No more patents found")
                    break

                time.sleep(1.5)  # Rate limit: 45 req/min = 1.33s between requests

            except Exception as e:
                self.logger.error(f"Error fetching patents at offset {offset}: {e}")
                break

        return all_patents[:self.limit]

    def _build_query(self) -> Dict:
        """Build PatentSearch API query (new format)"""
        # Build date filter using new API format
        date_conditions = []
        date_conditions.append({"_gte": {"patent_date": self.start_date.strftime("%Y-%m-%d")}})
        date_conditions.append({"_lte": {"patent_date": self.end_date.strftime("%Y-%m-%d")}})

        # Build keyword/CPC filter
        or_conditions = []

        # Add keyword searches
        for keyword in self.keywords:
            or_conditions.append({"_text_any": {"patent_title": keyword}})
            or_conditions.append({"_text_any": {"patent_abstract": keyword}})

        # Add CPC code searches
        for cpc_code in self.cpc_codes:
            or_conditions.append({"cpc_subgroup_id": cpc_code})

        # Combine filters
        all_conditions = date_conditions.copy()
        if or_conditions:
            all_conditions.append({"_or": or_conditions})

        query_filter = {"_and": all_conditions} if len(all_conditions) > 1 else all_conditions[0]

        # Build full query (new API format)
        query = {
            "q": query_filter,
            "f": [
                "patent_id",
                "patent_number",
                "patent_title",
                "patent_date",
                "patent_abstract",
                "assignees_at_grant",  # New API field name
                "inventors_at_grant",   # New API field name
                "cpc_current",          # New API field name
                "cited_by_patent_count", # New API field name
                "claims",                # New API field name
                "app_date"
            ],
            "o": {
                "size": 100,  # New API uses "size" not "per_page"
                "from": 0      # New API uses "from" not "page"
            },
            "s": [{"patent_date": "desc"}]  # Most recent first
        }

        return query

    def _save_patents(self, patents: List[Dict]):
        """Save patent records to JSON files"""
        self.logger.info("Saving patent records...")

        # Save all patents in a single JSON file
        patents_file = self.output_dir / "patents.json"

        with open(patents_file, 'w', encoding='utf-8') as f:
            json.dump(patents, f, indent=2, ensure_ascii=False)

        self.stats['success'] = len(patents)
        self.stats['total_size'] = patents_file.stat().st_size

        # Count granted vs pending
        for patent in patents:
            if patent.get('patent_date'):
                self.stats['by_type']['granted'] += 1
            else:
                self.stats['by_type']['pending'] += 1

        self.logger.info(f"Saved {len(patents)} patents to {patents_file}")

    def _save_metadata(self, patents: List[Dict]):
        """Generate and save metadata"""
        # Calculate metrics for hype cycle
        metrics = self._calculate_metrics(patents)

        metadata = {
            'download_date': datetime.now().isoformat(),
            'date_range': {
                'start': self.start_date.isoformat(),
                'end': self.end_date.isoformat()
            },
            'search_params': {
                'keywords': self.keywords,
                'cpc_codes': self.cpc_codes,
                'limit': self.limit
            },
            'total_patents': len(patents),
            'stats': self.stats,
            'metrics': metrics
        }

        metadata_path = self.output_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Metadata saved to {metadata_path}")

    def _calculate_metrics(self, patents: List[Dict]) -> Dict:
        """Calculate patent metrics for hype cycle analysis"""
        from collections import Counter

        if not patents:
            return {}

        # Extract dates
        filing_dates = [p.get('app_date') for p in patents if p.get('app_date')]
        grant_dates = [p.get('patent_date') for p in patents if p.get('patent_date')]

        # Extract assignees
        assignees = []
        for p in patents:
            orgs = p.get('assignees', [])
            if isinstance(orgs, list):
                assignees.extend([org.get('assignee_organization') for org in orgs
                                if org.get('assignee_organization')])
            elif isinstance(orgs, str):
                assignees.append(orgs)

        assignee_counts = Counter(assignees)

        # Extract citations
        citations = [p.get('citedby_patent_count', 0) for p in patents]
        avg_citations = sum(citations) / len(citations) if citations else 0

        # Extract claims
        claims = [p.get('claims_count', 0) for p in patents if p.get('claims_count')]
        avg_claims = sum(claims) / len(claims) if claims else 0

        metrics = {
            'filing_velocity': {
                'total_filings': len(filing_dates),
                'date_range_days': (self.end_date - self.start_date).days,
                'filings_per_month': len(filing_dates) / ((self.end_date - self.start_date).days / 30) if filing_dates else 0
            },
            'grant_rate': {
                'total_granted': len(grant_dates),
                'grant_percentage': (len(grant_dates) / len(patents) * 100) if patents else 0
            },
            'assignee_diversity': {
                'unique_assignees': len(assignee_counts),
                'top_10_assignees': dict(assignee_counts.most_common(10))
            },
            'citation_metrics': {
                'avg_citations': round(avg_citations, 2),
                'max_citations': max(citations) if citations else 0,
                'highly_cited_count': len([c for c in citations if c > 10])
            },
            'claim_metrics': {
                'avg_claims': round(avg_claims, 2),
                'broad_patents': len([c for c in claims if c > 20])  # >20 claims = broad patent
            }
        }

        return metrics

    def _print_summary(self):
        """Print download summary"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("PATENT DOWNLOAD SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Total Patents: {self.stats['success']}")
        self.logger.info(f"Granted: {self.stats['by_type']['granted']}")
        self.logger.info(f"Pending: {self.stats['by_type']['pending']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        self.logger.info(f"Total Size: {self.stats['total_size'] / 1024 / 1024:.2f} MB")
        self.logger.info("=" * 60)

    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'session'):
            self.session.close()


# Example usage
if __name__ == "__main__":
    from datetime import timedelta

    # eVTOL patent search
    output_dir = Path("./data/test_patents")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*2)  # Last 2 years

    keywords = [
        "eVTOL", "electric VTOL", "vertical takeoff landing electric",
        "urban air mobility", "electric vertical takeoff"
    ]

    cpc_codes = [
        "B64C39/02",  # VTOL aircraft
        "B64D27/24",  # Electric aircraft propulsion
    ]

    downloader = PatentDownloader(
        output_dir=output_dir,
        start_date=start_date,
        end_date=end_date,
        keywords=keywords,
        cpc_codes=cpc_codes,
        limit=100  # Test with 100 patents
    )

    results = downloader.download()
    print(f"\nDownloaded {results['success']} patents")
