"""
Run Company ChromaDB Indexing
Creates persistent ChromaDB collection for company lookup from companies.json
"""

from dotenv import load_dotenv
load_dotenv()

import json
from pathlib import Path
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import os

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from graph.entity_resolution.config import EntityResolutionConfig, get_pipeline_config


def load_companies_catalog(config: EntityResolutionConfig) -> dict:
    """Load companies catalog from data directory."""
    companies_file = config.data_dir / "companies" / "companies.json"

    if not companies_file.exists():
        raise FileNotFoundError(f"Companies catalog not found: {companies_file}")

    print(f"Loading companies catalog from: {companies_file}")

    with open(companies_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"  Loaded {data.get('total_companies', 0)} companies")
    print(f"  Catalog version: {data.get('catalog_version', 'unknown')}")

    return data


def index_companies(config: EntityResolutionConfig, companies_data: dict):
    """Index companies into ChromaDB."""
    pipeline_config = get_pipeline_config()

    # Get OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    # Initialize persistent ChromaDB client
    persist_directory = str(config.chromadb_dir)
    collection_name = pipeline_config['chromadb_company_collection_name']

    print(f"\nInitializing ChromaDB...")
    print(f"  Directory: {persist_directory}")
    print(f"  Collection: {collection_name}")

    client = chromadb.PersistentClient(
        path=persist_directory,
        settings=Settings(anonymized_telemetry=False)
    )

    # Create embedding function
    embedding_function = embedding_functions.OpenAIEmbeddingFunction(
        api_key=openai_api_key,
        model_name=pipeline_config['embedding_model']
    )

    # Delete collection if exists
    try:
        client.delete_collection(name=collection_name)
        print(f"  Deleted existing collection: {collection_name}")
    except:
        pass

    # Create new collection
    collection = client.create_collection(
        name=collection_name,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"}
    )

    print(f"  Created collection: {collection_name}")

    # Prepare documents for indexing
    print(f"\nIndexing {len(companies_data['companies'])} companies...")

    documents = []
    metadatas = []
    ids = []

    for company in companies_data['companies']:
        # Create document text: name + aliases + kind + country
        doc_text = company['name']

        # Add all aliases
        if company.get('aliases'):
            aliases_str = ", ".join(company['aliases'])
            doc_text += f" | Aliases: {aliases_str}"

        # Add company type (kind)
        if company.get('kind'):
            doc_text += f" | Type: {company['kind']}"

        # Add country
        if company.get('country'):
            doc_text += f" | Country: {company['country']}"

        documents.append(doc_text)

        # Create metadata
        metadatas.append({
            "canonical_name": company['name'],
            "company_id": company['id'],
            "kind": company.get('kind', 'unknown'),
            "country": company.get('country', 'unknown'),
            "alias_count": len(company.get('aliases', []))
        })

        # Use company ID as document ID
        ids.append(company['id'])

    # Add to ChromaDB collection
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

    print(f"  [SUCCESS] Indexed {len(documents)} companies")

    # Test query
    print(f"\nTesting index with sample queries...")

    test_queries = [
        "Boeing",
        "Joby Aviation",
        "ACHR"
    ]

    for query in test_queries:
        results = collection.query(
            query_texts=[query],
            n_results=3
        )

        if results and results['metadatas']:
            print(f"\n  Query: '{query}'")
            for i, metadata in enumerate(results['metadatas'][0][:3], 1):
                distance = results['distances'][0][i-1] if results.get('distances') else 0
                similarity = 1.0 - distance
                print(f"    {i}. {metadata.get('canonical_name', 'N/A')} ({metadata.get('kind', 'N/A')}) - sim={similarity:.3f}")

    return collection


def main():
    """Run company ChromaDB indexing."""
    config = EntityResolutionConfig(industry="eVTOL")

    print("="*80)
    print("COMPANY CHROMADB INDEXING")
    print("="*80)

    # Load companies catalog
    print("\nLoading companies catalog...")
    companies_data = load_companies_catalog(config)

    # Index companies
    print("\n" + "="*80)
    print("CREATING PERSISTENT CHROMADB COLLECTION")
    print("="*80)

    collection = index_companies(config, companies_data)

    # Print summary
    print("\n" + "="*80)
    print("INDEXING COMPLETE!")
    print("="*80)

    pipeline_config = get_pipeline_config()

    print(f"\nChromaDB Index:")
    print(f"  Collection: {pipeline_config['chromadb_company_collection_name']}")
    print(f"  Directory: {config.chromadb_dir}")
    print(f"  Indexed companies: {len(companies_data['companies'])}")
    print(f"  Embedding model: {pipeline_config['embedding_model']}")
    print(f"  Search type: Semantic")

    # Company type breakdown
    kind_counts = {}
    for company in companies_data['companies']:
        kind = company.get('kind', 'unknown')
        kind_counts[kind] = kind_counts.get(kind, 0) + 1

    print(f"\n  Company types:")
    for kind, count in sorted(kind_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"    - {kind}: {count}")

    print("\nNext Steps:")
    print("  1. Create company classifier")
    print("  2. Test company classification with sample names")
    print("  3. Integrate into SEC parser normalization")

    print("\n" + "="*80)


if __name__ == "__main__":
    main()
