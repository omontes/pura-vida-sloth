"""
Quick test to verify Narrative Scorer date fix.

Expected: evtol should return 101 news articles (currently returns 0).
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.neo4j_client import Neo4jClient
from agents.agent_04_narrative.agent import get_narrative_metrics


async def test_narrative_date_fix():
    """Test that narrative scorer now finds news articles."""
    print("\n" + "="*80)
    print("TEST: Narrative Scorer Date Fix")
    print("="*80)

    client = Neo4jClient()
    await client.connect()

    try:
        # Test with evtol (should have 101 articles)
        tech_id = "evtol"
        print(f"\nTesting narrative metrics for: {tech_id}")

        metrics = await get_narrative_metrics(
            driver=client.driver,
            tech_id=tech_id
        )

        print(f"\n[RESULTS]")
        print(f"  News count (3mo): {metrics.news_count_3mo}")
        print(f"  Tier 1 outlets: {metrics.tier1_count}")
        print(f"  Tier 2 outlets: {metrics.tier2_count}")
        print(f"  Tier 3 outlets: {metrics.tier3_count}")
        print(f"  Avg sentiment: {metrics.avg_sentiment}")
        print(f"  Sentiment trend: {metrics.sentiment_trend}")

        # Validation
        if metrics.news_count_3mo > 0:
            print(f"\n[PASS] Found {metrics.news_count_3mo} articles (expected ~101)")
            print(f"[PASS] Date fix is working!")
            return True
        else:
            print(f"\n[FAIL] Found 0 articles (expected ~101)")
            print(f"[FAIL] Date fix did not work")
            return False

    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await client.close()


if __name__ == "__main__":
    success = asyncio.run(test_narrative_date_fix())
    sys.exit(0 if success else 1)
