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


def get_node_color(labels: set[str]) -> str:
    """Get color for node based on its labels"""
    for label in labels:
        if label in NODE_COLORS:
            return NODE_COLORS[label]
    return DEFAULT_COLOR


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
            nodes.append({
                "id": str(tech_node.element_id),
                "label": get_node_label(tech_node),
                "color": get_node_color(set(tech_node.labels)),
                "group": list(tech_node.labels)[0] if tech_node.labels else "Node",
                "title": create_tooltip(tech_node),
                "size": 40,  # Technology node is larger
            })
            seen_nodes.add(tech_node.element_id)

        # Process related node
        if related_node and related_node.element_id not in seen_nodes:
            nodes.append({
                "id": str(related_node.element_id),
                "label": get_node_label(related_node),
                "color": get_node_color(set(related_node.labels)),
                "group": list(related_node.labels)[0] if related_node.labels else "Node",
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
                "label": relationship.type,
                "title": " | ".join(tooltip_parts),
                "arrows": "to",
            })

    return {"nodes": nodes, "edges": edges}
