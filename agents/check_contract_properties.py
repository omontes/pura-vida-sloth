"""Check what properties exist on government contract documents"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.neo4j_client import Neo4jClient


async def check_contract_properties():
    """Check what properties exist on government contract documents."""
    client = Neo4jClient()
    await client.connect()

    try:
        async with client.driver.session() as session:
            # Get sample contract documents
            query = """
            MATCH (d:Document {doc_type: 'government_contract'})
            RETURN d
            LIMIT 3
            """

            result = await session.run(query)
            records = await result.values()

            print("\n" + "="*80)
            print("GOVERNMENT CONTRACT DOCUMENT PROPERTIES")
            print("="*80 + "\n")

            if not records:
                print("No government_contract documents found in graph!")
                return

            for i, (doc,) in enumerate(records, 1):
                print(f"\nDocument {i}:")
                print(f"  doc_id: {doc.get('doc_id')}")
                print(f"  doc_type: {doc.get('doc_type')}")
                print(f"  title: {doc.get('title', 'N/A')[:80]}")

                # Check for awardee-related properties
                print(f"\n  Looking for awardee/contractor properties:")
                for key in sorted(doc.keys()):
                    if any(x in key.lower() for x in ['awardee', 'contractor', 'vendor', 'company', 'recipient']):
                        print(f"    {key}: {doc.get(key)}")

                print(f"\n  All properties:")
                for key in sorted(doc.keys()):
                    value = doc.get(key)
                    if isinstance(value, str) and len(value) > 60:
                        value = value[:60] + "..."
                    elif isinstance(value, list) and len(value) > 0:
                        value = f"[{len(value)} items]"
                    print(f"    {key}: {value}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(check_contract_properties())
