"""
Tests for Agent 1: Tech Discovery

Test Pattern: 1 → 10 → Full
1. Single technology retrieval
2. Top 10 technologies by document count
3. Full technology list (all 1,755)
"""

import asyncio
import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.graph.neo4j_client import Neo4jClient
from src.agents.agent_01_tech_discovery.agent import discover_technologies


async def test_single_technology():
    """Test 1: Retrieve single technology (limit=1)."""
    print("\n" + "="*80)
    print("TEST 1: Single Technology Retrieval (limit=1)")
    print("="*80)

    client = Neo4jClient()
    await client.connect()

    try:
        output = await discover_technologies(
            driver=client.driver,
            limit=1
        )

        print(f"\n[RESULT] Total technologies in graph: {output.total_count}")
        print(f"[RESULT] Retrieved: {output.filtered_count}")

        if output.filtered_count > 0:
            tech = output.technologies[0]
            print(f"\n[TECH] ID: {tech.id}")
            print(f"[TECH] Name: {tech.name}")
            print(f"[TECH] Domain: {tech.domain}")
            print(f"[TECH] Document Count: {tech.document_count}")
            print(f"[TECH] Doc Type Breakdown: {tech.doc_type_breakdown}")
            print(f"[TECH] Companies: {tech.companies}")
            print(f"[TECH] Community ID: {tech.community_id}")
            print(f"[TECH] PageRank: {tech.pagerank:.6f}")

            # Validation
            assert tech.id is not None, "Technology ID should not be None"
            assert tech.name is not None, "Technology name should not be None"
            assert tech.document_count > 0, "Document count should be > 0"
            assert len(tech.doc_type_breakdown) > 0, "Should have doc type breakdown"

            print("\n[PASS] Test 1 passed - Single technology retrieved successfully")
            return True
        else:
            print("\n[FAIL] Test 1 failed - No technologies found")
            return False

    finally:
        await client.close()


async def test_top_10_technologies():
    """Test 2: Retrieve top 10 technologies by document count."""
    print("\n" + "="*80)
    print("TEST 2: Top 10 Technologies by Document Count (limit=10)")
    print("="*80)

    client = Neo4jClient()
    await client.connect()

    try:
        output = await discover_technologies(
            driver=client.driver,
            limit=10
        )

        print(f"\n[RESULT] Total technologies in graph: {output.total_count}")
        print(f"[RESULT] Retrieved: {output.filtered_count}")

        if output.filtered_count >= 10:
            print(f"\n[INFO] Top 10 Technologies:")
            print(f"{'Rank':<6} {'ID':<30} {'Name':<40} {'Docs':<8} {'PageRank':<12}")
            print("-" * 100)

            for i, tech in enumerate(output.technologies[:10], start=1):
                print(f"{i:<6} {tech.id:<30} {tech.name:<40} {tech.document_count:<8} {tech.pagerank:<12.6f}")

            # Validation: Ensure descending order by document count
            doc_counts = [tech.document_count for tech in output.technologies[:10]]
            is_descending = all(doc_counts[i] >= doc_counts[i+1] for i in range(len(doc_counts)-1))

            if is_descending:
                print("\n[PASS] Test 2 passed - Technologies ordered correctly by document count")
                return True
            else:
                print("\n[FAIL] Test 2 failed - Technologies not ordered correctly")
                return False
        else:
            print(f"\n[WARN] Test 2 warning - Only {output.filtered_count} technologies found (expected 10)")
            return True  # Still pass if graph has fewer than 10 techs

    finally:
        await client.close()


async def test_full_technology_list():
    """Test 3: Retrieve full technology list (no limit)."""
    print("\n" + "="*80)
    print("TEST 3: Full Technology List (no limit)")
    print("="*80)

    client = Neo4jClient()
    await client.connect()

    try:
        output = await discover_technologies(
            driver=client.driver,
            limit=None
        )

        print(f"\n[RESULT] Total technologies in graph: {output.total_count}")
        print(f"[RESULT] Retrieved: {output.filtered_count}")

        # Should retrieve all technologies
        if output.filtered_count == output.total_count:
            print(f"\n[INFO] Successfully retrieved all {output.filtered_count} technologies")

            # Show statistics
            total_docs = sum(tech.document_count for tech in output.technologies)
            avg_docs = total_docs / output.filtered_count if output.filtered_count > 0 else 0

            print(f"\n[STATS] Total documents across all technologies: {total_docs:,}")
            print(f"[STATS] Average documents per technology: {avg_docs:.1f}")

            # Doc type distribution
            doc_types = {}
            for tech in output.technologies:
                for doc_type, count in tech.doc_type_breakdown.items():
                    doc_types[doc_type] = doc_types.get(doc_type, 0) + count

            print(f"\n[STATS] Document Type Distribution:")
            for doc_type, count in sorted(doc_types.items(), key=lambda x: x[1], reverse=True):
                print(f"  {doc_type:<20} {count:>6,}")

            # Community distribution
            community_counts = {}
            for tech in output.technologies:
                if tech.community_id is not None:
                    community_counts[tech.community_id] = community_counts.get(tech.community_id, 0) + 1

            print(f"\n[STATS] Technologies with community assignment: {len(community_counts)} unique communities")
            print(f"[STATS] Technologies without community: {sum(1 for t in output.technologies if t.community_id is None)}")

            print(f"\n[PASS] Test 3 passed - Retrieved all {output.filtered_count} technologies")
            return True
        else:
            print(f"\n[WARN] Retrieved {output.filtered_count} != Total {output.total_count}")
            return False

    finally:
        await client.close()


async def test_specific_technology():
    """Test 4: Verify solid_state_battery is in the list."""
    print("\n" + "="*80)
    print("TEST 4: Verify Specific Technology (solid_state_battery)")
    print("="*80)

    client = Neo4jClient()
    await client.connect()

    try:
        output = await discover_technologies(
            driver=client.driver,
            limit=None
        )

        # Find solid_state_battery
        ssbattery = next((t for t in output.technologies if t.id == "solid_state_battery"), None)

        if ssbattery:
            print(f"\n[FOUND] solid_state_battery technology:")
            print(f"  ID: {ssbattery.id}")
            print(f"  Name: {ssbattery.name}")
            print(f"  Domain: {ssbattery.domain}")
            print(f"  Document Count: {ssbattery.document_count}")
            print(f"  Doc Type Breakdown: {ssbattery.doc_type_breakdown}")
            print(f"  Companies: {ssbattery.companies}")
            print(f"  Community ID: {ssbattery.community_id}")
            print(f"  PageRank: {ssbattery.pagerank:.6f}")

            print(f"\n[PASS] Test 4 passed - solid_state_battery found and validated")
            return True
        else:
            print(f"\n[FAIL] Test 4 failed - solid_state_battery not found in graph")
            return False

    finally:
        await client.close()


async def main():
    """Run all Agent 1 tests."""
    print("\n" + "="*80)
    print("AGENT 1: TECH DISCOVERY - TEST SUITE")
    print("="*80)

    tests = [
        ("Test 1: Single Technology", test_single_technology),
        ("Test 2: Top 10 Technologies", test_top_10_technologies),
        ("Test 3: Full Technology List", test_full_technology_list),
        ("Test 4: Specific Technology (solid_state_battery)", test_specific_technology),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n[ERROR] {test_name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")

    print(f"\nTotal: {total} tests")
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")

    if passed == total:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print("\n[FAILURE] Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
