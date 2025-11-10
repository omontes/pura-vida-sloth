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
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timezone


# Phase ranges from HYPE_CYCLE.md
PHASE_RANGES = {
    "Innovation Trigger": (0.0, 0.7),
    "Peak of Inflated Expectations": (0.7, 1.4),
    "Trough of Disillusionment": (1.4, 2.7),
    "Slope of Enlightenment": (2.7, 4.2),
    "Plateau of Productivity": (4.2, 5.0)
}


def calculate_ranking_score(tech: Dict[str, Any], phase: str) -> float:
    """
    Calculate composite ranking score based on phase-specific criteria.

    Higher score = better rank (will appear earlier in phase on x-axis)

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
        # Rank by market traction + sustained innovation
        primary = adoption
        secondary = innovation
        tertiary = confidence
        return (primary * 10) + (secondary * 5) + (tertiary * 2)

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
        width = max_x - min_x
        k = len(techs)

        if k == 0:
            continue
        elif k == 1:
            # Single tech: place at midpoint
            techs[0]["chart_x"] = min_x + (width * 0.5)
        else:
            # Multiple techs: spread evenly
            # Rank 1 (best) appears earliest (leftmost) in phase
            for i, tech in enumerate(techs):
                # Linear interpolation: rank 1 → min_x, rank K → max_x
                position_fraction = i / (k - 1)
                tech["chart_x"] = min_x + (width * position_fraction)

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


def normalize_chart(
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

    # Rank technologies within each phase
    print(f"\n[2/6] Ranking technologies by phase-specific criteria...")
    ranked_by_phase = rank_technologies_by_phase(chart["technologies"])
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


def main():
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
        normalize_chart(
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
    exit(main())
