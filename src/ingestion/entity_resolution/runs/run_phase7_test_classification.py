"""
Run Phase 7: Technology Classification API Test
Tests the classifier with sample technology mentions
"""

from dotenv import load_dotenv
load_dotenv()

import json
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from graph.entity_resolution.tech_classifier import TechnologyClassifier
from graph.entity_resolution.config import EntityResolutionConfig


def main():
    """Test Phase 7: Technology classification."""
    config = EntityResolutionConfig(industry="eVTOL")

    print("="*80)
    print("PHASE 7: TECHNOLOGY CLASSIFICATION API TEST")
    print("="*80)

    # Initialize classifier
    print("\nInitializing classifier...")
    classifier = TechnologyClassifier(config)

    print("\n" + "="*80)
    print("TESTING CLASSIFICATION WITH SAMPLE MENTIONS")
    print("="*80)

    # Test cases
    test_mentions = [
        # Exact matches
        "Lithium-Ion Battery System",
        "Flight Control System",

        # Variant matches
        "Li-ion battery pack",
        "tilt-rotor propulsion",

        # Semantic matches
        "electric motor for propulsion",
        "battery management electronics",
        "autonomous flight controller",

        # Near matches
        "carbon fiber composite structure",
        "thermal management cooling",
        "noise reduction technology",

        # Unknown
        "quantum entanglement propulsion",
        "flux capacitor energy storage"
    ]

    print(f"\nTesting {len(test_mentions)} sample mentions...")
    print("="*80)

    results = []
    for i, mention in enumerate(test_mentions, 1):
        print(f"\n[{i}/{len(test_mentions)}] Query: '{mention}'")
        print("-" * 80)

        result = classifier.classify(mention, threshold=0.75)
        results.append(result)

        if result.canonical_name:
            print(f"  Match: {result.canonical_name}")
            print(f"  ID: {result.canonical_id}")
            print(f"  Similarity: {result.similarity_score:.3f}")
            print(f"  Method: {result.match_method}")
            print(f"  Confidence: {result.confidence}")

            if result.alternatives:
                print(f"\n  Alternatives:")
                for j, alt in enumerate(result.alternatives, 1):
                    print(f"    {j}. {alt['canonical_name']} (sim={alt['similarity_score']:.3f})")
        else:
            print(f"  No match found (threshold: 0.75)")

    # Summary statistics
    print("\n" + "="*80)
    print("CLASSIFICATION SUMMARY")
    print("="*80)

    matched = sum(1 for r in results if r.canonical_name is not None)
    high_conf = sum(1 for r in results if r.confidence == "high")
    medium_conf = sum(1 for r in results if r.confidence == "medium")
    low_conf = sum(1 for r in results if r.confidence == "low")

    print(f"\nTotal mentions tested: {len(results)}")
    print(f"Matched: {matched} ({matched/len(results)*100:.1f}%)")
    print(f"Not matched: {len(results) - matched} ({(len(results) - matched)/len(results)*100:.1f}%)")
    print(f"\nConfidence distribution:")
    print(f"  High (>0.90): {high_conf}")
    print(f"  Medium (0.75-0.90): {medium_conf}")
    print(f"  Low (<0.75): {low_conf}")

    # Match method distribution
    method_counts = {}
    for r in results:
        method_counts[r.match_method] = method_counts.get(r.match_method, 0) + 1

    print(f"\nMatch method distribution:")
    for method, count in sorted(method_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {method}: {count}")

    # Save results
    output_file = config.output_dir / "07_classification_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump([r.model_dump() for r in results], f, indent=2, ensure_ascii=False)

    print(f"\nSaved test results to: {output_file}")

    # API usage example
    print("\n" + "="*80)
    print("API USAGE EXAMPLE")
    print("="*80)

    print("""
from graph.entity_resolution.tech_classifier import TechnologyClassifier
from graph.entity_resolution.config import EntityResolutionConfig

# Initialize
config = EntityResolutionConfig(industry="eVTOL")
classifier = TechnologyClassifier(config)

# Classify single mention
result = classifier.classify("battery management system")
print(f"Canonical: {result.canonical_name}")
print(f"Confidence: {result.confidence}")

# Classify batch
mentions = ["motor controller", "carbon fiber wing", "lidar sensor"]
results = classifier.classify_batch(mentions)
""")

    print("\n" + "="*80)
    print("[SUCCESS] Phase 7 Testing Complete!")
    print("="*80)

    print("\nNext Steps:")
    print("  1. Review classification results: output/07_classification_test_results.json")
    print("  2. Integrate classifier into document processing pipeline")
    print("  3. Proceed to Phase 8: Post-Processing")


if __name__ == "__main__":
    main()
