"""
Job Market Tracker
==================
Tracks job postings as market adoption signal using Indeed RSS feeds

Target: 200-500 job postings per harvest (configurable)
Primary Source: Indeed RSS feeds (unlimited, free)
Data: Job postings, companies hiring, role types, locations

Hype Cycle Value:
- Market adoption (hiring activity)
- Company growth signals (posting velocity)
- Technology maturity (senior roles vs junior)
- Geographic expansion (location diversity)
"""

import feedparser
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from collections import Counter
from urllib.parse import quote_plus

from src.utils.logger import setup_logger
from src.utils.checkpoint_manager import CheckpointManager


class JobMarketTracker:
    """Track job postings via free job board RSS feeds"""

    # Free job board RSS feeds (Indeed RSS is blocked as of 2025)
    JOB_RSS_FEEDS = {
        'jobicy': 'https://jobicy.com/?feed=job_feed',  # Remote jobs, free, 50 jobs
        'weworkremotely': 'https://weworkremotely.com/remote-jobs.rss'  # Remote jobs, free
    }

    def __init__(self, output_dir: Path, keywords: List[str], limit: int = 500,
                 locations: List[str] = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.keywords = keywords
        self.limit = limit
        self.locations = locations or ["United States"]

        self.logger = setup_logger("JobMarketTracker", self.output_dir / "jobs.log")
        self.checkpoint = CheckpointManager(self.output_dir, 'jobs')

        self.stats = {
            'success': 0,
            'failed': 0,
            'total_size': 0,
            'postings_tracked': 0
        }

        resume_info = self.checkpoint.get_resume_info()
        if resume_info:
            self.logger.info(resume_info)

    def download(self) -> Dict:
        """Main tracking method"""
        self.logger.info(f"Starting job market tracking")
        self.logger.info(f"Keywords: {self.keywords}")
        self.logger.info(f"Limit: {self.limit} postings")

        # Collect job postings from all RSS feeds
        all_postings = []
        for feed_name, feed_url in self.JOB_RSS_FEEDS.items():
            if len(all_postings) >= self.limit:
                break

            postings = self._fetch_jobs_from_feed(feed_url, feed_name)

            # Filter by keywords
            filtered_postings = self._filter_by_keywords(postings)
            all_postings.extend(filtered_postings)
            self.logger.info(f"{feed_name}: {len(filtered_postings)} matching postings")

        # Deduplicate by URL
        unique_postings = self._deduplicate_postings(all_postings)
        unique_postings = unique_postings[:self.limit]

        self.logger.info(f"Total unique postings: {len(unique_postings)}")

        # Calculate hiring trends
        hiring_trends = self._calculate_hiring_trends(unique_postings)

        # Save data
        self._save_postings(unique_postings)
        self._save_trends(hiring_trends)
        self._save_metadata(unique_postings, hiring_trends)

        # Finalize
        self.checkpoint.finalize()
        self._print_summary()

        return self.stats

    def _fetch_jobs_from_feed(self, feed_url: str, feed_name: str) -> List[Dict]:
        """Fetch job postings from an RSS feed"""
        postings = []

        try:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries:
                posting = {
                    'title': entry.get('title', ''),
                    'company': self._extract_company(entry, feed_name),
                    'location': self._extract_location(entry, feed_name),
                    'url': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'description': entry.get('summary', ''),
                    'source': feed_name
                }

                postings.append(posting)

        except Exception as e:
            self.logger.error(f"Error fetching jobs from '{feed_name}': {e}")

        return postings

    def _filter_by_keywords(self, postings: List[Dict]) -> List[Dict]:
        """Filter postings by keywords"""
        if not self.keywords:
            return postings

        filtered = []
        for posting in postings:
            title_lower = posting['title'].lower()
            desc_lower = posting['description'].lower()

            for keyword in self.keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in title_lower or keyword_lower in desc_lower:
                    posting['keyword'] = keyword
                    filtered.append(posting)
                    self.stats['postings_tracked'] += 1
                    break  # Only count each posting once

        return filtered

    def _extract_company(self, entry: Dict, feed_name: str) -> str:
        """Extract company name from job posting"""
        # Try to extract from title (common format: "Job Title at Company Name")
        title = entry.get('title', '')

        if ' at ' in title:
            return title.split(' at ')[-1].strip()
        elif ' - ' in title:
            return title.split(' - ')[-1].strip()
        elif '|' in title:
            return title.split('|')[-1].strip()

        # Try to extract from summary/description
        summary = entry.get('summary', '')
        if 'Company:' in summary:
            parts = summary.split('Company:')
            if len(parts) > 1:
                return parts[1].split('<')[0].strip()

        return 'Unknown'

    def _extract_location(self, entry: Dict, feed_name: str) -> str:
        """Extract location from job posting"""
        # Most remote job boards list 'Remote' or 'Anywhere'
        summary = entry.get('summary', '')

        # Check for location in summary
        if 'Location:' in summary:
            parts = summary.split('Location:')
            if len(parts) > 1:
                return parts[1].split('<')[0].strip()

        # Default to Remote for remote job boards
        return 'Remote'

    def _deduplicate_postings(self, postings: List[Dict]) -> List[Dict]:
        """Remove duplicate postings by URL"""
        seen_urls = set()
        unique = []

        for posting in postings:
            url = posting['url']
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique.append(posting)

        self.logger.info(f"Deduplicated: {len(postings)} -> {len(unique)} postings")
        return unique

    def _calculate_hiring_trends(self, postings: List[Dict]) -> Dict:
        """Calculate hiring trend metrics"""
        if not postings:
            return {}

        # Company analysis
        companies = [p['company'] for p in postings if p.get('company')]
        company_counts = Counter(companies)

        # Location analysis
        locations = [p['location'] for p in postings if p.get('location')]
        location_counts = Counter(locations)

        # Keyword analysis
        keywords = [p['keyword'] for p in postings]
        keyword_counts = Counter(keywords)

        # Role type analysis (simplified - look for keywords in title)
        role_types = {'senior': 0, 'junior': 0, 'lead': 0, 'engineer': 0, 'manager': 0, 'director': 0}
        for posting in postings:
            title_lower = posting['title'].lower()
            for role, count in role_types.items():
                if role in title_lower:
                    role_types[role] += 1

        trends = {
            'total_postings': len(postings),
            'unique_companies': len(company_counts),
            'unique_locations': len(location_counts),
            'top_hiring_companies': dict(company_counts.most_common(10)),
            'top_locations': dict(location_counts.most_common(10)),
            'keyword_distribution': dict(keyword_counts),
            'role_type_distribution': role_types,
            'hiring_velocity': {
                'postings_per_company': round(len(postings) / len(company_counts), 2) if company_counts else 0,
                'avg_postings_per_keyword': round(len(postings) / len(self.keywords), 2)
            }
        }

        return trends

    def _save_postings(self, postings: List[Dict]):
        """Save job postings"""
        postings_file = self.output_dir / "postings.json"

        with open(postings_file, 'w', encoding='utf-8') as f:
            json.dump(postings, f, indent=2, ensure_ascii=False)

        self.stats['success'] = len(postings)
        self.stats['total_size'] = postings_file.stat().st_size

        self.logger.info(f"Saved {len(postings)} postings to {postings_file}")

    def _save_trends(self, trends: Dict):
        """Save hiring trends"""
        trends_file = self.output_dir / "hiring_trends.json"

        with open(trends_file, 'w', encoding='utf-8') as f:
            json.dump(trends, f, indent=2, ensure_ascii=False)

        self.stats['total_size'] += trends_file.stat().st_size

    def _save_metadata(self, postings: List[Dict], trends: Dict):
        """Save metadata"""
        metadata = {
            'download_date': datetime.now().isoformat(),
            'search_params': {
                'keywords': self.keywords,
                'locations': self.locations,
                'limit': self.limit
            },
            'total_postings': len(postings),
            'stats': self.stats,
            'trends_summary': {
                'unique_companies': trends.get('unique_companies', 0),
                'unique_locations': trends.get('unique_locations', 0)
            }
        }

        metadata_path = self.output_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def _print_summary(self):
        """Print summary"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("JOB MARKET TRACKING SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Postings Tracked: {self.stats['postings_tracked']}")
        self.logger.info(f"Total Size: {self.stats['total_size'] / 1024 / 1024:.2f} MB")
        self.logger.info("=" * 60)


# Example usage
if __name__ == "__main__":
    output_dir = Path("./data/test_jobs")

    keywords = ["eVTOL engineer", "urban air mobility", "electric aircraft"]

    tracker = JobMarketTracker(
        output_dir=output_dir,
        keywords=keywords,
        limit=100,
        locations=["United States", "California"]
    )

    results = tracker.download()
    print(f"\nTracked {results['postings_tracked']} job postings")
