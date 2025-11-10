"""
Run Phase 3: Full LLM Canonicalization (1,839 clusters)
With async concurrent processing for faster execution
"""

from dotenv import load_dotenv
load_dotenv()

import json
from graph.entity_resolution.llm_canonicalizer import LLMCanonicalizer
from graph.entity_resolution.schemas import TechnologyCluster
from graph.entity_resolution.config import EntityResolutionConfig


def main():
    """Run Phase 3 with ALL 1,839 clusters using async processing."""
    config = EntityResolutionConfig(industry="eVTOL")

    # Load clusters from Phase 2B
    print("Loading clusters from Phase 2B...")
    with open(config.output_dir / "02b_mention_clusters.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    all_clusters = [TechnologyCluster(**item) for item in data]
    print(f"Total clusters: {len(all_clusters)}")

    print("\n" + "="*80)
    print("PHASE 3: FULL RUN - LLM Canonicalization")
    print("="*80)
    print(f"Processing: {len(all_clusters)} clusters")
    print(f"Mode: Async Concurrent (20 parallel requests)")
    print(f"Model: gpt-4o-mini")
    print(f"Estimated time: 3-5 minutes")
    print(f"Estimated cost: ~$0.40")
    print("="*80)

    # Initialize canonicalizer
    print("\nInitializing LLM Canonicalizer...")
    canonicalizer = LLMCanonicalizer(config)

    # Run with async processing enabled
    print("\nStarting canonicalization...")
    results = canonicalizer.run(all_clusters, use_async=True)

    print(f"\n" + "="*80)
    print("[SUCCESS] Phase 3 Complete!")
    print("="*80)
    print(f"Total clusters canonicalized: {len(results)}")
    print(f"Total cost: ${canonicalizer.total_cost:.4f}")
    print(f"Total tokens: {canonicalizer.total_tokens:,}")
    print(f"\nOutput file: graph/entity_resolution/output/03_llm_canonical_names.json")

    # Show top 10 results
    print(f"\nTop 10 Canonical Names (by cluster size):")
    for i, result in enumerate(results[:10], 1):
        print(f"  {i}. {result.canonical_name} ({result.domain})")
        print(f"     Confidence: {result.confidence:.2f}, Variants: {len(result.input_variants)}")

    print(f"\n{'='*80}")
    print("Next Steps:")
    print("  1. Review canonical names in 03_llm_canonical_names.json")
    print("  2. Run Phase 4-8 to complete the pipeline")
    print("  3. Validate final catalog quality")
    print("="*80)


if __name__ == "__main__":
    main()
