"""
Script 2: Generate Embeddings
===============================

Purpose: Generate OpenAI embeddings for Documents, Technologies, and Companies.

This script creates:
- Document.embedding (768-dim) from title + summary + content
- Technology.embedding (768-dim) from name + domain + description
- Company.embedding (768-dim) from name + aliases (joined)

Model: text-embedding-3-small (768 dimensions, $0.00002/1k tokens)
Estimated cost: ~$0.20-1.00 depending on node counts

Runtime: ~10-15 minutes
Cost: $0.20-1.00 (OpenAI embeddings API)
Safe to run: YES (but expensive - confirm before running)

IMPORTANT: Creates 'embedding' property on nodes (doesn't exist yet)
"""

import os
import json
import sys
import argparse
from typing import List, Dict, Any
from neo4j import GraphDatabase
from dotenv import load_dotenv
import openai
from openai import OpenAI
import time

# Load environment variables
load_dotenv()


class EmbeddingGenerator:
    """Generate embeddings for graph nodes with checkpoint/resume capability."""

    def __init__(self, neo4j_uri: str, neo4j_username: str, neo4j_password: str,
                 neo4j_database: str, openai_api_key: str):
        """Initialize clients."""
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
        self.database = neo4j_database
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.checkpoint_file = "graph/prerequisites_configuration/.checkpoint_embeddings.json"

    def load_checkpoint(self) -> Dict[str, List[str]]:
        """Load checkpoint of completed node IDs."""
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        return {"documents": [], "technologies": [], "companies": []}

    def save_checkpoint(self, checkpoint: Dict[str, List[str]]):
        """Save checkpoint."""
        os.makedirs(os.path.dirname(self.checkpoint_file), exist_ok=True)
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI text-embedding-3-small."""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=768
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"  [WARN]  OpenAI API error: {e}")
            raise

    def get_nodes_to_embed(self, node_type: str, text_properties: List[str]) -> List[Dict[str, Any]]:
        """Get nodes that need embeddings."""
        # Build property extraction
        if node_type == "Document":
            id_property = "doc_id"
        elif node_type == "Technology":
            id_property = "id"
        elif node_type == "Company":
            id_property = "name"
        else:
            raise ValueError(f"Unknown node type: {node_type}")

        cypher = f"""
        MATCH (n:{node_type})
        WHERE n.embedding IS NULL OR size(n.embedding) = 0
        RETURN n.{id_property} AS id,
               {', '.join([f'n.{prop} AS {prop}' for prop in text_properties])}
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(cypher)
            return [dict(record) for record in result]

    def update_node_embedding(self, node_type: str, node_id: str, embedding: List[float]):
        """Update node with generated embedding."""
        if node_type == "Document":
            id_property = "doc_id"
        elif node_type == "Technology":
            id_property = "id"
        elif node_type == "Company":
            id_property = "name"
        else:
            raise ValueError(f"Unknown node type: {node_type}")

        cypher = f"""
        MATCH (n:{node_type} {{{id_property}: $node_id}})
        SET n.embedding = $embedding
        RETURN n.{id_property} AS id
        """

        with self.driver.session(database=self.database) as session:
            session.run(cypher, {"node_id": node_id, "embedding": embedding})

    def embed_documents(self, checkpoint: Dict[str, List[str]]) -> int:
        """Generate embeddings for Documents."""
        print("\n[DOCUMENTS] Generating embeddings...")

        nodes = self.get_nodes_to_embed("Document", ["title", "summary", "content"])
        total = len(nodes)

        if total == 0:
            print("  [OK] All documents already have embeddings")
            return 0

        print(f"  Found {total} documents without embeddings")

        processed = 0
        for idx, node in enumerate(nodes, 1):
            doc_id = node['id']

            # Skip if in checkpoint
            if doc_id in checkpoint['documents']:
                continue

            # Build text: title + summary + content
            title = node.get('title', '')
            summary = node.get('summary', '')
            content = node.get('content', '')
            text = f"{title} {summary} {content}".strip()

            if not text:
                print(f"  [WARN]  Skipping {doc_id} (empty text)")
                continue

            # Generate embedding
            try:
                embedding = self.generate_embedding(text)
                self.update_node_embedding("Document", doc_id, embedding)
                checkpoint['documents'].append(doc_id)
                processed += 1

                if processed % 10 == 0:
                    print(f"  Progress: {processed}/{total} documents")
                    self.save_checkpoint(checkpoint)

                # Rate limiting (OpenAI: 3000 RPM for tier 1)
                time.sleep(0.02)  # 50 requests/second = well under limit

            except Exception as e:
                print(f"  [WARN]  Failed {doc_id}: {e}")
                continue

        self.save_checkpoint(checkpoint)
        print(f"  [OK] Completed: {processed} documents")
        return processed

    def embed_technologies(self, checkpoint: Dict[str, List[str]]) -> int:
        """Generate embeddings for Technologies."""
        print("\n[TECHNOLOGIES] Generating embeddings...")

        nodes = self.get_nodes_to_embed("Technology", ["name", "domain", "description"])
        total = len(nodes)

        if total == 0:
            print("  [OK] All technologies already have embeddings")
            return 0

        print(f"  Found {total} technologies without embeddings")

        processed = 0
        for idx, node in enumerate(nodes, 1):
            tech_id = node['id']

            # Skip if in checkpoint
            if tech_id in checkpoint['technologies']:
                continue

            # Build text: name + domain + description
            name = node.get('name', '')
            domain = node.get('domain', '')
            description = node.get('description', '')
            text = f"{name} {domain} {description}".strip()

            if not text:
                print(f"  [WARN]  Skipping {tech_id} (empty text)")
                continue

            # Generate embedding
            try:
                embedding = self.generate_embedding(text)
                self.update_node_embedding("Technology", tech_id, embedding)
                checkpoint['technologies'].append(tech_id)
                processed += 1

                if processed % 10 == 0:
                    print(f"  Progress: {processed}/{total} technologies")
                    self.save_checkpoint(checkpoint)

                time.sleep(0.02)

            except Exception as e:
                print(f"  [WARN]  Failed {tech_id}: {e}")
                continue

        self.save_checkpoint(checkpoint)
        print(f"  [OK] Completed: {processed} technologies")
        return processed

    def embed_companies(self, checkpoint: Dict[str, List[str]]) -> int:
        """Generate embeddings for Companies."""
        print("\n[COMPANIES] Generating embeddings...")

        nodes = self.get_nodes_to_embed("Company", ["name", "aliases"])
        total = len(nodes)

        if total == 0:
            print("  [OK] All companies already have embeddings")
            return 0

        print(f"  Found {total} companies without embeddings")

        processed = 0
        for idx, node in enumerate(nodes, 1):
            company_name = node['id']

            # Skip if in checkpoint
            if company_name in checkpoint['companies']:
                continue

            # Build text: name + aliases (joined)
            name = node.get('name', '')
            aliases = node.get('aliases', [])
            # Join aliases list into string
            aliases_str = ' '.join(aliases) if aliases and isinstance(aliases, list) else ''
            text = f"{name} {aliases_str}".strip()

            if not text:
                print(f"  [WARN]  Skipping {company_name} (empty text)")
                continue

            # Generate embedding
            try:
                embedding = self.generate_embedding(text)
                self.update_node_embedding("Company", company_name, embedding)
                checkpoint['companies'].append(company_name)
                processed += 1

                if processed % 10 == 0:
                    print(f"  Progress: {processed}/{total} companies")
                    self.save_checkpoint(checkpoint)

                time.sleep(0.02)

            except Exception as e:
                print(f"  [WARN]  Failed {company_name}: {e}")
                continue

        self.save_checkpoint(checkpoint)
        print(f"  [OK] Completed: {processed} companies")
        return processed

    def close(self):
        """Close Neo4j driver."""
        self.driver.close()


