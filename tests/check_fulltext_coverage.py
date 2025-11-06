"""Check description and claims coverage in patent harvest"""
import json

with open('data/eVTOL/lens_patents/patents.json', encoding='utf-8') as f:
    patents = json.load(f)

total = len(patents)
recent_20 = patents[-20:]

# Check recent 20 patents (newly downloaded)
recent_with_desc = sum(1 for p in recent_20 if len(p.get('description', '')) > 0)
recent_with_claims = sum(1 for p in recent_20 if len(p.get('claims', '')) > 0)

# Check all patents
all_with_desc = sum(1 for p in patents if len(p.get('description', '')) > 0)
all_with_claims = sum(1 for p in patents if len(p.get('claims', '')) > 0)

print("="*60)
print("DESCRIPTION & CLAIMS COVERAGE CHECK")
print("="*60)
print(f"\nLast 20 patents (newly harvested):")
print(f"  With description: {recent_with_desc}/20 ({100*recent_with_desc/20:.1f}%)")
print(f"  With claims: {recent_with_claims}/20 ({100*recent_with_claims/20:.1f}%)")

print(f"\nAll {total} patents:")
print(f"  With description: {all_with_desc}/{total} ({100*all_with_desc/total:.1f}%)")
print(f"  With claims: {all_with_claims}/{total} ({100*all_with_claims/total:.1f}%)")

# Find an example with description/claims
print("\n" + "="*60)
print("LOOKING FOR EXAMPLE WITH FULL TEXT...")
print("="*60)

found_example = False
for patent in patents[-50:]:  # Check last 50
    desc_len = len(patent.get('description', ''))
    claims_len = len(patent.get('claims', ''))
    if desc_len > 0 or claims_len > 0:
        print(f"\nFound patent with full text:")
        print(f"  Lens ID: {patent.get('lens_id')}")
        print(f"  Patent Number: {patent.get('patent_number')}")
        print(f"  Lang: {patent.get('lang')}")
        print(f"  Description: {desc_len} chars")
        print(f"  Claims: {claims_len} chars")
        found_example = True
        break

if not found_example:
    print("\nWARNING: No patents with description/claims found in last 50 patents!")
    print("This suggests the Lens API may not be returning full text in search results.")
