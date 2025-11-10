"""
Chart Normalization with Ranking

Ranks technologies within each hype cycle phase and normalizes chart_x positions
to avoid overlapping. Uses phase-specific ranking criteria and spreads technologies
evenly across their phase range.

Usage:
    python agents/chart_normalization_ranked.py [--input INPUT] [--output OUTPUT] [--top-n N]
"""

import json
import argparse
import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

# Add project root to path for Neo4j client import
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.graph.neo4j_client import Neo4jClient


# Phase ranges from HYPE_CYCLE.md
PHASE_RANGES = {
    "Innovation Trigger": (0.0, 0.7),
    "Peak of Inflated Expectations": (0.7, 1.4),
    "Trough of Disillusionment": (1.4, 2.7),
    "Slope of Enlightenment": (2.7, 4.2),
    "Plateau of Productivity": (4.2, 5.0)
}

# Generic industry terms to exclude (not specific technologies)
GENERIC_TERMS = [
    "evtol",
    "evtol_technology",
    "advanced_air_mobility",
    "unmanned_aerial_vehicle_uav",
    "urban_air_mobility",
    "drone_delivery"
]

# Boundary padding to prevent technologies from appearing at exact phase boundaries
BOUNDARY_PADDING = 0.1  # Keep technologies 0.1 units away from phase boundaries


def calculate_ranking_score(tech: Dict[str, Any], phase: str) -> float:
    """
    Calculate composite ranking score based on phase-specific criteria.

    Higher score = better rank (will appear later in phase on x-axis, reflecting maturity)

    Args:
        tech: Technology dictionary with scores and phase_confidence
        phase: Phase name

    Returns:
        Composite score for ranking
    """
    scores = tech.get("scores", {})
    confidence = tech.get("phase_confidence", 0.5)
    evidence = tech.get("evidence_counts", {})

    # Extract scores
    innovation = scores.get("innovation", 0)
    adoption = scores.get("adoption", 0)
    narrative = scores.get("narrative", 0)
    risk = scores.get("risk", 50)
    hype = scores.get("hype", 0)

    # Count total evidence
    total_evidence = sum([
        evidence.get("patents", 0),
        evidence.get("papers", 0),
        evidence.get("github", 0),
        evidence.get("news", 0),
        evidence.get("sec_filings", 0),
        evidence.get("insider_transactions", 0)
    ])

    # Phase-specific ranking
    if phase == "Innovation Trigger":
        # Rank by innovation strength (high patents/papers)
        primary = innovation
        secondary = confidence
        tertiary = evidence.get("patents", 0) + evidence.get("papers", 0)
        return (primary * 10) + (secondary * 5) + (tertiary * 0.1)

    elif phase == "Peak of Inflated Expectations":
        # Rank by hype/narrative strength
        primary = (narrative + hype) / 2
        secondary = confidence
        tertiary = evidence.get("news", 0)
        return (primary * 10) + (secondary * 5) + (tertiary * 0.1)

    elif phase == "Trough of Disillusionment":
        # Rank by recovery potential (best of the worst)
        primary = (innovation + adoption) / 2
        secondary = confidence
        tertiary = total_evidence
        return (primary * 10) + (secondary * 5) + (tertiary * 0.1)

    elif phase == "Slope of Enlightenment":
        # Rank by research backing + market tracking (narrative)
        # Prioritize technologies with academic/IP validation + market importance
        papers = evidence.get("papers", 0)
        patents = evidence.get("patents", 0)
        return (papers * 25) + (patents * 8) + (narrative * 2) + (adoption * 3) + (confidence * 20)

    elif phase == "Plateau of Productivity":
        # Rank by market maturity + stability
        primary = adoption
        secondary = (100 - risk)  # Lower risk = higher score
        tertiary = confidence
        return (primary * 10) + (secondary * 5) + (tertiary * 2)

    else:
        # Default: use confidence + average scores
        avg_score = (innovation + adoption + narrative) / 3
        return (avg_score * 10) + (confidence * 5)


