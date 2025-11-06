"""Quick validation script for patent field extraction"""
import json

# Load patents
with open('data/eVTOL/lens_patents/patents.json', encoding='utf-8') as f:
    patents = json.load(f)

# Check the last patent (most recently added)
patent = patents[-1]

print(f"Total fields in patent: {len(patent)}")
print(f"\n{'='*60}")
print("NEW FIELD VALIDATION")
print(f"{'='*60}")

new_fields = [
    'doc_key', 'publication_type', 'lang',
    'simple_family_size', 'extended_family_size',
    'forward_citation_count', 'forward_citation_lens_ids',
    'current_owners', 'earliest_priority_date',
    'anticipated_term_date', 'discontinuation_date', 'has_terminal_disclaimer',
    'ipcr_codes', 'npl_resolved_count', 'detailed_citations',
    'description', 'claims'
]

present = 0
for field in new_fields:
    exists = field in patent
    if exists:
        present += 1
    status = "YES" if exists else "NO"
    print(f"  {field:30s} {status}")

print(f"\n{present}/{len(new_fields)} new fields present")

print(f"\n{'='*60}")
print("SAMPLE FIELD VALUES")
print(f"{'='*60}")
print(f"  Patent Number: {patent.get('patent_number', 'N/A')}")
print(f"  Lens ID: {patent.get('lens_id', 'N/A')}")
print(f"  Lang: {patent.get('lang', 'N/A')}")
print(f"  Publication Type: {patent.get('publication_type', 'N/A')}")
print(f"  Doc Key: {patent.get('doc_key', 'N/A')}")
print(f"  Simple Family Size: {patent.get('simple_family_size', 'N/A')}")
print(f"  Extended Family Size: {patent.get('extended_family_size', 'N/A')}")
print(f"  Forward Citations: {patent.get('forward_citation_count', 'N/A')}")
print(f"  Description Length: {len(patent.get('description', ''))} chars")
print(f"  Claims Length: {len(patent.get('claims', ''))} chars")
print(f"  Current Owners Count: {len(patent.get('current_owners', []))}")
print(f"  IPCR Codes Count: {len(patent.get('ipcr_codes', []))}")

print(f"\n{'='*60}")
print("CRITICAL CHECK: Full Text Fields")
print(f"{'='*60}")
desc = patent.get('description', '')
claims = patent.get('claims', '')
print(f"  Description present: {'YES' if desc else 'NO'} ({len(desc)} chars)")
print(f"  Claims present: {'YES' if claims else 'NO'} ({len(claims)} chars)")

if desc:
    print(f"\n  Description preview (first 200 chars):")
    print(f"  {desc[:200]}...")

if claims:
    print(f"\n  Claims preview (first 200 chars):")
    print(f"  {claims[:200]}...")
