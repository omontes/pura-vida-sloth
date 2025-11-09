"""
Clean Placeholder Company Names from SEC Filings
Removes generic/placeholder company names from SEC filing JSON
"""

import json
from pathlib import Path
from typing import Dict, List, Any

# Placeholder/generic company names to remove
PLACEHOLDER_COMPANIES = {
    "Another Retail Company",
    "Another Customer",
    "Another Supplier",
    "Certain Customers",
    "Certain Suppliers",
    "Major Customers",
    "Major Suppliers",
    "Various Customers",
    "Other Companies",
    "Third Party",
    "Unnamed Entity"
}


def clean_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove placeholder companies from a single document.

    Args:
        doc: Document dict with company_mentions and relations

    Returns:
        Cleaned document dict
    """
    # Filter company mentions
    if 'company_mentions' in doc:
        original_count = len(doc['company_mentions'])
        doc['company_mentions'] = [
            mention for mention in doc['company_mentions']
            if mention.get('name') not in PLACEHOLDER_COMPANIES
        ]
        removed = original_count - len(doc['company_mentions'])
        if removed > 0:
            print(f"    Removed {removed} placeholder company mention(s) from doc {doc.get('document', {}).get('doc_id', 'unknown')}")

    # Filter company-tech relations
    if 'company_tech_relations' in doc:
        original_count = len(doc['company_tech_relations'])
        doc['company_tech_relations'] = [
            rel for rel in doc['company_tech_relations']
            if rel.get('company_name') not in PLACEHOLDER_COMPANIES
        ]
        removed = original_count - len(doc['company_tech_relations'])
        if removed > 0:
            print(f"    Removed {removed} company-tech relation(s) with placeholders")

    # Filter company-company relations (both from and to)
    if 'company_company_relations' in doc:
        original_count = len(doc['company_company_relations'])
        doc['company_company_relations'] = [
            rel for rel in doc['company_company_relations']
            if (rel.get('from_company_name') not in PLACEHOLDER_COMPANIES and
                rel.get('to_company_name') not in PLACEHOLDER_COMPANIES)
        ]
        removed = original_count - len(doc['company_company_relations'])
        if removed > 0:
            print(f"    Removed {removed} company-company relation(s) with placeholders")

    return doc


def main():
    """Clean SEC filings and save cleaned version."""
    input_file = Path("data/eVTOL/sec_filings/relevant_evtol_sec_filings.json")
    output_file = Path("data/eVTOL/sec_filings/relevant_evtol_sec_filings_cleaned.json")

    print("="*80)
    print("CLEANING SEC FILINGS - REMOVING PLACEHOLDER COMPANIES")
    print("="*80)

    # Load data
    print(f"\nLoading: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Loaded {len(data)} documents")

    # Count placeholders before cleaning
    total_company_mentions = 0
    placeholder_mentions = 0
    for doc in data:
        if 'company_mentions' in doc:
            total_company_mentions += len(doc['company_mentions'])
            for mention in doc['company_mentions']:
                if mention.get('name') in PLACEHOLDER_COMPANIES:
                    placeholder_mentions += 1

    print(f"\nBefore cleaning:")
    print(f"  Total company mentions: {total_company_mentions}")
    print(f"  Placeholder mentions: {placeholder_mentions} ({placeholder_mentions/total_company_mentions*100:.1f}%)")

    # Clean documents
    print(f"\nCleaning documents...")
    cleaned_data = [clean_document(doc) for doc in data]

    # Count after cleaning
    total_after = sum(len(doc.get('company_mentions', [])) for doc in cleaned_data)
    print(f"\nAfter cleaning:")
    print(f"  Total company mentions: {total_after}")
    print(f"  Removed: {total_company_mentions - total_after}")

    # Save cleaned data
    print(f"\nSaving cleaned data to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, indent=2, ensure_ascii=False)

    print(f"\n[SUCCESS] Cleaned SEC filings saved!")
    print("="*80)
    print(f"\nNext step: Run normalization on cleaned data:")
    print(f"  python scripts/normalize_documents.py {output_file}")


if __name__ == "__main__":
    main()
