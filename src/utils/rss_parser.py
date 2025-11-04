"""
RSS Feed Parser
===============
Generic RSS/Atom feed parser for regulatory and press release feeds
"""

import feedparser
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


class RSSParser:
    """Parse RSS and Atom feeds with date filtering"""

    def __init__(self, start_date: datetime, end_date: datetime):
        """
        Initialize RSS parser

        Args:
            start_date: Filter entries after this date
            end_date: Filter entries before this date
        """
        self.start_date = start_date
        self.end_date = end_date

    def parse_feed(self, feed_url: str, source_name: str = None) -> List[Dict[str, Any]]:
        """
        Parse RSS/Atom feed and extract entries

        Args:
            feed_url: URL of the RSS/Atom feed
            source_name: Optional name for logging

        Returns:
            List of parsed entries with metadata
        """
        try:
            logger.info(f"Fetching feed: {source_name or feed_url}")
            feed = feedparser.parse(feed_url)

            if feed.bozo:
                logger.warning(f"Feed parsing warning for {source_name or feed_url}: {feed.bozo_exception}")

            entries = []
            for entry in feed.entries:
                parsed_entry = self._parse_entry(entry, source_name)
                if parsed_entry:
                    entries.append(parsed_entry)

            logger.info(f"Found {len(entries)} entries in date range from {source_name or feed_url}")
            return entries

        except Exception as e:
            logger.error(f"Error parsing feed {source_name or feed_url}: {e}")
            return []

    def _parse_entry(self, entry: Any, source_name: str = None) -> Optional[Dict[str, Any]]:
        """
        Parse individual feed entry

        Args:
            entry: Feed entry object
            source_name: Source identifier

        Returns:
            Parsed entry dict or None if outside date range
        """
        try:
            # Extract publication date
            pub_date = self._extract_date(entry)

            # Filter by date range
            if pub_date:
                if pub_date < self.start_date or pub_date > self.end_date:
                    return None

            # Extract title
            title = entry.get('title', 'Untitled').strip()

            # Extract link
            link = entry.get('link', '')

            # Extract summary/description
            summary = entry.get('summary', entry.get('description', ''))

            # Clean HTML from summary if present
            if summary:
                summary = self._clean_html(summary)

            # Extract additional metadata
            author = entry.get('author', '')
            tags = [tag.term for tag in entry.get('tags', [])] if hasattr(entry, 'tags') else []

            return {
                'title': title,
                'link': link,
                'summary': summary,
                'pub_date': pub_date,
                'author': author,
                'tags': tags,
                'source': source_name or 'Unknown'
            }

        except Exception as e:
            logger.debug(f"Error parsing entry: {e}")
            return None

    def _extract_date(self, entry: Any) -> Optional[datetime]:
        """
        Extract and parse publication date from entry

        Args:
            entry: Feed entry object

        Returns:
            Parsed datetime or None
        """
        # Try multiple date fields
        date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']

        for field in date_fields:
            if hasattr(entry, field):
                time_struct = getattr(entry, field)
                if time_struct:
                    try:
                        return datetime(*time_struct[:6])
                    except:
                        pass

        # Try string date fields
        string_fields = ['published', 'updated', 'created']
        for field in string_fields:
            if hasattr(entry, field):
                date_string = getattr(entry, field)
                if date_string:
                    try:
                        return date_parser.parse(date_string)
                    except:
                        pass

        return None

    def _clean_html(self, text: str) -> str:
        """
        Remove HTML tags from text

        Args:
            text: Text with potential HTML

        Returns:
            Cleaned text
        """
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(text, 'html.parser')
            return soup.get_text(strip=True)
        except:
            # Fallback: simple regex-based cleaning
            import re
            return re.sub(r'<[^>]+>', '', text).strip()


class FeedAggregator:
    """Aggregate entries from multiple RSS feeds"""

    def __init__(self, start_date: datetime, end_date: datetime):
        """
        Initialize feed aggregator

        Args:
            start_date: Filter entries after this date
            end_date: Filter entries before this date
        """
        self.parser = RSSParser(start_date, end_date)
        self.all_entries = []

    def add_feed(self, feed_url: str, source_name: str = None) -> int:
        """
        Add feed and parse entries

        Args:
            feed_url: URL of RSS/Atom feed
            source_name: Optional source identifier

        Returns:
            Number of entries added
        """
        entries = self.parser.parse_feed(feed_url, source_name)
        self.all_entries.extend(entries)
        return len(entries)

    def add_feeds(self, feeds: Dict[str, str]) -> Dict[str, int]:
        """
        Add multiple feeds

        Args:
            feeds: Dictionary of {source_name: feed_url}

        Returns:
            Dictionary of {source_name: entry_count}
        """
        results = {}
        for source_name, feed_url in feeds.items():
            count = self.add_feed(feed_url, source_name)
            results[source_name] = count
        return results

    def get_entries(self, sort_by_date: bool = True, deduplicate: bool = True) -> List[Dict[str, Any]]:
        """
        Get all aggregated entries

        Args:
            sort_by_date: Sort entries by publication date (newest first)
            deduplicate: Remove duplicate entries based on link

        Returns:
            List of entries
        """
        entries = self.all_entries.copy()

        # Deduplicate by link
        if deduplicate:
            seen_links = set()
            unique_entries = []
            for entry in entries:
                link = entry.get('link', '')
                if link and link not in seen_links:
                    seen_links.add(link)
                    unique_entries.append(entry)
            entries = unique_entries

        # Sort by publication date
        if sort_by_date:
            entries.sort(
                key=lambda x: x['pub_date'] if x.get('pub_date') else datetime.min,
                reverse=True
            )

        return entries

    def filter_by_keywords(self, keywords: List[str], case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """
        Filter entries by keywords in title or summary

        Args:
            keywords: List of keywords to search for
            case_sensitive: Whether search is case-sensitive

        Returns:
            Filtered entries
        """
        filtered = []

        for entry in self.all_entries:
            title = entry.get('title', '')
            summary = entry.get('summary', '')

            if not case_sensitive:
                title = title.lower()
                summary = summary.lower()
                keywords = [k.lower() for k in keywords]

            # Check if any keyword appears in title or summary
            for keyword in keywords:
                if keyword in title or keyword in summary:
                    filtered.append(entry)
                    break

        return filtered

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about aggregated feeds

        Returns:
            Statistics dictionary
        """
        total_entries = len(self.all_entries)

        # Count by source
        by_source = {}
        for entry in self.all_entries:
            source = entry.get('source', 'Unknown')
            by_source[source] = by_source.get(source, 0) + 1

        # Date range
        dates = [e['pub_date'] for e in self.all_entries if e.get('pub_date')]
        date_range = {
            'oldest': min(dates) if dates else None,
            'newest': max(dates) if dates else None
        }

        return {
            'total_entries': total_entries,
            'by_source': by_source,
            'date_range': date_range
        }
