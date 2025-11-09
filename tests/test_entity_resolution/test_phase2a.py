"""
Test Phase 2A: Catalog Matching
"""

from graph.entity_resolution.catalog_matcher import CatalogMatcher, load_normalized_mentions
from graph.entity_resolution.config import EntityResolutionConfig


def main():
    """Test Phase 2A with normalized mentions from test10."""
    print("=" * 80)
    print("TESTING PHASE 2A: CATALOG MATCHING")
    print("=" * 80)

    # Load configuration
    config = EntityResolutionConfig(industry="eVTOL")

    # Load normalized mentions from Phase 1 test
    print("\nLoading normalized mentions from Phase 1 test...")
    mentions = load_normalized_mentions(config, "01_normalized_mentions_test10.json")
    print(f"Loaded {len(mentions)} normalized mentions")

    # Initialize catalog matcher
    matcher = CatalogMatcher(config)

    # Run matching
    matched, unmatched = matcher.run(mentions)

    print(f"\nTest complete!")
    print(f"  Matched: {len(matched)}")
    print(f"  Unmatched: {len(unmatched)}")

    # Show sample matches
    if matched:
        print("\nSample matches:")
        for i, match in enumerate(matched[:5], 1):
            print(f"  {i}. {match.mention_name} → {match.canonical_name}")
            print(f"     Similarity: {match.similarity_score:.2f}")
            print(f"     Method: {match.match_method}")
            print()


if __name__ == "__main__":
    main()
