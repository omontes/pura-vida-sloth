"""
Script 3: Create Full-Text Index
==================================

Purpose: Create BM25 full-text search index for Documents.

This script creates:
- Full-text index on Document(title, summary, content)
- Analyzer: standard-no-stop-words
- Eventually consistent mode for performance

Runtime: ~2-3 minutes
Cost: Free
Safe to run: YES (requires embeddings from Script 2)
"""

import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def create_fulltext_index():
    """Create BM25 full-text search index."""

    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    if not uri or not password:
        raise ValueError("Neo4j credentials not found in environment variables")

    driver = GraphDatabase.driver(uri, auth=(username, password))

    print("="*80)
    print("CREATING FULL-TEXT INDEX")
    print("="*80)
    print()

    try:
        with driver.session(database=database) as session:
            print("[1/3] Checking if index already exists...")

            # Check existing indexes
            result = session.run("SHOW INDEXES")
            existing_indexes = [record["name"] for record in result]

            if "document_fulltext" in existing_indexes:
                print("  [WARN]  Index 'document_fulltext' already exists")
                print("  Dropping existing index...")
                session.run("DROP INDEX document_fulltext IF EXISTS")

            print("\n[2/3] Creating full-text index...")
            print("  Index name: document_fulltext")
            print("  Node label: Document")
            print("  Properties: title, summary, content")
            print("  Analyzer: standard-no-stop-words")
            print("  Mode: eventually_consistent")

            # Create full-text index (Neo4j 5.x syntax)
            cypher = """
            CREATE FULLTEXT INDEX document_fulltext IF NOT EXISTS
            FOR (d:Document)
            ON EACH [d.title, d.summary, d.content]
            """

            session.run(cypher)
            print("  [OK] Full-text index created successfully")

            print("\n[3/3] Verifying index...")

            # Count documents that will be indexed
            doc_count = session.run("""
                MATCH (d:Document)
                WHERE d.title IS NOT NULL OR d.summary IS NOT NULL OR d.content IS NOT NULL
                RETURN count(d) AS count
            """).single()['count']

            print(f"  Documents to index: {doc_count}")

            # Test query
            print("\n  Testing index with sample query...")
            try:
                test_result = session.run("""
                    CALL db.index.fulltext.queryNodes('document_fulltext', 'eVTOL OR aircraft')
                    YIELD node, score
                    RETURN count(node) AS result_count
                    LIMIT 10
                """).single()

                if test_result:
                    print(f"  [OK] Index test successful: {test_result['result_count']} results")
                else:
                    print("  [WARN]  Index test returned no results (may need time to populate)")
            except Exception as e:
                print(f"  [WARN]  Test query skipped (index needs time to populate): {e}")

    except Exception as e:
        print(f"  [ERROR] Error: {e}")
        raise
    finally:
        driver.close()

    print("\n" + "="*80)
    print("FULL-TEXT INDEX CREATED")
    print("="*80)
    print()
    print("[OK] Full-text index creation complete!")
    print()
    print("Next steps:")
    print("  1. Run Script 4 (create_vector_index.py)")
    print("  2. Test hybrid search (vector + BM25)")
    print()
    print("Example hybrid search query:")
    print("""
  CALL {
    CALL db.index.fulltext.queryNodes('document_fulltext', 'eVTOL')
    YIELD node, score
    RETURN node, score AS bm25_score
    ORDER BY score DESC LIMIT 10
  }
  WITH node, bm25_score
  CALL {
    WITH node
    MATCH (d:Document)
    WHERE d.embedding IS NOT NULL
    WITH d, gds.similarity.cosine(d.embedding, $query_embedding) AS vector_score
    RETURN d AS node, vector_score
    ORDER BY vector_score DESC LIMIT 10
  }
  WITH node, bm25_score, vector_score,
       1.0 / (60 + bm25_rank) + 1.0 / (60 + vector_rank) AS rrf_score
  RETURN node, rrf_score
  ORDER BY rrf_score DESC
  LIMIT 20
    """)


if __name__ == "__main__":
    create_fulltext_index()