def estimate_cost() -> Dict[str, Any]:
    """Estimate embedding generation cost."""
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    driver = GraphDatabase.driver(uri, auth=(username, password))

    with driver.session(database=database) as session:
        # Count nodes without embeddings
        doc_count = session.run("""
            MATCH (d:Document)
            WHERE d.embedding IS NULL OR size(d.embedding) = 0
            RETURN count(d) AS count
        """).single()['count']

        tech_count = session.run("""
            MATCH (t:Technology)
            WHERE t.embedding IS NULL OR size(t.embedding) = 0
            RETURN count(t) AS count
        """).single()['count']

        company_count = session.run("""
            MATCH (c:Company)
            WHERE c.embedding IS NULL OR size(c.embedding) = 0
            RETURN count(c) AS count
        """).single()['count']

    driver.close()

    # Estimate tokens (very rough: ~5 tokens per word, avg 30 words)
    doc_tokens = doc_count * 150  # title + summary
    tech_tokens = tech_count * 20  # name + domain
    company_tokens = company_count * 10  # just name

    total_tokens = doc_tokens + tech_tokens + company_tokens

    # OpenAI pricing: $0.00002 per 1k tokens
    estimated_cost = (total_tokens / 1000) * 0.00002

    return {
        "documents": doc_count,
        "technologies": tech_count,
        "companies": company_count,
        "total_nodes": doc_count + tech_count + company_count,
        "estimated_tokens": total_tokens,
        "estimated_cost_usd": round(estimated_cost, 2),
        "estimated_runtime_minutes": round((doc_count + tech_count + company_count) / 50 / 60, 1)
    }


