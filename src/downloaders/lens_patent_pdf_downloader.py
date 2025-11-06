"""
Lens Patent PDF Downloader - Download PDFs for Top Patents
==========================================================
Downloads PDFs for top N patents selected by composite score (recency + family size + citations).

Selection Strategy:
- Composite Score = 0.4 * recency + 0.3 * family_size + 0.3 * forward_citations
- Recency: Linear scale (newer = higher score)
- Family Size: Log scale (larger families = more strategic value)
- Forward Citations: Log scale (more citations = higher impact)

Download Strategy (2-Phase Waterfall):
1. USPTO: jurisdiction == 'US' → construct USPTO PDF URL
2. EPO: jurisdiction in EPO_JURISDICTIONS → construct EPO PDF URL

Usage:
    python -m src.downloaders.lens_patent_pdf_downloader --limit 200
    python -m src.downloaders.lens_patent_pdf_downloader --test  # 10 patents

Expected Success Rate: 60-75% (US/EP patents only)
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import json
import requests
import time
import pandas as pd
import numpy as np
from tqdm import tqdm

from src.utils.logger import setup_logger


class LensPatentPDFDownloader:
    """
    Download PDFs for top N patents using jurisdiction-specific URL construction.

    Supports:
    - US patents: USPTO Image Database
    - EP patents: EPO Publication Server
    """

    # USPTO PDF URL patterns
    USPTO_PDF_BASE = "https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf"

    # EPO PDF URL patterns
    EPO_PDF_BASE = "https://data.epo.org/publication-server/pdf-document"

    # EPO member states (for jurisdiction filtering)
    EPO_JURISDICTIONS = [
        'EP', 'AT', 'BE', 'BG', 'CH', 'CY', 'CZ', 'DE', 'DK',
        'EE', 'ES', 'FI', 'FR', 'GB', 'GR', 'HR', 'HU', 'IE',
        'IS', 'IT', 'LI', 'LT', 'LU', 'LV', 'MC', 'MK', 'MT',
        'NL', 'NO', 'PL', 'PT', 'RO', 'RS', 'SE', 'SI', 'SK', 'TR'
    ]

    def __init__(
        self,
        patents_json_path: str = "data/eVTOL/lens_patents/patents.json",
        output_dir: str = "data/eVTOL/lens_patents/pdfs",
        limit: int = 200
    ):
        """
        Initialize Patent PDF downloader.

        Args:
            patents_json_path: Path to patents.json file from lens_patents harvester
            output_dir: Directory to save downloaded PDFs
            limit: Number of top patents to download
        """
        self.patents_json_path = Path(patents_json_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.limit = limit

        self.logger = setup_logger("PatentPDFDownloader", self.output_dir / "pdf_download.log")

        # Session for HTTP requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # Statistics
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'by_source': {
                'uspto': 0,
                'epo': 0,
                'failed': 0
            },
            'failed_patents': []
        }

        # Load patents
        self.all_patents = []
        self._load_patents()

    def _load_patents(self):
        """Load patents from JSON file"""
        self.logger.info(f"Loading patents from: {self.patents_json_path}")

        if not self.patents_json_path.exists():
            raise FileNotFoundError(f"Patents file not found: {self.patents_json_path}")

        with open(self.patents_json_path, 'r', encoding='utf-8') as f:
            self.all_patents = json.load(f)

        self.logger.info(f"Loaded {len(self.all_patents)} patents")

    def download(self) -> Dict[str, Any]:
        """
        Main download orchestration.

        Steps:
        1. Select top N patents by composite score
        2. Download PDFs with waterfall strategy
        3. Generate download report

        Returns:
            Statistics dictionary with success/failure counts
        """
        self.logger.info("=" * 60)
        self.logger.info("LENS PDF DOWNLOADER - Starting")
        self.logger.info("=" * 60)
        self.logger.info(f"Total patents available: {len(self.all_patents)}")
        self.logger.info(f"Target: Top {self.limit} patents")
        self.logger.info("")

        # Step 1: Select top patents
        self.logger.info("[1/3] Selecting top patents by composite score...")
        selected_patents = self._select_top_patents()

        if not selected_patents:
            self.logger.error("No patents selected (empty list after filtering)")
            return self.stats

        self.stats['total'] = len(selected_patents)
        self.logger.info(f"✓ Selected {len(selected_patents)} patents")
        self.logger.info("")

        # Step 2: Download PDFs
        self.logger.info("[2/3] Downloading PDFs...")
        self._download_pdfs(selected_patents)

        # Step 3: Generate report
        self.logger.info("")
        self.logger.info("[3/3] Generating download report...")
        self._generate_report()

        self._print_summary()

        return self.stats

    def _select_top_patents(self) -> List[Dict]:
        """
        Select top N patents using composite score.

        Score = 0.4 * recency + 0.3 * family_size + 0.3 * forward_citations

        Pre-filters:
        - English language only (lang == 'en')
        - US or EP jurisdictions only (for PDF access)
        - Granted patents preferred (higher quality)

        Returns:
            List of selected patent dictionaries
        """
        df = pd.DataFrame(self.all_patents)

        # Pre-filter: Only English-language patents from US/EP
        df_filtered = df[
            (df['lang'].isin(['en', 'EN', ''])) &  # Empty = likely English
            (df['jurisdiction'].isin(['US'] + self.EPO_JURISDICTIONS))
        ].copy()

        if df_filtered.empty:
            self.logger.error("No patents match filtering criteria (English + US/EP)")
            return []

        self.logger.info(f"Patents after filtering: {len(df_filtered)}")

        # Convert date to datetime
        df_filtered['publication_date_dt'] = pd.to_datetime(
            df_filtered['publication_date'],
            errors='coerce'
        )

        # Remove patents with invalid dates
        df_filtered = df_filtered[df_filtered['publication_date_dt'].notna()].copy()

        # Calculate recency score (0-1, newer = higher)
        max_date = df_filtered['publication_date_dt'].max()
        min_date = df_filtered['publication_date_dt'].min()
        date_range_days = (max_date - min_date).days

        if date_range_days > 0:
            df_filtered['recency_score'] = (
                (df_filtered['publication_date_dt'] - min_date).dt.days / date_range_days
            )
        else:
            df_filtered['recency_score'] = 1.0

        # Calculate family size score (0-1, log scale)
        max_family = df_filtered['simple_family_size'].max()
        if max_family > 0:
            df_filtered['family_score'] = (
                np.log1p(df_filtered['simple_family_size']) / np.log1p(max_family)
            )
        else:
            df_filtered['family_score'] = 0.0

        # Calculate citation score (0-1, log scale - forward citations)
        max_citations = df_filtered['forward_citation_count'].max()
        if max_citations > 0:
            df_filtered['citation_score'] = (
                np.log1p(df_filtered['forward_citation_count']) / np.log1p(max_citations)
            )
        else:
            df_filtered['citation_score'] = 0.0

        # Composite score (weighted)
        df_filtered['composite_score'] = (
            0.4 * df_filtered['recency_score'] +
            0.3 * df_filtered['family_score'] +
            0.3 * df_filtered['citation_score']
        )

        # Select top N
        top_patents = df_filtered.nlargest(self.limit, 'composite_score')

        # Log selection criteria
        self.logger.info(f"Selection criteria:")
        self.logger.info(f"  Date range: {min_date.date()} to {max_date.date()}")
        self.logger.info(f"  Family size range: {df_filtered['simple_family_size'].min():.0f} - {df_filtered['simple_family_size'].max():.0f}")
        self.logger.info(f"  Forward citations range: {df_filtered['forward_citation_count'].min():.0f} - {df_filtered['forward_citation_count'].max():.0f}")
        self.logger.info(f"  Composite score range: {top_patents['composite_score'].min():.3f} - {top_patents['composite_score'].max():.3f}")

        # Log jurisdiction distribution
        us_count = len(top_patents[top_patents['jurisdiction'] == 'US'])
        ep_count = len(top_patents[top_patents['jurisdiction'].isin(self.EPO_JURISDICTIONS)])
        self.logger.info(f"  US patents: {us_count}")
        self.logger.info(f"  EP patents: {ep_count}")

        return top_patents.to_dict('records')

    def _download_pdfs(self, patents: List[Dict]):
        """Download PDFs for selected patents with progress bar"""

        # Use tqdm for progress tracking
        with tqdm(total=len(patents), desc="Downloading PDFs", unit="patent") as pbar:
            for patent in patents:
                result = self._download_pdf(patent)

                if result['success']:
                    self.stats['success'] += 1
                    self.stats['by_source'][result['source']] += 1
                    pbar.set_postfix(success_rate=f"{100*self.stats['success']/self.stats['total']:.1f}%")
                else:
                    self.stats['failed'] += 1
                    self.stats['by_source']['failed'] += 1
                    self.stats['failed_patents'].append({
                        'lens_id': patent['lens_id'],
                        'patent_number': patent['patent_number'],
                        'jurisdiction': patent['jurisdiction'],
                        'reason': result.get('reason', 'unknown')
                    })

                pbar.update(1)

                # Rate limiting: be respectful to patent offices
                time.sleep(1)  # 1 second delay between downloads

    def _download_pdf(self, patent: Dict) -> Dict[str, Any]:
        """
        Waterfall download strategy: US → EP

        Returns:
            {'success': bool, 'source': str, 'reason': str}
        """
        jurisdiction = patent.get('jurisdiction', '')
        doc_number = patent.get('patent_number', '')
        kind = patent.get('kind', '')
        lens_id = patent.get('lens_id', '')

        if not doc_number or not lens_id:
            return {'success': False, 'reason': 'missing_identifiers'}

        # Phase 1: USPTO (US patents)
        if jurisdiction == 'US':
            url = self._construct_uspto_url(doc_number, kind)
            if self._try_download_from_url(url, lens_id):
                return {'success': True, 'source': 'uspto'}

        # Phase 2: EPO (European patents)
        elif jurisdiction in self.EPO_JURISDICTIONS:
            url = self._construct_epo_url(doc_number, kind, jurisdiction)
            if self._try_download_from_url(url, lens_id):
                return {'success': True, 'source': 'epo'}

        return {'success': False, 'reason': f'unsupported_jurisdiction_{jurisdiction}'}

    def _construct_uspto_url(self, doc_number: str, kind: str) -> str:
        """
        Construct USPTO PDF URL from publication number.

        Examples:
        - US20130227762A1 → https://...downloadPdf/20130227762
        - US9234567B2 → https://...downloadPdf/9234567
        - USD123456S1 → https://...downloadPdf/D123456
        """
        # Remove 'US' prefix
        number = doc_number.replace('US', '')

        # Handle design patents (start with 'D')
        if number.startswith('D'):
            return f"{self.USPTO_PDF_BASE}/{number}"

        # Handle plant patents (start with 'PP')
        if number.startswith('PP'):
            return f"{self.USPTO_PDF_BASE}/{number}"

        # Handle utility patents and applications
        # Remove kind code suffix if present (A1, B2, etc.)
        if kind:
            number_clean = number.replace(kind, '')
        else:
            number_clean = number

        return f"{self.USPTO_PDF_BASE}/{number_clean}"

    def _construct_epo_url(self, doc_number: str, kind: str, jurisdiction: str) -> str:
        """
        Construct EPO PDF URL from publication number.

        Example:
        - EP2471949 + A1 + EP → https://data.epo.org/publication-server/pdf-document?pn=EP2471949.A1&cc=EP
        """
        return f"{self.EPO_PDF_BASE}?pn={doc_number}.{kind}&cc={jurisdiction}"

    def _try_download_from_url(self, url: str, lens_id: str) -> bool:
        """
        Download PDF from URL with validation.

        Returns:
            True if download successful, False otherwise
        """
        try:
            response = self.session.get(url, timeout=30, stream=True)

            if response.status_code == 200:
                # Validate content type
                content_type = response.headers.get('content-type', '').lower()
                if 'pdf' not in content_type and 'octet-stream' not in content_type:
                    self.logger.debug(f"  Invalid content type: {content_type}")
                    return False

                # Save PDF
                pdf_path = self.output_dir / f"{lens_id}.pdf"
                with open(pdf_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                # Validate size (patents are typically larger than papers)
                file_size = pdf_path.stat().st_size
                if file_size < 50_000:  # 50KB minimum (patents have drawings)
                    pdf_path.unlink()
                    self.logger.debug(f"  File too small: {file_size} bytes")
                    return False

                self.logger.info(f"✓ {lens_id} ({file_size/1024/1024:.2f} MB)")
                return True
            else:
                self.logger.debug(f"  HTTP {response.status_code} for {lens_id}")

        except Exception as e:
            self.logger.debug(f"  Download failed for {lens_id}: {e}")

        return False

    def _generate_report(self):
        """Generate JSON report of download results"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'patents_json': str(self.patents_json_path),
            'output_dir': str(self.output_dir),
            'limit': self.limit,
            'total_attempted': self.stats['total'],
            'successful': self.stats['success'],
            'failed': self.stats['failed'],
            'success_rate': round(100 * self.stats['success'] / self.stats['total'], 1) if self.stats['total'] > 0 else 0,
            'by_source': self.stats['by_source'],
            'failed_patents': self.stats['failed_patents']
        }

        report_path = self.output_dir / "pdf_download_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Report saved to: {report_path}")

    def _print_summary(self):
        """Print download summary"""
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("DOWNLOAD COMPLETE")
        self.logger.info("=" * 60)
        self.logger.info(f"Success: {self.stats['success']}/{self.stats['total']}")
        self.logger.info(f"Success Rate: {100*self.stats['success']/self.stats['total']:.1f}%")
        self.logger.info("")
        self.logger.info("By Source:")
        for source, count in self.stats['by_source'].items():
            self.logger.info(f"  {source}: {count}")
        self.logger.info("=" * 60)


