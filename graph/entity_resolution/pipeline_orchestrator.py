"""
Entity Resolution Pipeline Orchestrator
Coordinates all 8 phases of the technology normalization pipeline
"""

from typing import Optional
from dotenv import load_dotenv

from .config import EntityResolutionConfig
from .normalizer import TechMentionNormalizer
from .catalog_matcher import CatalogMatcher
from .hybrid_clusterer import HybridClusterer
from .llm_canonicalizer import LLMCanonicalizer
from .deduplicator import TechnologyDeduplicator, load_catalog_matches, load_llm_results
from .catalog_builder import CatalogBuilder, load_merged_catalog
from .chromadb_indexer import ChromaDBIndexer
from .tech_classifier import create_classifier
from .post_processor import create_post_processor

# Load environment variables
load_dotenv()


class EntityResolutionPipeline:
    """Orchestrates the complete entity resolution pipeline."""

    def __init__(self, industry: str = "eVTOL"):
        """
        Initialize pipeline.

        Args:
            industry: Industry name (e.g., "eVTOL")
        """
        self.config = EntityResolutionConfig(industry=industry)
        print(f"\nInitialized Entity Resolution Pipeline for {industry}")

    def run_phase1(self, limit: Optional[int] = None) -> int:
        """
        Phase 1: Data Loading & Normalization

        Args:
            limit: Document limit (None = all)

        Returns:
            Number of unique normalized mentions
        """
        normalizer = TechMentionNormalizer(self.config)
        mentions = normalizer.run(limit=limit)
        return len(mentions)

    def run_phase2a(self):
        """Phase 2A: Catalog Matching"""
        from .normalizer import TechMentionNormalizer
        from .catalog_matcher import load_normalized_mentions

        # Load normalized mentions from Phase 1
        mentions = load_normalized_mentions(self.config, "01_normalized_mentions.json")

        matcher = CatalogMatcher(self.config)
        matched, unmatched = matcher.run(mentions)

        return len(matched), len(unmatched)

    def run_phase2b(self):
        """Phase 2B: Hybrid Clustering"""
        from .hybrid_clusterer import load_unmatched_mentions

        # Load unmatched mentions from Phase 2A
        unmatched = load_unmatched_mentions(self.config, "02a_unmatched_mentions.json")

        clusterer = HybridClusterer(self.config)
        clusters = clusterer.run(unmatched)

        return len(clusters)

    def run_phase3(self, limit: Optional[int] = None):
        """
        Phase 3: LLM Canonical Name Selection

        Args:
            limit: Cluster limit (None = all)

        Returns:
            Number of clusters canonicalized
        """
        from .llm_canonicalizer import load_clusters

        # Load clusters from Phase 2B
        clusters = load_clusters(self.config, "02b_mention_clusters.json")

        canonicalizer = LLMCanonicalizer(self.config)
        results = canonicalizer.run(clusters, limit=limit)

        print(f"\nLLM Canonicalization cost: ${canonicalizer.total_cost:.4f}")

        return len(results)

    def run_phase4(self):
        """Phase 4: Deduplication & Merging"""
        # Load inputs
        catalog_matches = load_catalog_matches(self.config, "02a_catalog_matches.json")
        llm_results = load_llm_results(self.config, "03_llm_canonical_names.json")

        deduplicator = TechnologyDeduplicator(self.config)
        catalog = deduplicator.run(catalog_matches, llm_results)

        return len(catalog)

    def run_phase5(self, original_mention_count: int):
        """Phase 5: Catalog Validation & Output"""
        # Load merged catalog from Phase 4
        catalog = load_merged_catalog(self.config, "04_merged_catalog.json")

        builder = CatalogBuilder(self.config)
        final_catalog = builder.run(catalog, original_mention_count)

        return final_catalog

    def run_phase6(self):
        """Phase 6: ChromaDB Hybrid Search Index"""
        from .chromadb_indexer import load_final_catalog

        # Load final catalog from Phase 5
        catalog = load_final_catalog(self.config)

        indexer = ChromaDBIndexer(self.config)
        indexer.run(catalog)

    def run_phase7_test(self):
        """Phase 7: Test Technology Classifier"""
        classifier = create_classifier(self.config)

        # Test with sample queries
        print(f"\n{'='*80}")
        print("PHASE 7: TECHNOLOGY CLASSIFIER TEST")
        print(f"{'='*80}")

        test_queries = [
            "battery system",
            "tiltrotor",
            "autonomous flight",
            "electric propulsion",
            "vertiport"
        ]

        print(f"\nTesting classifier with {len(test_queries)} sample queries...")

        for query in test_queries:
            result = classifier.classify(query, threshold=0.75)
            print(f"\nQuery: '{query}'")
            if result.canonical_name:
                print(f"  → {result.canonical_name} (ID: {result.canonical_id})")
                print(f"  Confidence: {result.confidence}, Similarity: {result.similarity_score:.2f}")
                print(f"  Method: {result.match_method}")
            else:
                print(f"  → No match found")

        print(f"\n{'='*80}")

    def run_phase8(self, pattern: str, threshold: float = 0.85):
        """
        Phase 8: Post-Process Patent/Paper Files

        Args:
            pattern: Glob pattern for files to process
            threshold: Similarity threshold
        """
        classifier = create_classifier(self.config)
        post_processor = create_post_processor(self.config, classifier)

        post_processor.run(pattern, output_suffix="_NORMALIZED", threshold=threshold)

    def run_full_pipeline(self, doc_limit: Optional[int] = None,
                         cluster_limit: Optional[int] = None):
        """
        Run complete pipeline (Phases 1-6).

        Args:
            doc_limit: Document limit for Phase 1 (None = all)
            cluster_limit: Cluster limit for Phase 3 (None = all)
        """
        print(f"\n{'='*88}")
        print("ENTITY RESOLUTION PIPELINE - FULL RUN")
        print(f"{'='*88}")

        # Phase 1
        print(f"\n[1/6] Running Phase 1...")
        mention_count = self.run_phase1(limit=doc_limit)

        # Phase 2A
        print(f"\n[2/6] Running Phase 2A...")
        matched, unmatched = self.run_phase2a()

        # Phase 2B
        print(f"\n[3/6] Running Phase 2B...")
        cluster_count = self.run_phase2b()

        # Phase 3
        print(f"\n[4/6] Running Phase 3...")
        canonical_count = self.run_phase3(limit=cluster_limit)

        # Phase 4
        print(f"\n[5/6] Running Phase 4...")
        merged_count = self.run_phase4()

        # Phase 5
        print(f"\n[6/6] Running Phase 5...")
        final_catalog = self.run_phase5(mention_count)

        # Summary
        print(f"\n{'='*88}")
        print("PIPELINE COMPLETE")
        print(f"{'='*88}")
        print(f"Phase 1: {mention_count} unique mentions extracted")
        print(f"Phase 2A: {matched} matched, {unmatched} unmatched")
        print(f"Phase 2B: {cluster_count} clusters formed")
        print(f"Phase 3: {canonical_count} canonical names generated")
        print(f"Phase 4: {merged_count} technologies in merged catalog")
        print(f"Phase 5: {final_catalog.total_canonical_technologies} canonical technologies")
        print(f"         {final_catalog.total_variants} total variants")
        print(f"\nFinal catalog: data/{self.config.industry}/technologies/canonical_technologies_v2.json")
        print(f"{'='*88}")

        return final_catalog


def main():
    """Run the complete pipeline."""
    pipeline = EntityResolutionPipeline(industry="eVTOL")

    # Run full pipeline on all documents
    pipeline.run_full_pipeline(doc_limit=None, cluster_limit=None)

    # Index in ChromaDB
    print(f"\nIndexing in ChromaDB...")
    pipeline.run_phase6()

    # Test classifier
    pipeline.run_phase7_test()

    print(f"\n✓ Pipeline complete! Ready for Phase 8 post-processing.")


if __name__ == "__main__":
    main()
