"""
Run Phase 6: ChromaDB Hybrid Search Index
Creates persistent ChromaDB collection from final catalog
"""

from dotenv import load_dotenv
load_dotenv()

import json
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from graph.entity_resolution.chromadb_indexer import ChromaDBIndexer
from graph.entity_resolution.schemas import CanonicalTechnology, TechnologyCatalog
from graph.entity_resolution.config import EntityResolutionConfig, get_pipeline_config


def load_final_catalog(config: EntityResolutionConfig) -> TechnologyCatalog:
    """Load final catalog from Phase 5.5B output."""
    # Load from output directory (05_merged_catalog.json)
    catalog_path = config.output_dir / "05_merged_catalog.json"

    if not catalog_path.exists():
        raise FileNotFoundError(f"Final catalog not found: {catalog_path}")

    print(f"Loading final catalog from: {catalog_path}")

    with open(catalog_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Convert to CanonicalTechnology objects
    technologies = [CanonicalTechnology(**tech) for tech in data]

    # Create TechnologyCatalog
    from datetime import datetime, timezone
    catalog = TechnologyCatalog(
        version="2.0",
        generated_at=datetime.now(timezone.utc).isoformat(),
        industry=config.industry,
        total_canonical_technologies=len(technologies),
        total_variants=sum(len(tech.variants) for tech in technologies),
        technologies=technologies
    )

    print(f"  Loaded {len(technologies)} canonical technologies")
    print(f"  Total variants: {catalog.total_variants}")

    return catalog


def main():
    """Run Phase 6: ChromaDB indexing."""
    config = EntityResolutionConfig(industry="eVTOL")

    print("="*80)
    print("PHASE 6: CHROMADB HYBRID SEARCH INDEX")
    print("="*80)

    # Load final catalog
    print("\nLoading final catalog...")
    catalog = load_final_catalog(config)

    # Create indexer
    indexer = ChromaDBIndexer(config)

    # Run indexing
    print("\n" + "="*80)
    print("CREATING PERSISTENT CHROMADB COLLECTION")
    print("="*80)

    indexer.create_persistent_collection()
    indexer.index_catalog(catalog)
    indexer._test_index()

    # Print summary
    print("\n" + "="*80)
    print("PHASE 6 COMPLETE!")
    print("="*80)

    pipeline_config = get_pipeline_config()

    print(f"\nChromaDB Index:")
    print(f"  Collection: {pipeline_config['chromadb_collection_name']}")
    print(f"  Directory: {config.chromadb_dir}")
    print(f"  Indexed technologies: {catalog.total_canonical_technologies}")
    print(f"  Total variants: {catalog.total_variants}")
    print(f"  Embedding model: {pipeline_config['embedding_model']}")
    print(f"  Search type: Hybrid (Semantic)")

    print("\nNext Steps:")
    print("  1. Test classification with sample mentions")
    print("  2. Run Phase 7: Technology Classification API")
    print("  3. Validate lookup accuracy")

    print("\n" + "="*80)


if __name__ == "__main__":
    main()
