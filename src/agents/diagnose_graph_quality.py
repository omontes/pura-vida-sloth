"""
Graph Data Quality Diagnostics
Run this to check if missing properties are causing low scores.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.neo4j_client import Neo4jClient


async def check_property_completeness():
    """Check if critical properties exist in the graph."""
    print("\n" + "="*80)
    print("GRAPH DATA QUALITY DIAGNOSTICS")
    print("="*80)

    client = Neo4jClient()
    await client.connect()

    try:
        # Query 1: Check document property completeness
        query1 = """
        MATCH (d:Document)
        WHERE d.doc_type IN ['patent', 'technical_paper', 'news', 'government_contract', 'regulation', 'sec_filing']
        RETURN
          d.doc_type AS doc_type,
          count(d) AS total_docs,
          count(d.quality_score) AS has_quality_score,
          count(d.pagerank) AS has_pagerank,
          count(d.published_at) AS has_published_at,
          avg(d.quality_score) AS avg_quality_score,
          100.0 * count(d.quality_score) / count(d) AS pct_has_quality_score,
          100.0 * count(d.pagerank) / count(d) AS pct_has_pagerank
        ORDER BY d.doc_type
        """

        print("\n[CHECK 1] Document Property Completeness")
        print("-" * 80)
        print(f"{'Doc Type':<25} {'Total':<10} {'QScore%':<12} {'PageRank%':<12}")
        print("-" * 80)

        async with client.driver.session() as session:
            result = await session.run(query1)
            records = await result.values()

            for record in records:
                doc_type = record[0]
                total = record[1]
                pct_quality = record[6] if record[6] else 0.0
                pct_pagerank = record[7] if record[7] else 0.0

                print(f"{doc_type:<25} {total:<10} {pct_quality:<12.1f}% {pct_pagerank:<12.1f}%")

        # Query 2: Check relationship role coverage
        query2 = """
        MATCH (t:Technology)-[m:MENTIONED_IN]->(d:Document)
        RETURN
          d.doc_type AS doc_type,
          m.role AS role,
          count(m) AS relationship_count
        ORDER BY d.doc_type, relationship_count DESC
        LIMIT 30
        """

        print("\n[CHECK 2] Relationship Role Coverage (Top 30)")
        print("-" * 80)
        print(f"{'Doc Type':<25} {'Role':<25} {'Count':<10}")
        print("-" * 80)

        async with client.driver.session() as session:
            result = await session.run(query2)
            records = await result.values()

            for record in records:
                doc_type = record[0]
                role = record[1] if record[1] else "NULL"
                count = record[2]

                print(f"{doc_type:<25} {role:<25} {count:<10}")

        # Query 3: Sample technology coverage
        query3 = """
        MATCH (t:Technology)-[:MENTIONED_IN]->(d:Document)
        WITH t, d.doc_type AS doc_type, count(DISTINCT d) AS doc_count
        WITH t, collect({doc_type: doc_type, count: doc_count}) AS coverage, sum(doc_count) AS total_docs
        RETURN
          t.id AS tech_id,
          total_docs,
          coverage
        ORDER BY total_docs DESC
        LIMIT 10
        """

        print("\n[CHECK 3] Top 10 Technologies by Document Count")
        print("-" * 80)
        print(f"{'Technology ID':<35} {'Total Docs':<12}")
        print("-" * 80)

        async with client.driver.session() as session:
            result = await session.run(query3)
            records = await result.values()

            for record in records:
                tech_id = record[0]
                total = record[1]

                print(f"{tech_id:<35} {total:<12}")

        # Query 4: Check for quality_score filter impact
        query4 = """
        MATCH (d:Document)
        WHERE d.doc_type IN ['patent', 'technical_paper', 'news']
        WITH d.doc_type AS doc_type,
             count(d) AS total,
             count(CASE WHEN d.quality_score >= 0.85 THEN 1 END) AS above_085,
             count(CASE WHEN d.quality_score >= 0.70 THEN 1 END) AS above_070
        RETURN
          doc_type,
          total,
          above_085,
          above_070,
          100.0 * above_085 / total AS pct_above_085,
          100.0 * above_070 / total AS pct_above_070
        ORDER BY doc_type
        """

        print("\n[CHECK 4] Impact of quality_score Filter")
        print("-" * 80)
        print(f"{'Doc Type':<25} {'Total':<10} {'≥0.85%':<12} {'≥0.70%':<12}")
        print("-" * 80)

        async with client.driver.session() as session:
            result = await session.run(query4)
            records = await result.values()

            for record in records:
                doc_type = record[0]
                total = record[1]
                pct_085 = record[4] if record[4] else 0.0
                pct_070 = record[5] if record[5] else 0.0

                print(f"{doc_type:<25} {total:<10} {pct_085:<12.1f}% {pct_070:<12.1f}%")

        print("\n" + "="*80)
        print("DIAGNOSTICS COMPLETE")
        print("="*80)
        print("\n[RECOMMENDATIONS]")
        print("1. If quality_score % is low (<50%): Lower filter to 0.70 or remove")
        print("2. If pagerank % is low (<30%): PageRank may not be computed")
        print("3. If role is NULL for many relationships: Roles not set during ingestion")
        print("4. If document counts are very low: Check ingestion completeness")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(check_property_completeness())
