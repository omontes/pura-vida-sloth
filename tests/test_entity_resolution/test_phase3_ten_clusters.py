"""
Test Phase 3: LLM Canonicalization with 10 Clusters
"""

from dotenv import load_dotenv
load_dotenv()

import json
from graph.entity_resolution.llm_canonicalizer import LLMCanonicalizer
from graph.entity_resolution.schemas import TechnologyCluster
from graph.entity_resolution.config import EntityResolutionConfig


def main():
    """Test Phase 3 with 10 clusters - mix of different sizes."""
    config = EntityResolutionConfig(industry="eVTOL")

    # Load clusters from Phase 2B
    print("Loading clusters from Phase 2B...")
    with open(config.output_dir / "02b_mention_clusters.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    all_clusters = [TechnologyCluster(**item) for item in data]
    print(f"Total clusters: {len(all_clusters)}")

    # Get top 10 largest clusters (most interesting for testing)
    top_10_clusters = sorted(all_clusters, key=lambda c: c.size, reverse=True)[:10]

    print("\n" + "="*80)
    print("TEST: Phase 3 with 10 CLUSTERS (Top 10 largest)")
    print("="*80)
    print("\nClusters to process:")
    for i, cluster in enumerate(top_10_clusters, 1):
        print(f"  {i}. Cluster {cluster.cluster_id}: {cluster.size} variants, avg_sim={cluster.avg_cluster_similarity:.2f}")
        print(f"     Preview: {cluster.mention_names[0]}")
        if cluster.size > 1:
            print(f"              {cluster.mention_names[1]}")

    # Initialize canonicalizer
    print("\n" + "="*80)
    print("Initializing LLM Canonicalizer...")
    canonicalizer = LLMCanonicalizer(config)

    # Run canonicalization on 10 clusters with async processing
    print("\n" + "="*80)
    print("Processing 10 clusters with LLM (gpt-4o-mini) - ASYNC MODE")
    print("="*80)

    # Use async processing for speed test
    results = canonicalizer.run(top_10_clusters, use_async=True)

    # Results already saved and printed by run() method
    results = results  # Already processed

    # Display summary
    print("\n" + "="*80)
    print("PHASE 3 RESULTS SUMMARY (10 clusters)")
    print("="*80)

    for i, result in enumerate(results, 1):
        print(f"\n{i}. Cluster {result.cluster_id} ({len(result.input_variants)} variants)")
        print(f"   Canonical Name: {result.canonical_name}")
        print(f"   Domain: {result.domain}")
        print(f"   Confidence: {result.confidence:.2f}")
        print(f"   Input variants: {', '.join(result.input_variants[:3])}")
        if len(result.input_variants) > 3:
            print(f"                   ... and {len(result.input_variants) - 3} more")
        print(f"   Reasoning: {result.reasoning[:150]}...")

    print("\n" + "="*80)
    print("COST & PERFORMANCE")
    print("="*80)
    print(f"Total cost: ${canonicalizer.total_cost:.4f}")
    print(f"Total tokens: {canonicalizer.total_tokens}")
    print(f"Average cost per cluster: ${canonicalizer.total_cost / len(results):.6f}")
    print(f"Average tokens per cluster: {canonicalizer.total_tokens / len(results):.0f}")

    # Estimate full run cost
    total_clusters = len(all_clusters)
    estimated_full_cost = (canonicalizer.total_cost / len(results)) * total_clusters
    estimated_full_tokens = (canonicalizer.total_tokens / len(results)) * total_clusters

    print("\n" + "="*80)
    print("FULL RUN ESTIMATES")
    print("="*80)
    print(f"Total clusters: {total_clusters}")
    print(f"Estimated cost: ${estimated_full_cost:.2f}")
    print(f"Estimated tokens: {estimated_full_tokens:,.0f}")
    print(f"Estimated time: ~{total_clusters * 0.5 / 60:.0f} minutes")

    print("\n" + "="*80)
    print("[SUCCESS] Phase 3 Test (10 clusters) Complete!")
    print("="*80)
    print("\nReady for user approval of full run.")


if __name__ == "__main__":
    main()
