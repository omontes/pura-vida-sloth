"""Check what SEC filing documents and properties exist in the graph"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.neo4j_client import Neo4jClient


async def check_sec_filing_properties():
    """Check what SEC filing documents and properties exist."""
    client = Neo4jClient()
    await client.connect()

    try:
        async with client.driver.session() as session:
            # Check sec_filing documents
            print("\n" + "="*80)
            print("SEC FILING PROPERTIES")
            print("="*80 + "\n")

            # Get sample sec_filing documents
            sample_query = """
            MATCH (d:Document {doc_type: 'sec_filing'})
            RETURN d
            LIMIT 5
            """

            result = await session.run(sample_query)
            records = await result.values()

            if not records:
                print("No sec_filing documents found in graph!")
                return

            for i, (doc,) in enumerate(records, 1):
                print(f"\nDocument {i}:")
                print(f"  doc_id: {doc.get('doc_id')}")
                print(f"  doc_type: {doc.get('doc_type')}")
                print(f"  title: {doc.get('title', 'N/A')[:80]}")
                print(f"  published_at: {doc.get('published_at')}")

                # Check for form-related properties
                print(f"\n  Looking for form type properties:")
                for key in sorted(doc.keys()):
                    if 'form' in key.lower() or 'filing' in key.lower():
                        print(f"    {key}: {doc.get(key)}")

                # Check for insider trading properties
                print(f"\n  Looking for insider trading properties:")
                for key in sorted(doc.keys()):
                    if any(x in key.lower() for x in ['transaction', 'shares', 'position', 'insider']):
                        print(f"    {key}: {doc.get(key)}")

                # Check for institutional holdings properties
                print(f"\n  Looking for institutional holdings properties:")
                for key in sorted(doc.keys()):
                    if any(x in key.lower() for x in ['holding', 'institutional', 'value']):
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
    asyncio.run(check_sec_filing_properties())