def rank_technologies_by_phase(technologies: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group technologies by phase and rank within each phase.

    Args:
        technologies: List of technology dictionaries

    Returns:
        Dictionary mapping phase name to list of ranked technologies
    """
    # Group by phase
    by_phase = {}
    for tech in technologies:
        phase = tech.get("phase", "Unknown")
        if phase not in by_phase:
            by_phase[phase] = []
        by_phase[phase].append(tech)

    # Rank within each phase
    ranked_by_phase = {}
    for phase, techs in by_phase.items():
        # Calculate ranking score for each tech
        for tech in techs:
            tech["_ranking_score"] = calculate_ranking_score(tech, phase)

        # Sort by ranking score (descending = best first)
        sorted_techs = sorted(techs, key=lambda t: t["_ranking_score"], reverse=True)

        # Add rank number
        for i, tech in enumerate(sorted_techs, start=1):
            tech["_rank"] = i

        ranked_by_phase[phase] = sorted_techs

    return ranked_by_phase


def filter_top_n(ranked_by_phase: Dict[str, List[Dict[str, Any]]], n: int) -> Dict[str, List[Dict[str, Any]]]:
    """
    Keep only top N technologies per phase.

    Args:
        ranked_by_phase: Dictionary mapping phase to ranked technologies
        n: Maximum number of technologies to keep per phase

    Returns:
        Filtered dictionary
    """
    filtered = {}
    for phase, techs in ranked_by_phase.items():
        filtered[phase] = techs[:n]
    return filtered


def apply_minimum_spacing(technologies: List[Dict[str, Any]], min_x: float, max_x: float, min_spacing: float = 0.05) -> None:
    """
    Ensure minimum spacing between adjacent technologies to prevent overlapping.

    Args:
        technologies: List of tech dicts with chart_x values (pre-sorted by chart_x descending)
        min_x: Minimum allowed x position for this phase
        max_x: Maximum allowed x position for this phase
        min_spacing: Minimum distance between adjacent techs (default: 0.05)
    """
    if len(technologies) <= 1:
        return

    # Sort by chart_x descending (highest to lowest)
    technologies.sort(key=lambda t: t["chart_x"], reverse=True)

    # Enforce minimum spacing from right to left
    for i in range(1, len(technologies)):
        prev_x = technologies[i-1]["chart_x"]
        curr_x = technologies[i]["chart_x"]

        # If too close, push current tech to the left
        if prev_x - curr_x < min_spacing:
            technologies[i]["chart_x"] = prev_x - min_spacing

        # Ensure we don't go below min_x
        if technologies[i]["chart_x"] < min_x:
            technologies[i]["chart_x"] = min_x


def normalize_chart_positions(ranked_by_phase: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Normalize chart_x positions to spread technologies evenly within their phase range.

    Args:
        ranked_by_phase: Dictionary mapping phase to ranked technologies

    Returns:
        Updated dictionary with normalized chart_x values
    """
    for phase, techs in ranked_by_phase.items():
        if phase not in PHASE_RANGES:
            print(f"Warning: Unknown phase '{phase}', skipping normalization")
            continue

        min_x, max_x = PHASE_RANGES[phase]

        # Apply boundary padding to avoid exact phase boundaries
        padded_min = min_x + BOUNDARY_PADDING
        padded_max = max_x - BOUNDARY_PADDING
        width = padded_max - padded_min
        k = len(techs)

        if k == 0:
            continue
        elif k == 1:
            # Single tech: place at midpoint of padded range
            techs[0]["chart_x"] = padded_min + (width * 0.5)
        else:
            # Multiple techs: spread evenly within padded range
            # Rank 1 (best) appears latest (rightmost) in phase
            for i, tech in enumerate(techs):
                # Linear interpolation: rank 1 → padded_max, rank K → padded_min
                position_fraction = (k - 1 - i) / (k - 1)
                tech["chart_x"] = padded_min + (width * position_fraction)

            # Apply minimum spacing to prevent overlaps (within padded boundaries)
            apply_minimum_spacing(techs, padded_min, padded_max, min_spacing=0.05)

        # Update phase_position based on new chart_x
        for tech in techs:
            chart_x = tech["chart_x"]
            relative_pos = (chart_x - min_x) / width

            if relative_pos < 0.4:
                tech["phase_position"] = "early"
            elif relative_pos < 0.7:
                tech["phase_position"] = "mid"
            else:
                tech["phase_position"] = "late"

    return ranked_by_phase


def validate_chart(technologies: List[Dict[str, Any]]) -> bool:
    """
    Validate that all chart_x values are within correct phase ranges.

    Args:
        technologies: List of technology dictionaries

    Returns:
        True if valid, False otherwise
    """
    valid = True
    for tech in technologies:
        phase = tech.get("phase")
        chart_x = tech.get("chart_x")

        if phase not in PHASE_RANGES:
            print(f"Error: Unknown phase '{phase}' for tech '{tech.get('id')}'")
            valid = False
            continue

        min_x, max_x = PHASE_RANGES[phase]
        if not (min_x <= chart_x <= max_x):
            print(f"Error: chart_x {chart_x} not in range [{min_x}, {max_x}] for phase '{phase}' (tech: {tech.get('id')})")
            valid = False

    return valid


async def query_graph_metadata(client: Neo4jClient) -> Dict[str, Any]:
    """
    Query Neo4j for comprehensive graph statistics.

    Returns:
        Dictionary with communities, documents, technologies, companies, and relationships stats
    """
    try:
        # Query 1: Community statistics
        community_query = """
        MATCH (c:Community)
        WITH c.id AS community_id
        RETURN
            count(*) AS total_communities,
            size([id IN collect(community_id) WHERE id STARTS WITH 'v0_']) AS v0_count,
            size([id IN collect(community_id) WHERE id STARTS WITH 'v1_']) AS v1_count,
            size([id IN collect(community_id) WHERE id STARTS WITH 'v2_']) AS v2_count
        """
        community_result = await client.run_query(community_query)
        community_stats = community_result[0] if community_result else {}

        # Query 2: Community classification (v1 only)
        classification_query = """
        MATCH (c:Community)
        WHERE c.id STARTS WITH 'v1_'
        RETURN
            c.lifecycle_stage AS stage,
            count(*) AS count
        """
        classification_result = await client.run_query(classification_query)
        classification = {row['stage']: row['count'] for row in classification_result} if classification_result else {}

        # Query 3: Document statistics
        document_query = """
        MATCH (d:Document)
        RETURN
            count(*) AS total_documents,
            count(CASE WHEN d.doc_type = 'patent' THEN 1 END) AS patents,
            count(CASE WHEN d.doc_type = 'news' THEN 1 END) AS news,
            count(CASE WHEN d.doc_type = 'technical_paper' THEN 1 END) AS papers,
            count(CASE WHEN d.doc_type = 'government_contract' THEN 1 END) AS contracts,
            count(CASE WHEN d.doc_type = 'sec_filing' THEN 1 END) AS sec_filings,
            count(CASE WHEN d.doc_type = 'github' THEN 1 END) AS github
        """
        document_result = await client.run_query(document_query)
        document_stats = document_result[0] if document_result else {}

        # Query 4: Technology statistics with document thresholds
        technology_query = """
        MATCH (t:Technology)
        OPTIONAL MATCH (t)-[:MENTIONED_IN]->(d:Document)
        WITH t, count(DISTINCT d) AS doc_count
        RETURN
            count(*) AS total_technologies,
            sum(CASE WHEN doc_count > 0 THEN 1 ELSE 0 END) AS with_documents,
            sum(CASE WHEN doc_count >= 5 THEN 1 ELSE 0 END) AS min_5,
            sum(CASE WHEN doc_count >= 10 THEN 1 ELSE 0 END) AS min_10,
            sum(CASE WHEN doc_count >= 15 THEN 1 ELSE 0 END) AS min_15,
            sum(CASE WHEN doc_count >= 20 THEN 1 ELSE 0 END) AS min_20
        """
        technology_result = await client.run_query(technology_query)
        technology_stats = technology_result[0] if technology_result else {}

        # Query 5: Company statistics
        company_query = "MATCH (c:Company) RETURN count(*) AS total_companies"
        company_result = await client.run_query(company_query)
        company_stats = company_result[0] if company_result else {}

        # Query 6: Relationship statistics
        relationship_query = """
        MATCH ()-[r]->()
        RETURN
            count(*) AS total_relationships,
            count(CASE WHEN type(r) = 'MENTIONED_IN' THEN 1 END) AS mentioned_in,
            count(CASE WHEN type(r) = 'HAS_MEMBER' THEN 1 END) AS has_member
        """
        relationship_result = await client.run_query(relationship_query)
        relationship_stats = relationship_result[0] if relationship_result else {}

        # Construct comprehensive metadata
        return {
            "communities": {
                "total": community_stats.get('total_communities', 0),
                "versions": {
                    "v0": community_stats.get('v0_count', 0),
                    "v1": community_stats.get('v1_count', 0),
                    "v2": community_stats.get('v2_count', 0)
                },
                "classification_v1": classification
            },
            "documents": {
                "total": document_stats.get('total_documents', 0),
                "by_type": {
                    "patent": document_stats.get('patents', 0),
                    "news": document_stats.get('news', 0),
                    "technical_paper": document_stats.get('papers', 0),
                    "government_contract": document_stats.get('contracts', 0),
                    "sec_filing": document_stats.get('sec_filings', 0),
                    "github": document_stats.get('github', 0)
                }
            },
            "technologies": {
                "total": technology_stats.get('total_technologies', 0),
                "with_documents": technology_stats.get('with_documents', 0),
                "by_doc_threshold": {
                    "min_5": technology_stats.get('min_5', 0),
                    "min_10": technology_stats.get('min_10', 0),
                    "min_15": technology_stats.get('min_15', 0),
                    "min_20": technology_stats.get('min_20', 0)
                }
            },
            "companies": {
                "total": company_stats.get('total_companies', 0)
            },
            "relationships": {
                "total": relationship_stats.get('total_relationships', 0),
                "mentioned_in": relationship_stats.get('mentioned_in', 0),
                "has_member": relationship_stats.get('has_member', 0)
            }
        }
    except Exception as e:
        print(f"Warning: Could not query graph metadata: {e}")
        return {}


async def normalize_chart(
    input_file: str = "hype_cycle_chart.json",
    output_file: str = "hype_cycle_chart_normalized.json",
    top_n: int = 10
) -> Dict[str, Any]:
    """
    Main normalization function.

    Args:
        input_file: Path to input chart JSON
        output_file: Path to output normalized chart JSON
        top_n: Maximum number of technologies to keep per phase

    Returns:
        Normalized chart dictionary
    """
    print(f"\n{'='*80}")
    print(f"CHART NORMALIZATION WITH RANKING")
    print(f"{'='*80}\n")

    # Load input chart
    print(f"[1/6] Loading input chart: {input_file}")
    with open(input_file, 'r') as f:
        chart = json.load(f)

    original_count = len(chart.get("technologies", []))
    print(f"  Original technologies: {original_count}")
    print(f"  Original phase distribution:")
    for phase, count in chart.get("metadata", {}).get("phases", {}).items():
        print(f"    {phase}: {count}")

    # Filter out generic industry terms
    filtered_techs = [
        tech for tech in chart["technologies"]
        if tech.get("id") not in GENERIC_TERMS
    ]
    filtered_count = len(filtered_techs)
    if filtered_count < original_count:
        print(f"  Filtered out {original_count - filtered_count} generic industry terms")
        print(f"  Remaining: {filtered_count} specific technologies")

    # Rank technologies within each phase
    print(f"\n[2/6] Ranking technologies by phase-specific criteria...")
    ranked_by_phase = rank_technologies_by_phase(filtered_techs)
    for phase, techs in ranked_by_phase.items():
        print(f"  {phase}: {len(techs)} technologies ranked")

    # Filter to top N per phase
    print(f"\n[3/6] Filtering to top {top_n} per phase...")
    filtered_by_phase = filter_top_n(ranked_by_phase, top_n)
    total_after_filter = sum(len(techs) for techs in filtered_by_phase.values())
    print(f"  Kept {total_after_filter} technologies (from {original_count})")
    for phase, techs in filtered_by_phase.items():
        print(f"    {phase}: {len(techs)}")

    # Normalize chart_x positions
    print(f"\n[4/6] Normalizing chart_x positions...")
    normalized_by_phase = normalize_chart_positions(filtered_by_phase)

    # Show chart_x ranges per phase
    for phase, techs in normalized_by_phase.items():
        if techs:
            min_x = min(t["chart_x"] for t in techs)
            max_x = max(t["chart_x"] for t in techs)
            print(f"  {phase}: chart_x range [{min_x:.3f}, {max_x:.3f}]")

    # Flatten back to list
    all_technologies = []
    for techs in normalized_by_phase.values():
        for tech in techs:
            # Remove internal ranking fields
            tech.pop("_ranking_score", None)
            tech.pop("_rank", None)
            all_technologies.append(tech)

    # Update metadata
    print(f"\n[5/6] Updating metadata...")
    chart["technologies"] = all_technologies
    chart["metadata"]["total_count"] = len(all_technologies)
    chart["metadata"]["normalized_at"] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    chart["metadata"]["normalization_config"] = {
        "top_n_per_phase": top_n,
        "original_count": original_count,
        "filtered_count": len(all_technologies)
    }

    # Update phase counts
    phase_counts = {
        "innovation_trigger": 0,
        "peak": 0,
        "trough": 0,
        "slope": 0,
        "plateau": 0
    }

    for phase, techs in normalized_by_phase.items():
        if phase == "Innovation Trigger":
            phase_counts["innovation_trigger"] = len(techs)
        elif phase == "Peak of Inflated Expectations":
            phase_counts["peak"] = len(techs)
        elif phase == "Trough of Disillusionment":
            phase_counts["trough"] = len(techs)
        elif phase == "Slope of Enlightenment":
            phase_counts["slope"] = len(techs)
        elif phase == "Plateau of Productivity":
            phase_counts["plateau"] = len(techs)

    chart["metadata"]["phases"] = phase_counts

    # Query graph metadata for transparency
    print(f"\n  Querying graph metadata...")
    try:
        client = Neo4jClient()
        await client.connect()
        try:
            graph_data = await query_graph_metadata(client)
            if graph_data:
                chart["metadata"]["graph_data"] = graph_data
                print(f"  [OK] Graph metadata added:")
                print(f"    Communities: {graph_data.get('communities', {}).get('total', 0)}")
                print(f"    Documents: {graph_data.get('documents', {}).get('total', 0)}")
                print(f"    Technologies: {graph_data.get('technologies', {}).get('total', 0)}")
                print(f"    Companies: {graph_data.get('companies', {}).get('total', 0)}")
            else:
                print(f"  [WARN] No graph metadata available")
        finally:
            await client.close()
    except Exception as e:
        print(f"  [WARN] Could not connect to Neo4j: {e}")
        print(f"  [INFO] Continuing without graph metadata...")

    # Validate
    print(f"\n[6/6] Validating normalized chart...")
    if validate_chart(all_technologies):
        print(f"  [OK] All chart_x values within valid ranges")
    else:
        print(f"  [ERROR] Validation failed!")
        return None

    # Save output
    print(f"\n[OUTPUT] Saving normalized chart: {output_file}")
    with open(output_file, 'w') as f:
        json.dump(chart, f, indent=2)

    print(f"\n{'='*80}")
    print(f"NORMALIZATION COMPLETE")
    print(f"{'='*80}\n")

    # Print summary
    print(f"Summary:")
    print(f"  Input: {original_count} technologies")
    print(f"  Output: {len(all_technologies)} technologies (top {top_n} per phase)")
    print(f"  Reduction: {original_count - len(all_technologies)} technologies filtered")
    print(f"\nPhase distribution:")
    for phase, count in phase_counts.items():
        print(f"  {phase}: {count}")

    return chart


async def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Normalize hype cycle chart with ranking and position spreading"
    )
    parser.add_argument(
        "--input",
        default="hype_cycle_chart.json",
        help="Input chart JSON file (default: hype_cycle_chart.json)"
    )
    parser.add_argument(
        "--output",
        default="hype_cycle_chart_normalized.json",
        help="Output normalized chart JSON file (default: hype_cycle_chart_normalized.json)"
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Maximum number of technologies to keep per phase (default: 10)"
    )

    args = parser.parse_args()

    try:
        await normalize_chart(
            input_file=args.input,
            output_file=args.output,
            top_n=args.top_n
        )
        return 0
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