def generate_embeddings(auto_approve: bool = False):
    """Main function to generate all embeddings."""

    print("="*80)
    print("GENERATING EMBEDDINGS")
    print("="*80)

    # Load environment
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not all([uri, password, openai_api_key]):
        raise ValueError("Missing required environment variables")

    # Estimate cost first
    print("\n[1/4] Estimating cost...")
    estimate = estimate_cost()
    print(f"  Documents: {estimate['documents']}")
    print(f"  Technologies: {estimate['technologies']}")
    print(f"  Companies: {estimate['companies']}")
    print(f"  Total nodes: {estimate['total_nodes']}")
    print(f"  Estimated tokens: {estimate['estimated_tokens']:,}")
    print(f"  Estimated cost: ${estimate['estimated_cost_usd']}")
    print(f"  Estimated runtime: {estimate['estimated_runtime_minutes']} minutes")

    if estimate['total_nodes'] == 0:
        print("\n[OK] All nodes already have embeddings!")
        return

    # Confirm before proceeding
    if not auto_approve:
        print("\n[WARN]  This operation will call OpenAI API and incur costs.")
        response = input("Proceed? (yes/no): ").strip().lower()
        if response != 'yes':
            print("[ERROR] Aborted by user")
            return
    else:
        print("\n[AUTO-APPROVE] Proceeding automatically...")

    # Initialize generator
    print("\n[2/4] Initializing generator...")
    generator = EmbeddingGenerator(uri, username, password, database, openai_api_key)

    # Load checkpoint
    print("[3/4] Loading checkpoint...")
    checkpoint = generator.load_checkpoint()
    print(f"  Previously completed: {len(checkpoint['documents'])} docs, "
          f"{len(checkpoint['technologies'])} techs, {len(checkpoint['companies'])} companies")

    # Generate embeddings
    print("\n[4/4] Generating embeddings...")
    total_processed = 0

    try:
        total_processed += generator.embed_documents(checkpoint)
        total_processed += generator.embed_technologies(checkpoint)
        total_processed += generator.embed_companies(checkpoint)
    except KeyboardInterrupt:
        print("\n[WARN]  Interrupted by user - checkpoint saved")
    finally:
        generator.close()

    print("\n" + "="*80)
    print(f"EMBEDDINGS GENERATED: {total_processed} nodes")
    print("="*80)
    print()
    print("[OK] Embedding generation complete!")
    print()
    print("Next steps:")
    print("  1. Run Script 3 (create_fulltext_index.py)")
    print("  2. Run Script 4 (create_vector_index.py)")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate embeddings for Neo4j nodes")
    parser.add_argument("--auto-approve", action="store_true",
                       help="Auto-approve without prompting")
    args = parser.parse_args()

    generate_embeddings(auto_approve=args.auto_approve)
