"""
News Article Metadata Extractors
Author: Pura Vida Sloth Intelligence System

Helper functions for loading, extracting, and classifying news article data.
Includes Tavily Extract API integration for article content retrieval.
"""

import json
import os
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse


def load_articles_from_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Load news articles from JSON file.

    Args:
        file_path: Path to JSON file containing article data

    Returns:
        List of article dictionaries
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle both single object and array formats
    return data if isinstance(data, list) else [data]


def extract_article_metadata(article: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and normalize article metadata.

    Args:
        article: Raw article dictionary from GDELT

    Returns:
        Normalized metadata dictionary
    """
    return {
        'url': article.get('url', ''),
        'title': article.get('title', ''),
        'domain': article.get('domain', ''),
        'language': article.get('language', 'English'),
        'seendate': article.get('seendate', ''),
        'tone': article.get('tone', 0.0),  # Placeholder, not used by LLM
        'keyword': article.get('keyword', ''),
        'socialimage': article.get('socialimage', '')
    }


def parse_seendate(seendate: str) -> Optional[datetime]:
    """
    Parse GDELT seendate format to datetime.

    Args:
        seendate: GDELT seendate string (format: "20250828T014500Z")

    Returns:
        Datetime object or None if parsing fails
    """
    if not seendate:
        return None

    try:
        # Format: "20250828T014500Z" → YYYY-MM-DD HH:MM:SS
        return datetime.strptime(seendate, "%Y%m%dT%H%M%SZ")
    except (ValueError, TypeError):
        return None


def classify_outlet_tier(domain: str) -> str:
    """
    Classify news outlet tier based on domain.

    5-tier credibility system:
    - Industry Authority: Aviation specialty, academic journals
    - Financial Authority: Major financial news
    - Mainstream Media: General business news
    - Press Release/Wire: PR distribution services
    - Niche/Aggregator: Blogs, aggregators, non-English sites

    Args:
        domain: News outlet domain (e.g., "fool.com")

    Returns:
        Outlet tier classification
    """
    domain_lower = domain.lower()

    # Industry Authority (aviation specialty, academic journals)
    industry_domains = [
        'aviationweek.com', 'ainonline.com', 'flightglobal.com',
        'aerospaceamerica.aiaa.org', 'verticalmag.com', 'rotorcraft.com',
        'ieee.org', 'nature.com', 'science.org'
    ]
    if any(d in domain_lower for d in industry_domains):
        return "Industry Authority"

    # Financial Authority (major financial news)
    financial_domains = [
        'bloomberg.com', 'reuters.com', 'wsj.com', 'ft.com',
        'forbes.com', 'barrons.com', 'marketwatch.com', 'cnbc.com'
    ]
    if any(d in domain_lower for d in financial_domains):
        return "Financial Authority"

    # Press Release/Wire services
    wire_domains = [
        'prnewswire.com', 'businesswire.com', 'globenewswire.com',
        'accesswire.com', 'prweb.com', 'marketscreener.com'
    ]
    if any(d in domain_lower for d in wire_domains):
        return "Press Release/Wire"

    # Mainstream Media (general business news)
    mainstream_domains = [
        'benzinga.com', 'yahoo.com', 'fool.com', 'seekingalpha.com',
        'investing.com', 'finance.yahoo.com', 'msn.com', 'google.com/finance'
    ]
    if any(d in domain_lower for d in mainstream_domains):
        return "Mainstream Media"

    # Default: Niche/Aggregator
    return "Niche/Aggregator"


def extract_article_with_tavily(
    url: str,
    api_key: str,
    extract_depth: str = "basic"
) -> Optional[str]:
    """
    Extract article content using Tavily Extract API.

    Args:
        url: Article URL
        api_key: Tavily API key
        extract_depth: "basic" or "advanced" (basic recommended for news)

    Returns:
        Article content in markdown format, or None if extraction fails
    """
    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)

        # Extract content from URL
        response = client.extract(
            urls=[url],
            format="markdown",
            extract_depth=extract_depth
        )

        # Parse response
        if response and 'results' in response and len(response['results']) > 0:
            result = response['results'][0]
            return result.get('raw_content', '')

        return None

    except Exception as e:
        print(f"  [WARNING] Tavily extraction failed for {url}: {e}")
        return None


def build_document_id(url: str) -> str:
    """
    Generate standardized document ID for news article.

    Args:
        url: Article URL

    Returns:
        Document ID in format "news_article_{hash}"
    """
    # Generate hash from URL for unique ID
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:12]
    return f"news_article_{url_hash}"


def extract_domain(url: str) -> str:
    """
    Extract domain from URL.

    Args:
        url: Article URL

    Returns:
        Domain name (e.g., "fool.com")
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def extract_publisher_name(domain: str) -> str:
    """
    Extract publisher name from domain.

    Args:
        domain: News outlet domain (e.g., "fool.com")

    Returns:
        Publisher name (e.g., "The Motley Fool")
    """
    # Map common domains to publisher names
    publisher_map = {
        'fool.com': 'The Motley Fool',
        'benzinga.com': 'Benzinga',
        'finance.yahoo.com': 'Yahoo Finance',
        'yahoo.com': 'Yahoo',
        'seekingalpha.com': 'Seeking Alpha',
        'forbes.com': 'Forbes',
        'bloomberg.com': 'Bloomberg',
        'reuters.com': 'Reuters',
        'wsj.com': 'The Wall Street Journal',
        'aviationweek.com': 'Aviation Week',
        'ainonline.com': 'AIN Online',
        'flightglobal.com': 'Flight Global',
        'prnewswire.com': 'PR Newswire',
        'businesswire.com': 'Business Wire',
        'globenewswire.com': 'GlobeNewswire'
    }

    domain_lower = domain.lower()

    # Check exact matches
    if domain_lower in publisher_map:
        return publisher_map[domain_lower]

    # Check partial matches
    for key, name in publisher_map.items():
        if key in domain_lower:
            return name

    # Default: capitalize domain name
    return domain.replace('.com', '').replace('.', ' ').title()
