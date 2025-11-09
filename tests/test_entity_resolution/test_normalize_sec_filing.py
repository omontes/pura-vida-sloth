"""
Integration Test: Normalize SEC Filing JSON
Tests the complete tech + company normalization pipeline with sample SEC filing
"""

from dotenv import load_dotenv
load_dotenv()

import json
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from graph.entity_resolution.normalize_tech_company import TechCompanyNormalizer
from graph.entity_resolution.config import EntityResolutionConfig


def create_sample_sec_filing():
    """Create a sample SEC filing JSON (based on user's example)."""
    return {
        "document": {
            "doc_id": "sec_000162828025008823",
            "doc_type": "sec_filing",
            "title": "Archer Aviation Inc. - 10-K - 2025-02-28",
            "url": "https://www.sec.gov/Archives/edgar/data/1824502/000162828025008823/0001628280-25-008823-index.htm",
            "source": "SEC EDGAR",
            "published_at": "2025-02-28",
            "summary": "The company is engaged in the aerospace sector, focusing on innovative aircraft technologies...",
            "content": "",
            "quality_score": 0.85,
            "relevance_score": 0.0,
            "filing_type": "10-K",
            "cik": "0001824502",
            "accession_number": "0001628280-25-008823",
            "filing_date": "2025-02-28",
            "fiscal_year": 2024,
            "fiscal_quarter": "Q4",
            "embedding": []
        },
        "document_metadata": {
            "company_name": "Archer Aviation Inc.",
            "ticker": "ACHR",
            "fiscal_year_end": "1231",
            "sic_code": "3721",
            "sic_description": "AIRCRAFT",
            "state_of_incorporation": None,
            "ein": "852730902",
            "report_period": "2024-12-31",
            "revenue_mentioned": False,
            "revenue_amount": None,
            "risk_factor_mentioned": True
        },
        "tech_mentions": [
            {
                "name": "eVTOL Aircraft",
                "role": "subject",
                "strength": 0.95,
                "evidence_confidence": 0.95,
                "evidence_text": "Focused on developing electric vertical takeoff and landing (eVTOL) aircraft"
            },
            {
                "name": "Distributed Electric Propulsion",
                "role": "studied",
                "strength": 0.7,
                "evidence_confidence": 0.85,
                "evidence_text": "Utilizes a proprietary 12-tilt-6 distributed electric propulsion platform"
            },
            {
                "name": "Hybrid-Propulsion VTOL Aircraft",
                "role": "proposed",
                "strength": 0.6,
                "evidence_confidence": 0.8,
                "evidence_text": "Collaborating with Anduril to create a hybrid-propulsion VTOL aircraft"
            }
        ],
        "company_mentions": [
            {
                "name": "United Airlines",
                "role": "partner",
                "strength": 0.85,
                "evidence_confidence": 0.95,
                "evidence_text": "Established partnerships to enhance operational capabilities"
            },
            {
                "name": "Stellantis",
                "role": "partner",
                "strength": 0.85,
                "evidence_confidence": 0.95,
                "evidence_text": "PIPE financing and contract manufacturing relationship"
            },
            {
                "name": "Anduril Industries",
                "role": "partner",
                "strength": 0.7,
                "evidence_confidence": 0.8,
                "evidence_text": "Strategic partnership for next-generation defense aircraft"
            },
            {
                "name": "Synovus Bank",
                "role": "sponsor",
                "strength": 0.4,
                "evidence_confidence": 0.6,
                "evidence_text": "Secured loans to support growth and operational needs"
            }
        ],
        "company_tech_relations": [
            {
                "company_name": "Archer Aviation Inc.",
                "technology_name": "eVTOL Aircraft",
                "relation_type": "develops",
                "evidence_confidence": 0.95,
                "evidence_text": "Developing eVTOL aircraft aimed at urban air mobility",
                "doc_ref": "sec_000162828025008823"
            },
            {
                "company_name": "Archer Aviation Inc.",
                "technology_name": "Distributed Electric Propulsion",
                "relation_type": "develops",
                "evidence_confidence": 0.85,
                "evidence_text": "Utilizing distributed electric propulsion for Midnight aircraft",
                "doc_ref": "sec_000162828025008823"
            }
        ],
        "tech_tech_relations": [],
        "company_company_relations": [
            {
                "from_company_name": "Archer Aviation Inc.",
                "to_company_name": "United Airlines",
                "relation_type": "partners_with",
                "evidence_confidence": 0.95,
                "evidence_text": "Partnership to enhance operational capabilities",
                "doc_ref": "sec_000162828025008823"
            },
            {
                "from_company_name": "Archer Aviation Inc.",
                "to_company_name": "Stellantis",
                "relation_type": "partners_with",
                "evidence_confidence": 0.95,
                "evidence_text": "Contract manufacturing relationship with Stellantis",
                "doc_ref": "sec_000162828025008823"
            },
            {
                "from_company_name": "Archer Aviation Inc.",
                "to_company_name": "Anduril Industries",
                "relation_type": "partners_with",
                "evidence_confidence": 0.8,
                "evidence_text": "Collaboration for defense aircraft development",
                "doc_ref": "sec_000162828025008823"
            }
        ]
    }


