"""
Run Phase 4 & 5: Deduplication + Validation (Full Pipeline)
Merges catalog matches with LLM results, validates, and builds final catalog
"""

from dotenv import load_dotenv
load_dotenv()

import json
from graph.entity_resolution.deduplicator import (
    TechnologyDeduplicator,
    load_catalog_matches,
    load_llm_results
)
from graph.entity_resolution.catalog_builder import CatalogBuilder
from graph.entity_resolution.config import EntityResolutionConfig


def main():
    """Run Phase 4 & 5 with full dataset."""
    config = EntityResolutionConfig(industry="eVTOL")

    print("\n" + "="*80)
    print("PHASE 4 & 5: DEDUPLICATION + VALIDATION")
    print("="*80)
    print("\nInput Files:")
    print(f"  - Catalog matches (Phase 2A): graph/entity_resolution/output/02a_catalog_matches.json")
    print(f"  - LLM canonical names (Phase 3): graph/entity_resolution/output/03_llm_canonical_names.json")
    print(f"  - Existing catalog: data/eVTOL/technologies/technologies.json")
    print("\nExpected Processing:")
    print(f"  - Load 151 existing canonical technologies")
    print(f"  - Merge 35 catalog matches as variants")
    print(f"  - Deduplicate and merge 1,837 LLM canonical names")
    print(f"  - Validate final catalog")
    print(f"  - Estimated output: ~1,800-1,900 canonical technologies")
    print(f"  - Estimated cost: ~$0.05-0.10 (embeddings for duplicate detection)")
    print(f"  - Estimated time: 2-3 minutes")
    print("="*80)

    # =================================================================
    # PHASE 4: DEDUPLICATION
    # =================================================================

    print("\n" + "="*80)
    print("STARTING PHASE 4: DEDUPLICATION & MERGING")
    print("="*80)

    # Load inputs
    print("\nLoading Phase 2A catalog matches...")
    catalog_matches = load_catalog_matches(config, "02a_catalog_matches.json")
    print(f"  Loaded {len(catalog_matches)} catalog matches")

    print("\nLoading Phase 3 LLM canonical results...")
    llm_results = load_llm_results(config, "03_llm_canonical_names.json")
    print(f"  Loaded {len(llm_results)} LLM canonical names")

    # Run Phase 4
    deduplicator = TechnologyDeduplicator(config)
    merged_catalog = deduplicator.run(catalog_matches, llm_results)

    print(f"\n{'='*80}")
    print("[SUCCESS] Phase 4 Complete!")
    print(f"{'='*80}")
    print(f"Merged catalog: {len(merged_catalog)} canonical technologies")
    print(f"Output file: graph/entity_resolution/output/04_merged_catalog.json")

    # =================================================================
    # PHASE 5: VALIDATION & OUTPUT
    # =================================================================

    print("\n" + "="*80)
    print("STARTING PHASE 5: VALIDATION & CATALOG BUILDING")
    print("="*80)

    # Original mention count for coverage calculation
    original_mention_count = 2143  # From Phase 1 (01_normalized_mentions.json)

    # Run Phase 5
    catalog_builder = CatalogBuilder(config)
    final_catalog = catalog_builder.run(merged_catalog, original_mention_count)

    print(f"\n{'='*80}")
    print("[SUCCESS] Phase 5 Complete!")
    print(f"{'='*80}")
    print(f"Final catalog: {final_catalog.total_canonical_technologies} canonical technologies")
    print(f"Total variants: {final_catalog.total_variants}")
    print(f"Coverage: {(final_catalog.total_variants / original_mention_count * 100):.1f}%")
    print(f"\nOutput files:")
    print(f"  - Validation report: graph/entity_resolution/output/05_validation_report.json")
    print(f"  - Final catalog: data/eVTOL/technologies/canonical_technologies_v2.json")

    # =================================================================
    # SUMMARY
    # =================================================================

    print("\n" + "="*80)
    print("PHASE 4 & 5 PIPELINE COMPLETE")
    print("="*80)
    print("\nWhat we accomplished:")
    print(f"  ✅ Loaded 151 existing canonical technologies")
    print(f"  ✅ Merged 35 catalog matches from Phase 2A")
    print(f"  ✅ Deduplicated and merged {len(llm_results)} LLM canonical names")
    print(f"  ✅ Created {final_catalog.total_canonical_technologies} final canonical technologies")
    print(f"  ✅ Mapped {final_catalog.total_variants} technology variants")
    print(f"  ✅ Achieved {(final_catalog.total_variants / original_mention_count * 100):.1f}% coverage")

    print("\nNext Steps:")
    print("  1. Review validation report: graph/entity_resolution/output/05_validation_report.json")
    print("  2. Inspect final catalog: data/eVTOL/technologies/canonical_technologies_v2.json")
    print("  3. Proceed to Phase 6: ChromaDB Indexing")
    print("  4. Proceed to Phase 7: Technology Classification API")
    print("  5. Proceed to Phase 8: Post-Processing (update original files)")

    print("\n" + "="*80)


if __name__ == "__main__":
    main()
