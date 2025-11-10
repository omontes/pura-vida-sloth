"""
Tests for Agent 3: Adoption Scorer

Test Pattern: 1 → 3 → 20
1. Single technology scoring (solid_state_battery)
2. Three technologies (diverse domains)
3. Batch of 20 technologies (validate consistency)
"""

import asyncio
import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.graph.neo4j_client import Neo4jClient
from agents.agent_03_adoption.agent import score_adoption
from agents.agent_01_tech_discovery.agent import discover_technologies


async def test_single_technology():
    """Test 1: Score single technology (solid_state_battery)."""
    print("\n" + "="*80)
    print("TEST 1: Single Technology Adoption Scoring")
    print("="*80)

    client = Neo4jClient()
    await client.connect()

    try:
        print("\n[INFO] Scoring: solid_state_battery")

        output = await score_adoption(
            driver=client.driver,
            tech_id="solid_state_battery",
            start_date="2023-07-01",
            end_date="2025-01-01",
        )

        print(f"\n[RESULT] Adoption Score: {output.adoption_score:.1f}/100")
        print(f"[RESULT] Confidence: {output.confidence}")
        print(f"\n[REASONING] {output.reasoning}")

        # Print key metrics
        metrics = output.key_metrics
        print(f"\n[METRICS] Government Contracts:")
        print(f"  - Contract count (1yr): {metrics.gov_contract_count_1yr}")
        print(f"  - Total value: ${metrics.gov_contract_total_value:,.0f}")
        print(f"  - Avg value: ${metrics.gov_contract_avg_value:,.0f}")

        print(f"\n[METRICS] Regulatory & Company Activity:")
        print(f"  - Regulatory approvals: {metrics.regulatory_approval_count}")
        print(f"  - Companies developing: {metrics.companies_developing}")
        print(f"  - Top companies: {', '.join(metrics.top_companies) if metrics.top_companies else 'None'}")

        # Validation
        assert 0 <= output.adoption_score <= 100, "Score must be 0-100"
        assert output.confidence in ["high", "medium", "low"], "Confidence must be high/medium/low"
        assert len(output.reasoning) > 20, "Reasoning should be substantive"

        print("\n[PASS] Test 1 passed - Single technology scored successfully")
        return True

    except Exception as e:
        print(f"\n[FAIL] Test 1 failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await client.close()


async def test_three_technologies():
    """Test 2: Score three technologies from different domains."""
    print("\n" + "="*80)
    print("TEST 2: Three Technologies - Diverse Domains")
    print("="*80)

    client = Neo4jClient()
    await client.connect()

    try:
        # Get top 3 technologies by document count (diverse representation)
        tech_discovery = await discover_technologies(
            driver=client.driver,
            limit=3
        )

        print(f"\n[INFO] Discovered {len(tech_discovery.technologies)} technologies")
        print(f"\n{'Tech ID':<30} {'Domain':<20} {'Score':<10} {'Confidence':<12}")
        print("-" * 75)

        results = []
        for tech in tech_discovery.technologies:
            output = await score_adoption(
                driver=client.driver,
                tech_id=tech.id,
            )

            results.append(output)
            print(f"{tech.id:<30} {tech.domain or 'Unknown':<20} {output.adoption_score:<10.1f} {output.confidence:<12}")

        # Validation
        assert len(results) == 3, "Should score 3 technologies"
        for output in results:
            assert 0 <= output.adoption_score <= 100, f"{output.tech_id}: Score out of range"
            assert output.confidence in ["high", "medium", "low"], f"{output.tech_id}: Invalid confidence"

        print("\n[PASS] Test 2 passed - Three technologies scored successfully")
        return True

    except Exception as e:
        print(f"\n[FAIL] Test 2 failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await client.close()


async def test_batch_scoring():
    """Test 3: Score batch of 20 technologies (validate consistency)."""
    print("\n" + "="*80)
    print("TEST 3: Batch Scoring - 20 Technologies")
    print("="*80)

    client = Neo4jClient()
    await client.connect()

    try:
        # Get top 20 technologies by document count
        tech_discovery = await discover_technologies(
            driver=client.driver,
            limit=20
        )

        print(f"\n[INFO] Scoring {len(tech_discovery.technologies)} technologies...")

        results = []
        for i, tech in enumerate(tech_discovery.technologies, start=1):
            print(f"[{i}/20] Scoring: {tech.id}...", end=" ")

            output = await score_adoption(
                driver=client.driver,
                tech_id=tech.id,
            )

            results.append(output)
            print(f"Score: {output.adoption_score:.1f}")

        # Statistics
        scores = [r.adoption_score for r in results]
        avg_score = sum(scores) / len(scores)
        min_score = min(scores)
        max_score = max(scores)

        print(f"\n[STATS] Score Distribution:")
        print(f"  Average: {avg_score:.1f}")
        print(f"  Min: {min_score:.1f}")
        print(f"  Max: {max_score:.1f}")
        print(f"  Range: {max_score - min_score:.1f}")

        # Confidence distribution
        confidence_counts = {"high": 0, "medium": 0, "low": 0}
        for r in results:
            confidence_counts[r.confidence] += 1

        print(f"\n[STATS] Confidence Distribution:")
        print(f"  High: {confidence_counts['high']}")
        print(f"  Medium: {confidence_counts['medium']}")
        print(f"  Low: {confidence_counts['low']}")

        # Show top 5 and bottom 5
        sorted_results = sorted(results, key=lambda x: x.adoption_score, reverse=True)

        print(f"\n[STATS] Top 5 Adoption Scores:")
        print(f"{'Rank':<6} {'Tech ID':<30} {'Score':<10}")
        print("-" * 50)
        for i, r in enumerate(sorted_results[:5], start=1):
            print(f"{i:<6} {r.tech_id:<30} {r.adoption_score:<10.1f}")

        print(f"\n[STATS] Bottom 5 Adoption Scores:")
        print(f"{'Rank':<6} {'Tech ID':<30} {'Score':<10}")
        print("-" * 50)
        for i, r in enumerate(sorted_results[-5:], start=16):
            print(f"{i:<6} {r.tech_id:<30} {r.adoption_score:<10.1f}")

        # Validation
        assert len(results) == 20, "Should score 20 technologies"
        for output in results:
            assert 0 <= output.adoption_score <= 100, f"{output.tech_id}: Score out of range"
            assert output.confidence in ["high", "medium", "low"], f"{output.tech_id}: Invalid confidence"

        print("\n[PASS] Test 3 passed - Batch scoring completed successfully")
        return True

    except Exception as e:
        print(f"\n[FAIL] Test 3 failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await client.close()


async def main():
    """Run all Agent 3 tests."""
    print("\n" + "="*80)
    print("AGENT 3: ADOPTION SCORER - TEST SUITE")
    print("="*80)

    tests = [
        ("Test 1: Single Technology (solid_state_battery)", test_single_technology),
        ("Test 2: Three Technologies (Diverse Domains)", test_three_technologies),
        ("Test 3: Batch Scoring (20 Technologies)", test_batch_scoring),
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
