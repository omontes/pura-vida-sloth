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
    ```cypher
    MATCH (t:Technology {id: $tech_id})
    OPTIONAL MATCH (t)-[r]-(n)
    RETURN t, r, n
    ```

    Returns vis-network compatible format for frontend visualization.
    """
    try:
        # Execute Cypher query
        neo4j_records = await get_technology_subgraph(request.tech_id, driver)

        if not neo4j_records:
            raise HTTPException(
                status_code=404,
                detail=f"Technology '{request.tech_id}' not found in Neo4j"
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
