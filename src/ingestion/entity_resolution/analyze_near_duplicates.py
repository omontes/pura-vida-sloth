"""
Analyze merged catalog for potential near-duplicates (0.75-0.85 similarity)
"""

import json
from rapidfuzz import fuzz
from collections import defaultdict

# Load merged catalog
with open('graph/entity_resolution/output/04_merged_catalog.json', 'r', encoding='utf-8') as f:
    catalog = json.load(f)

canonical_names = [tech['canonical_name'] for tech in catalog]
print(f"Total canonical technologies: {len(canonical_names)}")
print(f"Analyzing for near-duplicates (fuzzy similarity 0.75-0.85)...\n")

# Find near-duplicates
near_duplicates = []
checked_pairs = set()

for i, name1 in enumerate(canonical_names):
    for j, name2 in enumerate(canonical_names):
        if i >= j:
            continue

        pair_key = tuple(sorted([name1, name2]))
        if pair_key in checked_pairs:
            continue
        checked_pairs.add(pair_key)

        # Calculate fuzzy similarity
        fuzzy_score = fuzz.ratio(name1.lower(), name2.lower()) / 100.0

        # Flag near-duplicates (0.75-0.85 range - below threshold but suspicious)
        if 0.75 <= fuzzy_score < 0.85:
            near_duplicates.append({
                'name1': name1,
                'name2': name2,
                'fuzzy_score': fuzzy_score
            })

# Sort by similarity (highest first)
near_duplicates.sort(key=lambda x: x['fuzzy_score'], reverse=True)

print(f"Found {len(near_duplicates)} potential near-duplicates (fuzzy 0.75-0.85)\n")

if near_duplicates:
    print("Top 20 suspicious pairs:\n")
    for i, pair in enumerate(near_duplicates[:20], 1):
        print(f"{i}. Fuzzy: {pair['fuzzy_score']:.3f}")
        print(f"   '{pair['name1']}'")
        print(f"   '{pair['name2']}'")
        print()

# Group by fuzzy score ranges
ranges = defaultdict(int)
for pair in near_duplicates:
    score = pair['fuzzy_score']
    if 0.80 <= score < 0.85:
        ranges['0.80-0.85'] += 1
    elif 0.75 <= score < 0.80:
        ranges['0.75-0.80'] += 1

print("\nDistribution by fuzzy score range:")
for range_key in ['0.80-0.85', '0.75-0.80']:
    count = ranges.get(range_key, 0)
    print(f"  {range_key}: {count} pairs")

print("\n" + "="*80)
print("RECOMMENDATION")
print("="*80)

if len([p for p in near_duplicates if p['fuzzy_score'] >= 0.80]) > 10:
    print("⚠️  WARNING: Found significant near-duplicates (>10 pairs at 0.80+)")
    print("   Consider running Phase 4B: Canonical Name Clustering")
    print("   This would merge semantically similar canonical names")
else:
    print("✅ Low risk: < 10 pairs at 0.80+ similarity")
    print("   Manual review recommended but not critical")
