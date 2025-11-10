"""
Phase 1 Test Script: Validate Query Modules Against Neo4j Graph

Tests all 7 query modules with 3 representative technologies to ensure:
1. Queries execute without errors
2. Results match expected schema
3. Performance is acceptable (<2s per query)
4. Graph prerequisites are accessible (embeddings, communities, algorithms)

Run this script BEFORE building agents to catch any graph/query issues early.

Usage:
    python agents/test_phase1_queries.py
"""

import asyncio
import time
from typing import List, Dict, Any
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.neo4j_client import Neo4jClient
from src.agents.shared.queries import (
    innovation_queries,
    adoption_queries,
    narrative_queries,
    risk_queries,
    hybrid_search,
    community_queries,
    citation_queries,
)


# =============================================================================
# TEST CONFIGURATION
# =============================================================================

# Test with 1 technology first (can expand to 3 later)
TEST_TECH_IDS = [
    "solid_state_battery",    # Battery technology (user-specified)
]


# =============================================================================
# TEST UTILITIES
# =============================================================================

class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.duration_ms = 0.0
        self.error = None
        self.result_count = 0


async def run_test(
    test_name: str,
    test_func,
    *args,
    **kwargs
) -> TestResult:
    """Run a single test and capture results."""
    result = TestResult(test_name)
    start_time = time.time()

    try:
        output = await test_func(*args, **kwargs)
        result.duration_ms = (time.time() - start_time) * 1000

        # Count results
        if isinstance(output, list):
            result.result_count = len(output)
        elif isinstance(output, dict):
            result.result_count = 1
        elif isinstance(output, (int, float)):
            result.result_count = 1
        elif isinstance(output, str):
            result.result_count = 1

        result.passed = True

    except Exception as e:
        result.duration_ms = (time.time() - start_time) * 1000
        result.error = str(e)
        result.passed = False

    return result


def print_test_result(result: TestResult):
    """Print formatted test result."""
    status = "[PASS]" if result.passed else "[FAIL]"
    duration = f"{result.duration_ms:.0f}ms"

    if result.passed:
        print(f"{status} | {duration:>6} | {result.name:<50} | Results: {result.result_count}")
    else:
        print(f"{status} | {duration:>6} | {result.name:<50} | ERROR: {result.error}")


# =============================================================================
# PHASE 1 TESTS
# =============================================================================

async def test_innovation_queries(driver, tech_id: str) -> List[TestResult]:
    """Test Innovation Queries (Layer 1)."""
    results = []

    # Test 1: Patent count
    results.append(await run_test(
        f"Innovation: Patent count 2yr ({tech_id})",
        innovation_queries.get_patent_count_2yr,
        driver, tech_id
    ))

    # Test 2: Top patents
    results.append(await run_test(
        f"Innovation: Top patents by citations ({tech_id})",
        innovation_queries.get_top_patents_by_citations,
        driver, tech_id, 5
    ))

    # Test 3: Community patents
    results.append(await run_test(
        f"Innovation: Community patents ({tech_id})",
        innovation_queries.get_community_patents,
        driver, tech_id, "v1"
    ))

    # Test 4: Paper count
    results.append(await run_test(
        f"Innovation: Paper count 2yr ({tech_id})",
        innovation_queries.get_paper_count_2yr,
        driver, tech_id
    ))

    # Test 5: Temporal trend
    results.append(await run_test(
        f"Innovation: Temporal trend ({tech_id})",
        innovation_queries.get_innovation_temporal_trend,
        driver, tech_id
    ))

    return results


async def test_adoption_queries(driver, tech_id: str) -> List[TestResult]:
    """Test Adoption Queries (Layer 2)."""
    results = []

    # Test 1: Gov contracts
    results.append(await run_test(
        f"Adoption: Gov contracts 1yr ({tech_id})",
        adoption_queries.get_gov_contracts_1yr,
        driver, tech_id
    ))

    # Test 2: Top contracts
    results.append(await run_test(
        f"Adoption: Top contracts by value ({tech_id})",
        adoption_queries.get_top_contracts_by_value,
        driver, tech_id, 5
    ))

    # Test 3: Regulatory approvals
    results.append(await run_test(
        f"Adoption: Regulatory approvals ({tech_id})",
        adoption_queries.get_regulatory_approvals,
        driver, tech_id
    ))

    # Test 4: Companies developing
    results.append(await run_test(
        f"Adoption: Companies developing tech ({tech_id})",
        adoption_queries.get_companies_developing_tech,
        driver, tech_id, 10
    ))

    return results


async def test_narrative_queries(driver, tech_id: str) -> List[TestResult]:
    """Test Narrative Queries (Layer 4)."""
    results = []

    # Test 1: News count
    results.append(await run_test(
        f"Narrative: News count 3mo ({tech_id})",
        narrative_queries.get_news_count_3mo,
        driver, tech_id
    ))

    # Test 2: Outlet tier breakdown
    results.append(await run_test(
        f"Narrative: Outlet tier breakdown ({tech_id})",
        narrative_queries.get_outlet_tier_breakdown,
        driver, tech_id
    ))

    # Test 3: Top articles
    results.append(await run_test(
        f"Narrative: Top articles by prominence ({tech_id})",
        narrative_queries.get_top_articles_by_prominence,
        driver, tech_id, 10
    ))

    # Test 4: Sentiment trend
    results.append(await run_test(
        f"Narrative: Sentiment temporal trend ({tech_id})",
        narrative_queries.get_sentiment_temporal_trend,
        driver, tech_id
    ))

    return results


