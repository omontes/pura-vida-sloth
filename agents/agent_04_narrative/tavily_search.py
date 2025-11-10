"""
Tavily Search Integration for Real-Time Narrative Analysis

This module supplements graph-based news queries with real-time web search
to detect narrative acceleration and hype signals in the last 30 days.

Strategy:
- Primary: Graph data (historical baseline, reproducible)
- Supplement: Tavily search (real-time freshness indicator)
- Merge: Combine counts to calculate "freshness score"
"""

from typing import List, Dict, Any
import os
from langchain_community.tools.tavily_search import TavilySearchResults


async def get_recent_news_tavily(
    tech_id: str,
    tech_name: str,
    days: int = 30,
    max_results: int = 20
) -> Dict[str, Any]:
    """
    Search for recent news coverage using Tavily web search.

    This supplements graph-based queries to detect:
    - Narrative acceleration (sudden spike in coverage)
    - Media saturation (hype peak signal)
    - Very recent developments (last 7-30 days)

    Args:
        tech_id: Technology ID (e.g., "evtol")
        tech_name: Human-readable name (e.g., "eVTOL")
        days: Time range in days (default: 30)
        max_results: Maximum articles to retrieve (default: 20)

    Returns:
        {
            "article_count": int,           # Number of recent articles found
            "headlines": List[str],          # Top 5 headlines for evidence
            "sources": List[str],            # Publication names
            "freshness_score": float,        # Relative to historical baseline
            "search_query": str,             # Query used
            "time_range_days": int          # Actual time range
        }

    Example:
        >>> result = await get_recent_news_tavily("evtol", "eVTOL", days=30)
        >>> result
        {
            "article_count": 45,
            "headlines": ["New eVTOL certification...", ...],
            "sources": ["TechCrunch", "The Verge", ...],
            "freshness_score": 2.5,  # 2.5x higher than baseline
            "search_query": "eVTOL technology news",
            "time_range_days": 30
        }
    """
    # Check if Tavily API key is available
    if not os.getenv("TAVILY_API_KEY"):
        print("[TAVILY] Warning: TAVILY_API_KEY not found in environment")
        return {
            "article_count": 0,
            "headlines": [],
            "sources": [],
            "freshness_score": 0.0,
            "search_query": "",
            "time_range_days": days,
            "error": "TAVILY_API_KEY not configured"
        }

    # Construct search query
    # Format: "{tech_name} technology news" (e.g., "eVTOL technology news")
    search_query = f"{tech_name} technology news"

    # Map days to Tavily time_range
    if days <= 1:
        time_range = "day"
    elif days <= 7:
        time_range = "week"
    elif days <= 30:
        time_range = "month"
    else:
        time_range = "year"

    try:
        print(f"[TAVILY] Searching for: '{search_query}' (time_range={time_range}, max_results={max_results})")

        # Initialize Tavily search tool
        tavily_tool = TavilySearchResults(
            max_results=max_results,
            search_depth="advanced",  # Use advanced for better news coverage
            include_answer=False,
            include_raw_content=False,
            include_images=False,
        )

        # Execute search
        # Note: TavilySearchResults.invoke() is synchronous, not async
        results = tavily_tool.invoke({"query": search_query})

        # Parse results
        headlines = []
        sources = []

        if isinstance(results, list):
            for result in results[:5]:  # Top 5 for evidence
                if isinstance(result, dict):
                    title = result.get("title", result.get("content", "")[:100])
                    url = result.get("url", "")

                    headlines.append(title)

                    # Extract domain from URL as source
                    if url:
                        try:
                            from urllib.parse import urlparse
                            domain = urlparse(url).netloc.replace("www.", "")
                            sources.append(domain)
                        except:
                            sources.append("Unknown")

            article_count = len(results)
        else:
            article_count = 0

        print(f"[TAVILY] Found {article_count} articles")

        return {
            "article_count": article_count,
            "headlines": headlines[:5],
            "sources": sources[:5],
            "freshness_score": 0.0,  # Will be calculated separately
            "search_query": search_query,
            "time_range_days": days
        }

    except Exception as e:
        print(f"[TAVILY] Error during search: {e}")
        return {
            "article_count": 0,
            "headlines": [],
            "sources": [],
            "freshness_score": 0.0,
            "search_query": search_query,
            "time_range_days": days,
            "error": str(e)
        }


def calculate_freshness_score(
    graph_count: int,
    tavily_count: int,
    days_tavily: int = 30,
    days_graph: int = 180
) -> float:
    """
    Calculate narrative freshness score (acceleration indicator).

    Freshness indicates if recent coverage is spiking vs. historical baseline.

    Formula:
        freshness = (tavily_daily_rate / graph_daily_rate)

    Interpretation:
        - <0.5: Coverage declining (interest waning)
        - 0.5-1.5: Stable coverage (normal pattern)
        - 1.5-3.0: Accelerating coverage (growing interest)
        - >3.0: Spiking coverage (PEAK hype signal)

    Args:
        graph_count: Articles from graph (historical, e.g., 6 months)
        tavily_count: Articles from Tavily (recent, e.g., 30 days)
        days_tavily: Days covered by Tavily search
        days_graph: Days covered by graph query

    Returns:
        Freshness score (0.0+, typical range 0.5-3.0)

    Example:
        >>> calculate_freshness_score(graph_count=60, tavily_count=30, days_tavily=30, days_graph=180)
        5.0  # 30 articles in 30 days = 5x the 6-month daily rate → PEAK signal

        >>> calculate_freshness_score(graph_count=60, tavily_count=10, days_tavily=30, days_graph=180)
        1.0  # Stable coverage

        >>> calculate_freshness_score(graph_count=60, tavily_count=2, days_tavily=30, days_graph=180)
        0.2  # Declining interest
    """
    if graph_count == 0:
        # No historical baseline - use Tavily count as-is
        return float(tavily_count) if tavily_count > 0 else 0.0

    # Calculate daily rates
    graph_daily_rate = graph_count / days_graph
    tavily_daily_rate = tavily_count / days_tavily

    # Avoid division by zero
    if graph_daily_rate == 0:
        return float(tavily_count)

    # Freshness = Recent rate / Historical rate
    freshness = tavily_daily_rate / graph_daily_rate

    return round(freshness, 2)
