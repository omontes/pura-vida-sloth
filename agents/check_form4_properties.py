"""Check if Form 4 insider trading documents exist and their properties"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.neo4j_client import Neo4jClient


async def check_form4_properties():
    """Check Form 4 documents for insider trading properties."""
    client = Neo4jClient()
    await client.connect()

    try:
        async with client.driver.session() as session:
            # Check for Form 4 documents
            query = """
            MATCH (d:Document {doc_type: 'sec_filing'})
            WHERE d.filing_type IN ['3', '4', '5', '13F', 'form_3', 'form_4', 'form_5', 'form_13f']
            RETURN d.filing_type AS filing_type, count(*) AS count
            ORDER BY count DESC
            """

            result = await session.run(query)
            records = await result.values()

            print("\n" + "="*80)
            print("INSIDER TRADING FORM TYPES")
            print("="*80 + "\n")

            if not records:
                print("No Form 3/4/5/13F documents found!")
                print("\nChecking all filing_type values:")

                all_types_query = """
                MATCH (d:Document {doc_type: 'sec_filing'})
                RETURN DISTINCT d.filing_type AS filing_type, count(*) AS count
                ORDER BY count DESC
                """
                result = await session.run(all_types_query)
                all_records = await result.values()

                for filing_type, count in all_records:
                    print(f"  {filing_type}: {count}")

                print("\nConclusion: No insider trading forms in graph.")
                print("Risk queries trying to access Form 3/4/5/13F will return zero results.")
            else:
                for filing_type, count in records:
                    print(f"{filing_type}: {count} documents")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(check_form4_properties())
