"""
Neo4j Service

Executes Cypher queries to fetch technology subgraphs from Neo4j Aura.

Query Patterns:
    Full graph (tech_id=None):
        MATCH (t:Technology)
        OPTIONAL MATCH (t)-[r]-(n)
        WHERE n IS NULL OR NOT n:Community
        RETURN t, r, n
        LIMIT 1000  # Limit for performance

    Filtered subgraph (tech_id provided):
        MATCH (t:Technology {id: $tech_id})
        OPTIONAL MATCH (t)-[r]-(n)
        WHERE n IS NULL OR NOT n:Community
        RETURN t, r, n
"""

from neo4j import AsyncDriver
from ..dependencies import neo4j_session_context


async def get_technology_subgraph(tech_id: str | None, driver: AsyncDriver) -> list[dict]:
    """
    Execute Cypher query to get technology node(s) and relationships.

    Args:
        tech_id: Optional technology ID. If None, returns full graph of all technologies.
                 If provided (e.g., "evtol"), returns subgraph for that specific technology.
        driver: Neo4j async driver

    Returns:
        List of records with 't' (technology), 'r' (relationship), 'n' (related node)

    Example Result:
        [
            {'t': <Node id=1 labels={'Technology'} properties={'id': 'evtol', 'name': 'eVTOL'}>,
             'r': <Relationship type='MENTIONED_IN'>,
             'n': <Node id=2 labels={'Patent'} properties={'title': '...'}>},
            ...
        ]
    """
    async with neo4j_session_context(driver) as session:
        # Conditional query based on whether tech_id is provided
        if tech_id:
            # Filtered subgraph for specific technology
            query = """
                MATCH (t:Technology {id: $tech_id})
                OPTIONAL MATCH (t)-[r]-(n)
                WHERE n IS NULL OR NOT n:Community
                RETURN t, r, n
            """
            result = await session.run(query, tech_id=tech_id)
        else:
            # Full graph with all technologies (limited for performance)
            query = """
                MATCH (t:Technology)
                OPTIONAL MATCH (t)-[r]-(n)
                WHERE n IS NULL OR NOT n:Community
                RETURN t, r, n
                LIMIT 100
            """
            result = await session.run(query)

        # Extract records
        records = []
        async for record in result:
            records.append({
                't': record.get('t'),
                'r': record.get('r'),
                'n': record.get('n'),
            })

        return records


async def get_technology_by_id(tech_id: str, driver: AsyncDriver) -> dict | None:
    """
    Get single technology node by ID.

    Args:
        tech_id: Technology ID
        driver: Neo4j async driver

    Returns:
        Technology properties dict or None if not found
    """
    async with neo4j_session_context(driver) as session:
        result = await session.run(
            """
            MATCH (t:Technology {id: $tech_id})
            RETURN t
            """,
            tech_id=tech_id,
        )

        record = await result.single()
        if record:
            node = record.get('t')
            if node:
                return dict(node)

        return None
