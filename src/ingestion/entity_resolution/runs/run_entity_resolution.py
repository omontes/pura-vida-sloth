"""
Run Entity Resolution Pipeline
Processes all documents to generate canonical technology catalog
"""

from graph.entity_resolution.pipeline_orchestrator import EntityResolutionPipeline


def main():
    """Run the complete entity resolution pipeline."""
    print("\n" + "="*88)
    print("ENTITY RESOLUTION PIPELINE")
    print("Technology Normalization for Strategic Intelligence")
    print("="*88)

    # Initialize pipeline
    pipeline = EntityResolutionPipeline(industry="eVTOL")

    # Run Phases 1-5 (core pipeline)
    print("\n[PHASES 1-5] Running: Normalization -> Clustering -> LLM -> Dedup -> Validation")
    final_catalog = pipeline.run_full_pipeline(
        doc_limit=None,      # Process ALL documents
        cluster_limit=None   # Canonicalize ALL clusters
    )

    # Run Phase 6 (ChromaDB indexing)
    print("\n[PHASE 6] Running: ChromaDB Indexing")
    pipeline.run_phase6()

    # Run Phase 7 (Test classifier)
    print("\n[PHASE 7] Running: Test Classifier")
    pipeline.run_phase7_test()

    print("\n[SUCCESS] PIPELINE COMPLETE!")
    print(f"\nOutput:")
    print(f"   Canonical Catalog: data/eVTOL/technologies/canonical_technologies_v2.json")
    print(f"   ChromaDB Index: graph/entity_resolution/chromadb/")
    print(f"   Intermediate Files: graph/entity_resolution/output/")

    print(f"\nReady for Phase 8:")
    print(f"   Apply normalization to patents using:")
    print(f"   pipeline.run_phase8('data/eVTOL/lens_patents/batch_processing/relevant_patents_scored_*.json')")


if __name__ == "__main__":
    main()
