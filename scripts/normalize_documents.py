"""
Generic Document Normalization Script
Normalizes tech/company mentions in any JSON with standard document structure
Outputs two versions: normalized (with metadata) and final (clean)
"""

from dotenv import load_dotenv
load_dotenv()

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timezone
import argparse

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from graph.entity_resolution.normalize_tech_company import TechCompanyNormalizer
from graph.entity_resolution.config import EntityResolutionConfig


def create_final_version(normalized_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create clean final version by replacing original names with normalized names
    and removing all normalization metadata fields.

    Args:
        normalized_doc: Document with normalization metadata

    Returns:
        Clean document with only normalized names, no extra fields
    """
    import copy
    final_doc = copy.deepcopy(normalized_doc)

    # Fields to remove (normalization metadata)
    metadata_fields = [
        'normalized_name',
        'tech_id',
        'company_id',
        'normalization_confidence',
        'normalization_score',
        'normalization_method',
        'company_normalization_confidence',
        'company_normalization_score',
        'tech_normalization_confidence',
        'tech_normalization_score',
        'from_company_confidence',
        'from_company_score',
        'to_company_confidence',
        'to_company_score',
        'from_tech_id',
        'to_tech_id',
        'from_company_id',
        'to_company_id',
        'normalized_company_name',
        'normalized_tech_name',
        'normalized_from_company',
        'normalized_to_company',
        'normalized_from_tech',
        'normalized_to_tech'
    ]

    # Process tech_mentions
    if 'tech_mentions' in final_doc:
        for mention in final_doc['tech_mentions']:
            # Replace name with normalized_name
            if 'normalized_name' in mention and mention['normalized_name'] and mention['normalized_name'] != "Unknown":
                mention['name'] = mention['normalized_name']
            # Remove metadata fields
            for field in metadata_fields:
                mention.pop(field, None)

    # Process company_mentions
    if 'company_mentions' in final_doc:
        for mention in final_doc['company_mentions']:
            # Replace name with normalized_name
            if 'normalized_name' in mention and mention['normalized_name'] and mention['normalized_name'] != "Unknown":
                mention['name'] = mention['normalized_name']
            # Remove metadata fields
            for field in metadata_fields:
                mention.pop(field, None)

    # Process company_tech_relations
    if 'company_tech_relations' in final_doc:
        for relation in final_doc['company_tech_relations']:
            # Replace company name
            if 'normalized_company_name' in relation and relation['normalized_company_name'] and relation['normalized_company_name'] != "Unknown":
                relation['company_name'] = relation['normalized_company_name']
            # Replace tech name
            if 'normalized_tech_name' in relation and relation['normalized_tech_name'] and relation['normalized_tech_name'] != "Unknown":
                relation['technology_name'] = relation['normalized_tech_name']
            # Remove metadata fields
            for field in metadata_fields:
                relation.pop(field, None)

    # Process tech_tech_relations
    if 'tech_tech_relations' in final_doc:
        for relation in final_doc['tech_tech_relations']:
            # Replace from_tech
            from_field = 'from_tech_name' if 'from_tech_name' in relation else 'source_tech'
            if 'normalized_from_tech' in relation and relation['normalized_from_tech'] and relation['normalized_from_tech'] != "Unknown":
                relation[from_field] = relation['normalized_from_tech']
            # Replace to_tech
            to_field = 'to_tech_name' if 'to_tech_name' in relation else 'target_tech'
            if 'normalized_to_tech' in relation and relation['normalized_to_tech'] and relation['normalized_to_tech'] != "Unknown":
                relation[to_field] = relation['normalized_to_tech']
            # Remove metadata fields
            for field in metadata_fields:
                relation.pop(field, None)

    # Process company_company_relations
    if 'company_company_relations' in final_doc:
        for relation in final_doc['company_company_relations']:
            # Replace from_company
            if 'normalized_from_company' in relation and relation['normalized_from_company'] and relation['normalized_from_company'] != "Unknown":
                relation['from_company_name'] = relation['normalized_from_company']
            # Replace to_company
            if 'normalized_to_company' in relation and relation['normalized_to_company'] and relation['normalized_to_company'] != "Unknown":
                relation['to_company_name'] = relation['normalized_to_company']
            # Remove metadata fields
            for field in metadata_fields:
                relation.pop(field, None)

    return final_doc


def print_statistics(documents: List[Dict[str, Any]], title: str):
    """Print normalization statistics."""
    print(f"\n{'='*80}")
    print(title)
    print('='*80)

    # Count tech mentions
    total_tech = 0
    matched_tech = 0
    high_conf_tech = 0
    medium_conf_tech = 0
    low_conf_tech = 0

    # Count company mentions
    total_company = 0
    matched_company = 0
    high_conf_company = 0
    medium_conf_company = 0
    low_conf_company = 0

    for doc in documents:
        # Tech mentions
        if 'tech_mentions' in doc:
            for mention in doc['tech_mentions']:
                total_tech += 1
                if mention.get('normalized_name') and mention['normalized_name'] != "Unknown":
                    matched_tech += 1
                    conf = mention.get('normalization_confidence', 'low')
                    if conf == 'high':
                        high_conf_tech += 1
                    elif conf == 'medium':
                        medium_conf_tech += 1
                    else:
                        low_conf_tech += 1

        # Company mentions
        if 'company_mentions' in doc:
            for mention in doc['company_mentions']:
                total_company += 1
                if mention.get('normalized_name') and mention['normalized_name'] != "Unknown":
                    matched_company += 1
                    conf = mention.get('normalization_confidence', 'low')
                    if conf == 'high':
                        high_conf_company += 1
                    elif conf == 'medium':
                        medium_conf_company += 1
                    else:
                        low_conf_company += 1

    # Print tech stats
    if total_tech > 0:
        print(f"\nTechnology Mentions:")
        print(f"  Total: {total_tech}")
        print(f"  Matched: {matched_tech} ({matched_tech/total_tech*100:.1f}%)")
        print(f"  High confidence: {high_conf_tech}")
        print(f"  Medium confidence: {medium_conf_tech}")
        print(f"  Low confidence: {low_conf_tech}")

    # Print company stats
    if total_company > 0:
        print(f"\nCompany Mentions:")
        print(f"  Total: {total_company}")
        print(f"  Matched: {matched_company} ({matched_company/total_company*100:.1f}%)")
        print(f"  High confidence: {high_conf_company}")
        print(f"  Medium confidence: {medium_conf_company}")
        print(f"  Low confidence: {low_conf_company}")

    # Relations
    total_ct_relations = sum(len(doc.get('company_tech_relations', [])) for doc in documents)
    total_cc_relations = sum(len(doc.get('company_company_relations', [])) for doc in documents)
    total_tt_relations = sum(len(doc.get('tech_tech_relations', [])) for doc in documents)

    if total_ct_relations > 0 or total_cc_relations > 0 or total_tt_relations > 0:
        print(f"\nRelations:")
        if total_ct_relations > 0:
            print(f"  Company-Tech: {total_ct_relations}")
        if total_cc_relations > 0:
            print(f"  Company-Company: {total_cc_relations}")
        if total_tt_relations > 0:
            print(f"  Tech-Tech: {total_tt_relations}")


def main():
    """Main normalization pipeline."""
    parser = argparse.ArgumentParser(
        description='Normalize tech/company mentions in JSON documents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/normalize_documents.py data/eVTOL/technologies/technologies_patents_papers.json
  python scripts/normalize_documents.py data/eVTOL/sec/sec_filings.json --tech-threshold 0.6

Outputs:
  - {input}_normalized.json: Full version with normalization metadata
  - {input}_final.json: Clean version with only normalized names
        """
    )
    parser.add_argument('input_file', type=str, help='Path to input JSON file')
    parser.add_argument('--tech-threshold', type=float, default=0.5,
                       help='Tech similarity threshold (default: 0.5)')
    parser.add_argument('--company-threshold', type=float, default=0.5,
                       help='Company similarity threshold (default: 0.5)')
    parser.add_argument('--industry', type=str, default='eVTOL',
                       help='Industry name (default: eVTOL)')

    args = parser.parse_args()

    # Validate input file
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_path}")
        sys.exit(1)

    print("="*80)
    print("GENERIC DOCUMENT NORMALIZATION")
    print("="*80)
    print(f"\nInput: {input_path}")
    print(f"Tech threshold: {args.tech_threshold}")
    print(f"Company threshold: {args.company_threshold}")
    print(f"Industry: {args.industry}")

    # Load input data
    print(f"\n{'='*80}")
    print("LOADING INPUT DATA")
    print('='*80)

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle both single doc and array
    if isinstance(data, dict):
        documents = [data]
    elif isinstance(data, list):
        documents = data
    else:
        print(f"[ERROR] Invalid JSON structure: expected dict or list, got {type(data)}")
        sys.exit(1)

    print(f"Loaded {len(documents)} document(s)")

    # Initialize normalizer
    print(f"\n{'='*80}")
    print("INITIALIZING NORMALIZER")
    print('='*80)

    config = EntityResolutionConfig(industry=args.industry)
    normalizer = TechCompanyNormalizer(
        config,
        tech_threshold=args.tech_threshold,
        company_threshold=args.company_threshold
    )

    # Normalize documents
    print(f"\n{'='*80}")
    print("NORMALIZING DOCUMENTS")
    print('='*80)

    normalized_docs = []
    for i, doc in enumerate(documents, 1):
        if i % 50 == 0 or i == len(documents):
            print(f"  Progress: {i}/{len(documents)}")

        normalized_doc = normalizer.normalize_document(doc)
        normalized_docs.append(normalized_doc)

    print(f"\n[SUCCESS] Normalized {len(normalized_docs)} documents")

    # Create final version
    print(f"\n{'='*80}")
    print("CREATING FINAL VERSION")
    print('='*80)

    final_docs = []
    for i, doc in enumerate(normalized_docs, 1):
        if i % 50 == 0 or i == len(normalized_docs):
            print(f"  Progress: {i}/{len(normalized_docs)}")

        final_doc = create_final_version(doc)
        final_docs.append(final_doc)

    print(f"\n[SUCCESS] Created {len(final_docs)} final documents")

    # Generate output paths
    input_stem = input_path.stem  # filename without extension
    input_dir = input_path.parent

    normalized_path = input_dir / f"{input_stem}_normalized.json"
    final_path = input_dir / f"{input_stem}_final.json"

    # Save normalized version
    print(f"\n{'='*80}")
    print("SAVING OUTPUT FILES")
    print('='*80)

    print(f"\nSaving normalized version...")
    with open(normalized_path, 'w', encoding='utf-8') as f:
        json.dump(normalized_docs, f, indent=2, ensure_ascii=False)
    print(f"  [SUCCESS] {normalized_path}")

    # Save final version
    print(f"\nSaving final version...")
    with open(final_path, 'w', encoding='utf-8') as f:
        json.dump(final_docs, f, indent=2, ensure_ascii=False)
    print(f"  [SUCCESS] {final_path}")

    # Print statistics
    print_statistics(normalized_docs, "NORMALIZATION STATISTICS")

    # Summary
    print(f"\n{'='*80}")
    print("NORMALIZATION COMPLETE!")
    print('='*80)
    print(f"\nOutput Files:")
    print(f"  1. Normalized (with metadata): {normalized_path}")
    print(f"  2. Final (clean): {final_path}")
    print(f"\nProcessed {len(documents)} document(s)")
    print(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    print('='*80)


if __name__ == "__main__":
    main()
