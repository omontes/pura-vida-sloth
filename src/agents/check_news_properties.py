"""Check if news documents have sentiment property"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.neo4j_client import Neo4jClient


async def check_news_properties():
    """Check if news documents have sentiment property."""
    client = Neo4jClient()
    await client.connect()

    try:
        async with client.driver.session() as session:
            # Check for news documents
            query = """
            MATCH (d:Document {doc_type: 'news'})
            RETURN d
            LIMIT 3
            """

            result = await session.run(query)
            records = await result.values()

            print("\n" + "="*80)
            print("NEWS DOCUMENT PROPERTIES")
            print("="*80 + "\n")

            if not records:
                print("No news documents found in graph!")
                return

            for i, (doc,) in enumerate(records, 1):
                print(f"\nDocument {i}:")
                print(f"  doc_id: {doc.get('doc_id')}")
                print(f"  title: {doc.get('title', 'N/A')[:80]}")
                print(f"  sentiment: {doc.get('sentiment', 'MISSING')}")

                print(f"\n  All properties:")
                for key in sorted(doc.keys()):
                    value = doc.get(key)
                    if isinstance(value, str) and len(value) > 60:
                        value = value[:60] + "..."
                    elif isinstance(value, list) and len(value) > 0:
                        value = f"[{len(value)} items]"
                    print(f"    {key}: {value}")

            # Count how many news docs have sentiment
            count_query = """
            MATCH (d:Document {doc_type: 'news'})
            RETURN
              count(d) as total_news,
              count(d.sentiment) as with_sentiment
            """
            result = await session.run(count_query)
            record = await result.single()

            print("\n" + "="*80)
            print(f"Total news documents: {record['total_news']}")
            print(f"Documents with sentiment: {record['with_sentiment']}")
            print("="*80)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(check_news_properties())
