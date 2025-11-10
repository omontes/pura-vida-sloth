"""Check what properties exist on patent documents"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.graph.neo4j_client import Neo4jClient


async def check_patent_properties():
    """Check what properties exist on patent documents."""
    client = Neo4jClient()
    await client.connect()

    try:
        async with client.driver.session() as session:
            # Get sample patent documents
            query = """
            MATCH (d:Document {doc_type: 'patent'})
            RETURN d
            LIMIT 3
            """

            result = await session.run(query)
            records = await result.values()

            print("\n" + "="*80)
            print("PATENT DOCUMENT PROPERTIES")
            print("="*80 + "\n")

            if not records:
                print("No patent documents found in graph!")
                return

            for i, (doc,) in enumerate(records, 1):
                print(f"\nDocument {i}:")
                print(f"  doc_id: {doc.get('doc_id')}")
                print(f"  doc_type: {doc.get('doc_type')}")
                print(f"  title: {doc.get('title', 'N/A')[:80]}")

                # Check for citation-related properties
                print(f"\n  Looking for citation properties:")
                for key in sorted(doc.keys()):
                    if 'citation' in key.lower() or 'cite' in key.lower():
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
    asyncio.run(check_patent_properties())
