"""
Citation Tracker
=================
Tracks academic paper citations using OpenAlex API

Target: 500-1,000 papers per harvest (configurable)
Primary Source: OpenAlex API (100k requests/day, free)
Data: Papers, citation counts, citation velocity, influential papers

Hype Cycle Value:
- Research momentum (citation velocity)
- Academic influence (highly cited papers)
- Technology maturity (citation patterns)
- Knowledge progression (publication trends)
"""

import requests
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from collections import Counter
from tqdm import tqdm

from src.utils.logger import setup_logger
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.retry_handler import retry_on_error


class CitationTracker:
    """Track academic citations using OpenAlex"""

    OPENALEX_API = "https://api.openalex.org/works"

    def __init__(self, output_dir: Path, start_date: datetime, end_date: datetime,
                 keywords: List[str], limit: int = 500):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.start_date = start_date
        self.end_date = end_date
        self.keywords = keywords
        self.limit = limit

        self.logger = setup_logger("CitationTracker", self.output_dir / "citations.log")
        self.checkpoint = CheckpointManager(self.output_dir, 'citations')

        self.stats = {
            'success': 0,
            'failed': 0,
            'total_size': 0,
            'papers_tracked': 0
        }

        resume_info = self.checkpoint.get_resume_info()
        if resume_info:
            self.logger.info(resume_info)

    def download(self) -> Dict:
        """Main tracking method"""
        self.logger.info(f"Starting citation tracking")
        self.logger.info(f"Keywords: {self.keywords}")
        self.logger.info(f"Limit: {self.limit} papers")

        # Search papers
        papers = self._search_papers()
        self.logger.info(f"Found {len(papers)} papers")

        # Calculate metrics
        metrics = self._calculate_citation_metrics(papers)

        # Save data
        self._save_papers(papers)
        self._save_metrics(metrics)
        self._save_metadata(papers, metrics)

        # Finalize
        self.checkpoint.finalize()
        self._print_summary()

        return self.stats

    @retry_on_error(max_retries=3)
    def _search_papers(self) -> List[Dict]:
        """Search papers using OpenAlex"""
        all_papers = []

        for keyword in self.keywords:
            if len(all_papers) >= self.limit:
                break

            try:
                params = {
                    'filter': f'title.search:{keyword},from_publication_date:{self.start_date.strftime("%Y-%m-%d")}',
                    'per-page': 100,
                    'sort': 'cited_by_count:desc'
                }

                response = requests.get(self.OPENALEX_API, params=params, timeout=30)
                response.raise_for_status()

                data = response.json()

                if 'results' in data:
                    for work in data['results']:
                        if len(all_papers) >= self.limit:
                            break

                        paper = {
                            'id': work.get('id', ''),
                            'title': work.get('title', ''),
                            'publication_date': work.get('publication_date', ''),
                            'cited_by_count': work.get('cited_by_count', 0),
                            'doi': work.get('doi', ''),
                            'type': work.get('type', ''),
                            'open_access': work.get('open_access', {}).get('is_oa', False),
                            'authors': [a.get('author', {}).get('display_name', '')
                                      for a in work.get('authorships', [])],
                            'institutions': list(set([inst.get('display_name', '')
                                                     for a in work.get('authorships', [])
                                                     for inst in a.get('institutions', [])
                                                     if inst.get('display_name')])),
                            'concepts': [c.get('display_name', '')
                                        for c in work.get('concepts', [])[:5]],
                            'keyword': keyword
                        }

                        all_papers.append(paper)
                        self.stats['papers_tracked'] += 1

                self.logger.debug(f"Keyword '{keyword}': {len(data.get('results', []))} papers")

            except Exception as e:
                self.logger.error(f"Error searching for '{keyword}': {e}")
                continue

        return all_papers[:self.limit]

    def _calculate_citation_metrics(self, papers: List[Dict]) -> Dict:
        """Calculate citation metrics"""
        if not papers:
            return {}

        citations = [p['cited_by_count'] for p in papers]
        total_citations = sum(citations)
        avg_citations = total_citations / len(papers) if papers else 0

        # Identify highly cited papers (top 10%)
        threshold = sorted(citations, reverse=True)[len(citations)//10] if len(citations) >= 10 else max(citations)
        highly_cited = [p for p in papers if p['cited_by_count'] >= threshold]

        # Institution analysis
        all_institutions = []
        for p in papers:
            all_institutions.extend(p['institutions'])
        institution_counts = Counter(all_institutions)

        # Concept/topic analysis
        all_concepts = []
        for p in papers:
            all_concepts.extend(p['concepts'])
        concept_counts = Counter(all_concepts)

        # Publication timeline
        pub_years = [p['publication_date'][:4] for p in papers if p.get('publication_date')]
        year_counts = Counter(pub_years)

        metrics = {
            'total_papers': len(papers),
            'total_citations': total_citations,
            'avg_citations': round(avg_citations, 2),
            'max_citations': max(citations) if citations else 0,
            'highly_cited_count': len(highly_cited),
            'highly_cited_threshold': threshold,
            'top_institutions': dict(institution_counts.most_common(10)),
            'top_concepts': dict(concept_counts.most_common(10)),
            'publication_timeline': dict(sorted(year_counts.items())),
            'open_access_count': len([p for p in papers if p['open_access']]),
            'top_cited_papers': sorted(papers, key=lambda p: p['cited_by_count'], reverse=True)[:10]
        }

        return metrics

    def _save_papers(self, papers: List[Dict]):
        """Save paper data"""
        papers_file = self.output_dir / "papers.json"

        with open(papers_file, 'w', encoding='utf-8') as f:
            json.dump(papers, f, indent=2, ensure_ascii=False)

        self.stats['success'] = len(papers)
        self.stats['total_size'] = papers_file.stat().st_size

        self.logger.info(f"Saved {len(papers)} papers to {papers_file}")

    def _save_metrics(self, metrics: Dict):
        """Save citation metrics"""
        metrics_file = self.output_dir / "citation_metrics.json"

        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

        self.stats['total_size'] += metrics_file.stat().st_size

    def _save_metadata(self, papers: List[Dict], metrics: Dict):
        """Save metadata"""
        metadata = {
            'download_date': datetime.now().isoformat(),
            'date_range': {
                'start': self.start_date.isoformat(),
                'end': self.end_date.isoformat()
            },
            'search_params': {
                'keywords': self.keywords,
                'limit': self.limit
            },
            'total_papers': len(papers),
            'stats': self.stats,
            'metrics_summary': {
                'total_citations': metrics.get('total_citations', 0),
                'avg_citations': metrics.get('avg_citations', 0),
                'highly_cited_count': metrics.get('highly_cited_count', 0)
            }
        }

        metadata_path = self.output_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def _print_summary(self):
        """Print summary"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("CITATION TRACKING SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Papers Tracked: {self.stats['papers_tracked']}")
        self.logger.info(f"Total Size: {self.stats['total_size'] / 1024 / 1024:.2f} MB")
        self.logger.info("=" * 60)


# Example usage
if __name__ == "__main__":
    from datetime import timedelta

    output_dir = Path("./data/test_citations")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*2)

    keywords = ["eVTOL", "urban air mobility", "electric VTOL"]

    tracker = CitationTracker(
        output_dir=output_dir,
        start_date=start_date,
        end_date=end_date,
        keywords=keywords,
        limit=100
    )

    results = tracker.download()
    print(f"\nTracked {results['papers_tracked']} papers")
