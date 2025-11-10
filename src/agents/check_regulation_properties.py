"""Check what properties exist on regulation documents"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.neo4j_client import Neo4jClient


async def check_regulation_properties():
    """Check what properties exist on regulation documents."""
    client = Neo4jClient()
    await client.connect()

    try:
        async with client.driver.session() as session:
            # Get sample regulation documents
            query = """
            MATCH (d:Document)
            WHERE d.doc_type = 'regulation'
            RETURN d
            LIMIT 5
            """

            result = await session.run(query)
            records = await result.values()

            print("\n" + "="*80)
            print("REGULATION DOCUMENT PROPERTIES")
            print("="*80 + "\n")

            if not records:
                print("No regulation documents found in graph!")
                return

            for i, (doc,) in enumerate(records, 1):
                print(f"\nDocument {i}:")
                print(f"  doc_id: {doc.get('doc_id')}")
                print(f"  doc_type: {doc.get('doc_type')}")
                print(f"  title: {doc.get('title', 'N/A')[:80]}")
                print(f"  published_at: {doc.get('published_at')}")
                print(f"  quality_score: {doc.get('quality_score')}")

                # Check for agency-related properties
                print(f"\n  Looking for agency/regulation properties:")
                for key in doc.keys():
                    if 'agency' in key.lower() or 'regulation' in key.lower() or 'type' in key.lower():
                        print(f"    {key}: {doc.get(key)}")

                print(f"\n  All properties:")
                for key in sorted(doc.keys()):
                    value = doc.get(key)
                    if isinstance(value, str) and len(value) > 60:
                        value = value[:60] + "..."
                    print(f"    {key}: {value}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(check_regulation_properties())
