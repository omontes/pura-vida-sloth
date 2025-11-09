"""
Test Phase 2B: Hybrid Clustering
"""

from dotenv import load_dotenv
load_dotenv()  # Load environment variables

from graph.entity_resolution.hybrid_clusterer import HybridClusterer, load_unmatched_mentions
from graph.entity_resolution.config import EntityResolutionConfig


def main():
    """Test Phase 2B with unmatched mentions from Phase 2A."""
    print("=" * 80)
    print("TESTING PHASE 2B: HYBRID CLUSTERING")
    print("=" * 80)

    # Load configuration
    config = EntityResolutionConfig(industry="eVTOL")

    # Load unmatched mentions from Phase 2A
    print("\nLoading unmatched mentions from Phase 2A...")
    unmatched = load_unmatched_mentions(config, "02a_unmatched_mentions.json")
    print(f"Loaded {len(unmatched)} unmatched mentions")

    # Initialize clusterer
    clusterer = HybridClusterer(config)

    # Run clustering
    clusters = clusterer.run(unmatched)

    print(f"\nTest complete!")
    print(f"  Created {len(clusters)} clusters from {len(unmatched)} mentions")

    # Show sample clusters
    if clusters:
        print("\nSample clusters:")
        for i, cluster in enumerate(clusters[:5], 1):
            print(f"\n  Cluster {i} (size={cluster.size}, avg_sim={cluster.avg_cluster_similarity:.2f}):")
            for name in cluster.mention_names[:5]:
                print(f"    - {name}")
            if cluster.size > 5:
                print(f"    ... and {cluster.size - 5} more")


if __name__ == "__main__":
    main()
