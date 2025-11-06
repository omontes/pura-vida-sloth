"""
Lens PDF Downloader - Download PDFs for Top Scholarly Works
============================================================
Downloads PDFs for top N papers selected by composite score (recency + impact).

Selection Strategy:
- Composite Score = 0.5 * recency_score + 0.5 * impact_score
- Recency: Linear scale (newer papers = higher score)
- Impact: Log scale (papers with more references = quality indicator)

Download Strategy (4-Phase Waterfall):
1. Lens Direct: open_access.locations.pdf_urls
2. Unpaywall: DOI → open access PDF lookup
3. ArXiv: ArXiv ID → direct PDF download
4. PubMed Central: PMC ID → free PDF access

Usage:
    python -m src.downloaders.lens_pdf_downloader --limit 50
    python -m src.downloaders.lens_pdf_downloader --test  # 10 papers
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
import time
import requests
import pandas as pd
import numpy as np
from tqdm import tqdm

from src.utils.logger import setup_logger
from src.utils.checkpoint_manager import CheckpointManager


class LensPDFDownloader:
    """
    Download PDFs for top N scholarly works using hybrid multi-source strategy.

    Mandatory Design Patterns:
    1. Pandas Selection - Efficient filtering and composite scoring
    2. Waterfall Strategy - Try multiple sources in priority order
    3. Checkpoint/Resume - Track completed downloads
    4. Rate Limiting - Respect API limits (Unpaywall)
    5. PDF Validation - Check file size and content type
    6. Progress Tracking - tqdm progress bars
    7. Download Report - JSON summary with sources
    """

    # Unpaywall API configuration
    UNPAYWALL_BASE = "https://api.unpaywall.org/v2"
    UNPAYWALL_EMAIL = "research@strategic-intelligence.ai"  # Required by Unpaywall
    UNPAYWALL_RATE_LIMIT = 2  # Seconds between requests

    # PDF validation
    MIN_PDF_SIZE = 100_000  # 100KB minimum

    def __init__(
        self,
        papers_json_path: str,
        output_dir: str,
        limit: int = 50
    ):
        """
        Initialize PDF downloader.

        Args:
            papers_json_path: Path to papers.json from lens_scholarly harvest
            output_dir: Where to save PDFs
            limit: Number of papers to download (default 50)
        """
        self.papers_json_path = Path(papers_json_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.limit = limit

        # Setup logger
        self.logger = setup_logger("LensPDFDownloader", self.output_dir / "pdf_download.log")

        # Checkpoint manager
        self.checkpoint = CheckpointManager(self.output_dir, 'pdf_download')

        # Stats
        self.stats = {
            'total_attempted': 0,
            'successful': 0,
            'failed': 0,
            'by_source': {
                'lens_direct': 0,
                'unpaywall': 0,
                'arxiv': 0,
                'pmc': 0,
                'failed': 0
            },
            'failed_papers': []
        }

        # Load papers
        self.logger.info(f"Loading papers from: {self.papers_json_path}")
        with open(self.papers_json_path, encoding='utf-8') as f:
            self.all_papers = json.load(f)
        self.logger.info(f"Loaded {len(self.all_papers)} papers")

    def download(self) -> Dict[str, Any]:
        """
        Main download orchestration.

        Returns:
            Stats dict with download results
        """
        self.logger.info("=" * 60)
        self.logger.info("LENS PDF DOWNLOADER - Starting")
        self.logger.info("=" * 60)
        self.logger.info(f"Total papers available: {len(self.all_papers)}")
        self.logger.info(f"Target: Top {self.limit} papers")

        # Step 1: Select top papers
        self.logger.info("\n[1/3] Selecting top papers by composite score...")
        selected_papers = self._select_top_papers()
        self.logger.info(f"✓ Selected {len(selected_papers)} papers")

        # Step 2: Download PDFs
        self.logger.info("\n[2/3] Downloading PDFs...")
        self._download_pdfs(selected_papers)

        # Step 3: Generate report
        self.logger.info("\n[3/3] Generating download report...")
        self._generate_report()

        self.logger.info("\n" + "=" * 60)
        self.logger.info("DOWNLOAD COMPLETE")
        self.logger.info("=" * 60)
        self.logger.info(f"Success: {self.stats['successful']}/{self.stats['total_attempted']}")
        self.logger.info(f"Success Rate: {self.stats['successful']/self.stats['total_attempted']*100:.1f}%")
        self.logger.info(f"By Source:")
        for source, count in self.stats['by_source'].items():
            if count > 0:
                self.logger.info(f"  {source}: {count}")

        return {
            'success': self.stats['successful'],
            'total': self.stats['total_attempted'],
            'success_rate': self.stats['successful'] / self.stats['total_attempted'] * 100 if self.stats['total_attempted'] > 0 else 0,
            'by_source': self.stats['by_source']
        }

    def _select_top_papers(self) -> List[Dict]:
        """
        Select top N papers using composite score.

        Composite Score = 0.5 * recency + 0.5 * impact
        - Recency: Linear scale based on publication date
        - Impact: Log scale based on references_count
        """
        # Convert to DataFrame
        df = pd.DataFrame(self.all_papers)

        # Parse dates
        df['date_published'] = pd.to_datetime(df['date_published'], errors='coerce')

        # Filter out papers without dates or references
        df = df.dropna(subset=['date_published', 'references_count'])

        self.logger.info(f"Papers after filtering: {len(df)}")

        # Calculate recency score (0 to 1, newer = higher)
        max_date = df['date_published'].max()
        min_date = df['date_published'].min()
        date_range = (max_date - min_date).days

        if date_range > 0:
            df['recency_score'] = (df['date_published'] - min_date).dt.days / date_range
        else:
            df['recency_score'] = 1.0

        # Calculate impact score (0 to 1, more refs = higher quality)
        max_refs = df['references_count'].max()
        if max_refs > 0:
            df['impact_score'] = np.log1p(df['references_count']) / np.log1p(max_refs)
        else:
            df['impact_score'] = 0.0

        # Composite score (50/50 weighting)
        df['composite_score'] = 0.5 * df['recency_score'] + 0.5 * df['impact_score']

        # Sort and select top N
        top_papers = df.nlargest(self.limit, 'composite_score')

        self.logger.info(f"Selection criteria:")
        self.logger.info(f"  Date range: {min_date.date()} to {max_date.date()}")
        self.logger.info(f"  References range: {top_papers['references_count'].min():.0f} - {top_papers['references_count'].max():.0f}")
        self.logger.info(f"  Composite score range: {top_papers['composite_score'].min():.3f} - {top_papers['composite_score'].max():.3f}")

        return top_papers.to_dict('records')

    def _download_pdfs(self, papers: List[Dict]):
        """Download PDFs for selected papers with progress bar."""
        self.stats['total_attempted'] = len(papers)

        # Progress bar
        with tqdm(total=len(papers), desc="Downloading PDFs", unit="paper") as pbar:
            for paper in papers:
                lens_id = paper['lens_id']

                # Check if already downloaded
                pdf_path = self.output_dir / f"{lens_id}.pdf"
                if pdf_path.exists() and self.checkpoint.is_completed(lens_id):
                    self.logger.debug(f"Skipping {lens_id} (already downloaded)")
                    self.stats['successful'] += 1
                    self.stats['by_source']['lens_direct'] += 1  # Assume it was successful before
                    pbar.update(1)
                    continue

                # Try download
                result = self._download_pdf(paper)

                if result['success']:
                    self.stats['successful'] += 1
                    self.stats['by_source'][result['source']] += 1
                    self.checkpoint.mark_completed(lens_id, metadata={
                        'title': paper.get('title', ''),
                        'source': result['source']
                    })
                    pbar.set_postfix({'success_rate': f"{self.stats['successful']/self.stats['total_attempted']*100:.1f}%"})
                else:
                    self.stats['by_source']['failed'] += 1
                    self.stats['failed_papers'].append({
                        'lens_id': lens_id,
                        'title': paper.get('title', ''),
                        'reason': result.get('reason', 'unknown')
                    })
                    self.checkpoint.mark_failed(lens_id, result.get('reason', 'unknown'))

                pbar.update(1)

    def _download_pdf(self, paper: Dict) -> Dict[str, Any]:
        """
        Waterfall download strategy: Try 4 sources in order.

        Returns:
            {'success': bool, 'source': str, 'reason': str}
        """
        lens_id = paper['lens_id']

        # Phase 1: Lens Direct (open_access.locations.pdf_urls)
        if paper.get('open_access'):
            locations = paper['open_access'].get('locations', {})
            pdf_urls = locations.get('pdf_urls', [])

            for pdf_url in pdf_urls:
                if self._try_download_from_url(pdf_url, lens_id):
                    return {'success': True, 'source': 'lens_direct'}

        # Phase 2: Unpaywall (DOI lookup)
        doi = self._extract_doi(paper.get('external_ids', []))
        if doi:
            unpaywall_result = self._try_unpaywall(doi, lens_id)
            if unpaywall_result:
                return {'success': True, 'source': 'unpaywall'}

        # Phase 3: ArXiv
        arxiv_id = self._extract_arxiv(paper.get('external_ids', []))
        if arxiv_id:
            if self._try_arxiv(arxiv_id, lens_id):
                return {'success': True, 'source': 'arxiv'}

        # Phase 4: PubMed Central
        pmcid = self._extract_pmcid(paper.get('external_ids', []))
        if pmcid:
            if self._try_pmc(pmcid, lens_id):
                return {'success': True, 'source': 'pmc'}

        # All sources failed
        return {'success': False, 'reason': 'no_pdf_source'}

    def _try_download_from_url(self, url: str, lens_id: str) -> bool:
        """Download PDF from URL with validation."""
        try:
            response = requests.get(
                url,
                timeout=30,
                stream=True,
                headers={'User-Agent': 'Mozilla/5.0 (Strategic Intelligence Harvester/1.0)'}
            )

            if response.status_code == 200:
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                if 'pdf' not in content_type and 'octet-stream' not in content_type:
                    self.logger.debug(f"Not a PDF: {content_type}")
                    return False

                # Save PDF
                pdf_path = self.output_dir / f"{lens_id}.pdf"
                with open(pdf_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                # Validate size
                file_size = pdf_path.stat().st_size
                if file_size < self.MIN_PDF_SIZE:
                    self.logger.debug(f"PDF too small ({file_size} bytes)")
                    pdf_path.unlink()
                    return False

                self.logger.info(f"✓ {lens_id} ({file_size/1024/1024:.2f} MB)")
                return True

        except Exception as e:
            self.logger.debug(f"Download failed: {e}")
            return False

        return False

    def _try_unpaywall(self, doi: str, lens_id: str) -> bool:
        """Query Unpaywall API for open access PDF."""
        try:
            url = f"{self.UNPAYWALL_BASE}/{doi}?email={self.UNPAYWALL_EMAIL}"
            response = requests.get(url, timeout=10)

            if response.ok:
                data = response.json()
                best_oa = data.get('best_oa_location', {})
                pdf_url = best_oa.get('url_for_pdf')

                if pdf_url:
                    # Rate limiting
                    time.sleep(self.UNPAYWALL_RATE_LIMIT)
                    return self._try_download_from_url(pdf_url, lens_id)

            # Rate limiting even on failure
            time.sleep(self.UNPAYWALL_RATE_LIMIT)

        except Exception as e:
            self.logger.debug(f"Unpaywall failed for {doi}: {e}")

        return False

    def _try_arxiv(self, arxiv_id: str, lens_id: str) -> bool:
        """Download PDF from ArXiv."""
        # ArXiv PDF URL pattern
        arxiv_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        return self._try_download_from_url(arxiv_url, lens_id)

    def _try_pmc(self, pmcid: str, lens_id: str) -> bool:
        """Download PDF from PubMed Central."""
        # Remove PMC prefix if present
        pmcid_clean = pmcid.replace('PMC', '').replace('pmc', '')
        pmc_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid_clean}/pdf/"
        return self._try_download_from_url(pmc_url, lens_id)

    def _extract_doi(self, external_ids: List[Dict]) -> Optional[str]:
        """Extract DOI from external_ids array."""
        for ext_id in external_ids:
            if ext_id.get('type') == 'doi':
                return ext_id.get('value')
        return None

    def _extract_arxiv(self, external_ids: List[Dict]) -> Optional[str]:
        """Extract ArXiv ID from external_ids array."""
        for ext_id in external_ids:
            if ext_id.get('type') == 'arxiv':
                return ext_id.get('value')
        return None

    def _extract_pmcid(self, external_ids: List[Dict]) -> Optional[str]:
        """Extract PMC ID from external_ids array."""
        for ext_id in external_ids:
            if ext_id.get('type') in ['pmcid', 'pmc']:
                return ext_id.get('value')
        return None

    def _generate_report(self):
        """Generate download report JSON."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'papers_json': str(self.papers_json_path),
            'output_dir': str(self.output_dir),
            'limit': self.limit,
            'total_attempted': self.stats['total_attempted'],
            'successful': self.stats['successful'],
            'failed': len(self.stats['failed_papers']),
            'success_rate': self.stats['successful'] / self.stats['total_attempted'] * 100 if self.stats['total_attempted'] > 0 else 0,
            'by_source': self.stats['by_source'],
            'failed_papers': self.stats['failed_papers'][:10]  # Limit to first 10
        }

        report_path = self.output_dir / "pdf_download_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Report saved to: {report_path}")


