"""
Diagnose Data Availability - Check what data actually exists in Neo4j

Check if the graph has sufficient documents for layer scoring:
- Contracts for adoption scoring
- News for narrative scoring
- Patents for innovation scoring
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.graph.neo4j_client import Neo4jClient


async def diagnose_data_for_tech(tech_id: str):
    """Check what documents exist for a specific technology."""
    print(f"\n{'='*80}")
    print(f"DATA AVAILABILITY FOR: {tech_id}")
    print(f"{'='*80}")

    client = Neo4jClient()
    await client.connect()

    try:
        async with client.driver.session() as session:
            # Check all documents for this tech
            query = """
            MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
            RETURN
              d.doc_type AS doc_type,
              count(d) AS count,
              avg(d.quality_score) AS avg_quality,
              min(date(datetime(d.published_at))) AS earliest_date,
              max(date(datetime(d.published_at))) AS latest_date
            ORDER BY count DESC
            """

            result = await session.run(query, tech_id=tech_id)
            records = await result.values()

            print(f"\n[DOCUMENT TYPES]")
            total_docs = 0
            for record in records:
                doc_type, count, avg_q, earliest, latest = record
                total_docs += count
                print(f"  {doc_type:<25} {count:>4} docs  (quality: {avg_q:.2f})  [{earliest} to {latest}]")

            print(f"\n  TOTAL: {total_docs} documents")

            # Check contracts specifically (for adoption)
            contracts_query = """
            MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
            WHERE d.doc_type = 'government_contract'
            RETURN
              count(d) AS total,
              count(CASE WHEN date(datetime(d.published_at)) >= date('2024-01-01') THEN 1 END) AS last_year,
              count(CASE WHEN m.role = 'procured' THEN 1 END) AS with_procured_role,
              avg(d.quality_score) AS avg_quality
            """

            result = await session.run(contracts_query, tech_id=tech_id)
            record = await result.single()

            print(f"\n[CONTRACTS DETAIL]")
            if record:
                print(f"  Total contracts: {record['total']}")
                print(f"  Last year (2024+): {record['last_year']}")
                print(f"  With 'procured' role: {record['with_procured_role']}")
                print(f"  Avg quality: {record['avg_quality']:.2f}")

            # Check news specifically (for narrative)
            news_query = """
            MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
            WHERE d.doc_type = 'news'
            RETURN
              count(d) AS total,
              count(CASE WHEN date(datetime(d.published_at)) >= date('2024-07-01') THEN 1 END) AS last_6mo,
              count(CASE WHEN m.role = 'subject' THEN 1 END) AS with_subject_role,
              avg(d.quality_score) AS avg_quality,
              avg(d.sentiment) AS avg_sentiment
            """

            result = await session.run(news_query, tech_id=tech_id)
            record = await result.single()

            print(f"\n[NEWS DETAIL]")
            if record:
                print(f"  Total news: {record['total']}")
                print(f"  Last 6 months (2024-07+): {record['last_6mo']}")
                print(f"  With 'subject' role: {record['with_subject_role']}")
                print(f"  Avg quality: {record['avg_quality']:.2f}" if record['avg_quality'] else "  Avg quality: N/A")
                avg_sent = record.get('avg_sentiment')
                print(f"  Avg sentiment: {avg_sent:.2f}" if avg_sent is not None else "  Avg sentiment: N/A")

            # Check patents specifically (for innovation)
            patents_query = """
            MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
            WHERE d.doc_type = 'patent'
            RETURN
              count(d) AS total,
              count(CASE WHEN date(datetime(d.published_at)) >= date('2023-01-01') THEN 1 END) AS last_2yr,
              avg(d.quality_score) AS avg_quality
            """

            result = await session.run(patents_query, tech_id=tech_id)
            record = await result.single()

            print(f"\n[PATENTS DETAIL]")
            if record:
                print(f"  Total patents: {record['total']}")
                print(f"  Last 2 years (2023+): {record['last_2yr']}")
                print(f"  Avg quality: {record['avg_quality']:.2f}")

            # Sample some actual documents
            sample_query = """
            MATCH (t:Technology {id: $tech_id})-[m:MENTIONED_IN]->(d:Document)
            RETURN d.doc_id, d.doc_type, d.title, d.published_at, d.quality_score, m.role
            ORDER BY d.quality_score DESC
            LIMIT 10
            """

            result = await session.run(sample_query, tech_id=tech_id)
            records = await result.values()

            print(f"\n[SAMPLE DOCUMENTS - Top 10 by quality_score]")
            for doc_id, doc_type, title, pub_date, quality, role in records:
                title_short = (title[:50] + "...") if title and len(title) > 50 else (title or "No title")
                print(f"  {doc_type:<20} Q={quality:.2f}  role={role:<12}  {title_short}")

    finally:
        await client.close()


async def diagnose_multiple_techs():
    """Check data for multiple sample technologies."""
    # Sample technologies from different phases
    sample_techs = [
        "evtol",  # Should have lots of data
        "friction_welding_process",  # The only innovation_trigger
        "tilting_fan_assembly",  # A slope tech
        "evtol_powertrain_system",  # A trough tech
    ]

    for tech_id in sample_techs:
        await diagnose_data_for_tech(tech_id)
        print("\n")


if __name__ == "__main__":
    asyncio.run(diagnose_multiple_techs())
