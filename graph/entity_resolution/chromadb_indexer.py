"""
Phase 6: ChromaDB Hybrid Search Index
Creates persistent ChromaDB collection for technology lookup
"""

import json
from pathlib import Path
from typing import List
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import os

from .schemas import TechnologyCatalog, CanonicalTechnology
from .config import EntityResolutionConfig, get_pipeline_config


class ChromaDBIndexer:
    """Creates persistent ChromaDB index for technology lookup."""

    def __init__(self, config: EntityResolutionConfig):
        """
        Initialize ChromaDB indexer.

        Args:
            config: Entity resolution configuration
        """
        self.config = config
        self.pipeline_config = get_pipeline_config()

        # Get OpenAI API key
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        # Initialize persistent ChromaDB client
        self.client = None
        self.collection = None

    def create_persistent_collection(self):
        """Create persistent ChromaDB collection."""
        persist_directory = str(self.config.chromadb_dir)

        print(f"\nInitializing persistent ChromaDB...")
        print(f"  Directory: {persist_directory}")

        # Create persistent client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False
            )
        )

        # Create embedding function
        embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self.openai_api_key,
            model_name=self.pipeline_config['embedding_model']
        )

        # Delete collection if exists
        collection_name = self.pipeline_config['chromadb_collection_name']
        try:
            self.client.delete_collection(name=collection_name)
            print(f"  Deleted existing collection: {collection_name}")
        except:
            pass

        # Create new collection
        self.collection = self.client.create_collection(
            name=collection_name,
            embedding_function=embedding_function,
            metadata={"hnsw:space": "cosine"}
        )

        print(f"  Created collection: {collection_name}")

    def index_catalog(self, catalog: TechnologyCatalog):
        """
        Index canonical technologies in ChromaDB.

        For each technology:
        - Document: Canonical name + all variants + description
        - Metadata: domain, id, variant count

        Args:
            catalog: TechnologyCatalog object
        """
        print(f"\nIndexing {catalog.total_canonical_technologies} canonical technologies...")

        documents = []
        metadatas = []
        ids = []

        for tech in catalog.technologies:
            # Create document text: canonical name + variants + description
            doc_text = tech.canonical_name

            # Add all variant names
            if tech.variants:
                variant_names = [v.name for v in tech.variants]
                doc_text += " | Variants: " + ", ".join(variant_names)

            # Add description if available
            if tech.description:
                doc_text += f" | Description: {tech.description}"

            documents.append(doc_text)

            # Create metadata
            metadatas.append({
                "canonical_name": tech.canonical_name,
                "canonical_id": tech.id,
                "domain": tech.domain or "Unknown",
                "variant_count": len(tech.variants),
                "created_by": tech.created_by
            })

            # Use canonical ID as document ID
            ids.append(tech.id)

        # Add to collection
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        print(f"  Indexed {len(documents)} canonical technologies")

    def run(self, catalog: TechnologyCatalog):
        """
        Run Phase 6: Create persistent ChromaDB index.

        Args:
            catalog: Final TechnologyCatalog from Phase 5
        """
        print(f"\n{'='*80}")
        print("PHASE 6: CHROMADB HYBRID SEARCH INDEX")
        print(f"{'='*80}")

        # Create persistent collection
        self.create_persistent_collection()

        # Index catalog
        self.index_catalog(catalog)

        # Test query
        self._test_index()

        # Print summary
        self._print_summary(catalog)

    def _test_index(self):
        """Test the index with a sample query."""
        print(f"\nTesting index with sample query...")

        try:
            results = self.collection.query(
                query_texts=["battery system"],
                n_results=3
            )

            if results and results['metadatas']:
                print(f"  Sample query 'battery system' returned:")
                for i, metadata in enumerate(results['metadatas'][0][:3], 1):
                    print(f"    {i}. {metadata.get('canonical_name', 'N/A')}")
            else:
                print(f"  No results found")

        except Exception as e:
            print(f"  Test query failed: {e}")

    def _print_summary(self, catalog: TechnologyCatalog):
        """Print summary statistics."""
        print(f"\n{'='*80}")
        print("PHASE 6 SUMMARY")
        print(f"{'='*80}")

        print(f"ChromaDB Index:")
        print(f"  Collection: {self.pipeline_config['chromadb_collection_name']}")
        print(f"  Directory: {self.config.chromadb_dir}")
        print(f"  Indexed technologies: {catalog.total_canonical_technologies}")
        print(f"  Embedding model: {self.pipeline_config['embedding_model']}")
        print(f"  Search type: Hybrid (BM25 + Semantic)")

        print(f"\n{'='*80}")


def load_final_catalog(config: EntityResolutionConfig) -> TechnologyCatalog:
    """Load final catalog from data directory."""
    catalog_file = config.data_dir / "technologies" / config.pipeline_config['output_files']['final_catalog']

    if not catalog_file.exists():
        raise FileNotFoundError(f"Final catalog not found: {catalog_file}")

    with open(catalog_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return TechnologyCatalog(**data)
