"""
Test Script: Validate Scholarly Parser with Single Paper

This script:
1. Loads industry config (eVTOL)
2. Initializes ScholarlyRelevanceParser
3. Parses ONE paper from dataset
4. Displays results (relevance, nodes, relationships, cost)
5. Saves output for manual review

Run BEFORE batch processing to validate parser and estimate costs.
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from parsers.scholarly.scholarly_parser import (
    ScholarlyRelevanceParser,
    load_papers_from_file,
    load_industry_config
)


def test_single_paper(
    config_path: str = "configs/evtol_config.json",
    papers_file: str = "data/eVTOL/lens_scholarly/papers.json",
    output_file: str = "parsers/scholarly/test_output_single.json",
    paper_index: int = 0
):
    """
    Test parser with a single paper.

    Args:
        config_path: Path to industry config JSON
        papers_file: Path to papers dataset JSON
        output_file: Where to save test results
        paper_index: Which paper to test (default: 0 = first paper)
    """

    print("=" * 80)
    print("SCHOLARLY PARSER - SINGLE PAPER TEST")
    print("=" * 80)

    # Load API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    # Load industry config
    print(f"\n[1/5] Loading industry config: {config_path}")
    config = load_industry_config(config_path)

    industry = config.get("industry", "Unknown")
    industry_name = config.get("industry_name", "Unknown")
    industry_keywords = config.get("keywords", {}).get("core", [])

    # Create industry description
    industry_description = f"{industry_name} - Urban air mobility aircraft with electric vertical takeoff and landing capabilities"

    print(f"  Industry: {industry}")
    print(f"  Full Name: {industry_name}")
    print(f"  Core Keywords: {len(industry_keywords)} keywords")

    # Initialize parser
    print(f"\n[2/5] Initializing ScholarlyRelevanceParser")
    parser = ScholarlyRelevanceParser(
        openai_api_key=api_key,
        industry_name=industry,
        industry_keywords=industry_keywords,
        industry_description=industry_description,
        model_name="gpt-4o-mini",
        temperature=0.0,
        relevance_threshold=8.0
    )
    print(f"  Model: gpt-4o-mini")
    print(f"  Temperature: 0.0 (deterministic)")
    print(f"  Relevance Threshold: 8.0/10")

    # Load papers
    print(f"\n[3/5] Loading papers: {papers_file}")
    papers = load_papers_from_file(papers_file, limit=None)
    print(f"  Total papers in dataset: {len(papers)}")

    if paper_index >= len(papers):
        raise ValueError(f"paper_index {paper_index} out of range (dataset has {len(papers)} papers)")

    # Select test paper
    paper = papers[paper_index]
    print(f"\n[4/5] Testing paper #{paper_index + 1}")
    print(f"  Lens ID: {paper.get('lens_id', 'Unknown')}")
    print(f"  Title: {paper.get('title', 'No title')[:80]}...")
    print(f"  Year: {paper.get('year_published', 'Unknown')}")
    print(f"  Type: {paper.get('publication_type', 'Unknown')}")

    abstract = paper.get('abstract', '')
    if abstract and len(abstract) > 50:
        print(f"  Abstract: {len(abstract)} characters")
    else:
        print(f"  Abstract: [Missing or empty]")

    # Parse paper
    print(f"\n[5/5] Parsing paper with LLM...")
    print("-" * 80)

    result = parser.parse_and_save(
        paper_data=paper,
        out_path=output_file
    )

    # Display results
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)

    # Relevance assessment
    relevance = result.get("relevance_assessment", {})
    print(f"\n[RELEVANCE ASSESSMENT]")
    print(f"  Score: {relevance.get('relevance_score', 0.0):.1f}/10")
    print(f"  Is Relevant: {relevance.get('is_relevant', False)}")
    print(f"  Category: {relevance.get('relevance_category', 'unknown')}")
    print(f"  Confidence: {relevance.get('confidence', 0.0):.2f}")
    print(f"\n  Justification:")
    justification = relevance.get('justification', 'N/A')
    # Wrap justification text
    words = justification.split()
    line = "    "
    for word in words:
        if len(line) + len(word) + 1 > 76:
            print(line)
            line = "    " + word
        else:
            line += " " + word if line != "    " else word
    if line.strip():
        print(line)

    # Knowledge graph (if relevant)
    is_relevant = relevance.get('is_relevant', False)
    if is_relevant:
        nodes = result.get("technology_nodes", [])
        relationships = result.get("relationships", [])

        print(f"\n[KNOWLEDGE GRAPH]")
        print(f"  Technology Nodes: {len(nodes)}")
        if nodes:
            print(f"\n  Sample Nodes:")
            for idx, node in enumerate(nodes[:5], 1):
                print(f"    {idx}. {node.get('name', 'Unknown')} ({node.get('node_type', 'unknown')})")
                print(f"       Domain: {node.get('domain', 'unknown')} | Maturity: {node.get('maturity', 'unknown')}")

        print(f"\n  Relationships: {len(relationships)}")
        if relationships:
            print(f"\n  Sample Relationships:")
            for idx, rel in enumerate(relationships[:5], 1):
                print(f"    {idx}. {rel.get('subject', '?')} --[{rel.get('predicate', '?')}]--> {rel.get('object', '?')}")
                print(f"       Confidence: {rel.get('confidence', 0.0):.2f}")

        # Innovation signals
        signals = result.get("innovation_signals", {})
        print(f"\n[INNOVATION SIGNALS]")
        print(f"  Research Stage: {signals.get('research_stage', 'unknown')}")
        print(f"  Innovation Type: {signals.get('innovation_type', 'unknown')}")
        print(f"  Impact Potential: {signals.get('impact_potential', 'unknown')}")
        print(f"  Technical Risk: {signals.get('technical_risk', 'unknown')}")

        adoption = signals.get('adoption_indicators', [])
        if adoption:
            print(f"\n  Adoption Indicators ({len(adoption)}):")
            for idx, indicator in enumerate(adoption, 1):
                print(f"    {idx}. {indicator}")
    else:
        print(f"\n[KNOWLEDGE GRAPH]")
        print(f"  Not extracted (paper below relevance threshold)")

    print("\n" + "=" * 80)
    print(f"Test output saved to: {output_file}")
    print("=" * 80 + "\n")

    return result


def find_paper_with_abstract(
    papers_file: str = "data/eVTOL/lens_scholarly/papers.json",
    output_file: str = "parsers/scholarly/test_output_single.json"
):
    """
    Alternative test: Find first paper WITH abstract and test it.
    (Many papers have empty abstracts which limits relevance assessment quality)
    """

    print("=" * 80)
    print("SCHOLARLY PARSER - FINDING PAPER WITH ABSTRACT")
    print("=" * 80)

    # Load papers
    print(f"\n[1/2] Loading papers: {papers_file}")
    papers = load_papers_from_file(papers_file, limit=None)
    print(f"  Total papers: {len(papers)}")

    # Find paper with abstract
    print(f"\n[2/2] Searching for paper with substantial abstract...")
    paper_index = None
    for idx, paper in enumerate(papers):
        abstract = paper.get('abstract', '')
        if abstract and len(abstract) > 100:
            paper_index = idx
            print(f"  Found paper #{idx + 1} with {len(abstract)} character abstract")
            print(f"  Title: {paper.get('title', 'No title')[:80]}...")
            break

    if paper_index is None:
        print("  WARNING: No papers with substantial abstracts found in dataset")
        print("  Using first paper anyway...")
        paper_index = 0

    print("\n" + "=" * 80)
    print(f"Testing paper #{paper_index + 1}")
    print("=" * 80 + "\n")

    # Run test with found paper
    return test_single_paper(
        paper_index=paper_index,
        output_file=output_file
    )


if __name__ == "__main__":
    # Test with first paper that has abstract
    # (Better test than papers with missing abstracts)
    result = find_paper_with_abstract()

    # Uncomment to test specific paper by index:
    # result = test_single_paper(paper_index=5)
