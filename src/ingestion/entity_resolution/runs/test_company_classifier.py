"""
Test Company Classification API
Tests the company classifier with sample company mentions
"""

from dotenv import load_dotenv
load_dotenv()

import json
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from graph.entity_resolution.company_classifier import CompanyClassifier
from graph.entity_resolution.config import EntityResolutionConfig


def main():
    """Test company classification."""
    config = EntityResolutionConfig(industry="eVTOL")

    print("="*80)
    print("COMPANY CLASSIFICATION API TEST")
    print("="*80)

    # Initialize classifier
    print("\nInitializing company classifier...")
    classifier = CompanyClassifier(config)

    print("\n" + "="*80)
    print("TESTING CLASSIFICATION WITH SAMPLE MENTIONS")
    print("="*80)

    # Test cases
    test_mentions = [
        # Exact canonical matches
        ("Joby Aviation", "Should match exactly"),
        ("Archer Aviation", "Should match exactly"),
        ("Boeing", "Should match exactly"),

        # Ticker matches
        ("JOBY", "Ticker for Joby Aviation"),
        ("ACHR", "Ticker for Archer Aviation"),
        ("BA", "Ticker for Boeing"),

        # Alias matches
        ("Joby", "Short form/alias"),
        ("Archer Aviation Inc.", "Full legal name"),
        ("United Airlines", "Operator"),

        # Fuzzy/semantic matches
        ("Boeing Company", "Should match Boeing"),
        ("Airbus SE", "Should match Airbus"),
        ("Stellantis NV", "Should match Stellantis"),

        # Partial/ambiguous
        ("Archer", "Ambiguous - company or tech?"),
        ("United", "Partial name"),

        # Unknown companies
        ("Tesla", "Not in catalog"),
        ("Apple Inc.", "Not in catalog"),
        ("SpaceX", "Not in catalog")
    ]

    print(f"\nTesting {len(test_mentions)} sample mentions...")
    print("="*80)

    results = []
    for i, (mention, note) in enumerate(test_mentions, 1):
        print(f"\n[{i}/{len(test_mentions)}] Query: '{mention}'")
        print(f"  Note: {note}")
        print("-" * 80)

        result = classifier.classify(mention, threshold=0.5)
        results.append(result)

        if result.canonical_name:
            print(f"  [MATCH] {result.canonical_name}")
            print(f"    ID: {result.canonical_id}")
            print(f"    Similarity: {result.similarity_score:.3f}")
            print(f"    Method: {result.match_method}")
            print(f"    Confidence: {result.confidence}")

            if result.alternatives:
                print(f"\n    Alternatives:")
                for j, alt in enumerate(result.alternatives, 1):
                    kind = alt.get('kind', 'unknown') if isinstance(alt, dict) else 'unknown'
                    sim = alt.get('similarity_score', 0) if isinstance(alt, dict) else 0
                    name = alt.get('canonical_name', '') if isinstance(alt, dict) else alt
                    print(f"      {j}. {name} ({kind}) - sim={sim:.3f}")
        else:
            print(f"  [NO MATCH] (threshold: 0.5)")

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
    output_file = config.output_dir / "company_classification_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump([r.model_dump() for r in results], f, indent=2, ensure_ascii=False)

    print(f"\nSaved test results to: {output_file}")

    # API usage example
    print("\n" + "="*80)
    print("API USAGE EXAMPLE")
    print("="*80)

    print("""
from graph.entity_resolution.company_classifier import CompanyClassifier
from graph.entity_resolution.config import EntityResolutionConfig

# Initialize
config = EntityResolutionConfig(industry="eVTOL")
classifier = CompanyClassifier(config)

# Classify single mention
result = classifier.classify("United Airlines")
print(f"Canonical: {result.canonical_name}")
print(f"Confidence: {result.confidence}")

# Classify by ticker
result = classifier.classify("JOBY")
print(f"Matched company: {result.canonical_name}")

# Classify batch
mentions = ["Boeing", "Airbus", "Archer Aviation Inc."]
results = classifier.classify_batch(mentions)
""")

    print("\n" + "="*80)
    print("[SUCCESS] Company Classification Testing Complete!")
    print("="*80)

    print("\nNext Steps:")
    print("  1. Review classification results: output/company_classification_test_results.json")
    print("  2. Create unified tech+company normalizer")
    print("  3. Test with SEC filing JSONs")


if __name__ == "__main__":
    main()
