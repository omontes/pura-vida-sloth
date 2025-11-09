"""
Phase 7: Technology Classification/Lookup Function
Classifies new technology mentions using hybrid search against canonical catalog
"""

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from typing import Optional, List
from rapidfuzz import fuzz
import os

from .schemas import LookupResult, TechnologyCatalog
from .config import EntityResolutionConfig, get_pipeline_config


class TechnologyClassifier:
    """Classifies technology mentions using hybrid search."""

    def __init__(self, config: EntityResolutionConfig):
        """
        Initialize technology classifier.

        Args:
            config: Entity resolution configuration
        """
        self.config = config
        self.pipeline_config = get_pipeline_config()

        # Load OpenAI API key
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        # Load ChromaDB collection
        self.client = None
        self.collection = None
        self._load_chromadb()

        # Load catalog for exact variant matching
        self.catalog = self._load_catalog()

    def _load_chromadb(self):
        """Load persistent ChromaDB collection."""
        persist_directory = str(self.config.chromadb_dir)
        collection_name = self.pipeline_config['chromadb_collection_name']

        print(f"Loading ChromaDB collection...")
        print(f"  Directory: {persist_directory}")
        print(f"  Collection: {collection_name}")

        # Load persistent client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

        # Get embedding function
        embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self.openai_api_key,
            model_name=self.pipeline_config['embedding_model']
        )

        # Get collection
        self.collection = self.client.get_collection(
            name=collection_name,
            embedding_function=embedding_function
        )

        print(f"  Collection loaded: {self.collection.count()} technologies")

    def _load_catalog(self) -> Optional[TechnologyCatalog]:
        """Load final catalog for exact variant matching."""
        try:
            import json
            from .schemas import CanonicalTechnology
            from datetime import datetime, timezone

            # Load from output directory (05_merged_catalog.json)
            catalog_path = self.config.output_dir / "05_merged_catalog.json"

            if not catalog_path.exists():
                print(f"  Warning: Catalog not found at {catalog_path}")
                return None

            with open(catalog_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Convert to CanonicalTechnology objects
            technologies = [CanonicalTechnology(**tech) for tech in data]

            # Create TechnologyCatalog
            catalog = TechnologyCatalog(
                version="2.0",
                generated_at=datetime.now(timezone.utc).isoformat(),
                industry=self.config.industry,
                total_canonical_technologies=len(technologies),
                total_variants=sum(len(tech.variants) for tech in technologies),
                technologies=technologies
            )

            print(f"  Catalog loaded: {catalog.total_canonical_technologies} technologies")
            return catalog
        except Exception as e:
            print(f"  Warning: Could not load catalog: {e}")
            return None

    def exact_variant_match(self, query: str) -> Optional[LookupResult]:
        """
        Check for exact match against known variants.

        Args:
            query: Technology mention

        Returns:
            LookupResult if exact match found, else None
        """
        if not self.catalog:
            return None

        query_lower = query.lower()

        for tech in self.catalog.technologies:
            # Check canonical name
            if tech.canonical_name.lower() == query_lower:
                return LookupResult(
                    query_mention=query,
                    canonical_name=tech.canonical_name,
                    canonical_id=tech.id,
                    similarity_score=1.0,
                    match_method="exact_canonical",
                    confidence="high",
                    alternatives=[]
                )

            # Check variants
            for variant in tech.variants:
                if variant.name.lower() == query_lower:
                    return LookupResult(
                        query_mention=query,
                        canonical_name=tech.canonical_name,
                        canonical_id=tech.id,
                        similarity_score=1.0,
                        match_method="exact_variant",
                        confidence="high",
                        alternatives=[]
                    )

        return None

    def hybrid_search(self, query: str, threshold: float = 0.75) -> Optional[LookupResult]:
        """
        Perform hybrid search using ChromaDB.

        Args:
            query: Technology mention
            threshold: Minimum similarity threshold (default: 0.75)

        Returns:
            LookupResult if match found, else None
        """
        top_k = self.pipeline_config['chromadb_search_top_k']

        # Query ChromaDB
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            include=['distances', 'metadatas']
        )

        if not results or not results['distances'] or len(results['distances']) == 0:
            return None

        distances = results['distances'][0]
        metadatas = results['metadatas'][0]

        # Best match
        best_distance = distances[0]
        best_metadata = metadatas[0]

        # Convert distance to similarity
        similarity = 1.0 - best_distance

        # Check threshold
        if similarity < threshold:
            return None

        # Determine confidence
        if similarity >= 0.90:
            confidence = "high"
        elif similarity >= 0.75:
            confidence = "medium"
        else:
            confidence = "low"

        # Build alternatives list
        alternatives = []
        for i in range(1, min(3, len(distances))):
            alt_sim = 1.0 - distances[i]
            if alt_sim >= threshold:
                alternatives.append({
                    "canonical_name": metadatas[i].get('canonical_name', ''),
                    "canonical_id": metadatas[i].get('canonical_id', ''),
                    "similarity_score": alt_sim
                })

        return LookupResult(
            query_mention=query,
            canonical_name=best_metadata.get('canonical_name', ''),
            canonical_id=best_metadata.get('canonical_id', ''),
            similarity_score=similarity,
            match_method="hybrid_search",
            confidence=confidence,
            alternatives=alternatives
        )

    def classify(self, mention: str, threshold: float = 0.75) -> LookupResult:
        """
        Classify a technology mention.

        Lookup pipeline:
        1. Exact variant match (fastest)
        2. ChromaDB hybrid search
        3. Return "unknown" if no match

        Args:
            mention: Technology mention to classify
            threshold: Minimum similarity threshold (default: 0.75)

        Returns:
            LookupResult object
        """
        # 1. Exact variant match
        exact_match = self.exact_variant_match(mention)
        if exact_match:
            return exact_match

        # 2. Hybrid search
        hybrid_match = self.hybrid_search(mention, threshold=threshold)
        if hybrid_match:
            return hybrid_match

        # 3. No match found
        return LookupResult(
            query_mention=mention,
            canonical_name=None,
            canonical_id=None,
            similarity_score=0.0,
            match_method="none",
            confidence="low",
            alternatives=[]
        )

    def classify_batch(self, mentions: List[str],
                      threshold: float = 0.75) -> List[LookupResult]:
        """
        Classify a batch of technology mentions.

        Args:
            mentions: List of technology mentions
            threshold: Minimum similarity threshold

        Returns:
            List of LookupResult objects
        """
        print(f"\nClassifying {len(mentions)} technology mentions...")

        results = []
        for i, mention in enumerate(mentions, 1):
            if i % 100 == 0:
                print(f"  Progress: {i}/{len(mentions)}")

            result = self.classify(mention, threshold=threshold)
            results.append(result)

        # Summary
        matched = sum(1 for r in results if r.canonical_name is not None)
        high_conf = sum(1 for r in results if r.confidence == "high")
        medium_conf = sum(1 for r in results if r.confidence == "medium")
        low_conf = sum(1 for r in results if r.confidence == "low")

        print(f"\nClassification summary:")
        print(f"  Total: {len(results)}")
        print(f"  Matched: {matched} ({matched/len(results)*100:.1f}%)")
        print(f"  High confidence: {high_conf}")
        print(f"  Medium confidence: {medium_conf}")
        print(f"  Low confidence: {low_conf}")

        return results


def create_classifier(config: EntityResolutionConfig) -> TechnologyClassifier:
    """
    Create and initialize technology classifier.

    Args:
        config: Entity resolution configuration

    Returns:
        TechnologyClassifier instance
    """
    return TechnologyClassifier(config)
