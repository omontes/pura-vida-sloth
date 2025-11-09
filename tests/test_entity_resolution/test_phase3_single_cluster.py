"""
Test Phase 3: LLM Canonicalization with 1 Cluster
"""

from dotenv import load_dotenv
load_dotenv()

import json
from graph.entity_resolution.llm_canonicalizer import LLMCanonicalizer
from graph.entity_resolution.schemas import TechnologyCluster
from graph.entity_resolution.config import EntityResolutionConfig


def main():
    """Test Phase 3 with 1 cluster - largest cluster for best example."""
    config = EntityResolutionConfig(industry="eVTOL")

    # Load clusters from Phase 2B
    print("Loading clusters from Phase 2B...")
    with open(config.output_dir / "02b_mention_clusters.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    all_clusters = [TechnologyCluster(**item) for item in data]
    print(f"Total clusters: {len(all_clusters)}")

    # Get the largest cluster (most variants) for best test
    largest_cluster = max(all_clusters, key=lambda c: c.size)

    print("\n" + "="*80)
    print("TEST: Phase 3 with 1 CLUSTER (Largest cluster)")
    print("="*80)
    print(f"\nCluster ID: {largest_cluster.cluster_id}")
    print(f"Size: {largest_cluster.size} variants")
    print(f"Avg similarity: {largest_cluster.avg_cluster_similarity:.2f}")

    print(f"\nVariants:")
    for i, name in enumerate(largest_cluster.mention_names, 1):
        meta = largest_cluster.mention_metadata.get(name, {})
        print(f"  {i}. {name}")
        print(f"     - {meta.get('occurrence_count', 0)} occurrences")
        print(f"     - Strength: {meta.get('avg_strength', 0):.2f}, Confidence: {meta.get('avg_confidence', 0):.2f}")
        print(f"     - Roles: {', '.join(meta.get('roles', []))}")

    # Initialize canonicalizer
    print("\n" + "="*80)
    print("Initializing LLM Canonicalizer...")
    canonicalizer = LLMCanonicalizer(config)

    # Show formatted prompt
    print("\n" + "="*80)
    print("PROMPT SENT TO LLM:")
    print("="*80)
    prompt = canonicalizer._format_cluster_for_llm(largest_cluster)
    print(prompt)
    print("="*80)

    # Run canonicalization
    print("\n" + "="*80)
    print("Calling LLM API (gpt-4o-mini)...")
    print("="*80)

    result = canonicalizer.canonicalize_cluster(largest_cluster)

    if result:
        print("\n" + "="*80)
        print("LLM RESULT:")
        print("="*80)
        print(f"Canonical Name: {result.canonical_name}")
        print(f"Domain: {result.domain}")
        print(f"Description: {result.description}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"\nReasoning:")
        print(f"  {result.reasoning}")
        print("="*80)

        print(f"\nCost: ${canonicalizer.total_cost:.6f}")
        print(f"Tokens: {canonicalizer.total_tokens}")
    else:
        print("\n[ERROR] Failed to canonicalize cluster")

    print("\n" + "="*80)
    print("[SUCCESS] Phase 3 Test (1 cluster) Complete!")
    print("="*80)
    print("\nNext: Test with 10 clusters")


if __name__ == "__main__":
    main()
