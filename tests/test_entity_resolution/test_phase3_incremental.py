"""
Test Phase 3: LLM Canonicalization (Incremental)
"""

from dotenv import load_dotenv
load_dotenv()

import json
from graph.entity_resolution.llm_canonicalizer import LLMCanonicalizer
from graph.entity_resolution.schemas import TechnologyCluster
from graph.entity_resolution.config import EntityResolutionConfig


def main():
    """Test Phase 3 with 1 cluster to validate enhanced metadata in LLM prompt."""
    config = EntityResolutionConfig(industry="eVTOL")

    # Load clusters from Phase 2B
    print("Loading clusters from Phase 2B...")
    with open(config.output_dir / "02b_mention_clusters.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    all_clusters = [TechnologyCluster(**item) for item in data]
    print(f"Total clusters: {len(all_clusters)}")

    # Test with first cluster
    print("\n" + "="*80)
    print("TEST: Phase 3 with 1 cluster (validate enhanced metadata)")
    print("="*80)

    test_cluster = all_clusters[0]

    # Show what will be sent to LLM
    print(f"\nCluster ID: {test_cluster.cluster_id}")
    print(f"Variants: {len(test_cluster.mention_names)}")
    print(f"\nMetadata preview:")
    for name in test_cluster.mention_names[:3]:
        meta = test_cluster.mention_metadata.get(name, {})
        print(f"  - {name}")
        print(f"    Occurrences: {meta.get('occurrence_count', 0)}")
        print(f"    Strength: {meta.get('avg_strength', 0):.2f}")
        print(f"    Confidence: {meta.get('avg_confidence', 0):.2f}")
        print(f"    Roles: {', '.join(meta.get('roles', []))}")
        doc_types = meta.get('doc_types', [])
        patent_count = sum(1 for d in doc_types if d == "patent")
        paper_count = sum(1 for d in doc_types if d == "technical_paper")
        print(f"    Sources: {patent_count} patents + {paper_count} papers")

    # Initialize canonicalizer
    print("\n" + "="*80)
    print("Initializing LLM Canonicalizer...")
    canonicalizer = LLMCanonicalizer(config)

    # Show formatted prompt
    print("\n" + "="*80)
    print("FORMATTED PROMPT FOR LLM (with enhanced metadata):")
    print("="*80)
    prompt = canonicalizer._format_cluster_for_llm(test_cluster)
    print(prompt)
    print("="*80)

    # Ask for approval before calling LLM
    print(f"\n" + "="*80)
    print(f"APPROVAL NEEDED to call LLM API:")
    print(f"  - Clusters to process: 1")
    print(f"  - Estimated cost: ~$0.0002")
    print(f"  - Model: gpt-4o-mini")
    print(f"="*80)
    print("\nThis test shows the IMPROVED prompt format with metadata.")
    print("Ready to test Phase 3 with enhanced context for LLM expert analysis.")


if __name__ == "__main__":
    main()
