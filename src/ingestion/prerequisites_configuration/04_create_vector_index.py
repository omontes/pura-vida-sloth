"""
Script 4: Create Vector Index
===============================

Purpose: Create vector similarity search index for Documents.

This script creates:
- Vector index on Document.embedding
- Dimensions: 768 (text-embedding-3-small)
- Similarity metric: cosine

Runtime: ~2-3 minutes
Cost: Free
Safe to run: YES (requires embeddings from Script 2)
"""

import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def create_vector_index():
    """Create vector similarity search index."""

    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    if not uri or not password:
        raise ValueError("Neo4j credentials not found in environment variables")

    driver = GraphDatabase.driver(uri, auth=(username, password))

    print("="*80)
    print("CREATING VECTOR INDEX")
    print("="*80)
    print()

    try:
        with driver.session(database=database) as session:
            print("[1/4] Checking if index already exists...")

            # Check existing indexes
            result = session.run("SHOW INDEXES")
            existing_indexes = [record["name"] for record in result]

            if "document_embeddings" in existing_indexes:
                print("  [WARN]  Index 'document_embeddings' already exists")
                print("  Dropping existing index...")
                session.run("DROP INDEX document_embeddings IF EXISTS")

            print("\n[2/4] Verifying embeddings exist...")

            # Count documents with embeddings
            with_embeddings = session.run("""
                MATCH (d:Document)
                WHERE d.embedding IS NOT NULL AND size(d.embedding) = 768
                RETURN count(d) AS count
            """).single()['count']

            without_embeddings = session.run("""
                MATCH (d:Document)
                WHERE d.embedding IS NULL OR size(d.embedding) <> 768
                RETURN count(d) AS count
            """).single()['count']

            print(f"  Documents with embeddings: {with_embeddings}")
            print(f"  Documents without embeddings: {without_embeddings}")

            if with_embeddings == 0:
                print("\n  [ERROR] ERROR: No documents have embeddings!")
                print("  Please run Script 2 (generate_embeddings.py) first")
                return

            if without_embeddings > 0:
                print(f"\n  [WARN]  WARNING: {without_embeddings} documents missing embeddings")
                print("  Consider running Script 2 again to complete embedding generation")

            print("\n[3/4] Creating vector index...")
            print("  Index name: document_embeddings")
            print("  Node label: Document")
            print("  Property: embedding")
            print("  Dimensions: 768")
            print("  Similarity: cosine")

            # Create vector index
            cypher = """
            CALL db.index.vector.createNodeIndex(
                'document_embeddings',
                'Document',
                'embedding',
                768,
                'cosine'
            )
            """

            session.run(cypher)
            print("  [OK] Vector index created successfully")

            print("\n[4/4] Testing vector index...")

            # Get a sample embedding to test
            sample = session.run("""
                MATCH (d:Document)
                WHERE d.embedding IS NOT NULL AND size(d.embedding) = 768
                RETURN d.embedding AS embedding
                LIMIT 1
            """).single()

            if sample:
                test_embedding = sample['embedding']

                # Test vector search
                test_result = session.run("""
                    CALL db.index.vector.queryNodes('document_embeddings', 10, $embedding)
                    YIELD node, score
                    RETURN count(node) AS result_count
                """, {"embedding": test_embedding}).single()

                if test_result:
                    print(f"  [OK] Index test successful: {test_result['result_count']} results")
                else:
                    print("  [WARN]  Index test returned no results")
            else:
                print("  [WARN]  Could not get sample embedding for testing")

    except Exception as e:
        print(f"  [ERROR] Error: {e}")
        raise
    finally:
        driver.close()

    print("\n" + "="*80)
    print("VECTOR INDEX CREATED")
    print("="*80)
    print()
    print("[OK] Vector index creation complete!")
    print()
    print("Next steps:")
    print("  1. Run Script 5 (compute_communities.py)")
    print("  2. Test hybrid search (vector + BM25)")
    print()
    print("Example vector search query:")
    print("""
  CALL db.index.vector.queryNodes(
    'document_embeddings',
    20,
    $query_embedding
  )
  YIELD node, score
  RETURN node.doc_id AS doc_id,
         node.title AS title,
         score AS similarity
  ORDER BY score DESC
    """)


if __name__ == "__main__":
    create_vector_index()
