"""
Test Full Pipeline - End-to-end test of 12-agent hype cycle system.

Usage:
    python agents/test_full_pipeline.py
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.neo4j_client import Neo4jClient
from agents.langgraph_orchestrator import (
    analyze_single_technology,
    generate_hype_cycle_chart,
)


async def test_single_technology():
    """Test pipeline with single technology."""
    print("\n" + "="*80)
    print("TEST 1: Single Technology Analysis (solid_state_battery)")
    print("="*80)

    client = Neo4jClient()
    await client.connect()

    try:
        result = await analyze_single_technology(
            driver=client.driver,
            tech_id="solid_state_battery",
            tech_name="Solid-State Battery"
        )

        print(f"\n[RESULT] Technology: {result['tech_id']}")
        print(f"\n[SCORES]")
        print(f"  Innovation: {result.get('innovation_score', 0):.1f}/100")
        print(f"  Adoption: {result.get('adoption_score', 0):.1f}/100")
        print(f"  Narrative: {result.get('narrative_score', 0):.1f}/100")
        print(f"  Risk: {result.get('risk_score', 0):.1f}/100")
        print(f"  Hype: {result.get('hype_score', 0):.1f}/100")

        print(f"\n[POSITIONING]")
        print(f"  Phase: {result.get('hype_cycle_phase', 'unknown')}")
        print(f"  X (maturity): {result.get('x_position', 0):.1f}")
        print(f"  Y (expectations): {result.get('y_position', 0):.1f}")

        print(f"\n[ANALYSIS]")
        print(f"  {result.get('executive_summary', 'N/A')}")

        print(f"\n[VALIDATION]")
        print(f"  Status: {result.get('validation_status', 'unknown')}")
        if result.get('validation_errors'):
            print(f"  Errors: {result['validation_errors']}")

        print("\n[PASS] Single technology analysis completed")
        return True

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await client.close()


async def test_multiple_technologies():
    """Test pipeline with 100 technologies."""
    print("\n" + "="*80)
    print("TEST 2: Multiple Technologies Analysis (100 technologies)")
    print("="*80)

    client = Neo4jClient()
    await client.connect()

    try:
        chart = await generate_hype_cycle_chart(
            driver=client.driver,
            limit=100
        )

        print(f"\n[RESULT] Generated chart with {len(chart['technologies'])} technologies")

        print(f"\n[TECHNOLOGIES]")
        print(f"{'Tech ID':<35} {'Phase':<35} {'chart_x':<8} {'Position':<8}")
        print("-" * 95)

        for tech in chart['technologies']:
            phase = tech.get('phase', 'Unknown')
            chart_x = tech.get('chart_x', 0)
            phase_pos = tech.get('phase_position', 'mid')
            print(f"{tech['id']:<35} {phase:<35} {chart_x:<8.3f} {phase_pos:<8}")

        print(f"\n[PHASE DISTRIBUTION]")
        for phase, count in chart['metadata']['phases'].items():
            print(f"  {phase}: {count}")

        # Save to file
        output_file = "hype_cycle_chart.json"
        with open(output_file, "w") as f:
            json.dump(chart, f, indent=2)

        print(f"\n[OUTPUT] Saved to {output_file}")
        print("\n[PASS] Multiple technology analysis completed")
        return True

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await client.close()


async def main():
    """Run all pipeline tests."""
    print("\n" + "="*80)
    print("FULL PIPELINE TEST - 12-Agent Hype Cycle System")
    print("="*80)

    tests = [
        #("Single Technology Analysis", test_single_technology),
        ("Multiple Technologies (100)", test_multiple_technologies),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n[ERROR] {test_name} failed: {e}")
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

    if passed == total:
        print("\n[SUCCESS] All pipeline tests passed!")
        return 0
    else:
        print("\n[FAILURE] Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
