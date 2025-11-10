"""
Neo4j Routes

POST /api/neo4j/subgraph - Get technology subgraph
"""

from fastapi import APIRouter, Depends, HTTPException
from neo4j import AsyncDriver
from ..dependencies import get_neo4j_driver
from ..models.schemas import SubgraphRequest, SubgraphResponse
from ..services.neo4j_service import get_technology_subgraph
from ..services.vis_converter import neo4j_to_vis

router = APIRouter(prefix="/api", tags=["Neo4j"])


@router.post("/neo4j/subgraph", response_model=SubgraphResponse)
async def fetch_technology_subgraph(
    request: SubgraphRequest,
    driver: AsyncDriver = Depends(get_neo4j_driver),
):
    """
    Fetch technology subgraph from Neo4j.

    Executes Cypher query:
    - If tech_id is None: Returns full graph (limited to 1000 results for performance)
      ```cypher
      MATCH (t:Technology)
      OPTIONAL MATCH (t)-[r]-(n)
      WHERE n IS NULL OR NOT n:Community
      RETURN t, r, n
      LIMIT 1000
      ```

    - If tech_id is provided: Returns filtered subgraph for that technology
      ```cypher
      MATCH (t:Technology {id: $tech_id})
      OPTIONAL MATCH (t)-[r]-(n)
      WHERE n IS NULL OR NOT n:Community
      RETURN t, r, n
      ```

    Returns vis-network compatible format for frontend visualization.
    """
    try:
        # Execute Cypher query
        neo4j_records = await get_technology_subgraph(request.tech_id, driver)

        if not neo4j_records:
            if request.tech_id:
                # Specific technology requested but not found
                raise HTTPException(
                    status_code=404,
                    detail=f"Technology '{request.tech_id}' not found in Neo4j"
                )
            else:
                # Full graph requested but empty (no technologies in database)
                raise HTTPException(
                    status_code=404,
                    detail="No technologies found in Neo4j database"
                )

        # Convert to vis.js format
        vis_data = neo4j_to_vis(neo4j_records)

        return vis_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch subgraph: {str(e)}"
        )
