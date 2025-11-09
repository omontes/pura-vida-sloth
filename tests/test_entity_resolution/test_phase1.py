"""
Test Phase 1: Data Loading & Normalization
"""

from graph.entity_resolution.normalizer import TechMentionNormalizer
from graph.entity_resolution.config import EntityResolutionConfig


def main():
    """Test Phase 1 with 10 documents."""
    print("=" * 80)
    print("TESTING PHASE 1: DATA LOADING & NORMALIZATION")
    print("=" * 80)

    # Load configuration
    config = EntityResolutionConfig(industry="eVTOL")

    # Initialize normalizer
    normalizer = TechMentionNormalizer(config)

    # Test with 10 documents
    print("\nRunning Phase 1 with 10 documents...")
    mentions = normalizer.run(limit=10, output_file="01_normalized_mentions_test10.json")

    print(f"\nTest complete! Extracted {len(mentions)} unique technologies from 10 documents.")

    # Show sample output
    if mentions:
        print("\nSample normalized mentions:")
        for i, mention in enumerate(mentions[:5], 1):
            print(f"  {i}. {mention.original_name}")
            print(f"     Normalized: {mention.normalized_name}")
            print(f"     Occurrences: {mention.occurrence_count}")
            print(f"     Avg Strength: {mention.avg_strength:.2f}")
            print(f"     Avg Confidence: {mention.avg_confidence:.2f}")
            print()


if __name__ == "__main__":
    main()
