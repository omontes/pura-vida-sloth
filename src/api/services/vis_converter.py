"""
Vis.js Format Converter

Transforms Neo4j query results into vis-network-react compatible format.

Input: Neo4j records with nodes and relationships
Output: {nodes: [...], edges: [...]}
"""

from typing import Any


# Node color palette (Professional hierarchy - matching frontend/src/config/visNetworkConfig.ts)
NODE_COLORS = {
    # Entity types (Primary hierarchy - high visual weight)
    "Technology": "#0f766e",    # Teal (brand color) - PRIMARY NODE
    "Company": "#f59e0b",       # Amber (warm contrast) - ACTION/ENTERPRISE
    "Person": "#59a14f",        # Green (kept original)

    # Document types (Secondary hierarchy - subtle grays with slight variations)
    "Patent": "#64748b",              # Slate-500 (blue-gray medium)
    "TechnicalPaper": "#94a3b8",      # Slate-400 (blue-gray light)
    "SECFiling": "#475569",           # Slate-600 (blue-gray dark)
    "Regulation": "#71717a",          # Zinc-500 (neutral gray)
    "GitHub": "#78716c",              # Stone-500 (warm gray)
    "GovernmentContract": "#57534e",  # Stone-600 (warm gray dark)
    "News": "#a8a29e",                # Stone-400 (warm gray light)
    "InsiderTransaction": "#6b7280",  # Gray-500 (pure gray)
    "StockPrice": "#9ca3af",          # Gray-400 (pure gray light)
    "InstitutionalHolding": "#52525b", # Zinc-600 (neutral dark gray)
}

DEFAULT_COLOR = "#8892a6"

# Mapping from doc_type property values to color keys
DOC_TYPE_TO_COLOR_KEY = {
    "patent": "Patent",
    "technical_paper": "TechnicalPaper",
    "sec_filing": "SECFiling",
    "regulation": "Regulation",
    "github": "GitHub",
    "government_contract": "GovernmentContract",
    "news": "News",
}


def get_node_color(labels: set[str], properties: dict[str, Any] | None = None) -> str:
    """
    Get color for node based on its labels and properties.

    For Document nodes, uses doc_type property to determine specific color.
    For other nodes, uses label-based coloring.
    """
    # Check if this is a Document node
    if "Document" in labels and properties:
        doc_type = properties.get("doc_type")
        if doc_type and doc_type in DOC_TYPE_TO_COLOR_KEY:
            color_key = DOC_TYPE_TO_COLOR_KEY[doc_type]
            return NODE_COLORS.get(color_key, DEFAULT_COLOR)

    # For non-document nodes, use label-based coloring
    for label in labels:
        if label in NODE_COLORS:
            return NODE_COLORS[label]

    return DEFAULT_COLOR


def get_node_group(labels: set[str], properties: dict[str, Any] | None = None) -> str:
    """
    Get group name for node (used for legend categorization).

    For Document nodes, returns specific document type (e.g., "Patent", "TechnicalPaper").
    For other nodes, returns the first label.
    """
    # Check if this is a Document node
    if "Document" in labels and properties:
        doc_type = properties.get("doc_type")
        if doc_type and doc_type in DOC_TYPE_TO_COLOR_KEY:
            return DOC_TYPE_TO_COLOR_KEY[doc_type]

    # For non-document nodes, return first label
    return list(labels)[0] if labels else "Node"


def get_edge_label(relationship_type: str, properties: dict[str, Any]) -> str:
    """
    Get semantic edge label based on relationship type and properties.

    Uses meaningful property values instead of generic relationship types:
    - MENTIONED_IN → uses "role" property (e.g., owner, developer, operator)
    - RELATED_COMPANY/TECH/TO_TECH → uses "relation_type" property

    Falls back to relationship type if property not found.
    """
    # Mapping of relationship types to their semantic property
    SEMANTIC_PROPERTY_MAP = {
        "MENTIONED_IN": "role",
        "RELATED_COMPANY": "relation_type",
        "RELATED_TECH": "relation_type",
        "RELATED_TO_TECH": "relation_type",
    }

    # Check if this relationship type has a semantic property
    if relationship_type in SEMANTIC_PROPERTY_MAP:
        property_name = SEMANTIC_PROPERTY_MAP[relationship_type]
        semantic_value = properties.get(property_name)
        if semantic_value:
            return str(semantic_value)

    # Fallback to relationship type
    return relationship_type


def get_node_label(node: Any) -> str:
    """
    Extract best label for node display.

    Priority: name > title > id > element_id
    """
    props = dict(node)
    return (
        props.get("name")
        or props.get("title")
        or props.get("id")
        or str(node.element_id)
    )


def create_tooltip(node: Any) -> str:
    """Create HTML tooltip for node"""
    labels = list(node.labels)
    label_str = labels[0] if labels else "Node"

    props = dict(node)

    # Show top 5 properties (exclude embedding and search_corpus)
    relevant_props = {
        k: v
        for k, v in props.items()
        if v is not None
        and "embedding" not in k.lower()
        and "search_corpus" not in k.lower()
    }

    lines = [f"<b>{label_str}</b>"]
    for key, value in list(relevant_props.items())[:5]:
        value_str = str(value)
        if len(value_str) > 50:
            value_str = value_str[:47] + "..."
        lines.append(f"{key}: {value_str}")

    return "<br>".join(lines)


def neo4j_to_vis(neo4j_records: list[dict]) -> dict:
    """
    Convert Neo4j query results to vis.js format.

    Args:
        neo4j_records: List of dicts with 't', 'r', 'n' keys

    Returns:
        {
            "nodes": [
                {"id": "...", "label": "...", "color": "...", "group": "...", "title": "..."},
                ...
            ],
            "edges": [
                {"from": "...", "to": "...", "label": "...", "title": "..."},
                ...
            ]
        }
    """
    nodes = []
    edges = []
    seen_nodes = set()

    for record in neo4j_records:
        tech_node = record.get("t")
        relationship = record.get("r")
        related_node = record.get("n")

        # Process technology node
        if tech_node and tech_node.element_id not in seen_nodes:
            tech_props = dict(tech_node)
            tech_labels = set(tech_node.labels)
            nodes.append({
                "id": str(tech_node.element_id),
                "label": get_node_label(tech_node),
                "color": get_node_color(tech_labels, tech_props),
                "group": get_node_group(tech_labels, tech_props),
                "title": create_tooltip(tech_node),
                "size": 40,  # Technology node is larger
            })
            seen_nodes.add(tech_node.element_id)

        # Process related node
        if related_node and related_node.element_id not in seen_nodes:
            related_props = dict(related_node)
            related_labels = set(related_node.labels)
            nodes.append({
                "id": str(related_node.element_id),
                "label": get_node_label(related_node),
                "color": get_node_color(related_labels, related_props),
                "group": get_node_group(related_labels, related_props),
                "title": create_tooltip(related_node),
                "size": 30,  # Related nodes are smaller
            })
            seen_nodes.add(related_node.element_id)

        # Process relationship
        if relationship and tech_node and related_node:
            rel_props = dict(relationship)
            role = rel_props.get("role", "")
            strength = rel_props.get("strength", "")

            tooltip_parts = [relationship.type]
            if role:
                tooltip_parts.append(f"Role: {role}")
            if strength:
                tooltip_parts.append(f"Strength: {strength}")

            edges.append({
                "from": str(tech_node.element_id),
                "to": str(related_node.element_id),
                "label": get_edge_label(relationship.type, rel_props),
                "title": " | ".join(tooltip_parts),
                "arrows": "to",
            })

    return {"nodes": nodes, "edges": edges}
