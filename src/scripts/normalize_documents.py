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


def get_technology_details(tech_id: str, catalog: dict) -> Dict[str, Any]:
    """
    Fetch full technology details from catalog.

    Args:
        tech_id: Technology canonical ID
        catalog: Technology catalog dict

    Returns:
        Technology details dict or None if not found
    """
    for tech in catalog.get('technologies', []):
        if tech.get('id') == tech_id:
            return {
                'id': tech.get('id'),
                'name': tech.get('canonical_name'),
                'domain': tech.get('domain'),
                'description': tech.get('description'),
                'aliases': [v.get('name') if isinstance(v, dict) else v for v in tech.get('variants', [])]
            }
    return None


def get_company_details(company_id: str, catalog: dict) -> Dict[str, Any]:
    """
    Fetch full company details from catalog.

    Args:
        company_id: Company canonical ID
        catalog: Company catalog dict

    Returns:
        Company details dict or None if not found
    """
    for company in catalog.get('companies', []):
        if company.get('id') == company_id:
            return {
                'id': company.get('id'),
                'name': company.get('name'),
                'aliases': company.get('aliases', []),
                'ticker': company.get('ticker'),
                'kind': company.get('kind'),
                'sector': company.get('sector'),
                'country': company.get('country'),
                'description': company.get('description')
            }
    return None


def enrich_document_with_entities(
    normalized_doc: Dict[str, Any],
    tech_catalog: dict,
    company_catalog: dict
) -> Dict[str, Any]:
    """
    Add technologies and companies arrays with full details from catalogs.

    Args:
        normalized_doc: Document with normalized mentions
        tech_catalog: Technology catalog dict
        company_catalog: Company catalog dict

    Returns:
        Enriched document with technologies and companies arrays
    """
    # Extract unique tech IDs from all sources
    unique_tech_ids = set()

    # From tech_mentions
    for mention in normalized_doc.get('tech_mentions', []):
        tech_id = mention.get('tech_id')
        if tech_id and mention.get('normalized_name') != "Unknown":
            unique_tech_ids.add(tech_id)

    # From company_tech_relations
    for relation in normalized_doc.get('company_tech_relations', []):
        tech_id = relation.get('tech_id')
        if tech_id and relation.get('normalized_tech_name') != "Unknown":
            unique_tech_ids.add(tech_id)

    # From tech_tech_relations
    for relation in normalized_doc.get('tech_tech_relations', []):
        from_tech_id = relation.get('from_tech_id')
        to_tech_id = relation.get('to_tech_id')
        if from_tech_id and relation.get('normalized_from_tech') != "Unknown":
            unique_tech_ids.add(from_tech_id)
        if to_tech_id and relation.get('normalized_to_tech') != "Unknown":
            unique_tech_ids.add(to_tech_id)

    # Extract unique company IDs from all sources
    unique_company_ids = set()

    # From company_mentions
    for mention in normalized_doc.get('company_mentions', []):
        company_id = mention.get('company_id')
        if company_id and mention.get('normalized_name') != "Unknown":
            unique_company_ids.add(company_id)

    # From company_tech_relations
    for relation in normalized_doc.get('company_tech_relations', []):
        company_id = relation.get('company_id')
        if company_id and relation.get('normalized_company_name') != "Unknown":
            unique_company_ids.add(company_id)

    # From company_company_relations
    for relation in normalized_doc.get('company_company_relations', []):
        from_company_id = relation.get('from_company_id')
        to_company_id = relation.get('to_company_id')
        if from_company_id and relation.get('normalized_from_company') != "Unknown":
            unique_company_ids.add(from_company_id)
        if to_company_id and relation.get('normalized_to_company') != "Unknown":
            unique_company_ids.add(to_company_id)

    # Fetch full details for technologies
    technologies = []
    for tech_id in sorted(unique_tech_ids):
        details = get_technology_details(tech_id, tech_catalog)
        if details:
            technologies.append(details)

    # Fetch full details for companies
    companies = []
    for company_id in sorted(unique_company_ids):
        details = get_company_details(company_id, company_catalog)
        if details:
            companies.append(details)

    # Add enrichment arrays to document
    normalized_doc['technologies'] = technologies
    normalized_doc['companies'] = companies

    return normalized_doc


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

    # Load catalogs for enrichment
    print(f"\n{'='*80}")
    print("LOADING ENTITY CATALOGS FOR ENRICHMENT")
    print('='*80)

    # Access tech catalog from classifier (Pydantic model)
    tech_catalog_model = normalizer.tech_classifier.catalog
    # Convert to dict for helper functions
    tech_catalog = {'technologies': [t.model_dump() for t in tech_catalog_model.technologies]}
    print(f"  Loaded {len(tech_catalog['technologies'])} technologies from catalog")

    # Access company catalog from classifier (dict)
    company_catalog = normalizer.company_classifier.companies_catalog
    print(f"  Loaded {len(company_catalog.get('companies', []))} companies from catalog")

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

    # Enrich documents with entity details
    print(f"\n{'='*80}")
    print("ENRICHING DOCUMENTS WITH ENTITY DETAILS")
    print('='*80)

    enriched_docs = []
    for i, doc in enumerate(normalized_docs, 1):
        if i % 50 == 0 or i == len(normalized_docs):
            print(f"  Progress: {i}/{len(normalized_docs)}")

        enriched_doc = enrich_document_with_entities(doc, tech_catalog, company_catalog)
        enriched_docs.append(enriched_doc)

    # Count unique entities across all documents
    all_tech_ids = set()
    all_company_ids = set()
    for doc in enriched_docs:
        all_tech_ids.update(t['id'] for t in doc.get('technologies', []))
        all_company_ids.update(c['id'] for c in doc.get('companies', []))

    print(f"\n[SUCCESS] Enriched {len(enriched_docs)} documents")
    print(f"  Unique technologies across all docs: {len(all_tech_ids)}")
    print(f"  Unique companies across all docs: {len(all_company_ids)}")

    # Create final version
    print(f"\n{'='*80}")
    print("CREATING FINAL VERSION")
    print('='*80)

    final_docs = []
    for i, doc in enumerate(enriched_docs, 1):
        if i % 50 == 0 or i == len(enriched_docs):
            print(f"  Progress: {i}/{len(enriched_docs)}")

        final_doc = create_final_version(doc)
        final_docs.append(final_doc)

    print(f"\n[SUCCESS] Created {len(final_docs)} final documents")

    # Generate output paths
    input_stem = input_path.stem  # filename without extension
    input_dir = input_path.parent

    normalized_path = input_dir / f"{input_stem}_normalized.json"
    final_path = input_dir / f"{input_stem}_final.json"

    # Save normalized version (with enrichment)
    print(f"\n{'='*80}")
    print("SAVING OUTPUT FILES")
    print('='*80)

    print(f"\nSaving normalized version (with enrichment)...")
    with open(normalized_path, 'w', encoding='utf-8') as f:
        json.dump(enriched_docs, f, indent=2, ensure_ascii=False)
    print(f"  [SUCCESS] {normalized_path}")

    # Save final version
    print(f"\nSaving final version...")
    with open(final_path, 'w', encoding='utf-8') as f:
        json.dump(final_docs, f, indent=2, ensure_ascii=False)
    print(f"  [SUCCESS] {final_path}")

    # Print statistics
    print_statistics(enriched_docs, "NORMALIZATION STATISTICS")

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
