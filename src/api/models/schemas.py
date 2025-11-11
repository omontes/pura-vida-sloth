"""
Pydantic Models for API Requests and Responses
"""

from typing import Any
from pydantic import BaseModel, Field


class SubgraphRequest(BaseModel):
    """Request body for POST /api/neo4j/subgraph"""

    tech_id: str | None = Field(
        None,
        description="Technology ID (e.g., 'evtol'). If None, returns full graph with all technologies."
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "tech_id": "evtol"
                },
                {
                    "tech_id": None
                }
            ]
        }


class VisNode(BaseModel):
    """vis.js node format"""

    id: str
    label: str
    color: str
    group: str
    title: str
    size: int = 30
    properties: dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            # Handle any type serialization
            object: str
        }


class VisEdge(BaseModel):
    """vis.js edge format"""

    from_: str = Field(..., alias="from")
    to: str
    label: str
    title: str
    arrows: str = "to"

    class Config:
        populate_by_name = True


class SubgraphResponse(BaseModel):
    """Response for POST /api/neo4j/subgraph"""

    nodes: list[VisNode]
    edges: list[VisEdge]

    class Config:
        json_schema_extra = {
            "example": {
                "nodes": [
                    {
                        "id": "1",
                        "label": "eVTOL",
                        "color": "#4e79a7",
                        "group": "Technology",
                        "title": "Technology: eVTOL",
                        "size": 40
                    }
                ],
                "edges": [
                    {
                        "from": "1",
                        "to": "2",
                        "label": "MENTIONED_IN",
                        "title": "MENTIONED_IN | Role: invented",
                        "arrows": "to"
                    }
                ]
            }
        }
