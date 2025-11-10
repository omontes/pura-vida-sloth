"""
Test script to verify exclude_ids parameter works correctly in sample_techs_from_communities.

This script:
1. Samples 10 technologies from all communities (baseline)
2. Samples 10 MORE technologies, excluding the first batch
3. Verifies that the two batches have no overlap
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.graph.neo4j_client import Neo4jClient
from src.agents.agent_01_tech_discovery.agent import sample_techs_from_communities
from src.agents.shared.queries import community_queries


async def test_exclude_ids():
    """Test that exclude_ids parameter filters correctly."""

    client = Neo4jClient()
    await client.connect()

    try:
        print("=" * 80)
        print("TESTING exclude_ids PARAMETER IN sample_techs_from_communities")
        print("=" * 80)

        # Step 1: Get all communities
        print("\n[1/4] Fetching communities...")

        # First, check if ANY communities exist
        check_query = "MATCH (c:Community) RETURN count(c) as total, collect(DISTINCT c.version)[0..5] as versions"
        check_result = await client.run_query(check_query)
        if check_result:
            print(f"      Total Community nodes in DB: {check_result[0]['total']}")
            print(f"      Sample versions: {check_result[0]['versions']}")

        # Now get communities for version 1
        communities = await community_queries.get_all_communities_for_version(client.driver, version=1, min_member_count=0)
        print(f"      Found {len(communities)} communities (version=1, min_member_count=0)")

        if len(communities) == 0:
            print("[ERROR] No communities found for version=1!")
            print("[INFO] This might mean:")
            print("        - Community detection hasn't been run")
            print("        - Communities use a different version number")
            print("        - Database connection issue")
            return

        # Step 2: Sample 10 technologies (baseline)
        print("\n[2/4] Sampling 10 technologies (baseline, no exclusions)...")
        batch1 = await sample_techs_from_communities(
            driver=client.driver,
            communities=communities,
            limit=10,
            version="v1",
            min_document_count=5,
            exclude_ids=None  # No exclusions
        )

        print(f"      Returned {len(batch1)} technologies")
        if len(batch1) == 0:
            print("[ERROR] No technologies returned! Check min_document_count threshold.")
            return

        batch1_ids = [t.id for t in batch1]
        print(f"      Technology IDs: {batch1_ids[:5]}..." if len(batch1_ids) > 5 else f"      Technology IDs: {batch1_ids}")

        # Step 3: Sample 10 MORE technologies, excluding batch1
        print("\n[3/4] Sampling 10 MORE technologies (excluding first batch)...")
        print(f"      Excluding {len(batch1_ids)} technology IDs")

        batch2 = await sample_techs_from_communities(
            driver=client.driver,
            communities=communities,
            limit=10,
            version="v1",
            min_document_count=5,
            exclude_ids=batch1_ids  # Exclude first batch
        )

        print(f"      Returned {len(batch2)} technologies")
        batch2_ids = [t.id for t in batch2]
        print(f"      Technology IDs: {batch2_ids[:5]}..." if len(batch2_ids) > 5 else f"      Technology IDs: {batch2_ids}")

        # Step 4: Verify no overlap
        print("\n[4/4] Verifying no overlap between batches...")
        overlap = set(batch1_ids) & set(batch2_ids)

        if len(overlap) > 0:
            print(f"[FAIL] Found {len(overlap)} overlapping technologies: {overlap}")
            print("       exclude_ids parameter is NOT working correctly!")
            return False
        else:
            print(f"[PASS] No overlap detected!")
            print(f"       Batch 1: {len(batch1_ids)} unique IDs")
            print(f"       Batch 2: {len(batch2_ids)} unique IDs")
            print(f"       Total unique: {len(set(batch1_ids) | set(batch2_ids))} technologies")

        # Additional check: Verify batch2 does NOT contain any excluded IDs
        print("\n[VERIFICATION] Double-checking that batch2 contains NONE of the excluded IDs...")
        for tech_id in batch2_ids:
            if tech_id in batch1_ids:
                print(f"[FAIL] Found excluded ID in batch2: {tech_id}")
                return False

        print("[PASS] Verification complete - exclude_ids works correctly!")

        print("\n" + "=" * 80)
        print("TEST SUMMARY: SUCCESS")
        print("=" * 80)
        print("The exclude_ids parameter correctly filters out already-seen technologies.")
        print("This fix will allow fill sampling to return NEW technologies instead of duplicates.")

        return True

    finally:
        await client.close()


async def main():
    """Run the test."""
    success = await test_exclude_ids()

    if not success:
        print("\n[!] TEST FAILED - Check the implementation")
        sys.exit(1)
    else:
        print("\n[OK] TEST PASSED - Ready for full pipeline test")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
