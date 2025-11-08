"""
Test script for single paper parsing with new standardized structure.
"""

import os
import json
from dotenv import load_dotenv
from scholarly_parser import ScholarlyRelevanceParser

load_dotenv()


def test_single_paper():
    """Test parsing a single paper to validate refactored structure."""

    print("\n" + "=" * 80)
    print("TESTING: Single Paper Parsing (Standardized Structure)")
    print("=" * 80 + "\n")

    print("This will test the refactored parser with:")
    print("  - Config-driven relation types")
    print("  - Python metadata extraction (no LLM)")
    print("  - Quality score (0-1 scale)")
    print("  - Role-based entity mentions")
    print("  - document_metadata populated with extra fields\n")

    # Load API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    # Initialize parser
    print("[1/4] Initializing parser...")
    parser = ScholarlyRelevanceParser(
        openai_api_key=api_key,
        config_path="configs/eVTOL_graph_relations.json",
        industry_name="eVTOL",
        industry_keywords=["eVTOL", "electric VTOL", "urban air mobility"],
        industry_description="Electric Vertical Takeoff and Landing aircraft for urban air mobility",
        model_name="gpt-4o-mini",
        temperature=0.0
    )
    print("  Parser initialized successfully")

    # Load papers
    print("\n[2/4] Loading paper data...")
    papers_file = "data/eVTOL/lens_scholarly/papers.json"
    with open(papers_file, "r", encoding="utf-8") as f:
        papers = json.load(f)

    if not papers:
        print("  ERROR: No papers found in file")
        return

    paper = papers[2]  # Test with paper 2 (has abstract) to verify LLM call
    print(f"  Loaded paper: {paper.get('title', 'No title')[:80]}...")
    print(f"  Year: {paper.get('year_published', 'Unknown')}")
    print(f"  Source: {paper.get('source', {}).get('title', 'Unknown')}")
    print(f"  Abstract length: {len(paper.get('abstract', ''))} characters")

    # Parse paper
    print("\n[3/4] Parsing paper...")
    result = parser.parse_paper(paper)

    # Save result
    print("\n[4/4] Saving results...")
    output_path = "parsers/test_scholarly_output.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"  Saved to: {output_path}")

    # Display summary
    print("\n" + "=" * 80)
    print("PARSING RESULTS SUMMARY")
    print("=" * 80 + "\n")

    # Document info
    doc = result.get('document', {})
    print(f"Document Type: {doc.get('doc_type', 'N/A')}")
    print(f"Doc ID: {doc.get('doc_id', 'N/A')}")
    print(f"Title: {doc.get('title', 'N/A')[:70]}...")
    print(f"Source: {doc.get('source', 'N/A')}")
    print(f"Published At: {doc.get('published_at', 'N/A')}")
    print(f"Quality Score: {doc.get('quality_score', 0.0):.2f}")
    print(f"Citation Count: {doc.get('citation_count', 0)}")
    print(f"Patent Citations: {doc.get('patent_citations_count', 0)}")
    print(f"DOI: {doc.get('doi', 'N/A')}")
    print(f"Venue Type: {doc.get('venue_type', 'N/A')}")
    print(f"Peer Reviewed: {doc.get('peer_reviewed', 'N/A')}")
    print()

    # Entity and relation counts
    print(f"Technology Mentions: {len(result.get('tech_mentions', []))}")
    print(f"Company Mentions: {len(result.get('company_mentions', []))}")
    print(f"Company-Tech Relations: {len(result.get('company_tech_relations', []))}")
    print(f"Tech-Tech Relations: {len(result.get('tech_tech_relations', []))}")
    print(f"Company-Company Relations: {len(result.get('company_company_relations', []))}")
    print()

    # Document metadata check
    doc_metadata = result.get('document_metadata', {})
    print(f"Document Metadata Fields: {len(doc_metadata)} fields")
    if doc_metadata:
        print(f"  Sample fields: {', '.join(list(doc_metadata.keys())[:5])}...")
    print()

    # Show sample tech mentions
    if result.get('tech_mentions'):
        print("Sample Technology Mentions:")
        for i, tech in enumerate(result['tech_mentions'][:3], 1):
            print(f"  {i}. {tech.get('name', 'N/A')} (role={tech.get('role', 'N/A')}, strength={tech.get('strength', 0):.2f})")
    print()

    # Validation
    print("=" * 80)
    print("VALIDATION CHECKS")
    print("=" * 80 + "\n")

    checks = [
        ("doc_type == 'technical_paper'", doc.get('doc_type') == 'technical_paper'),
        ("published_at uses date_published", doc.get('published_at') == paper.get('date_published')),
        ("summary is empty string", doc.get('summary') == ""),
        ("content is abstract", doc.get('content') == parser._clean_abstract(paper.get('abstract', ''))),
        ("quality_score between 0-1", 0 <= doc.get('quality_score', 0) <= 1),
        ("document_metadata not empty", len(doc_metadata) > 0),
        ("doc_ref added to relations", all('doc_ref' in rel for rel in result.get('tech_tech_relations', []))),
    ]

    all_passed = True
    for check_name, passed in checks:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {check_name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print("SUCCESS: All validation checks passed!")
    else:
        print("WARNING: Some validation checks failed - review output")
    print("=" * 80 + "\n")

    return result


if __name__ == "__main__":
    test_single_paper()
