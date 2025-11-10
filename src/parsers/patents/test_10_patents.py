"""
Test script to parse first 10 eVTOL patents and validate parser performance.
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

from patents_parser import PatentTechnologyParser, load_patents_from_file


def validate_10_patents():
    """Parse first 10 patents and create analysis report."""

    # Load API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    # Initialize parser
    parser = PatentTechnologyParser(
        openai_api_key=api_key,
        model_name="gpt-4o-mini",
        temperature=0.0
    )

    # Load first 10 patents
    patents_file = "data/eVTOL/lens_patents/patents.json"
    patents = load_patents_from_file(patents_file, limit=10)

    print(f"\n{'='*80}")
    print("VALIDATING PATENT PARSER - 10 PATENTS")
    print(f"{'='*80}\n")

    results = []
    total_cost = 0.0
    total_nodes = 0
    total_relationships = 0

    for idx, patent in enumerate(patents, 1):
        patent_id = patent.get("lens_id", f"unknown_{idx}")
        title = patent.get("title", "No title")

        print(f"\n[{idx}/10] Parsing: {patent_id}")
        print(f"  Title: {title[:80]}...")

        try:
            result = parser.parse_patent(patent)

            # Count elements
            nodes = len(result.get('technology_nodes', []))
            rels = len(result.get('relationships', []))

            total_nodes += nodes
            total_relationships += rels

            # Add metadata
            result['parsing_metadata'] = {
                'index': idx,
                'success': True,
                'nodes_extracted': nodes,
                'relationships_extracted': rels
            }

            results.append(result)

            print(f"  ✓ Success: {nodes} nodes, {rels} relationships")

        except Exception as e:
            print(f"  ✗ Failed: {e}")
            results.append({
                'patent_metadata': {
                    'lens_id': patent_id,
                    'title': title,
                    'error': str(e)
                },
                'parsing_metadata': {
                    'index': idx,
                    'success': False
                }
            })

    # Save results
    output_file = "data/eVTOL/lens_patents/example_parser.json"

    analysis = {
        "validation_summary": {
            "total_patents": len(patents),
            "successfully_parsed": sum(1 for r in results if r.get('parsing_metadata', {}).get('success', False)),
            "failed": sum(1 for r in results if not r.get('parsing_metadata', {}).get('success', True)),
            "total_technology_nodes": total_nodes,
            "total_relationships": total_relationships,
            "avg_nodes_per_patent": round(total_nodes / len(patents), 2),
            "avg_relationships_per_patent": round(total_relationships / len(patents), 2)
        },
        "parsed_patents": results,
        "validation_notes": {
            "parser_model": "gpt-4o-mini",
            "temperature": 0.0,
            "date": "2025-11-05",
            "purpose": "Validate parser consistency and quality across eVTOL patent dataset"
        }
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*80}")
    print("VALIDATION COMPLETE")
    print(f"{'='*80}")
    print(f"Successfully parsed: {analysis['validation_summary']['successfully_parsed']}/10")
    print(f"Total nodes extracted: {total_nodes}")
    print(f"Total relationships: {total_relationships}")
    print(f"Average nodes/patent: {analysis['validation_summary']['avg_nodes_per_patent']}")
    print(f"Average relationships/patent: {analysis['validation_summary']['avg_relationships_per_patent']}")
    print(f"\nResults saved to: {output_file}")
    print(f"{'='*80}\n")

    return analysis


if __name__ == "__main__":
    validate_10_patents()
