"""
Script 1: Create Indexes
=========================

Purpose: Create temporal and composite indexes for fast Neo4j queries.

This script creates:
- Temporal index on Document.published_at (datetime field)
- Composite index on (doc_type, published_at)
- Technology ID index
- Company name index (NOT ticker, per user specification)
- Document doc_id index

Runtime: ~2 minutes
Cost: Free
Safe to run: YES
"""

import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def create_indexes():
    """Create all required indexes for the multi-agent system."""

    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    if not uri or not password:
        raise ValueError("Neo4j credentials not found in environment variables")

    driver = GraphDatabase.driver(uri, auth=(username, password), database=database)

    print("="*80)
    print("CREATING NEO4J INDEXES")
    print("="*80)
    print()

    indexes = [
        {
            "name": "document_published_at",
            "cypher": "CREATE INDEX document_published_at IF NOT EXISTS FOR (d:Document) ON (d.published_at)",
            "description": "Temporal index on Document.published_at"
        },
        {
            "name": "document_type_published",
            "cypher": "CREATE INDEX document_type_published IF NOT EXISTS FOR (d:Document) ON (d.doc_type, d.published_at)",
            "description": "Composite index on (doc_type, published_at)"
        },
        {
            "name": "technology_id",
            "cypher": "CREATE INDEX technology_id IF NOT EXISTS FOR (t:Technology) ON (t.id)",
            "description": "Technology ID index (primary lookup)"
        },
        {
            "name": "company_name",
            "cypher": "CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name)",
            "description": "Company name index (NOT ticker)"
        },
        {
            "name": "document_doc_id",
            "cypher": "CREATE INDEX document_doc_id IF NOT EXISTS FOR (d:Document) ON (d.doc_id)",
            "description": "Document doc_id index (for deduplication)"
        }
    ]

    created_count = 0

    with driver.session() as session:
        for idx in indexes:
            print(f"[{idx['name']}] {idx['description']}")
            try:
                session.run(idx['cypher'])
                print(f"  [OK] Created successfully")
                created_count += 1
            except Exception as e:
                print(f"  [WARN]  Error: {e}")
            print()

    driver.close()

    print("="*80)
    print(f"INDEXES CREATED: {created_count}/{len(indexes)}")
    print("="*80)
    print()
    print("[OK] Index creation complete!")
    print()
    print("Next steps:")
    print("  1. Run Script 7 (validate_prerequisites.py) to verify")
    print("  2. Review cost estimate for embeddings generation")
    print()


if __name__ == "__main__":
    create_indexes()
