"""
Run Phase 2B: Full Clustering (2,108 unmatched mentions)
"""

from dotenv import load_dotenv
load_dotenv()

import json
from graph.entity_resolution.hybrid_clusterer import HybridClusterer
from graph.entity_resolution.schemas import NormalizedMention
from graph.entity_resolution.config import EntityResolutionConfig


def main():
    """Run Phase 2B with ALL 2,108 unmatched mentions."""
    config = EntityResolutionConfig(industry="eVTOL")

    # Load ALL unmatched mentions
    print("Loading unmatched mentions from Phase 2A...")
    with open(config.output_dir / "02a_unmatched_mentions.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    all_unmatched = [NormalizedMention(**item) for item in data]
    print(f"Total unmatched: {len(all_unmatched)}")

    print("\n" + "="*80)
    print("PHASE 2B: FULL RUN - Hybrid Clustering")
    print("="*80)
    print(f"Processing: {len(all_unmatched)} mentions")
    print(f"Method: BM25 (40%) + Semantic (60%)")
    print(f"Threshold: 0.85")
    print(f"Estimated time: 10-15 minutes")
    print("="*80)

    # Run clustering
    clusterer = HybridClusterer(config)
    clusters = clusterer.run(all_unmatched)

    print(f"\n" + "="*80)
    print(f"[SUCCESS] Phase 2B Complete!")
    print(f"="*80)
    print(f"Total clusters created: {len(clusters)}")
    print(f"Output: graph/entity_resolution/output/02b_mention_clusters.json")
    print(f"\nNext: Phase 3 - LLM Canonicalization")
    print(f"  - Test with 1 cluster first")
    print(f"  - Then test with 10 clusters")
    print(f"  - Evaluate results before full run")
    print(f"="*80)


if __name__ == "__main__":
    main()
