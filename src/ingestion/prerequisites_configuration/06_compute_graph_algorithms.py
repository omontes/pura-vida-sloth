"""
Script 6: Compute Graph Algorithms
====================================

Purpose: Pre-compute graph algorithms for node importance/centrality.

This script computes:
- PageRank (technology/company importance)
- Degree Centrality (connection count)
- Betweenness Centrality (technology bridging role)

Stores as node properties:
- pagerank (float)
- degree_centrality (float)
- betweenness_centrality (float)

Runtime: ~5-10 minutes (depends on graph size)
Cost: Free (computation only)
Safe to run: YES (but expensive - confirm before running)
"""

import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()


def compute_graph_algorithms():
    """Compute PageRank, degree centrality, and betweenness centrality."""

    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    if not uri or not password:
        raise ValueError("Neo4j credentials not found in environment variables")

    driver = GraphDatabase.driver(uri, auth=(username, password))

    print("="*80)
    print("COMPUTING GRAPH ALGORITHMS")
    print("="*80)
    print()

    try:
        with driver.session(database=database) as session:
            print("[1/4] Estimating graph size...")

            # Count nodes and relationships
            node_count = session.run("MATCH (n) RETURN count(n) AS count").single()['count']
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()['count']

            print(f"  Nodes: {node_count:,}")
            print(f"  Relationships: {rel_count:,}")
            print(f"  Estimated runtime: {round((node_count + rel_count) / 50000 * 3, 1)} minutes")

            if node_count == 0 or rel_count == 0:
                print("\n  [ERROR] ERROR: Graph is empty or has no relationships!")
                print("  Cannot compute algorithms on empty graph")
                return

            # Confirm before proceeding
            print("\n[WARN]  This operation will compute 3 graph algorithms:")
            print("  1. PageRank (importance scoring)")
            print("  2. Degree Centrality (connection count)")
            print("  3. Betweenness Centrality (bridging role)")
            print("\nThis is computationally expensive and may take 5-10 minutes.")
            response = input("Proceed? (yes/no): ").strip().lower()
            if response != 'yes':
                print("[ERROR] Aborted by user")
                return

            print("\n[2/4] Computing PageRank...")
            start_time = time.time()

            try:
                # Create graph projection
                session.run("""
                    CALL gds.graph.project('pagerank-graph', '*', '*')
                """)

                # PageRank algorithm (GDS 2.x syntax)
                cypher_pagerank = """
                CALL gds.pageRank.write(
                    'pagerank-graph',
                    {
                        writeProperty: 'pagerank',
                        maxIterations: 20,
                        dampingFactor: 0.85,
                        tolerance: 0.0000001
                    }
                )
                YIELD nodePropertiesWritten, ranIterations
                RETURN nodePropertiesWritten, ranIterations
                """

                result = session.run(cypher_pagerank).single()
                elapsed = time.time() - start_time

                if result:
                    print(f"  [OK] Completed in {elapsed:.1f}s")
                    print(f"  Nodes updated: {result['nodePropertiesWritten']}")
                    print(f"  Iterations: {result['ranIterations']}")

                    # Show top PageRank nodes
                    top_nodes = session.run("""
                        MATCH (n)
                        WHERE n.pagerank IS NOT NULL
                        RETURN labels(n)[0] AS label, coalesce(n.name, n.id, n.doc_id) AS name,
                               n.pagerank AS pagerank
                        ORDER BY n.pagerank DESC
                        LIMIT 5
                    """).data()

                    if top_nodes:
                        print("  Top 5 by PageRank:")
                        for node in top_nodes:
                            print(f"    {node['label']}: {node['name']} ({node['pagerank']:.6f})")

                # Drop graph projection
                session.run("CALL gds.graph.drop('pagerank-graph')")

            except Exception as e:
                print(f"  [ERROR] Error: {e}")
                # Try to drop graph if it exists
                try:
                    session.run("CALL gds.graph.drop('pagerank-graph')")
                except:
                    pass

            print("\n[3/4] Computing Degree Centrality...")
            start_time = time.time()

            try:
                # Create graph projection
                session.run("""
                    CALL gds.graph.project('degree-graph', '*', '*')
                """)

                # Degree Centrality (GDS 2.x syntax)
                cypher_degree = """
                CALL gds.degree.write(
                    'degree-graph',
                    {
                        writeProperty: 'degree_centrality'
                    }
                )
                YIELD nodePropertiesWritten
                RETURN nodePropertiesWritten
                """

                result = session.run(cypher_degree).single()
                elapsed = time.time() - start_time

                if result:
                    print(f"  [OK] Completed in {elapsed:.1f}s")
                    print(f"  Nodes updated: {result['nodePropertiesWritten']}")

                    # Show top degree centrality nodes
                    top_nodes = session.run("""
                        MATCH (n)
                        WHERE n.degree_centrality IS NOT NULL
                        RETURN labels(n)[0] AS label, coalesce(n.name, n.id, n.doc_id) AS name,
                               n.degree_centrality AS degree
                        ORDER BY n.degree_centrality DESC
                        LIMIT 5
                    """).data()

                    if top_nodes:
                        print("  Top 5 by Degree Centrality:")
                        for node in top_nodes:
                            print(f"    {node['label']}: {node['name']} ({node['degree']:.0f} connections)")

                # Drop graph projection
                session.run("CALL gds.graph.drop('degree-graph')")

            except Exception as e:
                print(f"  [ERROR] Error: {e}")
                # Try to drop graph if it exists
                try:
                    session.run("CALL gds.graph.drop('degree-graph')")
                except:
                    pass

            print("\n[4/4] Computing Betweenness Centrality...")
            start_time = time.time()

            try:
                # Create graph projection
                session.run("""
                    CALL gds.graph.project('betweenness-graph', '*', '*')
                """)

                # Betweenness Centrality (GDS 2.x syntax)
                cypher_betweenness = """
                CALL gds.betweenness.write(
                    'betweenness-graph',
                    {
                        writeProperty: 'betweenness_centrality'
                    }
                )
                YIELD nodePropertiesWritten
                RETURN nodePropertiesWritten
                """

                result = session.run(cypher_betweenness).single()
                elapsed = time.time() - start_time

                if result:
                    print(f"  [OK] Completed in {elapsed:.1f}s")
                    print(f"  Nodes updated: {result['nodePropertiesWritten']}")

                    # Show top betweenness centrality nodes
                    top_nodes = session.run("""
                        MATCH (n)
                        WHERE n.betweenness_centrality IS NOT NULL
                        RETURN labels(n)[0] AS label, coalesce(n.name, n.id, n.doc_id) AS name,
                               n.betweenness_centrality AS betweenness
                        ORDER BY n.betweenness_centrality DESC
                        LIMIT 5
                    """).data()

                    if top_nodes:
                        print("  Top 5 by Betweenness Centrality:")
                        for node in top_nodes:
                            print(f"    {node['label']}: {node['name']} ({node['betweenness']:.2f})")

                # Drop graph projection
                session.run("CALL gds.graph.drop('betweenness-graph')")

            except Exception as e:
                print(f"  [ERROR] Error: {e}")
                # Try to drop graph if it exists
                try:
                    session.run("CALL gds.graph.drop('betweenness-graph')")
                except:
                    pass

            print("\n[SUMMARY] Verifying all algorithms...")

            # Verify all properties were created
            verify_cypher = """
            MATCH (n)
            WHERE n.pagerank IS NOT NULL
            RETURN
                count(n) AS nodes_with_pagerank,
                count(CASE WHEN n.degree_centrality IS NOT NULL THEN 1 END) AS nodes_with_degree,
                count(CASE WHEN n.betweenness_centrality IS NOT NULL THEN 1 END) AS nodes_with_betweenness
            """

            verify_result = session.run(verify_cypher).single()

            if verify_result:
                print(f"\n  Nodes with PageRank: {verify_result['nodes_with_pagerank']}")
                print(f"  Nodes with Degree Centrality: {verify_result['nodes_with_degree']}")
                print(f"  Nodes with Betweenness Centrality: {verify_result['nodes_with_betweenness']}")

    except Exception as e:
        print(f"\n  [ERROR] Error: {e}")
        raise
    finally:
        driver.close()

    print("\n" + "="*80)
    print("GRAPH ALGORITHMS COMPUTED")
    print("="*80)
    print()
    print("[OK] Graph algorithm computation complete!")
    print()
    print("Next steps:")
    print("  1. Run Script 7 (validate_prerequisites.py)")
    print("  2. Start multi-agent system development")
    print()
    print("Example algorithm query:")
    print("""
  MATCH (t:Technology)
  WHERE t.pagerank IS NOT NULL
  RETURN t.id AS technology_id,
         t.name AS technology_name,
         t.pagerank AS importance,
         t.degree_centrality AS connections,
         t.betweenness_centrality AS bridging_role
  ORDER BY t.pagerank DESC
  LIMIT 10
    """)


if __name__ == "__main__":
    compute_graph_algorithms()
