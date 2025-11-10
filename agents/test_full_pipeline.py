"""
Test Full Pipeline - End-to-end test of 12-agent hype cycle system.

Usage:
    python agents/test_full_pipeline.py                      # Default: 50 techs, normal logging
    python agents/test_full_pipeline.py -v                   # Verbose mode (agent I/O)
    python agents/test_full_pipeline.py -vv                  # Debug mode (LLM prompts)
    python agents/test_full_pipeline.py --tech-count 100     # Analyze 100 technologies
    python agents/test_full_pipeline.py --community v2       # Use v2 communities
    python agents/test_full_pipeline.py --no-tavily          # Disable Tavily search
"""

import asyncio
import json
import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.neo4j_client import Neo4jClient
from agents.langgraph_orchestrator import (
    analyze_single_technology,
    generate_hype_cycle_chart,
)
from agents.chart_normalization_ranked import normalize_chart
from agents.shared.logger import AgentLogger, LogLevel


async def test_single_technology(logger: AgentLogger, enable_tavily: bool = True):
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
            tech_name="Solid-State Battery",
            logger=logger,
            enable_tavily=enable_tavily
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


async def test_multiple_technologies(
    logger: AgentLogger,
    tech_count: int = 50,
    community_version: str = "v1",
    enable_tavily: bool = True,
    min_docs: int = 5
):
    """Test pipeline with multiple technologies."""
    print("\n" + "="*80)
    print(f"TEST 2: Multiple Technologies Analysis ({tech_count} technologies)")
    print("="*80)

    client = Neo4jClient()
    await client.connect()

    try:
        chart = await generate_hype_cycle_chart(
            driver=client.driver,
            limit=tech_count,
            logger=logger,
            enable_tavily=enable_tavily,
            community_version=community_version,
            min_document_count=min_docs
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

        # Generate normalized chart
        print(f"\n[NORMALIZATION] Generating normalized chart...")
        try:
            normalized_chart = normalize_chart(
                input_file=output_file,
                output_file="hype_cycle_chart_normalized.json",
                top_n=5
            )
            if normalized_chart:
                print(f"[OK] Normalized chart saved to hype_cycle_chart_normalized.json")
        except Exception as e:
            print(f"[WARN] Normalization failed: {e}")
            # Continue anyway - original chart is still valid

        print(f"\n[OUTPUT] Charts generated:")
        print(f"  - Original: {output_file} ({len(chart['technologies'])} technologies)")
        print(f"  - Normalized: hype_cycle_chart_normalized.json (top 10 per phase)")
        print("\n[PASS] Multiple technology analysis completed")
        return True

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await client.close()


def parse_args():
    """Parse CLI arguments for pipeline configuration."""
    parser = argparse.ArgumentParser(
        description="Test full hype cycle analysis pipeline with configurable parameters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python agents/test_full_pipeline.py                      # Default: 50 techs, normal logging
  python agents/test_full_pipeline.py -v                   # Verbose mode (agent I/O)
  python agents/test_full_pipeline.py -vv                  # Debug mode (LLM prompts)
  python agents/test_full_pipeline.py --tech-count 100     # Analyze 100 technologies
  python agents/test_full_pipeline.py --community v2       # Use v2 communities
  python agents/test_full_pipeline.py --no-tavily          # Disable Tavily search
        """
    )

    # Verbosity control
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Increase verbosity: -v for agent I/O, -vv for LLM prompts (default: normal)"
    )

    # Pipeline configuration
    parser.add_argument(
        "--tech-count",
        type=int,
        default=50,
        help="Number of technologies to analyze (default: 50)"
    )

    parser.add_argument(
        "--community",
        type=str,
        choices=["v0", "v1", "v2"],
        default="v1",
        help="Community version for tech discovery (default: v1)"
    )

    parser.add_argument(
        "--no-tavily",
        action="store_true",
        help="Disable Tavily real-time search (default: enabled)"
    )

    parser.add_argument(
        "--min-docs",
        type=int,
        default=5,
        help="Minimum document count per technology (default: 5)"
    )

    # Logging output
    parser.add_argument(
        "--log-file",
        type=str,
        default="pipeline_logs.json",
        help="Path to save structured JSON logs (default: pipeline_logs.json)"
    )

    # Test selection
    parser.add_argument(
        "--single-tech",
        action="store_true",
        help="Run single technology test (solid_state_battery)"
    )

    return parser.parse_args()


async def main():
    """Run all pipeline tests."""
    args = parse_args()

    # Map verbosity to LogLevel
    if args.verbose == 0:
        log_level = LogLevel.NORMAL
    elif args.verbose == 1:
        log_level = LogLevel.VERBOSE
    else:  # args.verbose >= 2
        log_level = LogLevel.DEBUG

    # Initialize logger
    logger = AgentLogger(level=log_level, log_file=args.log_file)

    print("\n" + "="*80)
    print("FULL PIPELINE TEST - 12-Agent Hype Cycle System")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  Tech Count: {args.tech_count}")
    print(f"  Community Version: {args.community}")
    print(f"  Tavily Search: {'disabled' if args.no_tavily else 'enabled'}")
    print(f"  Min Documents: {args.min_docs}")
    print(f"  Verbosity: {log_level.name}")
    print(f"  Log File: {args.log_file}")

    enable_tavily = not args.no_tavily

    # Build test suite based on arguments
    tests = []
    if args.single_tech:
        tests.append(("Single Technology Analysis",
                     lambda: test_single_technology(logger, enable_tavily)))
    else:
        tests.append(("Multiple Technologies",
                     lambda: test_multiple_technologies(
                         logger,
                         args.tech_count,
                         args.community,
                         enable_tavily,
                         args.min_docs
                     )))

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
