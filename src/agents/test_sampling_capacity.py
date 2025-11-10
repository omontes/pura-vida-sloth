"""
Test Sampling Capacity - Check how many technologies we can actually get

Run this to see if limit=1000 can be satisfied or not.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.neo4j_client import Neo4jClient
from src.agents.shared.queries import community_queries
from src.agents.agent_01_tech_discovery.agent import (
    classify_communities_by_maturity,
    sample_techs_from_communities,
)


async def test_sampling_capacity():
    """Test how many technologies can be sampled with different limits."""
    print("\n" + "="*80)
    print("SAMPLING CAPACITY TEST")
    print("="*80)

    client = Neo4jClient()
    await client.connect()

    try:
        # First, check total technologies available
        total_query = """
        MATCH (t:Technology)-[:MENTIONED_IN]->(d:Document)
        WHERE d.quality_score >= 0.75
        RETURN count(DISTINCT t) AS total_techs
        """

        async with client.driver.session() as session:
            result = await session.run(total_query)
            record = await result.single()
            total_techs = record["total_techs"] if record else 0

        print(f"\n[TOTAL AVAILABLE] {total_techs} technologies with quality_score >= 0.75")

        # Get communities and classify
        communities = await community_queries.get_all_communities_for_version(
            client.driver,
            version=1,
            min_member_count=3
        )

        print(f"\n[COMMUNITIES] Found {len(communities)} communities")

        early, mid, late, hype = classify_communities_by_maturity(communities)

        print(f"\n[CLASSIFICATION]")
        print(f"  Early-stage: {len(early)} communities")
        print(f"  Mid-stage: {len(mid)} communities")
        print(f"  Late-stage: {len(late)} communities")
        print(f"  Hype-stage: {len(hype)} communities")

        # Test sampling from each stratum
        print(f"\n" + "-"*80)
        print("TESTING SAMPLE CAPACITY FROM EACH STRATUM")
        print("-"*80)

        # Sample max from each stratum
        print("\n[Sampling from EARLY-STAGE communities]")
        early_techs = await sample_techs_from_communities(
            client.driver, early, 1000, "v1", 1
        )
        print(f"  Can sample: {len(early_techs)} technologies")

        print("\n[Sampling from MID-STAGE communities]")
        mid_techs = await sample_techs_from_communities(
            client.driver, mid, 1000, "v1", 1
        )
        print(f"  Can sample: {len(mid_techs)} technologies")

        print("\n[Sampling from LATE-STAGE communities]")
        late_techs = await sample_techs_from_communities(
            client.driver, late, 1000, "v1", 1
        )
        print(f"  Can sample: {len(late_techs)} technologies")

        print("\n[Sampling from HYPE-STAGE communities]")
        hype_techs = await sample_techs_from_communities(
            client.driver, hype, 1000, "v1", 1
        )
        print(f"  Can sample: {len(hype_techs)} technologies")

        # Calculate total capacity
        total_from_strata = len(early_techs) + len(mid_techs) + len(late_techs) + len(hype_techs)

        print(f"\n" + "-"*80)
        print("CAPACITY ANALYSIS")
        print("-"*80)
        print(f"\nTotal from stratified sampling: {total_from_strata} technologies")
        print(f"Total available in graph: {total_techs} technologies")

        if total_from_strata < total_techs:
            remaining = total_techs - total_from_strata
            print(f"\nCan fill remaining {remaining} from ALL communities (adaptive fill)")

        # Test specific limits
        print(f"\n" + "="*80)
        print("LIMIT FEASIBILITY")
        print("="*80)

        test_limits = [100, 500, 1000, 2000]

        for limit in test_limits:
            if limit <= total_techs:
                print(f"\nlimit={limit}: ✓ ACHIEVABLE (have {total_techs} total)")
            else:
                print(f"\nlimit={limit}: ✗ NOT ACHIEVABLE (only have {total_techs} total)")
                print(f"            Will return {total_techs} technologies instead")

        # Show expected distribution for limit=1000
        print(f"\n" + "="*80)
        print("EXPECTED DISTRIBUTION FOR limit=1000")
        print("="*80)

        if total_techs >= 1000:
            early_target = int(1000 * 0.2)
            mid_target = int(1000 * 0.4)
            late_target = int(1000 * 0.2)
            hype_target = int(1000 * 0.2)

            early_actual = min(len(early_techs), early_target * 2)
            mid_actual = min(len(mid_techs), mid_target * 2)
            late_actual = min(len(late_techs), late_target * 2)
            hype_actual = min(len(hype_techs), hype_target * 2)

            subtotal = early_actual + mid_actual + late_actual + hype_actual

            print(f"\nTarget distribution:")
            print(f"  Early: {early_target} (can deliver {early_actual})")
            print(f"  Mid: {mid_target} (can deliver {mid_actual})")
            print(f"  Late: {late_target} (can deliver {late_actual})")
            print(f"  Hype: {hype_target} (can deliver {hype_actual})")
            print(f"\nSubtotal from strata: {subtotal}")

            if subtotal < 1000:
                fill_needed = 1000 - subtotal
                fill_available = total_techs - subtotal
                print(f"Adaptive fill needed: {fill_needed}")
                print(f"Adaptive fill available: {fill_available}")

                if fill_available >= fill_needed:
                    print(f"\n✓ Can achieve 1000 technologies")
                else:
                    print(f"\n✗ Can only deliver {subtotal + fill_available} technologies")
        else:
            print(f"\n✗ Cannot achieve 1000 (only {total_techs} available)")
            print(f"   Will return {total_techs} technologies")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_sampling_capacity())
