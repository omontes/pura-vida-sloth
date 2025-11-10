"""Check what relationship roles actually exist in the graph"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.neo4j_client import Neo4jClient


async def check_roles():
    """Check all relationship roles in the graph."""
    client = Neo4jClient()
    await client.connect()

    try:
        async with client.driver.session() as session:
            # Check all roles by document type
            query = """
            MATCH (t:Technology)-[m:MENTIONED_IN]->(d:Document)
            WHERE t.id = 'evtol'
            RETURN
              d.doc_type AS doc_type,
              m.role AS role,
              count(*) AS count
            ORDER BY doc_type, count DESC
            """

            result = await session.run(query)
            records = await result.values()

            print("\n" + "="*80)
            print("RELATIONSHIP ROLES FOR 'evtol' BY DOCUMENT TYPE")
            print("="*80 + "\n")

            current_type = None
            for doc_type, role, count in records:
                if doc_type != current_type:
                    print(f"\n{doc_type}:")
                    current_type = doc_type
                print(f"  role='{role}' : {count} documents")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(check_roles())
