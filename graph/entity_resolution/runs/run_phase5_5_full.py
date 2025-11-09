"""
Run Phase 5.5: Canonical Name Clustering (Full Pipeline)
Clusters and merges near-duplicate canonical names from Phase 4 output
"""

from dotenv import load_dotenv
load_dotenv()

import json
from graph.entity_resolution.canonical_name_clusterer import (
    CanonicalNameClusterer,
    load_merged_catalog
)
from graph.entity_resolution.catalog_builder import CatalogBuilder
from graph.entity_resolution.config import EntityResolutionConfig


def main():
    """Run Phase 5.5 with full dataset."""
    config = EntityResolutionConfig(industry="eVTOL")

    print("\n" + "="*80)
    print("PHASE 5.5: CANONICAL NAME CLUSTERING")
    print("="*80)
    print("\nInput File:")
    print(f"  - Merged catalog (Phase 4): graph/entity_resolution/output/04_merged_catalog.json")
    print("\nExpected Processing:")
    print(f"  - Load 1,852 canonical technologies")
    print(f"  - Generate embeddings for clustering")
    print(f"  - Detect near-duplicates (0.75-0.85 similarity)")
    print(f"  - Auto-merge high-confidence duplicates (0.85+)")
    print(f"  - Flag medium-confidence pairs for review (0.75-0.85)")
    print(f"  - Estimated output: ~1,600-1,700 unique technologies")
    print(f"  - Estimated cost: ~$0.02-0.04 (embeddings)")
    print(f"  - Estimated time: 2-3 minutes")
    print("="*80)

    # =================================================================
    # PHASE 5.5: CANONICAL NAME CLUSTERING
    # =================================================================

    print("\n" + "="*80)
    print("LOADING PHASE 4 OUTPUT")
    print("="*80)

    # Load merged catalog from Phase 4
    print("\nLoading Phase 4 merged catalog...")
    catalog = load_merged_catalog(config, "04_merged_catalog.json")
    print(f"  Loaded {len(catalog)} canonical technologies")

    # Run Phase 5.5
    print("\n" + "="*80)
    print("RUNNING CANONICAL NAME CLUSTERING")
    print("="*80)

    clusterer = CanonicalNameClusterer(config)
    final_catalog = clusterer.run(catalog)

    print(f"\n{'='*80}")
    print("[SUCCESS] Phase 5.5 Complete!")
    print(f"{'='*80}")
    print(f"Original catalog: {len(catalog)} technologies")
    print(f"Final catalog: {len(final_catalog)} technologies")
    print(f"Technologies merged: {len(catalog) - len(final_catalog)}")
    print(f"Reduction: {((len(catalog) - len(final_catalog)) / len(catalog) * 100):.1f}%")
    print(f"\nOutput files:")
    print(f"  - Deduplicated catalog: graph/entity_resolution/output/05_merged_catalog.json")
    print(f"  - Merge audit: graph/entity_resolution/output/05_merge_audit.json")
    print(f"  - Review queue: graph/entity_resolution/output/05_merge_review_queue.json")

    # =================================================================
    # FINAL VALIDATION
    # =================================================================

    print("\n" + "="*80)
    print("RUNNING FINAL VALIDATION")
    print("="*80)

    # Original mention count for coverage calculation
    original_mention_count = 2143  # From Phase 1

    # Run Phase 5 validation on the Phase 5.5 output
    catalog_builder = CatalogBuilder(config)
    validation_report = catalog_builder.validate_catalog(final_catalog, original_mention_count)

    # Save final validation report
    validation_output = config.output_dir / "05_validation_report_final.json"
    with open(validation_output, 'w', encoding='utf-8') as f:
        json.dump(validation_report.model_dump(), f, indent=2, ensure_ascii=False)

    print(f"\nFinal Validation Results:")
    print(f"  Status: {'v PASS' if validation_report.passed else 'x FAIL'}")
    print(f"  Total canonical technologies: {validation_report.total_canonical_technologies}")
    print(f"  Total variants: {validation_report.total_variants}")
    print(f"  Coverage: {validation_report.coverage_percentage:.1f}%")
    print(f"  Duplicate canonical names: {len(validation_report.duplicate_canonical_names)}")
    print(f"  Orphaned variants: {len(validation_report.orphaned_variants)}")

    if validation_report.duplicate_canonical_names:
        print(f"\n  WARNING: Found {len(validation_report.duplicate_canonical_names)} duplicates:")
        for name in validation_report.duplicate_canonical_names[:5]:
            print(f"    - {name}")

    if validation_report.warnings:
        print(f"\n  Warnings:")
        for warning in validation_report.warnings:
            print(f"    - {warning}")

    # =================================================================
    # COMPARISON WITH PHASE 4 OUTPUT
    # =================================================================

    print("\n" + "="*80)
    print("PHASE 4 vs PHASE 5.5 COMPARISON")
    print("="*80)

    print(f"\nPhase 4 Output (before clustering):")
    print(f"  Technologies: {len(catalog)}")
    print(f"  Variants: {sum(len(t.variants) for t in catalog)}")
    print(f"  Duplicates: Unknown (not validated)")

    print(f"\nPhase 5.5 Output (after clustering):")
    print(f"  Technologies: {len(final_catalog)}")
    print(f"  Variants: {sum(len(t.variants) for t in final_catalog)}")
    print(f"  Duplicates: {len(validation_report.duplicate_canonical_names)}")
    print(f"  Coverage: {validation_report.coverage_percentage:.1f}%")

    print(f"\nImprovements:")
    print(f"  - Reduced technologies: {len(catalog) - len(final_catalog)} (-{((len(catalog) - len(final_catalog)) / len(catalog) * 100):.1f}%)")
    print(f"  - Auto-merged pairs: {len(clusterer.merge_audit)}")
    print(f"  - Review queue size: {len(clusterer.review_queue)}")

    # =================================================================
    # SUMMARY
    # =================================================================

    print("\n" + "="*80)
    print("PHASE 5.5 PIPELINE COMPLETE")
    print("="*80)

    print("\nWhat we accomplished:")
    print(f"  + Loaded 1,852 canonical technologies from Phase 4")
    print(f"  + Generated embeddings for hybrid clustering")
    print(f"  + Detected {len(catalog) - len(final_catalog)} near-duplicate technologies")
    print(f"  + Auto-merged {len(clusterer.merge_audit)} high-confidence pairs")
    print(f"  + Flagged {len(clusterer.review_queue)} medium-confidence pairs for review")
    print(f"  + Final catalog: {len(final_catalog)} unique technologies")
    print(f"  + Coverage: {validation_report.coverage_percentage:.1f}%")
    print(f"  + Duplicate check: {'PASS' if len(validation_report.duplicate_canonical_names) == 0 else 'FAIL'}")

    print("\nNext Steps:")
    print("  1. Review merge audit: graph/entity_resolution/output/05_merge_audit.json")
    print("  2. Review borderline cases: graph/entity_resolution/output/05_merge_review_queue.json")
    print("  3. Inspect final catalog: graph/entity_resolution/output/05_merged_catalog.json")
    print("  4. Proceed to Phase 6: ChromaDB Indexing")

    print("\n" + "="*80)


if __name__ == "__main__":
    main()
