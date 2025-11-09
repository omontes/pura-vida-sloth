"""
Test Phase 2B: Hybrid Clustering (Incremental)
"""

from dotenv import load_dotenv
load_dotenv()

import json
from graph.entity_resolution.hybrid_clusterer import HybridClusterer
from graph.entity_resolution.schemas import NormalizedMention
from graph.entity_resolution.config import EntityResolutionConfig


def main():
    """Test Phase 2B with 10 unmatched mentions first."""
    config = EntityResolutionConfig(industry="eVTOL")

    # Load unmatched mentions
    print("Loading unmatched mentions from Phase 2A...")
    with open(config.output_dir / "02a_unmatched_mentions.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    all_unmatched = [NormalizedMention(**item) for item in data]
    print(f"Total unmatched: {len(all_unmatched)}")

    # Test with first 10
    print("\n" + "="*80)
    print("TEST: Phase 2B with 10 unmatched mentions")
    print("="*80)

    test_mentions = all_unmatched[:10]
    print(f"\nTesting with {len(test_mentions)} mentions:")
    for i, m in enumerate(test_mentions, 1):
        print(f"  {i}. {m.original_name} (occurrences: {m.occurrence_count})")

    # Run clustering
    clusterer = HybridClusterer(config)
    clusters = clusterer.run(test_mentions)

    print(f"\n" + "="*80)
    print(f"RESULTS: Created {len(clusters)} clusters")
    print("="*80)

    # Show clusters
    for i, cluster in enumerate(clusters, 1):
        print(f"\nCluster {i} (size={cluster.size}, avg_sim={cluster.avg_cluster_similarity:.2f}):")
        for name in cluster.mention_names:
            print(f"  - {name}")

    print(f"\n" + "="*80)
    print(f"APPROVAL NEEDED for full run:")
    print(f"  - Total unmatched mentions: {len(all_unmatched)}")
    print(f"  - Estimated clusters: ~{len(all_unmatched) // 2} (rough estimate)")
    print(f"  - Processing time: ~10-15 minutes")
    print(f"="*80)


if __name__ == "__main__":
    main()
