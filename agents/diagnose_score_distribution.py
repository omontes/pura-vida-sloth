"""
Diagnose Score Distribution - Check what layer scores are being produced

This will help us understand if the problem is:
1. LLM agents producing too-low scores
2. Phase detection thresholds still too high
3. Need for percentile-based classification
"""

import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.neo4j_client import Neo4jClient


async def diagnose_scores():
    """Analyze score distribution from the hype_cycle_chart.json output."""
    print("\n" + "="*80)
    print("SCORE DISTRIBUTION ANALYSIS")
    print("="*80)

    # Load the latest chart
    chart_file = "hype_cycle_chart.json"

    try:
        with open(chart_file, "r") as f:
            chart = json.load(f)
    except FileNotFoundError:
        print(f"\n[ERROR] {chart_file} not found. Run test_full_pipeline.py first!")
        return

    technologies = chart.get("technologies", [])

    if not technologies:
        print("\n[ERROR] No technologies in chart!")
        return

    print(f"\n[INFO] Analyzing {len(technologies)} technologies")

    # Collect all scores
    innovation_scores = []
    adoption_scores = []
    narrative_scores = []
    risk_scores = []
    hype_scores = []

    for tech in technologies:
        scores = tech.get("scores", {})
        innovation_scores.append(scores.get("innovation", 0))
        adoption_scores.append(scores.get("adoption", 0))
        narrative_scores.append(scores.get("narrative", 0))
        risk_scores.append(scores.get("risk", 0))
        hype_scores.append(scores.get("hype", 0))

    # Calculate statistics
    def stats(scores, name):
        if not scores:
            return

        scores_sorted = sorted(scores)
        min_score = min(scores)
        max_score = max(scores)
        avg_score = sum(scores) / len(scores)
        median = scores_sorted[len(scores) // 2]
        p25 = scores_sorted[len(scores) // 4]
        p75 = scores_sorted[3 * len(scores) // 4]

        print(f"\n{name}:")
        print(f"  Min: {min_score:.1f}")
        print(f"  25th percentile: {p25:.1f}")
        print(f"  Median: {median:.1f}")
        print(f"  Mean: {avg_score:.1f}")
        print(f"  75th percentile: {p75:.1f}")
        print(f"  Max: {max_score:.1f}")
        print(f"  Range: {min_score:.1f}-{max_score:.1f}")

    print("\n" + "-"*80)
    print("LAYER SCORE STATISTICS")
    print("-"*80)

    stats(innovation_scores, "INNOVATION")
    stats(adoption_scores, "ADOPTION")
    stats(narrative_scores, "NARRATIVE")
    stats(risk_scores, "RISK")
    stats(hype_scores, "HYPE")

    # Check phase distribution
    phases = chart.get("metadata", {}).get("phases", {})

    print("\n" + "-"*80)
    print("PHASE DISTRIBUTION")
    print("-"*80)

    total = len(technologies)
    for phase, count in phases.items():
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {phase}: {count} ({pct:.1f}%)")

    # Show sample technologies from each phase
    print("\n" + "-"*80)
    print("SAMPLE TECHNOLOGIES BY PHASE")
    print("-"*80)

    for phase_name in ["innovation_trigger", "peak", "trough", "slope", "plateau"]:
        phase_techs = [t for t in technologies if t.get("phase") == phase_name]

        if phase_techs:
            print(f"\n{phase_name.upper()} ({len(phase_techs)} total):")
            for tech in phase_techs[:3]:
                scores = tech.get("scores", {})
                print(f"  {tech['id'][:40]:<40} innov={scores.get('innovation',0):.0f} adopt={scores.get('adoption',0):.0f} narr={scores.get('narrative',0):.0f} risk={scores.get('risk',0):.0f}")

    # Analyze phase detection thresholds
    print("\n" + "="*80)
    print("PHASE DETECTION THRESHOLD ANALYSIS")
    print("="*80)

    print("\nCurrent thresholds:")
    print("  Innovation Trigger: innovation > 20 AND adoption < 15 AND narrative < 15")
    print("  Peak: narrative > 30 AND hype > 40 AND adoption < 25")
    print("  Plateau: adoption > 40 AND innovation > 25 AND 15 < narrative < 40")
    print("  Trough: narrative < 15 AND adoption < 15 AND innovation < 15")
    print("  Slope: Default (moderate signals)")

    # Count how many would qualify for each phase with current thresholds
    innovation_trigger_candidates = []
    peak_candidates = []
    plateau_candidates = []
    trough_candidates = []

    for tech in technologies:
        scores = tech.get("scores", {})
        innov = scores.get("innovation", 0)
        adopt = scores.get("adoption", 0)
        narr = scores.get("narrative", 0)
        risk = scores.get("risk", 0)
        hype = scores.get("hype", 0)

        if innov > 20 and adopt < 15 and narr < 15:
            innovation_trigger_candidates.append(tech)
        if narr > 30 and hype > 40 and adopt < 25:
            peak_candidates.append(tech)
        if adopt > 40 and innov > 25 and 15 < narr < 40:
            plateau_candidates.append(tech)
        if narr < 15 and adopt < 15 and innov < 15:
            trough_candidates.append(tech)

    print(f"\nTechnologies meeting threshold criteria:")
    print(f"  Innovation Trigger candidates: {len(innovation_trigger_candidates)}")
    print(f"  Peak candidates: {len(peak_candidates)}")
    print(f"  Plateau candidates: {len(plateau_candidates)}")
    print(f"  Trough candidates: {len(trough_candidates)}")

    # Recommendations
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)

    avg_innov = sum(innovation_scores) / len(innovation_scores)
    avg_adopt = sum(adoption_scores) / len(adoption_scores)
    avg_narr = sum(narrative_scores) / len(narrative_scores)

    if avg_innov < 15 and avg_adopt < 15 and avg_narr < 10:
        print("\n[PROBLEM] Layer scores are SEVERELY compressed (all averaging < 15)")
        print("\n[SOLUTION OPTIONS]:")
        print("  1. Use PERCENTILE-BASED classification instead of absolute thresholds")
        print("     - Top 20% innovation = innovation_trigger")
        print("     - Top 20% narrative = peak")
        print("     - etc.")
        print("  2. Further recalibrate LLM prompts (but risk overfitting)")
        print("  3. Accept that most techs are early-stage (trough/slope) in this dataset")
    elif len(innovation_trigger_candidates) == 0 and len(peak_candidates) == 0:
        print("\n[PROBLEM] NO technologies meet Innovation Trigger or Peak criteria")
        print("\n[SOLUTION] Consider percentile-based classification")
    else:
        print("\n[INFO] Score distribution looks reasonable")


if __name__ == "__main__":
    asyncio.run(diagnose_scores())
