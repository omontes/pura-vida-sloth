"""
Lens PDF Downloader - DuckDB-Enhanced Intelligent Selection
============================================================
Downloads PDFs for top N scholarly papers using DuckDB composite scoring.

Selection Strategy (DuckDB-Based):
- Composite Score = weighted combination of:
  * 40% LLM relevance score (8.0-9.0)
  * 20% Impact potential (innovation_signals)
  * 20% References count (citation quality)
  * 10% Innovation type (breakthrough > incremental)
  * 10% Recency (publication year)

Download Strategy (4-Phase Waterfall):
1. Lens Direct: open_access.locations.pdf_urls
2. Unpaywall: DOI → open access PDF lookup
3. ArXiv: ArXiv ID → direct PDF download
4. PubMed Central: PMC ID → free PDF access

Usage:
    python -m src.downloaders.lens_pdf_downloader \
        --papers data/eVTOL/lens_scholarly/papers.json \
        --scored-dir data/eVTOL/lens_scholarly/batch_processing \
        --output data/eVTOL/lens_scholarly/pdfs \
        --limit 200
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
import time
import requests
from tqdm import tqdm

from src.utils.logger import setup_logger
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.duckdb_scholarly_analysis import ScholarlyPapersDatabase


class LensPDFDownloader:
    """
    Download PDFs for top N scholarly works using DuckDB composite scoring.

    Mandatory Design Patterns:
    1. DuckDB Analysis - Fast SQL-based composite scoring
    2. Pandas Integration - Efficient data handling
    3. Waterfall Strategy - Try multiple sources in priority order
    4. Checkpoint/Resume - Track completed downloads
    5. Rate Limiting - Respect API limits (Unpaywall)
    6. PDF Validation - Check file size and content type
    7. Progress Tracking - tqdm progress bars
    8. Download Report - JSON summary with sources
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
        scored_papers_dir: str,
        output_dir: str,
        limit: int = 200,
        composite_weighting: Optional[Dict[str, float]] = None
    ):
        """
        Initialize PDF downloader with DuckDB integration.

        Args:
            papers_json_path: Path to papers.json from lens_scholarly harvest
            scored_papers_dir: Path to batch_processing directory with checkpoints
            output_dir: Where to save PDFs
            limit: Number of papers to download (default 200)
            composite_weighting: Custom weights for composite scoring
        """
        self.papers_json_path = Path(papers_json_path)
        self.scored_papers_dir = Path(scored_papers_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.limit = limit
        self.composite_weighting = composite_weighting

        # Setup logger
        self.logger = setup_logger("LensPDFDownloader", self.output_dir / "pdf_download.log")

        # Checkpoint manager
        self.checkpoint = CheckpointManager(self.output_dir, 'pdf_download')

        # Stats
        self.stats = {
            'total_attempted': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'by_source': {
                'lens_direct': 0,
                'unpaywall': 0,
                'arxiv': 0,
                'pmc': 0,
                'existing': 0,
                'failed': 0
            },
            'failed_papers': [],
            'composite_score_stats': {}
        }

        # Initialize DuckDB
        self.logger.info("Initializing DuckDB Scholarly Papers database...")
        self.db = ScholarlyPapersDatabase(
            scored_papers_dir=str(self.scored_papers_dir),
            original_papers_path=str(self.papers_json_path)
        )
        self.db.initialize()

        # Load original papers for PDF URL lookup
        self.logger.info(f"Loading original papers from: {self.papers_json_path}")
        with open(self.papers_json_path, encoding='utf-8') as f:
            self.all_papers = json.load(f)

        # Create lens_id → paper mapping for fast lookup
        self.papers_by_id = {p['lens_id']: p for p in self.all_papers}
        self.logger.info(f"Loaded {len(self.all_papers)} papers for metadata lookup")

    def download(self) -> Dict[str, Any]:
        """
        Main download orchestration with DuckDB composite scoring.

        Returns:
            Stats dict with download results
        """
        self.logger.info("=" * 60)
        self.logger.info("LENS PDF DOWNLOADER - DuckDB Enhanced")
        self.logger.info("=" * 60)
        self.logger.info(f"Target: Top {self.limit} papers by composite score")

        # Step 1: Select top papers using DuckDB
        self.logger.info("\n[1/3] Selecting top papers by DuckDB composite score...")
        selected_papers = self._select_top_papers_duckdb()
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
        if self.stats['skipped'] > 0:
            self.logger.info(f"Skipped: {self.stats['skipped']} (PDFs already existed)")
            self.logger.info(f"New Downloads: {self.stats['successful'] - self.stats['skipped']}")
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

    def _select_top_papers_duckdb(self) -> List[Dict]:
        """
        Select top N papers using DuckDB composite scoring.

        Uses SQL-based ranking combining:
        - LLM relevance score (40%)
        - Impact potential (20%)
        - References count (20%)
        - Innovation type (10%)
        - Recency (10%)
        """
        # Query top papers from DuckDB
        top_papers = self.db.get_top_papers_by_composite_score(
            limit=self.limit,
            min_relevance_score=8.0,  # Only LLM-validated papers
            weighting=self.composite_weighting
        )

        # Calculate composite score statistics
        if top_papers:
            scores = [p['composite_score'] for p in top_papers]
            self.stats['composite_score_stats'] = {
                'min': min(scores),
                'max': max(scores),
                'mean': sum(scores) / len(scores),
                'median': sorted(scores)[len(scores) // 2]
            }

            self.logger.info(f"Composite Score Statistics:")
            self.logger.info(f"  Range: {self.stats['composite_score_stats']['min']:.3f} - {self.stats['composite_score_stats']['max']:.3f}")
            self.logger.info(f"  Mean: {self.stats['composite_score_stats']['mean']:.3f}")
            self.logger.info(f"  Median: {self.stats['composite_score_stats']['median']:.3f}")

            # Show breakdown of top paper
            if top_papers:
                top = top_papers[0]
                self.logger.info(f"\nTop Paper:")
                self.logger.info(f"  Title: {top['title'][:60]}...")
                self.logger.info(f"  Composite Score: {top['composite_score']:.3f}")
                self.logger.info(f"  Relevance: {top['relevance_score']:.1f} | Impact: {top['impact_potential']}")
                self.logger.info(f"  Innovation: {top['innovation_type']} | Year: {top['year_published']}")

        # Enrich with original paper data (for PDF URLs)
        enriched_papers = []
        for paper in top_papers:
            lens_id = paper['lens_id']
            original = self.papers_by_id.get(lens_id, {})

            enriched = {
                **paper,
                'open_access': original.get('open_access', {}),
                'external_ids': original.get('external_ids', [])
            }
            enriched_papers.append(enriched)

        return enriched_papers

    def _download_pdfs(self, papers: List[Dict]):
        """Download PDFs for selected papers with progress bar."""
        self.stats['total_attempted'] = len(papers)

        # Progress bar
        with tqdm(total=len(papers), desc="Downloading PDFs", unit="paper") as pbar:
            for paper in papers:
                lens_id = paper['lens_id']

                # Check if already downloaded (skip if PDF exists in folder)
                pdf_path = self.output_dir / f"{lens_id}.pdf"
                if pdf_path.exists():
                    # Validate file size (must be > 100KB)
                    file_size = pdf_path.stat().st_size
                    if file_size >= self.MIN_PDF_SIZE:
                        self.logger.info(f"⊘ Skipping {lens_id} (PDF already exists, {file_size/1024/1024:.2f} MB)")
                        self.stats['successful'] += 1
                        self.stats['skipped'] += 1
                        self.stats['by_source']['existing'] += 1
                        # Mark as completed if not already
                        if not self.checkpoint.is_completed(lens_id):
                            self.checkpoint.mark_completed(lens_id, metadata={
                                'title': paper.get('title', ''),
                                'source': 'existing',
                                'composite_score': paper.get('composite_score', 0)
                            })
                        pbar.update(1)
                        continue
                    else:
                        # File too small, delete and re-download
                        self.logger.warning(f"Deleting invalid PDF: {lens_id} ({file_size} bytes)")
                        pdf_path.unlink()

                # Try download
                result = self._download_pdf(paper)

                if result['success']:
                    self.stats['successful'] += 1
                    self.stats['by_source'][result['source']] += 1
                    self.checkpoint.mark_completed(lens_id, metadata={
                        'title': paper.get('title', ''),
                        'source': result['source'],
                        'composite_score': paper.get('composite_score', 0)
                    })
                    pbar.set_postfix({'success_rate': f"{self.stats['successful']/self.stats['total_attempted']*100:.1f}%"})
                else:
                    self.stats['by_source']['failed'] += 1
                    self.stats['failed_papers'].append({
                        'lens_id': lens_id,
                        'title': paper.get('title', ''),
                        'composite_score': paper.get('composite_score', 0),
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
        """Generate enhanced download report JSON with composite score breakdown."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'papers_json': str(self.papers_json_path),
            'scored_papers_dir': str(self.scored_papers_dir),
            'output_dir': str(self.output_dir),
            'limit': self.limit,
            'selection_method': 'DuckDB Composite Scoring',
            'composite_weighting': self.composite_weighting or {
                'relevance': 0.4,
                'impact': 0.2,
                'references': 0.2,
                'innovation': 0.1,
                'recency': 0.1
            },
            'composite_score_stats': self.stats['composite_score_stats'],
            'total_attempted': self.stats['total_attempted'],
            'successful': self.stats['successful'],
            'skipped': self.stats['skipped'],
            'new_downloads': self.stats['successful'] - self.stats['skipped'],
            'failed': len(self.stats['failed_papers']),
            'success_rate': self.stats['successful'] / self.stats['total_attempted'] * 100 if self.stats['total_attempted'] > 0 else 0,
            'by_source': self.stats['by_source'],
            'failed_papers': self.stats['failed_papers'][:20]  # Limit to first 20
        }

        report_path = self.output_dir / "pdf_download_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Report saved to: {report_path}")


# Standalone execution
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Download PDFs for top scholarly works (DuckDB-enhanced)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download top 200 papers (default)
  python -m src.downloaders.lens_pdf_downloader \
      --papers data/eVTOL/lens_scholarly/papers.json \
      --scored-dir data/eVTOL/lens_scholarly/batch_processing \
      --output data/eVTOL/lens_scholarly/pdfs

  # Test mode (10 papers)
  python -m src.downloaders.lens_pdf_downloader \
      --papers data/eVTOL/lens_scholarly/papers.json \
      --scored-dir data/eVTOL/lens_scholarly/batch_processing \
      --output data/eVTOL/lens_scholarly/pdfs \
      --limit 10

  # Custom composite weighting
  python -m src.downloaders.lens_pdf_downloader \
      --papers data/eVTOL/lens_scholarly/papers.json \
      --scored-dir data/eVTOL/lens_scholarly/batch_processing \
      --output data/eVTOL/lens_scholarly/pdfs \
      --limit 50 \
      --weight-relevance 0.5 \
      --weight-impact 0.3
        """
    )

    parser.add_argument(
        '--papers',
        required=True,
        help='Path to papers.json file (original harvest)'
    )

    parser.add_argument(
        '--scored-dir',
        required=True,
        help='Path to batch_processing directory with checkpoints'
    )

    parser.add_argument(
        '--output',
        required=True,
        help='Output directory for PDFs'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=200,
        help='Number of papers to download (default: 200)'
    )

    # Custom composite weighting
    parser.add_argument(
        '--weight-relevance',
        type=float,
        default=0.4,
        help='Weight for relevance score (default: 0.4)'
    )

    parser.add_argument(
        '--weight-impact',
        type=float,
        default=0.2,
        help='Weight for impact potential (default: 0.2)'
    )

    parser.add_argument(
        '--weight-references',
        type=float,
        default=0.2,
        help='Weight for references count (default: 0.2)'
    )

    parser.add_argument(
        '--weight-innovation',
        type=float,
        default=0.1,
        help='Weight for innovation type (default: 0.1)'
    )

    parser.add_argument(
        '--weight-recency',
        type=float,
        default=0.1,
        help='Weight for recency (default: 0.1)'
    )

    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode: download only 10 papers'
    )

    args = parser.parse_args()

    # Override limit for test mode
    limit = 10 if args.test else args.limit

    # Build composite weighting
    composite_weighting = {
        'relevance': args.weight_relevance,
        'impact': args.weight_impact,
        'references': args.weight_references,
        'innovation': args.weight_innovation,
        'recency': args.weight_recency
    }

    # Validate weights sum to 1.0
    weight_sum = sum(composite_weighting.values())
    if abs(weight_sum - 1.0) > 0.01:
        print(f"ERROR: Composite weights must sum to 1.0 (current: {weight_sum:.2f})")
        exit(1)

    print("\n" + "=" * 60)
    print(f" LENS PDF DOWNLOADER - {'TEST' if args.test else 'PRODUCTION'} MODE")
    print("=" * 60)
    print(f"Papers JSON: {args.papers}")
    print(f"Scored Dir: {args.scored_dir}")
    print(f"Output Dir: {args.output}")
    print(f"Limit: {limit}")
    print(f"\nComposite Weighting:")
    for key, value in composite_weighting.items():
        print(f"  {key}: {value:.1%}")
    print("=" * 60 + "\n")

    # Initialize and run downloader
    downloader = LensPDFDownloader(
        papers_json_path=args.papers,
        scored_papers_dir=args.scored_dir,
        output_dir=args.output,
        limit=limit,
        composite_weighting=composite_weighting
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
