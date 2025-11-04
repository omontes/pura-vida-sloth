"""
News Sentiment Downloader
==========================
Downloads news articles with sentiment analysis from GDELT Project

Target: 1,000-2,000 articles per harvest (configurable)
Primary Source: GDELT DOC 2.0 API (unlimited, free)
Data: Article metadata, sentiment tone (-100 to +100), trends

Hype Cycle Value:
- Market perception (positive/negative sentiment)
- Media coverage velocity (article count over time)
- Geographic distribution of coverage
- Sentiment trends (peak hype vs trough)
"""

import requests
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict
from tqdm import tqdm

from src.utils.logger import setup_logger
from src.utils.config import Config
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.retry_handler import retry_on_error


class NewsSentimentDownloader:
    """Download news articles with sentiment from GDELT"""

    GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"

    def __init__(self, output_dir: Path, start_date: datetime, end_date: datetime,
                 keywords: List[str], limit: int = 2000, max_per_query: int = 250):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.start_date = start_date
        self.end_date = end_date
        self.keywords = keywords
        self.limit = limit
        self.max_per_query = min(max_per_query, 250)  # GDELT max

        self.logger = setup_logger("NewsSentiment", self.output_dir / "news.log")
        self.checkpoint = CheckpointManager(self.output_dir, 'news')

        self.stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total_size': 0,
            'by_sentiment': {
                'positive': 0,
                'neutral': 0,
                'negative': 0
            }
        }

        resume_info = self.checkpoint.get_resume_info()
        if resume_info:
            self.logger.info(resume_info)

    def download(self) -> Dict:
        """Main download method"""
        self.logger.info(f"Starting news sentiment download")
        self.logger.info(f"Date range: {self.start_date.date()} to {self.end_date.date()}")
        self.logger.info(f"Keywords: {len(self.keywords)}")
        self.logger.info(f"Limit: {self.limit} articles")

        # Collect articles
        all_articles = []
        for keyword in self.keywords:
            if len(all_articles) >= self.limit:
                break

            articles = self._query_gdelt(keyword)
            all_articles.extend(articles)
            self.logger.info(f"Keyword '{keyword}': {len(articles)} articles")

        # Deduplicate by URL
        unique_articles = self._deduplicate_articles(all_articles)
        unique_articles = unique_articles[:self.limit]

        self.logger.info(f"Total unique articles: {len(unique_articles)}")

        # Calculate sentiment trends
        sentiment_trends = self._calculate_sentiment_trends(unique_articles)

        # Save data
        self._save_articles(unique_articles)
        self._save_sentiment_trends(sentiment_trends)
        self._save_metadata(unique_articles, sentiment_trends)

        # Finalize checkpoint
        self.checkpoint.finalize()

        # Print summary
        self._print_summary()

        return self.stats

    @retry_on_error(max_retries=3)
    def _query_gdelt(self, keyword: str) -> List[Dict]:
        """Query GDELT API for articles"""
        articles = []

        try:
            params = {
                'query': keyword,
                'mode': 'ArtList',
                'maxrecords': self.max_per_query,
                'format': 'json',
                'startdatetime': self.start_date.strftime('%Y%m%d%H%M%S'),
                'enddatetime': self.end_date.strftime('%Y%m%d%H%M%S')
            }

            response = requests.get(self.GDELT_API, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if 'articles' in data:
                for article in data['articles']:
                    articles.append({
                        'url': article.get('url', ''),
                        'title': article.get('title', ''),
                        'domain': article.get('domain', ''),
                        'language': article.get('language', 'en'),
                        'seendate': article.get('seendate', ''),
                        'tone': float(article.get('tone', 0)),
                        'socialimage': article.get('socialimage', ''),
                        'keyword': keyword
                    })

        except Exception as e:
            self.logger.error(f"Error querying GDELT for '{keyword}': {e}")

        return articles

    def _deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles by URL"""
        seen_urls = set()
        unique = []

        for article in articles:
            url = article['url']
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique.append(article)

        self.logger.info(f"Deduplicated: {len(articles)} -> {len(unique)} articles")
        return unique

    def _calculate_sentiment_trends(self, articles: List[Dict]) -> Dict:
        """Calculate sentiment trends over time"""
        # Group by date
        daily_sentiment = defaultdict(list)
        daily_count = defaultdict(int)

        for article in articles:
            if article.get('seendate'):
                date = article['seendate'][:8]  # YYYYMMDD
                tone = article.get('tone', 0)

                daily_sentiment[date].append(tone)
                daily_count[date] += 1

                # Categorize sentiment
                if tone > 5:
                    self.stats['by_sentiment']['positive'] += 1
                elif tone < -5:
                    self.stats['by_sentiment']['negative'] += 1
                else:
                    self.stats['by_sentiment']['neutral'] += 1

        # Calculate daily averages
        trends = {}
        for date in sorted(daily_sentiment.keys()):
            tones = daily_sentiment[date]
            trends[date] = {
                'date': f"{date[:4]}-{date[4:6]}-{date[6:8]}",
                'article_count': daily_count[date],
                'avg_tone': round(sum(tones) / len(tones), 2),
                'positive_count': len([t for t in tones if t > 5]),
                'negative_count': len([t for t in tones if t < -5]),
                'neutral_count': len([t for t in tones if -5 <= t <= 5])
            }

        # Calculate overall sentiment trajectory
        if trends and len(trends) > 1:  # Need at least 2 dates
            dates = sorted(trends.keys())
            first_half = dates[:len(dates)//2]
            second_half = dates[len(dates)//2:]

            avg_first = sum(trends[d]['avg_tone'] for d in first_half) / len(first_half) if first_half else 0
            avg_second = sum(trends[d]['avg_tone'] for d in second_half) / len(second_half) if second_half else 0

            trends['_summary'] = {
                'total_articles': len(articles),
                'avg_tone_overall': round(sum(a['tone'] for a in articles) / len(articles), 2) if articles else 0,
                'avg_tone_first_half': round(avg_first, 2),
                'avg_tone_second_half': round(avg_second, 2),
                'sentiment_trend': 'improving' if avg_second > avg_first else 'declining',
                'trend_change': round(avg_second - avg_first, 2)
            }
        elif articles:
            # Single date or no date grouping
            trends['_summary'] = {
                'total_articles': len(articles),
                'avg_tone_overall': round(sum(a['tone'] for a in articles) / len(articles), 2) if articles else 0,
                'sentiment_trend': 'stable',
                'trend_change': 0
            }

        return trends

    def _save_articles(self, articles: List[Dict]):
        """Save article data"""
        articles_file = self.output_dir / "articles.json"

        with open(articles_file, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)

        self.stats['success'] = len(articles)
        self.stats['total_size'] = articles_file.stat().st_size

        self.logger.info(f"Saved {len(articles)} articles to {articles_file}")

    def _save_sentiment_trends(self, trends: Dict):
        """Save sentiment trend analysis"""
        trends_file = self.output_dir / "sentiment_trends.json"

        with open(trends_file, 'w', encoding='utf-8') as f:
            json.dump(trends, f, indent=2, ensure_ascii=False)

        self.stats['total_size'] += trends_file.stat().st_size

        self.logger.info(f"Saved sentiment trends to {trends_file}")

    def _save_metadata(self, articles: List[Dict], trends: Dict):
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
            'total_articles': len(articles),
            'stats': self.stats,
            'sentiment_summary': trends.get('_summary', {})
        }

        metadata_path = self.output_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Metadata saved to {metadata_path}")

    def _print_summary(self):
        """Print summary"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("NEWS SENTIMENT DOWNLOAD SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Total Articles: {self.stats['success']}")
        self.logger.info(f"Positive: {self.stats['by_sentiment']['positive']}")
        self.logger.info(f"Neutral: {self.stats['by_sentiment']['neutral']}")
        self.logger.info(f"Negative: {self.stats['by_sentiment']['negative']}")
        self.logger.info(f"Total Size: {self.stats['total_size'] / 1024 / 1024:.2f} MB")
        self.logger.info("=" * 60)


# Example usage
if __name__ == "__main__":
    output_dir = Path("./data/test_news")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    keywords = ["eVTOL", "electric VTOL", "urban air mobility"]

    downloader = NewsSentimentDownloader(
        output_dir=output_dir,
        start_date=start_date,
        end_date=end_date,
        keywords=keywords,
        limit=100
    )

    results = downloader.download()
    print(f"\nDownloaded {results['success']} articles")
