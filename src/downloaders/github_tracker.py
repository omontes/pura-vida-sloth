"""
GitHub Activity Tracker
========================
Tracks GitHub repository activity for hype cycle analysis

Target: 50-100 repositories per harvest (configurable)
Primary Source: GitHub REST API v3 (5,000 req/hr with token)
Data: Stars, forks, commits, contributors, languages, activity trends

Hype Cycle Value:
- Developer adoption (star growth, fork count)
- Community momentum (contributor growth, commit frequency)
- Technology maturity (stable APIs, production-ready code)
- Language ecosystem (diversity of implementations)
"""

import requests
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import Counter
from tqdm import tqdm

from src.utils.logger import setup_logger
from src.utils.config import Config
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.retry_handler import retry_on_error


class GitHubTracker:
    """Track GitHub repository activity and metrics"""

    GITHUB_API_BASE = "https://api.github.com"

    def __init__(self, output_dir: Path, keywords: List[str], limit: int = 100,
                 min_stars: int = 5, github_token: str = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.keywords = keywords
        self.limit = limit
        self.min_stars = min_stars
        self.github_token = github_token or Config.GITHUB_TOKEN if hasattr(Config, 'GITHUB_TOKEN') else None

        self.logger = setup_logger("GitHubTracker", self.output_dir / "github.log")
        self.checkpoint = CheckpointManager(self.output_dir, 'github')

        # Setup session with authentication
        self.session = requests.Session()
        if self.github_token:
            self.session.headers.update({
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            })
        else:
            self.logger.warning("No GitHub token provided - rate limited to 60 requests/hour")
            self.session.headers.update({
                'Accept': 'application/vnd.github.v3+json'
            })

        self.stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total_size': 0,
            'repositories_tracked': 0
        }

        resume_info = self.checkpoint.get_resume_info()
        if resume_info:
            self.logger.info(resume_info)

    def download(self) -> Dict:
        """Main tracking method"""
        self.logger.info(f"Starting GitHub activity tracking")
        self.logger.info(f"Keywords: {self.keywords}")
        self.logger.info(f"Limit: {self.limit} repositories")
        self.logger.info(f"Min stars: {self.min_stars}")

        # Search repositories
        repositories = self._search_repositories()
        self.logger.info(f"Found {len(repositories)} repositories")

        # Get detailed metrics for each repository
        detailed_repos = self._get_repository_metrics(repositories)

        # Calculate aggregate metrics
        aggregate_metrics = self._calculate_aggregate_metrics(detailed_repos)

        # Save data
        self._save_repositories(detailed_repos)
        self._save_metrics(aggregate_metrics)
        self._save_metadata(detailed_repos, aggregate_metrics)

        # Finalize checkpoint
        self.checkpoint.finalize()

        # Print summary
        self._print_summary()

        return self.stats

    @retry_on_error(max_retries=3)
    def _search_repositories(self) -> List[Dict]:
        """Search GitHub repositories by keywords"""
        all_repos = []
        seen_repos = set()

        for keyword in self.keywords:
            self.logger.info(f"Searching for keyword: '{keyword}'")

            try:
                # Search query
                url = f"{self.GITHUB_API_BASE}/search/repositories"
                params = {
                    'q': f'{keyword} stars:>={self.min_stars}',
                    'sort': 'stars',
                    'order': 'desc',
                    'per_page': min(100, self.limit)
                }

                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()

                data = response.json()

                if 'items' in data:
                    for repo in data['items']:
                        repo_id = repo['id']
                        if repo_id not in seen_repos:
                            seen_repos.add(repo_id)
                            all_repos.append(repo)

                            if len(all_repos) >= self.limit:
                                break

                self.logger.debug(f"Found {len(data.get('items', []))} repos for '{keyword}'")
                time.sleep(0.5)  # Rate limiting

                if len(all_repos) >= self.limit:
                    break

            except Exception as e:
                self.logger.error(f"Error searching for '{keyword}': {e}")
                continue

        return all_repos[:self.limit]

    def _get_repository_metrics(self, repositories: List[Dict]) -> List[Dict]:
        """Get detailed metrics for each repository"""
        detailed_repos = []

        self.logger.info("Fetching detailed metrics for repositories...")

        for repo in tqdm(repositories, desc="Fetching repo metrics"):
            try:
                owner = repo['owner']['login']
                name = repo['name']

                # Get additional metrics
                metrics = self._get_repo_details(owner, name)

                # Combine basic + detailed info
                repo_data = {
                    'id': repo['id'],
                    'name': repo['full_name'],
                    'owner': owner,
                    'description': repo.get('description', ''),
                    'url': repo['html_url'],
                    'created_at': repo['created_at'],
                    'updated_at': repo['updated_at'],
                    'pushed_at': repo.get('pushed_at'),
                    'language': repo.get('language'),
                    'stars': repo['stargazers_count'],
                    'forks': repo['forks_count'],
                    'watchers': repo['watchers_count'],
                    'open_issues': repo['open_issues_count'],
                    'size': repo['size'],
                    'topics': repo.get('topics', []),
                    'license': repo.get('license', {}).get('name') if repo.get('license') else None,
                    'metrics': metrics
                }

                detailed_repos.append(repo_data)
                self.stats['repositories_tracked'] += 1

                time.sleep(0.3)  # Rate limiting

            except Exception as e:
                self.logger.error(f"Error processing {repo.get('full_name')}: {e}")
                self.stats['failed'] += 1
                continue

        return detailed_repos

    @retry_on_error(max_retries=2)
    def _get_repo_details(self, owner: str, repo: str) -> Dict:
        """Get detailed repository statistics"""
        metrics = {}

        try:
            # Get repository details
            url = f"{self.GITHUB_API_BASE}/repos/{owner}/{repo}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            repo_data = response.json()

            # Get commit activity (last year, weekly)
            try:
                commit_url = f"{self.GITHUB_API_BASE}/repos/{owner}/{repo}/stats/commit_activity"
                commit_response = self.session.get(commit_url, timeout=30)
                if commit_response.status_code == 200:
                    commit_activity = commit_response.json()
                    if commit_activity:
                        total_commits = sum(week['total'] for week in commit_activity)
                        recent_commits = sum(week['total'] for week in commit_activity[-4:])  # Last month
                        metrics['commit_activity'] = {
                            'total_last_year': total_commits,
                            'last_month': recent_commits,
                            'weekly_average': total_commits / 52 if commit_activity else 0
                        }
                time.sleep(0.2)
            except:
                pass

            # Get contributor count
            try:
                contributors_url = f"{self.GITHUB_API_BASE}/repos/{owner}/{repo}/contributors"
                contrib_response = self.session.get(contributors_url, params={'per_page': 1}, timeout=30)
                if contrib_response.status_code == 200:
                    # GitHub returns total count in Link header
                    link_header = contrib_response.headers.get('Link', '')
                    if 'last' in link_header:
                        # Parse last page number
                        import re
                        match = re.search(r'page=(\d+)>; rel="last"', link_header)
                        if match:
                            metrics['contributor_count'] = int(match.group(1))
                    else:
                        contrib_data = contrib_response.json()
                        metrics['contributor_count'] = len(contrib_data)
                time.sleep(0.2)
            except:
                pass

            # Calculate activity score
            days_since_update = (datetime.now() - datetime.fromisoformat(repo_data['updated_at'].replace('Z', '+00:00'))).days
            metrics['days_since_last_update'] = days_since_update
            metrics['is_active'] = days_since_update < 30

            # Calculate popularity score
            metrics['popularity_score'] = (
                repo_data['stargazers_count'] * 1.0 +
                repo_data['forks_count'] * 0.5 +
                repo_data['watchers_count'] * 0.3
            )

        except Exception as e:
            self.logger.debug(f"Could not fetch all metrics for {owner}/{repo}: {e}")

        return metrics

    def _calculate_aggregate_metrics(self, repositories: List[Dict]) -> Dict:
        """Calculate aggregate metrics across all repositories"""
        if not repositories:
            return {}

        total_stars = sum(r['stars'] for r in repositories)
        total_forks = sum(r['forks'] for r in repositories)
        total_watchers = sum(r['watchers'] for r in repositories)

        # Language distribution
        languages = [r['language'] for r in repositories if r['language']]
        language_counts = Counter(languages)

        # Topic distribution
        all_topics = []
        for r in repositories:
            all_topics.extend(r.get('topics', []))
        topic_counts = Counter(all_topics)

        # Activity analysis
        active_repos = len([r for r in repositories if r.get('metrics', {}).get('is_active', False)])

        # Creation timeline
        creation_dates = [r['created_at'][:7] for r in repositories]  # YYYY-MM
        creation_timeline = Counter(creation_dates)

        aggregate = {
            'total_repositories': len(repositories),
            'total_stars': total_stars,
            'total_forks': total_forks,
            'total_watchers': total_watchers,
            'avg_stars': round(total_stars / len(repositories), 2),
            'avg_forks': round(total_forks / len(repositories), 2),
            'active_repositories': active_repos,
            'activity_rate': round((active_repos / len(repositories)) * 100, 2),
            'language_distribution': dict(language_counts.most_common(10)),
            'top_topics': dict(topic_counts.most_common(10)),
            'creation_timeline': dict(sorted(creation_timeline.items())),
            'top_repositories': sorted(
                repositories,
                key=lambda r: r.get('metrics', {}).get('popularity_score', 0),
                reverse=True
            )[:10]
        }

        return aggregate

    def _save_repositories(self, repositories: List[Dict]):
        """Save repository data"""
        repos_file = self.output_dir / "repositories.json"
        with open(repos_file, 'w', encoding='utf-8') as f:
            json.dump(repositories, f, indent=2, ensure_ascii=False)

        self.stats['success'] = len(repositories)
        self.stats['total_size'] += repos_file.stat().st_size

        self.logger.info(f"Saved {len(repositories)} repositories to {repos_file}")

    def _save_metrics(self, metrics: Dict):
        """Save aggregate metrics"""
        metrics_file = self.output_dir / "metrics_aggregate.json"
        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

        self.stats['total_size'] += metrics_file.stat().st_size

        self.logger.info(f"Saved aggregate metrics to {metrics_file}")

    def _save_metadata(self, repositories: List[Dict], aggregate_metrics: Dict):
        """Save metadata"""
        metadata = {
            'download_date': datetime.now().isoformat(),
            'search_params': {
                'keywords': self.keywords,
                'limit': self.limit,
                'min_stars': self.min_stars
            },
            'total_repositories': len(repositories),
            'stats': self.stats,
            'aggregate_metrics': aggregate_metrics
        }

        metadata_path = self.output_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Metadata saved to {metadata_path}")

    def _print_summary(self):
        """Print summary"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("GITHUB TRACKING SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Repositories Tracked: {self.stats['repositories_tracked']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        self.logger.info(f"Total Size: {self.stats['total_size'] / 1024 / 1024:.2f} MB")
        self.logger.info("=" * 60)

    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'session'):
            self.session.close()


# Example usage
if __name__ == "__main__":
    output_dir = Path("./data/test_github")

    keywords = [
        "eVTOL",
        "electric VTOL",
        "urban air mobility",
        "flying taxi"
    ]

    tracker = GitHubTracker(
        output_dir=output_dir,
        keywords=keywords,
        limit=50,
        min_stars=5
    )

    results = tracker.download()
    print(f"\nTracked {results['repositories_tracked']} repositories")
