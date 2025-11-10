"""
Script 5: Compute Communities
===============================

Purpose: Pre-compute 6 different community detection variants.

This script creates:
- Louvain v0 (resolution 0.8) - broader communities
- Louvain v1 (resolution 1.0) - balanced communities
- Louvain v2 (resolution 1.2) - finer communities
- Leiden v3 (resolution 0.8) - broader communities (higher quality)
- Leiden v4 (resolution 1.0) - balanced communities (higher quality)
- Leiden v5 (resolution 1.2) - finer communities (higher quality)

Stores as node properties: community_v0 through community_v5

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


def compute_communities():
    """Compute all 6 community detection variants."""

    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    if not uri or not password:
        raise ValueError("Neo4j credentials not found in environment variables")

    driver = GraphDatabase.driver(uri, auth=(username, password))

    print("="*80)
    print("COMPUTING COMMUNITIES")
    print("="*80)
    print()

    # Community configurations
    configs = [
        {"version": 0, "algorithm": "Louvain", "resolution": 0.8, "description": "Broader communities"},
        {"version": 1, "algorithm": "Louvain", "resolution": 1.0, "description": "Balanced communities"},
        {"version": 2, "algorithm": "Louvain", "resolution": 1.2, "description": "Finer communities"},
        {"version": 3, "algorithm": "Leiden", "resolution": 0.8, "description": "Broader communities (high quality)"},
        {"version": 4, "algorithm": "Leiden", "resolution": 1.0, "description": "Balanced communities (high quality)"},
        {"version": 5, "algorithm": "Leiden", "resolution": 1.2, "description": "Finer communities (high quality)"},
    ]

    try:
        with driver.session(database=database) as session:
            print("[1/3] Estimating graph size...")

            # Count nodes and relationships
            node_count = session.run("MATCH (n) RETURN count(n) AS count").single()['count']
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()['count']

            print(f"  Nodes: {node_count:,}")
            print(f"  Relationships: {rel_count:,}")
            print(f"  Estimated runtime: {round((node_count + rel_count) / 100000 * 2, 1)} minutes")

            if node_count == 0 or rel_count == 0:
                print("\n  [ERROR] ERROR: Graph is empty or has no relationships!")
                print("  Cannot compute communities on empty graph")
                return

            # Confirm before proceeding
            print("\n[WARN]  This operation will compute 6 community detection variants.")
            print("This is computationally expensive and may take 5-10 minutes.")
            response = input("Proceed? (yes/no): ").strip().lower()
            if response != 'yes':
                print("[ERROR] Aborted by user")
                return

            print("\n[2/3] Computing communities...")

            for config in configs:
                version = config['version']
                algorithm = config['algorithm']
                resolution = config['resolution']
                description = config['description']

                print(f"\n  [v{version}] {algorithm} (resolution={resolution}) - {description}")

                start_time = time.time()

                graph_name = f'graph-v{version}'
                write_property = f'community_v{version}'

                try:
                    # Step 1: Create graph projection
                    session.run(f"""
                        CALL gds.graph.project(
                            '{graph_name}',
                            '*',
                            '*'
                        )
                    """)

                    # Step 2: Run algorithm and write results
                    if algorithm == "Louvain":
                        cypher = f"""
                        CALL gds.louvain.write(
                            '{graph_name}',
                            {{
                                writeProperty: $write_property
                            }}
                        )
                        YIELD communityCount, modularity
                        RETURN communityCount, modularity
                        """
                    else:  # Leiden
                        cypher = f"""
                        CALL gds.leiden.write(
                            '{graph_name}',
                            {{
                                writeProperty: $write_property
                            }}
                        )
                        YIELD communityCount, modularity
                        RETURN communityCount, modularity
                        """

                    result = session.run(cypher, {
                        "write_property": write_property
                    }).single()

                    elapsed = time.time() - start_time

                    if result:
                        community_count = result.get('communityCount', 0)
                        modularity = result.get('modularity', 0.0)
                        print(f"    [OK] Completed in {elapsed:.1f}s")
                        print(f"    Communities: {community_count}")
                        print(f"    Modularity: {modularity:.3f}")
                    else:
                        print(f"    [WARN]  Completed but no result returned")

                    # Step 3: Drop the graph projection
                    session.run(f"CALL gds.graph.drop('{graph_name}')")

                except Exception as e:
                    print(f"    [ERROR] Error: {e}")
                    # Try to drop graph if it exists
                    try:
                        session.run(f"CALL gds.graph.drop('{graph_name}')")
                    except:
                        pass
                    continue

            print("\n[3/3] Verifying communities...")

            # Verify all versions were created
            verify_cypher = """
            MATCH (n)
            WHERE n.community_v0 IS NOT NULL
            RETURN
                count(DISTINCT n.community_v0) AS v0_count,
                count(DISTINCT n.community_v1) AS v1_count,
                count(DISTINCT n.community_v2) AS v2_count,
                count(DISTINCT n.community_v3) AS v3_count,
                count(DISTINCT n.community_v4) AS v4_count,
                count(DISTINCT n.community_v5) AS v5_count,
                count(n) AS total_nodes
            """

            verify_result = session.run(verify_cypher).single()

            if verify_result:
                print(f"\n  Nodes with communities: {verify_result['total_nodes']}")
                for i in range(6):
                    count = verify_result[f'v{i}_count']
                    print(f"    v{i}: {count} communities")
            else:
                print("  [WARN]  Verification query returned no results")

    except Exception as e:
        print(f"\n  [ERROR] Error: {e}")
        raise
    finally:
        driver.close()

    print("\n" + "="*80)
    print("COMMUNITIES COMPUTED")
    print("="*80)
    print()
    print("[OK] Community computation complete!")
    print()
    print("Next steps:")
    print("  1. Run Script 6 (compute_graph_algorithms.py)")
    print("  2. Test community-based queries")
    print()
    print("Example community query:")
    print("""
  MATCH (t:Technology)
  WHERE t.community_v1 = 123  // Example community ID
  RETURN t.id AS technology_id,
         t.name AS technology_name,
         t.community_v1 AS community
  ORDER BY t.id
    """)


if __name__ == "__main__":
    compute_communities()