def main():
    """Test SEC filing normalization."""
    config = EntityResolutionConfig(industry="eVTOL")

    print("="*80)
    print("SEC FILING NORMALIZATION INTEGRATION TEST")
    print("="*80)

    # Create sample SEC filing
    print("\nCreating sample SEC filing...")
    sample_filing = create_sample_sec_filing()

    print(f"  Document ID: {sample_filing['document']['doc_id']}")
    print(f"  Company: {sample_filing['document_metadata']['company_name']} ({sample_filing['document_metadata']['ticker']})")
    print(f"  Tech mentions: {len(sample_filing['tech_mentions'])}")
    print(f"  Company mentions: {len(sample_filing['company_mentions'])}")
    print(f"  Company-tech relations: {len(sample_filing['company_tech_relations'])}")
    print(f"  Company-company relations: {len(sample_filing['company_company_relations'])}")

    # Initialize normalizer
    print("\n" + "="*80)
    print("INITIALIZING NORMALIZER")
    print("="*80)

    normalizer = TechCompanyNormalizer(
        config,
        tech_threshold=0.5,
        company_threshold=0.5
    )

    # Normalize document
    print("="*80)
    print("NORMALIZING DOCUMENT")
    print("="*80)

    normalized_filing = normalizer.normalize_document(sample_filing)

    # Display results
    print("\n" + "="*80)
    print("NORMALIZATION RESULTS")
    print("="*80)

    # Tech mentions
    print("\n1. TECH MENTIONS:")
    print("-" * 80)
    for i, mention in enumerate(normalized_filing['tech_mentions'], 1):
        print(f"\n  [{i}] Original: '{mention['name']}'")
        print(f"      Normalized: '{mention.get('normalized_name', 'N/A')}'")
        print(f"      Tech ID: {mention.get('tech_id', 'N/A')}")
        print(f"      Confidence: {mention.get('normalization_confidence', 'N/A')} (score: {mention.get('normalization_score', 0):.3f})")
        print(f"      Method: {mention.get('normalization_method', 'N/A')}")

    # Company mentions
    print("\n2. COMPANY MENTIONS:")
    print("-" * 80)
    for i, mention in enumerate(normalized_filing['company_mentions'], 1):
        print(f"\n  [{i}] Original: '{mention['name']}'")
        print(f"      Normalized: '{mention.get('normalized_name', 'N/A')}'")
        print(f"      Company ID: {mention.get('company_id', 'N/A')}")
        print(f"      Confidence: {mention.get('normalization_confidence', 'N/A')} (score: {mention.get('normalization_score', 0):.3f})")
        print(f"      Method: {mention.get('normalization_method', 'N/A')}")

    # Company-tech relations
    print("\n3. COMPANY-TECH RELATIONS:")
    print("-" * 80)
    for i, relation in enumerate(normalized_filing['company_tech_relations'], 1):
        print(f"\n  [{i}] Relation: {relation['relation_type']}")
        print(f"      Company: '{relation['company_name']}' -> '{relation.get('normalized_company_name', 'N/A')}'")
        print(f"      Tech: '{relation['technology_name']}' -> '{relation.get('normalized_tech_name', 'N/A')}'")
        print(f"      Company confidence: {relation.get('company_normalization_confidence', 'N/A')}")
        print(f"      Tech confidence: {relation.get('tech_normalization_confidence', 'N/A')}")

    # Company-company relations
    print("\n4. COMPANY-COMPANY RELATIONS:")
    print("-" * 80)
    for i, relation in enumerate(normalized_filing['company_company_relations'], 1):
        print(f"\n  [{i}] Relation: {relation['relation_type']}")
        print(f"      From: '{relation['from_company_name']}' -> '{relation.get('normalized_from_company', 'N/A')}'")
        print(f"      To: '{relation['to_company_name']}' -> '{relation.get('normalized_to_company', 'N/A')}'")
        print(f"      From confidence: {relation.get('from_company_confidence', 'N/A')} (score: {relation.get('from_company_score', 0):.3f})")
        print(f"      To confidence: {relation.get('to_company_confidence', 'N/A')} (score: {relation.get('to_company_score', 0):.3f})")

    # Summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)

    # Count successful normalizations
    tech_matched = sum(1 for m in normalized_filing['tech_mentions'] if m.get('normalized_name') and m['normalized_name'] != "Unknown")
    company_matched = sum(1 for m in normalized_filing['company_mentions'] if m.get('normalized_name') and m['normalized_name'] != "Unknown")

    print(f"\nTech Mentions:")
    print(f"  Total: {len(normalized_filing['tech_mentions'])}")
    print(f"  Matched: {tech_matched} ({tech_matched/len(normalized_filing['tech_mentions'])*100:.1f}%)")

    print(f"\nCompany Mentions:")
    print(f"  Total: {len(normalized_filing['company_mentions'])}")
    print(f"  Matched: {company_matched} ({company_matched/len(normalized_filing['company_mentions'])*100:.1f}%)")

    print(f"\nRelations:")
    print(f"  Company-tech: {len(normalized_filing['company_tech_relations'])} (all normalized)")
    print(f"  Company-company: {len(normalized_filing['company_company_relations'])} (all normalized)")

    # Save normalized output
    output_file = Path("graph/entity_resolution/output/normalized_sec_filing_sample.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(normalized_filing, f, indent=2, ensure_ascii=False)

    print(f"\n[SUCCESS] Saved normalized filing to: {output_file}")

    print("\n" + "="*80)
    print("[SUCCESS] Integration Test Complete!")
    print("="*80)

    print("\nNext Steps:")
    print("  1. Review normalized output: graph/entity_resolution/output/normalized_sec_filing_sample.json")
    print("  2. Integrate normalizer into SEC parser pipeline")
    print("  3. Process batch of SEC filings")


if __name__ == "__main__":
    main()