def main():
    """Command-line interface"""
    import argparse

    # Print banner
    print("=" * 60)
    print(" LENS PATENT PDF DOWNLOADER - PRODUCTION MODE")
    print("=" * 60)

    parser = argparse.ArgumentParser(
        description='Download PDFs for top patents by composite score'
    )
    parser.add_argument(
        '--patents',
        default='data/eVTOL/lens_patents/patents.json',
        help='Path to patents.json file'
    )
    parser.add_argument(
        '--output',
        default='data/eVTOL/lens_patents/pdfs',
        help='Output directory for PDFs'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=200,
        help='Number of top patents to download (default: 200)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode: download only 10 patents'
    )

    args = parser.parse_args()

    # Test mode overrides limit
    if args.test:
        args.limit = 10
        print("TEST MODE: Downloading 10 patents")

    print(f"Patents JSON: {args.patents}")
    print(f"Output Dir: {args.output}")
    print(f"Limit: {args.limit}")
    print("=" * 60)
    print("\n")

    # Run downloader
    downloader = LensPatentPDFDownloader(
        patents_json_path=args.patents,
        output_dir=args.output,
        limit=args.limit
    )

    results = downloader.download()

    # Final summary
    success_rate = (results['success'] / results['total'] * 100) if results['total'] > 0 else 0
    print("\n")
    print("=" * 60)
    print(" DOWNLOAD COMPLETE")
    print("=" * 60)
    print(f"Success: {results['success']}/{results['total']}")
    print(f"Success Rate: {success_rate:.1f}%")
    print("")
    print("By Source:")
    for source, count in results['by_source'].items():
        print(f"  {source}: {count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
