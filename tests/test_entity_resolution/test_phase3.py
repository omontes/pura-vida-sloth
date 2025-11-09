"""
Test Phase 3: LLM Canonical Name Selection
"""

from dotenv import load_dotenv
load_dotenv()  # Load environment variables

from graph.entity_resolution.llm_canonicalizer import LLMCanonicalizer, load_clusters
from graph.entity_resolution.config import EntityResolutionConfig


def main():
    """Test Phase 3 with incremental limits: 1 cluster → 10 clusters → full."""
    print("=" * 80)
    print("TESTING PHASE 3: LLM CANONICAL NAME SELECTION")
    print("=" * 80)

    # Load configuration
    config = EntityResolutionConfig(industry="eVTOL")

    # Load clusters from Phase 2B
    print("\nLoading clusters from Phase 2B...")
    clusters = load_clusters(config, "02b_mention_clusters.json")
    print(f"Loaded {len(clusters)} clusters")

    # Initialize LLM canonicalizer
    canonicalizer = LLMCanonicalizer(config)

    # Test 1: Process 1 cluster first
    print("\n" + "=" * 80)
    print("TEST 1: Processing 1 cluster...")
    print("=" * 80)

    results_1 = canonicalizer.run(clusters, limit=1)

    print(f"\nTest 1 complete!")
    print(f"  Processed: {len(results_1)} cluster")
    print(f"  Cost: ${canonicalizer.total_cost:.4f}")

    if results_1:
        result = results_1[0]
        print(f"\nResult:")
        print(f"  Canonical Name: {result.canonical_name}")
        print(f"  Domain: {result.domain}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Variants: {result.input_variants}")
        print(f"  Reasoning: {result.reasoning}")

    # Ask user for approval to continue
    print("\n" + "=" * 80)
    response = input("\nProceed with 10 clusters? (y/n): ")

    if response.lower() != 'y':
        print("Stopping at Test 1.")
        return

    # Test 2: Process 10 clusters
    print("\n" + "=" * 80)
    print("TEST 2: Processing 10 clusters...")
    print("=" * 80)

    # Reset cost tracking
    canonicalizer.total_cost = 0.0
    canonicalizer.total_tokens = 0

    results_10 = canonicalizer.run(clusters, limit=10)

    print(f"\nTest 2 complete!")
    print(f"  Processed: {len(results_10)} clusters")
    print(f"  Cost: ${canonicalizer.total_cost:.4f}")

    # Show sample results
    if results_10:
        print(f"\nSample results:")
        for i, result in enumerate(results_10[:5], 1):
            print(f"\n  {i}. {result.canonical_name} (confidence: {result.confidence:.2f})")
            print(f"     Domain: {result.domain}")
            variants_preview = result.input_variants[0] if result.input_variants else "N/A"
            if len(result.input_variants) > 1:
                variants_preview += f" (+{len(result.input_variants)-1} more)"
            print(f"     Variants: {variants_preview}")

    # Ask user for approval to run full dataset
    print("\n" + "=" * 80)
    response = input("\nProceed with FULL dataset? (y/n): ")

    if response.lower() != 'y':
        print("Stopping at Test 2.")
        return

    # Full run
    print("\n" + "=" * 80)
    print("FULL RUN: Processing all clusters...")
    print("=" * 80)

    # Reset cost tracking
    canonicalizer.total_cost = 0.0
    canonicalizer.total_tokens = 0

    results_full = canonicalizer.run(clusters, limit=None)

    print(f"\nFull run complete!")
    print(f"  Processed: {len(results_full)} clusters")
    print(f"  Total cost: ${canonicalizer.total_cost:.4f}")


if __name__ == "__main__":
    main()
