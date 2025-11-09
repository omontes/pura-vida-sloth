"""
Merge High-Confidence Review Queue Items
Processes the 265 borderline cases from Phase 5.5 and merges high-confidence pairs.

Criteria for auto-merge:
- Similarity >= 0.85 (very high confidence)
- OR: Similarity >= 0.80 AND only 1 gate failed (medium-high confidence)
"""

from dotenv import load_dotenv
load_dotenv()

import json
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict

import sys
sys.path.append(str(Path(__file__).parent.parent))

from graph.entity_resolution.schemas import CanonicalTechnology, TechnologyVariant
from graph.entity_resolution.config import EntityResolutionConfig


def load_review_queue(config: EntityResolutionConfig) -> List[Dict[str, Any]]:
    """Load review queue from Phase 5.5."""
    review_queue_path = config.output_dir / "05_merge_review_queue.json"

    if not review_queue_path.exists():
        raise FileNotFoundError(f"Review queue not found: {review_queue_path}")

    with open(review_queue_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_merged_catalog(config: EntityResolutionConfig) -> List[CanonicalTechnology]:
    """Load merged catalog from Phase 5.5."""
    catalog_path = config.output_dir / "05_merged_catalog.json"

    if not catalog_path.exists():
        raise FileNotFoundError(f"Merged catalog not found: {catalog_path}")

    with open(catalog_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return [CanonicalTechnology(**item) for item in data]


def count_failed_gates(validation: Dict[str, Any]) -> int:
    """Count how many quality gates failed."""
    gates = validation.get('gates', {})
    failed_count = 0

    # Check domain compatibility
    if not gates.get('domain_compatibility', {}).get('passed', False):
        failed_count += 1

    # Check variant overlap
    if not gates.get('variant_overlap', {}).get('passed', False):
        failed_count += 1

    # Note: similarity_tier is not counted as a "gate failure"
    # since it's more of a confidence score

    return failed_count


def filter_high_confidence_merges(review_queue: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter review queue for high-confidence merge candidates.

    Criteria:
    - Similarity >= 0.85 (very high confidence)
    - OR: Similarity >= 0.80 AND only 1 gate failed (medium-high confidence)

    Args:
        review_queue: List of review queue items

    Returns:
        Filtered list of high-confidence merge candidates
    """
    high_confidence = []

    for item in review_queue:
        similarity = item.get('similarity', 0.0)
        validation = item.get('validation', {})

        # Criteria 1: Very high similarity (0.85+)
        if similarity >= 0.85:
            high_confidence.append(item)
            continue

        # Criteria 2: High similarity (0.80+) AND only 1 gate failed
        if similarity >= 0.80:
            failed_gates = count_failed_gates(validation)
            if failed_gates <= 1:
                high_confidence.append(item)
                continue

    return high_confidence


def merge_technologies(tech1: CanonicalTechnology, tech2: CanonicalTechnology) -> CanonicalTechnology:
    """
    Merge two canonical technologies.

    Strategy:
    - Keep tech1 as primary (base)
    - Merge variants from tech2 into tech1
    - Combine source documents
    - Keep tech1's domain and description (assume it's more authoritative)

    Args:
        tech1: Primary technology (kept)
        tech2: Secondary technology (merged into tech1)

    Returns:
        Merged CanonicalTechnology
    """
    # Merge variants (avoid duplicates)
    existing_variant_names = {v.name.lower() for v in tech1.variants}
    merged_variants = list(tech1.variants)

    for variant in tech2.variants:
        if variant.name.lower() not in existing_variant_names:
            merged_variants.append(variant)
            existing_variant_names.add(variant.name.lower())

    # Merge source documents (avoid duplicates)
    merged_sources = list(set(tech1.source_documents + tech2.source_documents))

    # Create merged technology
    merged = CanonicalTechnology(
        id=tech1.id,
        canonical_name=tech1.canonical_name,
        domain=tech1.domain,
        description=tech1.description,
        variants=merged_variants,
        source_documents=merged_sources
    )

    return merged


def apply_merges(catalog: List[CanonicalTechnology],
                merge_candidates: List[Dict[str, Any]]) -> tuple[List[CanonicalTechnology], List[Dict[str, Any]]]:
    """
    Apply merges to catalog.

    Args:
        catalog: Current merged catalog
        merge_candidates: High-confidence merge candidates from review queue

    Returns:
        Tuple of (updated_catalog, merge_audit)
    """
    # Create name -> technology lookup
    catalog_by_name = {tech.canonical_name: tech for tech in catalog}

    # Track merges
    merge_audit = []
    merged_names = set()  # Track which techs have been merged away

    print(f"\nApplying {len(merge_candidates)} high-confidence merges...")

    for i, candidate in enumerate(merge_candidates, 1):
        tech1_name = candidate['tech1']
        tech2_name = candidate['tech2']
        similarity = candidate['similarity']

        # Skip if either technology has already been merged
        if tech1_name in merged_names or tech2_name in merged_names:
            print(f"  [{i}/{len(merge_candidates)}] Skipping: '{tech1_name}' or '{tech2_name}' already merged")
            continue

        # Get technologies from catalog
        tech1 = catalog_by_name.get(tech1_name)
        tech2 = catalog_by_name.get(tech2_name)

        if not tech1 or not tech2:
            print(f"  [{i}/{len(merge_candidates)}] WARNING: Could not find '{tech1_name}' or '{tech2_name}' in catalog")
            continue

        # Merge tech2 into tech1
        merged_tech = merge_technologies(tech1, tech2)

        # Update catalog
        catalog_by_name[tech1_name] = merged_tech
        del catalog_by_name[tech2_name]
        merged_names.add(tech2_name)

        # Record merge
        merge_audit.append({
            'merged_from': tech2_name,
            'merged_into': tech1_name,
            'similarity': similarity,
            'validation': candidate.get('validation', {}),
            'variant_count_before': len(tech1.variants) + len(tech2.variants),
            'variant_count_after': len(merged_tech.variants)
        })

        print(f"  [{i}/{len(merge_candidates)}] Merged: '{tech2_name}' -> '{tech1_name}' (sim={similarity:.3f})")

    # Convert back to list
    updated_catalog = list(catalog_by_name.values())

    return updated_catalog, merge_audit


def main():
    """Run manual review queue merge."""
    config = EntityResolutionConfig(industry="eVTOL")

    print("="*80)
    print("MANUAL REVIEW QUEUE PROCESSING")
    print("="*80)

    # Load review queue
    print("\nLoading review queue...")
    review_queue = load_review_queue(config)
    print(f"  Loaded {len(review_queue)} review queue items")

    # Load current catalog
    print("\nLoading Phase 5.5 merged catalog...")
    catalog = load_merged_catalog(config)
    print(f"  Loaded {len(catalog)} canonical technologies")

    # Filter for high-confidence merges
    print("\nFiltering for high-confidence merge candidates...")
    high_confidence = filter_high_confidence_merges(review_queue)
    print(f"  Found {len(high_confidence)} high-confidence candidates")
    print(f"  Criteria: similarity >= 0.85 OR (similarity >= 0.80 AND <= 1 gate failed)")

    # Show distribution
    very_high = [x for x in high_confidence if x['similarity'] >= 0.85]
    high = [x for x in high_confidence if 0.80 <= x['similarity'] < 0.85]

    print(f"\n  Distribution:")
    print(f"    - Very high (0.85+): {len(very_high)} items")
    print(f"    - High (0.80-0.85): {len(high)} items")

    if len(high_confidence) == 0:
        print("\n[DONE] No high-confidence merges found. Catalog unchanged.")
        return

    # Apply merges
    print("\n" + "="*80)
    print("APPLYING MERGES")
    print("="*80)

    updated_catalog, merge_audit = apply_merges(catalog, high_confidence)

    # Save updated catalog
    print("\n" + "="*80)
    print("SAVING RESULTS")
    print("="*80)

    # Save updated merged catalog (overwrites 05_merged_catalog.json)
    catalog_output = config.output_dir / "05_merged_catalog.json"
    with open(catalog_output, 'w', encoding='utf-8') as f:
        json.dump([tech.model_dump() for tech in updated_catalog], f, indent=2, ensure_ascii=False)
    print(f"\n  Saved updated catalog: {catalog_output}")
    print(f"    Technologies: {len(catalog)} -> {len(updated_catalog)}")

    # Save manual merge audit
    audit_output = config.output_dir / "05_manual_merge_audit.json"
    with open(audit_output, 'w', encoding='utf-8') as f:
        json.dump(merge_audit, f, indent=2, ensure_ascii=False)
    print(f"  Saved manual merge audit: {audit_output}")
    print(f"    Merges applied: {len(merge_audit)}")

    # Generate comparison report
    print("\n" + "="*80)
    print("COMPARISON REPORT")
    print("="*80)

    print(f"\nPhase 5.5 Output (before manual review):")
    print(f"  Technologies: {len(catalog)}")
    print(f"  Review queue: {len(review_queue)}")

    print(f"\nAfter Manual Review:")
    print(f"  Technologies: {len(updated_catalog)}")
    print(f"  Additional merges: {len(merge_audit)}")
    print(f"  Total reduction: {len(catalog) - len(updated_catalog)} ({((len(catalog) - len(updated_catalog)) / len(catalog) * 100):.1f}%)")

    print(f"\nCumulative Pipeline Results:")
    print(f"  Phase 4 output: 1,852 technologies")
    print(f"  Phase 5.5 auto-merge: -29 (to 1,823)")
    print(f"  Manual review merge: -{len(merge_audit)} (to {len(updated_catalog)})")
    print(f"  Total reduction: {1852 - len(updated_catalog)} ({((1852 - len(updated_catalog)) / 1852 * 100):.1f}%)")

    # Show top merges
    print(f"\nTop 10 Merges by Similarity:")
    sorted_audit = sorted(merge_audit, key=lambda x: x['similarity'], reverse=True)
    for i, merge in enumerate(sorted_audit[:10], 1):
        print(f"  {i}. '{merge['merged_from']}' -> '{merge['merged_into']}' (sim={merge['similarity']:.3f})")

    print("\n" + "="*80)
    print("[SUCCESS] Manual Review Complete!")
    print("="*80)

    print("\nNext Steps:")
    print("  1. Validate final catalog for duplicates")
    print("  2. Review manual merge audit: graph/entity_resolution/output/05_manual_merge_audit.json")
    print("  3. Proceed to Phase 6: ChromaDB Indexing")


if __name__ == "__main__":
    main()