# Standalone execution
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Download PDFs for top scholarly works',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download top 50 papers
  python -m src.downloaders.lens_pdf_downloader --limit 50

  # Test mode (10 papers)
  python -m src.downloaders.lens_pdf_downloader --test

  # Custom paths
  python -m src.downloaders.lens_pdf_downloader --papers data/custom/papers.json --output pdfs/
        """
    )

    parser.add_argument(
        '--papers',
        default='data/eVTOL/lens_scholarly/papers.json',
        help='Path to papers.json file'
    )

    parser.add_argument(
        '--output',
        default='data/eVTOL/lens_scholarly/pdfs',
        help='Output directory for PDFs'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=50,
        help='Number of papers to download (default: 50)'
    )

    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode: download only 10 papers'
    )

    args = parser.parse_args()

    # Override limit for test mode
    limit = 10 if args.test else args.limit

    print("\n" + "=" * 60)
    print(f" LENS PDF DOWNLOADER - {'TEST' if args.test else 'PRODUCTION'} MODE")
    print("=" * 60)
    print(f"Papers JSON: {args.papers}")
    print(f"Output Dir: {args.output}")
    print(f"Limit: {limit}")
    print("=" * 60 + "\n")

    # Initialize and run downloader
    downloader = LensPDFDownloader(
        papers_json_path=args.papers,
        output_dir=args.output,
        limit=limit
    )

    results = downloader.download()

    print("\n" + "=" * 60)
    print(" DOWNLOAD COMPLETE")
    print("=" * 60)
    print(f"Success: {results['success']}/{results['total']}")
    print(f"Success Rate: {results['success_rate']:.1f}%")
    print(f"\nBy Source:")
    for source, count in results['by_source'].items():
        if count > 0:
            print(f"  {source}: {count}")
    print("=" * 60 + "\n")
