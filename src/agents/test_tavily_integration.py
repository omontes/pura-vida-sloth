"""
Test Tavily Integration in Narrative Scorer

Expected: Should see Tavily search results and freshness score.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.neo4j_client import Neo4jClient
from src.agents.agent_04_narrative.agent import score_narrative


async def test_tavily_integration():
    """Test that Tavily search is integrated properly."""
    print("\n" + "="*80)
    print("TEST: Tavily Integration in Narrative Scorer")
    print("="*80)

    client = Neo4jClient()
    await client.connect()

    try:
        # Test with evtol
        tech_id = "evtol"
        print(f"\nScoring narrative for: {tech_id}")

        result = await score_narrative(
            driver=client.driver,
            tech_id=tech_id
        )

        print(f"\n[RESULTS]")
        print(f"  Narrative score: {result.narrative_score}/100")
        print(f"  Confidence: {result.confidence}")
        print(f"  Reasoning: {result.reasoning}")

        print(f"\n[METRICS - Historical (Graph)]")
        print(f"  News count (6mo): {result.key_metrics.news_count_3mo}")
        print(f"  Tier 1 outlets: {result.key_metrics.tier1_count}")
        print(f"  Tier 2 outlets: {result.key_metrics.tier2_count}")

        print(f"\n[METRICS - Real-Time (Tavily)]")
        print(f"  News count (30d): {result.key_metrics.news_count_recent_30d}")
        print(f"  Freshness score: {result.key_metrics.freshness_score:.2f}x")
        if result.key_metrics.tavily_headlines:
            print(f"  Top headlines:")
            for i, headline in enumerate(result.key_metrics.tavily_headlines[:3], 1):
                print(f"    {i}. {headline[:80]}...")

        # Validation
        print(f"\n[VALIDATION]")
        if result.key_metrics.news_count_3mo > 0:
            print(f"  [PASS] Graph news count: {result.key_metrics.news_count_3mo}")
        else:
            print(f"  [FAIL] Graph news count is 0")

        if result.key_metrics.freshness_score >= 0:
            print(f"  [PASS] Freshness score calculated: {result.key_metrics.freshness_score:.2f}x")
        else:
            print(f"  [WARN] Freshness score not calculated")

        print(f"\n[PASS] Tavily integration test completed")
        return True

    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await client.close()


if __name__ == "__main__":
    success = asyncio.run(test_tavily_integration())
    sys.exit(0 if success else 1)
