"""
Test LLM relevance filter for Tavily results.

Tests that the filter correctly identifies relevant vs irrelevant articles.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.graph.neo4j_client import Neo4jClient
from src.agents.agent_04_narrative.agent import get_narrative_metrics


async def test_relevance_filter():
    """Test relevance filtering on a technology with expected low relevance."""

    async with Neo4jClient() as client:
        print("\n" + "="*80)
        print("Testing LLM Relevance Filter")
        print("="*80)

        # Test 1: Broad technology (should have high relevance)
        print("\n[TEST 1] Broad technology: evtol")
        print("-" * 40)

        metrics_evtol = await get_narrative_metrics(
            driver=client.driver,
            tech_id="evtol",
            enable_tavily=True
        )

        print(f"\nResults:")
        print(f"  Total found: {metrics_evtol.tavily_total_found}")
        print(f"  Relevant: {metrics_evtol.tavily_relevant_count}")
        print(f"  Relevance ratio: {metrics_evtol.tavily_relevance_ratio:.0%}")
        print(f"  Reasoning: {metrics_evtol.tavily_relevance_reasoning}")

        # Should have moderate-to-high relevance (>50%)
        if metrics_evtol.tavily_relevance_ratio > 0.5:
            print(f"\n[PASS] Moderate-to-high relevance for broad technology ({metrics_evtol.tavily_relevance_ratio:.0%})")
        else:
            print(f"\n[WARN] Expected moderate-to-high relevance for 'evtol', got {metrics_evtol.tavily_relevance_ratio:.0%}")

        # Test 2: Obscure component (should have low relevance)
        print("\n[TEST 2] Obscure component: independent_rotor_blade_control")
        print("-" * 40)

        metrics_component = await get_narrative_metrics(
            driver=client.driver,
            tech_id="independent_rotor_blade_control",
            enable_tavily=True
        )

        print(f"\nResults:")
        print(f"  Total found: {metrics_component.tavily_total_found}")
        print(f"  Relevant: {metrics_component.tavily_relevant_count}")
        print(f"  Relevance ratio: {metrics_component.tavily_relevance_ratio:.0%}")
        print(f"  Reasoning: {metrics_component.tavily_relevance_reasoning}")

        # Should have low relevance (<30%)
        if metrics_component.tavily_relevance_ratio < 0.3:
            print(f"\n[PASS] Low relevance for obscure component ({metrics_component.tavily_relevance_ratio:.0%})")
        else:
            print(f"\n[WARN] Expected low relevance for component, got {metrics_component.tavily_relevance_ratio:.0%}")

        print("\n" + "="*80)
        print("Test complete!")
        print("="*80)


if __name__ == "__main__":
    asyncio.run(test_relevance_filter())
