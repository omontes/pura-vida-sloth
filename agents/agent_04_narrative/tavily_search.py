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
from pydantic import BaseModel, Field
from agents.shared.openai_client import get_structured_llm


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
            "full_results": [],
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
        full_results = []  # Store full result objects for relevance filtering

        if isinstance(results, list):
            for result in results:
                if isinstance(result, dict):
                    title = result.get("title", result.get("content", "")[:100])
                    url = result.get("url", "")
                    content = result.get("content", "")

                    # Store for top 5 display
                    if len(headlines) < 5:
                        headlines.append(title)

                    # Extract domain from URL as source
                    if url and len(sources) < 5:
                        try:
                            from urllib.parse import urlparse
                            domain = urlparse(url).netloc.replace("www.", "")
                            sources.append(domain)
                        except:
                            sources.append("Unknown")

                    # Store full result for relevance filtering
                    full_results.append({
                        "title": title,
                        "content": content[:300],  # First 300 chars for LLM analysis
                        "url": url
                    })

            article_count = len(results)
        else:
            article_count = 0

        print(f"[TAVILY] Found {article_count} articles")

        return {
            "article_count": article_count,
            "headlines": headlines[:5],
            "sources": sources[:5],
            "full_results": full_results,  # For relevance filtering
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
            "full_results": [],
            "freshness_score": 0.0,
            "search_query": search_query,
            "time_range_days": days,
            "error": str(e)
        }


class RelevanceFilterOutput(BaseModel):
    """LLM output for relevance filtering."""
    relevant_count: int = Field(description="Number of articles truly about the technology")
    relevance_ratio: float = Field(description="Ratio of relevant articles (0.0-1.0)")
    reasoning: str = Field(description="Explanation of filtering decision")


async def filter_relevant_articles_with_llm(
    tech_name: str,
    tavily_results: List[Dict[str, Any]],
    total_found: int
) -> Dict[str, Any]:
    """
    Use LLM to filter Tavily results for relevance.

    Problem: Tavily finds 13-19 articles for almost everything (even obscure components),
    but many are tangentially related or false positives. This function uses an LLM to
    count only articles truly about the technology.

    Args:
        tech_name: Technology name (e.g., "eVTOL", "Independent Rotor Blade Control")
        tavily_results: List of article dicts with title, content, url
        total_found: Total articles from Tavily

    Returns:
        {
            "total_found": int,
            "relevant_count": int,
            "relevance_ratio": float,
            "reasoning": str,
            "relevant_headlines": List[str]
        }

    Example:
        >>> filter_relevant_articles_with_llm(
        ...     "Independent Rotor Blade Control",
        ...     tavily_results,
        ...     19
        ... )
        {
            "total_found": 19,
            "relevant_count": 2,
            "relevance_ratio": 0.11,
            "reasoning": "Only 2 of 19 articles directly discuss Independent Rotor Blade Control...",
            "relevant_headlines": [...]
        }
    """
    if not tavily_results or total_found == 0:
        return {
            "total_found": 0,
            "relevant_count": 0,
            "relevance_ratio": 0.0,
            "reasoning": "No articles found",
            "relevant_headlines": []
        }

    # Build prompt with article summaries
    articles_text = "\n\n".join([
        f"{i+1}. Title: {r['title']}\n   Snippet: {r['content'][:200]}"
        for i, r in enumerate(tavily_results[:20])  # Analyze up to 20 articles
    ])

    prompt = f"""You are analyzing web search results to determine relevance.

Technology: {tech_name}

Total articles found: {total_found}

Articles (title + snippet):
{articles_text}

Task: Count how many of these articles are SPECIFICALLY about "{tech_name}" (not just tangentially related).

Criteria for RELEVANT:
- Primary focus is the technology itself
- Discusses developments, trends, applications, or challenges
- Technology is prominently featured (in headline or first paragraph)
- Provides substantive information about the technology

Criteria for NOT RELEVANT:
- Only mentions technology in passing
- About broader industry/topic (technology is secondary)
- False match on search terms (different technology with similar name)
- Generic article that barely mentions the technology

Provide:
1. relevant_count: Number of relevant articles (0-{total_found})
2. relevance_ratio: Ratio of relevant/total (0.0-1.0)
3. reasoning: 1-2 sentences explaining your count

Be conservative - only count articles truly about the technology."""

    try:
        # Use gpt-4o-mini for cost efficiency (~$0.0001-0.0002 per call)
        llm = get_structured_llm(
            output_schema=RelevanceFilterOutput,
            model="gpt-4o-mini",
            temperature=0.0  # Deterministic for consistency
        )

        result = await llm.ainvoke(prompt)

        # Extract relevant headlines
        relevant_headlines = []
        if result.relevant_count > 0:
            # Take first N headlines as proxy (LLM doesn't specify which ones)
            relevant_headlines = [r['title'] for r in tavily_results[:min(result.relevant_count, 5)]]

        print(f"[TAVILY-FILTER] {result.relevant_count}/{total_found} articles relevant ({result.relevance_ratio:.0%})")

        return {
            "total_found": total_found,
            "relevant_count": result.relevant_count,
            "relevance_ratio": result.relevance_ratio,
            "reasoning": result.reasoning,
            "relevant_headlines": relevant_headlines
        }

    except Exception as e:
        print(f"[TAVILY-FILTER] Error during relevance filtering: {e}")
        # Fallback: assume all articles are relevant (conservative)
        return {
            "total_found": total_found,
            "relevant_count": total_found,
            "relevance_ratio": 1.0,
            "reasoning": f"Relevance filtering failed: {str(e)}. Assuming all articles are relevant.",
            "relevant_headlines": [r['title'] for r in tavily_results[:5]]
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
        # No historical baseline - return neutral (1.0) to avoid false acceleration signal
        # Without baseline, we cannot determine if coverage is accelerating
        return 1.0

    # Calculate daily rates
    graph_daily_rate = graph_count / days_graph
    tavily_daily_rate = tavily_count / days_tavily

    # Avoid division by zero
    if graph_daily_rate == 0:
        return float(tavily_count)

    # Freshness = Recent rate / Historical rate
    freshness = tavily_daily_rate / graph_daily_rate

    return round(freshness, 2)
