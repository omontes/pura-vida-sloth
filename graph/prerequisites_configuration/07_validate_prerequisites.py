"""
Script 7: Validate Prerequisites
==================================

Purpose: Comprehensive validation of all graph prerequisites.

This script validates:
1. Temporal and composite indexes
2. Document embeddings (768-dim)
3. Technology embeddings (768-dim)
4. Company embeddings (768-dim)
5. Full-text index (BM25)
6. Vector index (cosine similarity)
7. Community detection (6 versions)
8. Graph algorithms (PageRank, centrality)

Runtime: ~1 minute
Cost: Free
Safe to run: YES (read-only validation)
"""

import os
from typing import Dict, List, Any
from neo4j import GraphDatabase
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()


class PrerequisiteValidator:
    """Validate all graph prerequisites."""

    def __init__(self, neo4j_uri: str, neo4j_username: str, neo4j_password: str, neo4j_database: str):
        """Initialize validator."""
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
        self.database = neo4j_database
        self.results = {
            "indexes": {},
            "embeddings": {},
            "search_indexes": {},
            "communities": {},
            "community_summaries": {},
            "algorithms": {},
            "overall_status": "UNKNOWN"
        }

    def validate_indexes(self):
        """Validate temporal and composite indexes."""
        print("\n[1/9] Validating Indexes...")

        required_indexes = [
            "document_published_at",
            "document_type_published",
            "technology_id",
            "company_name",
            "document_doc_id"
        ]

        with self.driver.session(database=self.database) as session:
            result = session.run("SHOW INDEXES")
            existing_indexes = {record["name"]: record for record in result}

            for idx_name in required_indexes:
                if idx_name in existing_indexes:
                    print(f"  [OK] {idx_name}")
                    self.results["indexes"][idx_name] = "PASS"
                else:
                    print(f"  [ERROR] {idx_name} (MISSING)")
                    self.results["indexes"][idx_name] = "FAIL"

    def validate_embeddings(self):
        """Validate embeddings for Documents, Technologies, Companies."""
        print("\n[2/9] Validating Embeddings...")

        with self.driver.session(database=self.database) as session:
            # Documents
            doc_stats = session.run("""
                MATCH (d:Document)
                WITH count(d) AS total,
                     count(CASE WHEN d.embedding IS NOT NULL AND size(d.embedding) = 768 THEN 1 END) AS with_embeddings
                RETURN total, with_embeddings,
                       toFloat(with_embeddings) / total * 100 AS percentage
            """).single()

            if doc_stats and doc_stats['total'] > 0:
                coverage = doc_stats['percentage']
                print(f"  Documents: {doc_stats['with_embeddings']}/{doc_stats['total']} ({coverage:.1f}%)")
                if coverage >= 95:
                    print(f"    [OK] PASS (>=95% coverage)")
                    self.results["embeddings"]["documents"] = "PASS"
                elif coverage >= 80:
                    print(f"    [WARN]  WARNING (80-95% coverage)")
                    self.results["embeddings"]["documents"] = "WARNING"
                else:
                    print(f"    [ERROR] FAIL (<80% coverage)")
                    self.results["embeddings"]["documents"] = "FAIL"
            else:
                print(f"  Documents: No documents found")
                self.results["embeddings"]["documents"] = "N/A"

            # Technologies
            tech_stats = session.run("""
                MATCH (t:Technology)
                WITH count(t) AS total,
                     count(CASE WHEN t.embedding IS NOT NULL AND size(t.embedding) = 768 THEN 1 END) AS with_embeddings
                RETURN total, with_embeddings,
                       toFloat(with_embeddings) / total * 100 AS percentage
            """).single()

            if tech_stats and tech_stats['total'] > 0:
                coverage = tech_stats['percentage']
                print(f"  Technologies: {tech_stats['with_embeddings']}/{tech_stats['total']} ({coverage:.1f}%)")
                if coverage >= 95:
                    print(f"    [OK] PASS (>=95% coverage)")
                    self.results["embeddings"]["technologies"] = "PASS"
                elif coverage >= 80:
                    print(f"    [WARN]  WARNING (80-95% coverage)")
                    self.results["embeddings"]["technologies"] = "WARNING"
                else:
                    print(f"    [ERROR] FAIL (<80% coverage)")
                    self.results["embeddings"]["technologies"] = "FAIL"
            else:
                print(f"  Technologies: No technologies found")
                self.results["embeddings"]["technologies"] = "N/A"

            # Companies
            company_stats = session.run("""
                MATCH (c:Company)
                WITH count(c) AS total,
                     count(CASE WHEN c.embedding IS NOT NULL AND size(c.embedding) = 768 THEN 1 END) AS with_embeddings
                RETURN total, with_embeddings,
                       toFloat(with_embeddings) / total * 100 AS percentage
            """).single()

            if company_stats and company_stats['total'] > 0:
                coverage = company_stats['percentage']
                print(f"  Companies: {company_stats['with_embeddings']}/{company_stats['total']} ({coverage:.1f}%)")
                if coverage >= 95:
                    print(f"    [OK] PASS (>=95% coverage)")
                    self.results["embeddings"]["companies"] = "PASS"
                elif coverage >= 80:
                    print(f"    [WARN]  WARNING (80-95% coverage)")
                    self.results["embeddings"]["companies"] = "WARNING"
                else:
                    print(f"    [ERROR] FAIL (<80% coverage)")
                    self.results["embeddings"]["companies"] = "FAIL"
            else:
                print(f"  Companies: No companies found")
                self.results["embeddings"]["companies"] = "N/A"

    def validate_fulltext_index(self):
        """Validate BM25 full-text index."""
        print("\n[3/9] Validating Full-Text Index...")

        with self.driver.session(database=self.database) as session:
            result = session.run("SHOW INDEXES")
            existing_indexes = {record["name"]: record for record in result}

            if "document_fulltext" in existing_indexes:
                print(f"  [OK] Index exists: document_fulltext")

                # Test query
                try:
                    test_result = session.run("""
                        CALL db.index.fulltext.queryNodes('document_fulltext', 'technology OR innovation')
                        YIELD node, score
                        RETURN count(node) AS result_count
                        LIMIT 10
                    """).single()

                    if test_result and test_result['result_count'] > 0:
                        print(f"  [OK] Test query successful ({test_result['result_count']} results)")
                        self.results["search_indexes"]["fulltext"] = "PASS"
                    else:
                        print(f"  [WARN]  Index exists but returned no results")
                        self.results["search_indexes"]["fulltext"] = "WARNING"
                except Exception as e:
                    print(f"  [ERROR] Test query failed: {e}")
                    self.results["search_indexes"]["fulltext"] = "FAIL"
            else:
                print(f"  [ERROR] Index missing: document_fulltext")
                self.results["search_indexes"]["fulltext"] = "FAIL"

    def validate_vector_index(self):
        """Validate vector similarity index."""
        print("\n[4/9] Validating Vector Index...")

        with self.driver.session(database=self.database) as session:
            result = session.run("SHOW INDEXES")
            existing_indexes = {record["name"]: record for record in result}

            if "document_embeddings" in existing_indexes:
                print(f"  [OK] Index exists: document_embeddings")

                # Test query
                try:
                    # Get sample embedding
                    sample = session.run("""
                        MATCH (d:Document)
                        WHERE d.embedding IS NOT NULL AND size(d.embedding) = 768
                        RETURN d.embedding AS embedding
                        LIMIT 1
                    """).single()

                    if sample:
                        test_embedding = sample['embedding']
                        test_result = session.run("""
                            CALL db.index.vector.queryNodes('document_embeddings', 10, $embedding)
                            YIELD node, score
                            RETURN count(node) AS result_count
                        """, {"embedding": test_embedding}).single()

                        if test_result and test_result['result_count'] > 0:
                            print(f"  [OK] Test query successful ({test_result['result_count']} results)")
                            self.results["search_indexes"]["vector"] = "PASS"
                        else:
                            print(f"  [WARN]  Index exists but returned no results")
                            self.results["search_indexes"]["vector"] = "WARNING"
                    else:
                        print(f"  [WARN]  No embeddings found for testing")
                        self.results["search_indexes"]["vector"] = "WARNING"
                except Exception as e:
                    print(f"  [ERROR] Test query failed: {e}")
                    self.results["search_indexes"]["vector"] = "FAIL"
            else:
                print(f"  [ERROR] Index missing: document_embeddings")
                self.results["search_indexes"]["vector"] = "FAIL"

    def validate_communities(self):
        """Validate 6 community detection versions."""
        print("\n[5/9] Validating Communities...")

        with self.driver.session(database=self.database) as session:
            # Check all 6 versions
            community_stats = session.run("""
                MATCH (n)
                RETURN
                    count(DISTINCT n.community_v0) AS v0_communities,
                    count(CASE WHEN n.community_v0 IS NOT NULL THEN 1 END) AS v0_nodes,
                    count(DISTINCT n.community_v1) AS v1_communities,
                    count(CASE WHEN n.community_v1 IS NOT NULL THEN 1 END) AS v1_nodes,
                    count(DISTINCT n.community_v2) AS v2_communities,
                    count(CASE WHEN n.community_v2 IS NOT NULL THEN 1 END) AS v2_nodes,
                    count(DISTINCT n.community_v3) AS v3_communities,
                    count(CASE WHEN n.community_v3 IS NOT NULL THEN 1 END) AS v3_nodes,
                    count(DISTINCT n.community_v4) AS v4_communities,
                    count(CASE WHEN n.community_v4 IS NOT NULL THEN 1 END) AS v4_nodes,
                    count(DISTINCT n.community_v5) AS v5_communities,
                    count(CASE WHEN n.community_v5 IS NOT NULL THEN 1 END) AS v5_nodes,
                    count(n) AS total_nodes
            """).single()

            if community_stats:
                total = community_stats['total_nodes']
                for i in range(6):
                    communities = community_stats[f'v{i}_communities']
                    nodes = community_stats[f'v{i}_nodes']
                    coverage = (nodes / total * 100) if total > 0 else 0

                    print(f"  v{i}: {communities} communities, {nodes}/{total} nodes ({coverage:.1f}%)")

                    if coverage >= 95:
                        print(f"    [OK] PASS")
                        self.results["communities"][f"v{i}"] = "PASS"
                    elif coverage >= 80:
                        print(f"    [WARN]  WARNING")
                        self.results["communities"][f"v{i}"] = "WARNING"
                    elif communities > 0:
                        print(f"    [WARN]  PARTIAL")
                        self.results["communities"][f"v{i}"] = "PARTIAL"
                    else:
                        print(f"    [ERROR] FAIL (not computed)")
                        self.results["communities"][f"v{i}"] = "FAIL"

    def validate_community_summaries(self):
        """Validate Community nodes with LLM-generated summaries."""
        print("\n[6/9] Validating Community Summaries...")

        with self.driver.session(database=self.database) as session:
            # Count Community nodes for each variant
            community_node_stats = session.run("""
                MATCH (c:Community)
                RETURN
                    count(DISTINCT CASE WHEN c.version = 0 THEN c.id END) AS v0_count,
                    count(DISTINCT CASE WHEN c.version = 1 THEN c.id END) AS v1_count,
                    count(DISTINCT CASE WHEN c.version = 2 THEN c.id END) AS v2_count,
                    count(DISTINCT CASE WHEN c.version = 3 THEN c.id END) AS v3_count,
                    count(DISTINCT CASE WHEN c.version = 4 THEN c.id END) AS v4_count,
                    count(DISTINCT CASE WHEN c.version = 5 THEN c.id END) AS v5_count,
                    count(c) AS total_communities
            """).single()

            if not community_node_stats or community_node_stats['total_communities'] == 0:
                print("  [ERROR] No Community nodes found")
                print("  Make sure Script 5.5 (generate_community_summaries.py) has been run!")
                for i in range(6):
                    self.results["community_summaries"][f"v{i}"] = "FAIL"
                return

            total_communities = community_node_stats['total_communities']
            print(f"  Found {total_communities} Community nodes")

            # Validate each variant
            for i in range(6):
                count = community_node_stats[f'v{i}_count']
                print(f"  v{i}: {count} community nodes")

                if count > 0:
                    print(f"    [OK] PASS")
                    self.results["community_summaries"][f"v{i}"] = "PASS"
                else:
                    print(f"    [ERROR] FAIL (no Community nodes)")
                    self.results["community_summaries"][f"v{i}"] = "FAIL"

            # Validate that summaries exist
            summary_stats = session.run("""
                MATCH (c:Community)
                WHERE c.summary IS NOT NULL AND c.summary <> ''
                RETURN count(c) AS with_summaries
            """).single()

            summaries_count = summary_stats['with_summaries'] if summary_stats else 0
            coverage = (summaries_count / total_communities * 100) if total_communities > 0 else 0

            print(f"\n  Summaries: {summaries_count}/{total_communities} ({coverage:.1f}%)")
            if coverage >= 95:
                print(f"    [OK] Summary coverage excellent")
            elif coverage >= 80:
                print(f"    [WARN]  Some communities missing summaries")
            else:
                print(f"    [ERROR] Many communities missing summaries")

    def validate_algorithms(self):
        """Validate PageRank and centrality algorithms."""
        print("\n[7/9] Validating Graph Algorithms...")

        with self.driver.session(database=self.database) as session:
            algo_stats = session.run("""
                MATCH (n)
                RETURN
                    count(CASE WHEN n.pagerank IS NOT NULL THEN 1 END) AS pagerank_nodes,
                    count(CASE WHEN n.degree_centrality IS NOT NULL THEN 1 END) AS degree_nodes,
                    count(CASE WHEN n.betweenness_centrality IS NOT NULL THEN 1 END) AS betweenness_nodes,
                    count(n) AS total_nodes
            """).single()

            if algo_stats:
                total = algo_stats['total_nodes']

                algorithms = [
                    ("PageRank", "pagerank_nodes"),
                    ("Degree Centrality", "degree_nodes"),
                    ("Betweenness Centrality", "betweenness_nodes")
                ]

                for algo_name, field in algorithms:
                    nodes = algo_stats[field]
                    coverage = (nodes / total * 100) if total > 0 else 0

                    print(f"  {algo_name}: {nodes}/{total} nodes ({coverage:.1f}%)")

                    if coverage >= 95:
                        print(f"    [OK] PASS")
                        self.results["algorithms"][algo_name] = "PASS"
                    elif coverage >= 80:
                        print(f"    [WARN]  WARNING")
                        self.results["algorithms"][algo_name] = "WARNING"
                    else:
                        print(f"    [ERROR] FAIL")
                        self.results["algorithms"][algo_name] = "FAIL"

    def compute_overall_status(self):
        """Compute overall validation status."""
        print("\n[8/9] Computing Overall Status...")

        all_results = []
        for category in ["indexes", "embeddings", "search_indexes", "communities", "community_summaries", "algorithms"]:
            all_results.extend(self.results[category].values())

        fail_count = all_results.count("FAIL")
        warning_count = all_results.count("WARNING")
        pass_count = all_results.count("PASS")
        na_count = all_results.count("N/A")
        total = len([r for r in all_results if r != "N/A"])

        print(f"  PASS: {pass_count}/{total}")
        print(f"  WARNING: {warning_count}/{total}")
        print(f"  FAIL: {fail_count}/{total}")
        print(f"  N/A: {na_count}")

        if fail_count == 0 and warning_count == 0:
            self.results["overall_status"] = "PASS"
        elif fail_count == 0:
            self.results["overall_status"] = "WARNING"
        else:
            self.results["overall_status"] = "FAIL"

    def print_summary(self):
        """Print validation summary."""
        print("\n[9/9] Validation Summary")
        print("="*80)

        if self.results["overall_status"] == "PASS":
            print("[OK] ALL PREREQUISITES READY")
            print()
            print("The graph is fully configured for the multi-agent system!")
            print()
            print("Next steps:")
            print("  1. Start multi-agent system development")
            print("  2. Test single-run MVP")
        elif self.results["overall_status"] == "WARNING":
            print("[WARN]  PREREQUISITES MOSTLY READY (with warnings)")
            print()
            print("Some prerequisites have partial coverage. Review warnings above.")
            print("The system may work but with reduced functionality.")
        else:
            print("[ERROR] PREREQUISITES INCOMPLETE")
            print()
            print("Missing prerequisites detected. Run the following scripts:")
            print()

            # Check what's missing
            if any(v == "FAIL" for v in self.results["indexes"].values()):
                print("  - Script 1: create_indexes.py")
            if any(v == "FAIL" for v in self.results["embeddings"].values()):
                print("  - Script 2: generate_embeddings.py")
            if self.results["search_indexes"].get("fulltext") == "FAIL":
                print("  - Script 3: create_fulltext_index.py")
            if self.results["search_indexes"].get("vector") == "FAIL":
                print("  - Script 4: create_vector_index.py")
            if any(v == "FAIL" for v in self.results["communities"].values()):
                print("  - Script 5: compute_communities.py")
            if any(v == "FAIL" for v in self.results["community_summaries"].values()):
                print("  - Script 5.5: generate_community_summaries.py")
            if any(v == "FAIL" for v in self.results["algorithms"].values()):
                print("  - Script 6: compute_graph_algorithms.py")

        print("="*80)

    def save_report(self, output_path: str = "graph/prerequisites_configuration/validation_report.json"):
        """Save validation report to JSON."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nValidation report saved: {output_path}")

    def close(self):
        """Close Neo4j driver."""
        self.driver.close()


def validate_prerequisites():
    """Main validation function."""

    print("="*80)
    print("VALIDATING GRAPH PREREQUISITES")
    print("="*80)

    # Load environment
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    if not uri or not password:
        raise ValueError("Neo4j credentials not found in environment variables")

    # Initialize validator
    validator = PrerequisiteValidator(uri, username, password, database)

    try:
        # Run all validations
        validator.validate_indexes()
        validator.validate_embeddings()
        validator.validate_fulltext_index()
        validator.validate_vector_index()
        validator.validate_communities()
        validator.validate_community_summaries()
        validator.validate_algorithms()
        validator.compute_overall_status()
        validator.print_summary()
        validator.save_report()

    finally:
        validator.close()


if __name__ == "__main__":
    validate_prerequisites()