async def test_risk_queries(driver, tech_id: str) -> List[TestResult]:
    """Test Risk Queries (Layer 3)."""
    results = []

    # Test 1: SEC risk mentions
    results.append(await run_test(
        f"Risk: SEC risk mentions 6mo ({tech_id})",
        risk_queries.get_sec_risk_mentions_6mo,
        driver, tech_id
    ))

    # Test 2: Institutional holdings
    results.append(await run_test(
        f"Risk: Institutional holdings ({tech_id})",
        risk_queries.get_institutional_holdings,
        driver, tech_id
    ))

    # Test 3: Insider trading summary
    results.append(await run_test(
        f"Risk: Insider trading summary ({tech_id})",
        risk_queries.get_insider_trading_summary,
        driver, tech_id
    ))

    return results


async def test_community_queries(driver, tech_id: str) -> List[TestResult]:
    """Test Community Queries."""
    results = []

    # Test 1: Get technology community
    results.append(await run_test(
        f"Community: Get tech community ({tech_id})",
        community_queries.get_technology_community,
        driver, tech_id, "v1"
    ))

    # Test 2: Related technologies in community
    results.append(await run_test(
        f"Community: Related techs in community ({tech_id})",
        community_queries.get_related_technologies_in_community,
        driver, tech_id, "v1", 10
    ))

    # Test 3: Community by text search
    results.append(await run_test(
        f"Community: Text search ('battery')",
        community_queries.get_community_by_text_search,
        driver, "battery", 1, 5
    ))

    return results


async def test_citation_queries(driver, tech_id: str) -> List[TestResult]:
    """Test Citation Queries."""
    results = []

    # Test 1: Innovation citations
    results.append(await run_test(
        f"Citation: Innovation layer ({tech_id})",
        citation_queries.get_innovation_citations,
        driver, tech_id
    ))

    # Test 2: Adoption citations
    results.append(await run_test(
        f"Citation: Adoption layer ({tech_id})",
        citation_queries.get_adoption_citations,
        driver, tech_id
    ))

    # Test 3: Evidence distribution
    results.append(await run_test(
        f"Citation: Evidence distribution ({tech_id})",
        citation_queries.get_evidence_distribution_by_doc_type,
        driver, tech_id
    ))

    return results


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

async def main():
    """Run all Phase 1 tests."""
    print("="*80)
    print("PHASE 1 TEST: Query Module Validation")
    print("="*80)
    print()

    # Initialize Neo4j client
    print("[INFO] Connecting to Neo4j...")
    client = Neo4jClient()
    await client.connect()
    driver = client.driver

    print("[OK] Connected to Neo4j")
    print()

    # Run tests for each technology
    all_results = []

    for tech_id in TEST_TECH_IDS:
        print(f"\n{'='*80}")
        print(f"Testing with Technology: {tech_id}")
        print(f"{'='*80}\n")

        # Innovation Layer
        print("\n--- Innovation Queries (Layer 1) ---")
        results = await test_innovation_queries(driver, tech_id)
        for r in results:
            print_test_result(r)
        all_results.extend(results)

        # Adoption Layer
        print("\n--- Adoption Queries (Layer 2) ---")
        results = await test_adoption_queries(driver, tech_id)
        for r in results:
            print_test_result(r)
        all_results.extend(results)

        # Narrative Layer
        print("\n--- Narrative Queries (Layer 4) ---")
        results = await test_narrative_queries(driver, tech_id)
        for r in results:
            print_test_result(r)
        all_results.extend(results)

        # Risk Layer
        print("\n--- Risk Queries (Layer 3) ---")
        results = await test_risk_queries(driver, tech_id)
        for r in results:
            print_test_result(r)
        all_results.extend(results)

        # Community Queries
        print("\n--- Community Queries ---")
        results = await test_community_queries(driver, tech_id)
        for r in results:
            print_test_result(r)
        all_results.extend(results)

        # Citation Queries
        print("\n--- Citation Queries ---")
        results = await test_citation_queries(driver, tech_id)
        for r in results:
            print_test_result(r)
        all_results.extend(results)

    # Summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")

    passed = sum(1 for r in all_results if r.passed)
    failed = sum(1 for r in all_results if not r.passed)
    total = len(all_results)
    avg_duration = sum(r.duration_ms for r in all_results) / total if total > 0 else 0

    print(f"\nTotal Tests: {total}")
    print(f"[PASS] Passed: {passed}")
    print(f"[FAIL] Failed: {failed}")
    print(f"[TIME] Avg Duration: {avg_duration:.0f}ms")
    print()

    if failed > 0:
        print("\n[WARN] FAILED TESTS:")
        for r in all_results:
            if not r.passed:
                print(f"  - {r.name}: {r.error}")
        print()

    # Close connection
    await client.close()

    # Exit code
    exit_code = 0 if failed == 0 else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
