"""
Analyze document count distribution and compare sampling strategies.

This script helps determine the optimal min_document_count threshold
by comparing community-based sampling vs document-count filtering.
"""

import asyncio
import sys
import os
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.graph.neo4j_client import Neo4jClient


async def query_document_distribution(client: Neo4jClient) -> Dict[str, Any]:
    """Query document count distribution across all technologies."""

    # Query 1: Total technology count
    query_total = "MATCH (t:Technology) RETURN count(t) as total"
    result = await client.run_query(query_total)
    total_techs = result[0]["total"] if result else 0

    # Query 2: Document count distribution
    query_dist = """
    MATCH (t:Technology)
    OPTIONAL MATCH (t)-[:MENTIONED_IN]->(d:Document)
    WITH t, count(DISTINCT d) as doc_count
    RETURN
      CASE
        WHEN doc_count = 0 THEN '0 docs'
        WHEN doc_count < 5 THEN '1-4 docs'
        WHEN doc_count < 10 THEN '5-9 docs'
        WHEN doc_count < 15 THEN '10-14 docs'
        WHEN doc_count < 20 THEN '15-19 docs'
        WHEN doc_count < 30 THEN '20-29 docs'
        ELSE '30+ docs'
      END as doc_range,
      count(t) as tech_count
    ORDER BY doc_range
    """
    distribution = await client.run_query(query_dist)

    # Query 3: Technologies above different thresholds
    query_thresholds = """
    MATCH (t:Technology)
    OPTIONAL MATCH (t)-[:MENTIONED_IN]->(d:Document)
    WITH count(DISTINCT d) as doc_count
    RETURN
      sum(CASE WHEN doc_count >= 5 THEN 1 ELSE 0 END) as min_5,
      sum(CASE WHEN doc_count >= 10 THEN 1 ELSE 0 END) as min_10,
      sum(CASE WHEN doc_count >= 15 THEN 1 ELSE 0 END) as min_15,
      sum(CASE WHEN doc_count >= 20 THEN 1 ELSE 0 END) as min_20,
      sum(CASE WHEN doc_count >= 25 THEN 1 ELSE 0 END) as min_25,
      sum(CASE WHEN doc_count >= 30 THEN 1 ELSE 0 END) as min_30
    """
    thresholds = await client.run_query(query_thresholds)

    # Query 4: Top 50 technologies by document count
    query_top = """
    MATCH (t:Technology)
    OPTIONAL MATCH (t)-[:MENTIONED_IN]->(d:Document)
    WITH t, count(DISTINCT d) as doc_count
    WHERE doc_count > 0
    RETURN t.id as tech_id, t.name as tech_name, doc_count
    ORDER BY doc_count DESC
    LIMIT 50
    """
    top_techs = await client.run_query(query_top)

    return {
        "total": total_techs,
        "distribution": distribution,
        "thresholds": thresholds[0] if thresholds else {},
        "top_techs": top_techs
    }


async def simulate_community_sampling(client: Neo4jClient, sample_size: int = 150, final_limit: int = 100) -> Dict[str, Any]:
    """Simulate community-based stratified sampling strategy."""

    # Step 1: Get all communities (v1)
    query_communities = """
    MATCH (c:Community)
    WHERE c.id STARTS WITH 'v1_'
    OPTIONAL MATCH (c)-[:HAS_MEMBER]->(t:Technology)-[:MENTIONED_IN]->(d:Document)
    WITH c,
         count(DISTINCT t) as tech_count,
         collect(DISTINCT d.doc_type) as doc_types,
         count(CASE WHEN d.doc_type = 'patent' THEN 1 END) as patents,
         count(CASE WHEN d.doc_type = 'news' THEN 1 END) as news,
         count(CASE WHEN d.doc_type = 'government_contract' THEN 1 END) as contracts
    RETURN c.id as id, tech_count, patents, news, contracts
    ORDER BY tech_count DESC
    """
    communities = await client.run_query(query_communities)

    # Step 2: Classify communities (simplified version)
    early, mid, late, hype = [], [], [], []
    for comm in communities:
        patents = comm.get("patents", 0)
        news = comm.get("news", 0)
        contracts = comm.get("contracts", 0)

        if patents > news and patents >= 1 and contracts <= 1:
            early.append(comm)
        elif news > patents and news >= 1 and contracts <= 1:
            hype.append(comm)
        elif contracts >= 2 and (patents >= 1 or news >= 1):
            late.append(comm)
        else:
            mid.append(comm)

    print(f"\n[COMMUNITY CLASSIFICATION]")
    print(f"  Early-stage: {len(early)} communities")
    print(f"  Mid-stage: {len(mid)} communities")
    print(f"  Late-stage: {len(late)} communities")
    print(f"  Hype-stage: {len(hype)} communities")

    # Step 3: Sample technologies from communities (target sample_size=150)
    # Using current strategy: early=20%, mid=40%, late=20%, hype=20%
    early_target = int(sample_size * 0.20)
    mid_target = int(sample_size * 0.40)
    late_target = int(sample_size * 0.20)
    hype_target = int(sample_size * 0.20)

    # Get technologies from each community type
    async def get_techs_from_communities(comm_list: List[Dict], limit: int) -> List[Dict]:
        if not comm_list:
            return []
        comm_ids = [int(c["id"].split("_")[1]) for c in comm_list]
        query = f"""
        MATCH (t:Technology)
        WHERE t.community_v1 IN {comm_ids}
        OPTIONAL MATCH (t)-[:MENTIONED_IN]->(d:Document)
        WITH t, count(DISTINCT d) as doc_count
        WHERE doc_count >= 5
        RETURN t.id as tech_id, doc_count, t.community_v1 as community
        ORDER BY doc_count DESC
        LIMIT {limit}
        """
        return await client.run_query(query)

    early_techs = await get_techs_from_communities(early, early_target * 2)  # Oversample
    mid_techs = await get_techs_from_communities(mid, mid_target * 2)
    late_techs = await get_techs_from_communities(late, late_target * 2)
    hype_techs = await get_techs_from_communities(hype, hype_target * 2)

    # Take top by doc_count
    early_sample = sorted(early_techs, key=lambda x: x['doc_count'], reverse=True)[:early_target]
    mid_sample = sorted(mid_techs, key=lambda x: x['doc_count'], reverse=True)[:mid_target]
    late_sample = sorted(late_techs, key=lambda x: x['doc_count'], reverse=True)[:late_target]
    hype_sample = sorted(hype_techs, key=lambda x: x['doc_count'], reverse=True)[:hype_target]

    all_sampled = early_sample + mid_sample + late_sample + hype_sample

    # Sort by doc_count and take top final_limit
    final_sample = sorted(all_sampled, key=lambda x: x['doc_count'], reverse=True)[:final_limit]

    # Calculate statistics
    doc_counts = [t['doc_count'] for t in final_sample]
    avg_docs = sum(doc_counts) / len(doc_counts) if doc_counts else 0

    return {
        "strategy": "Community Sampling",
        "total_sampled": len(all_sampled),
        "final_count": len(final_sample),
        "avg_doc_count": avg_docs,
        "min_doc_count": min(doc_counts) if doc_counts else 0,
        "max_doc_count": max(doc_counts) if doc_counts else 0,
        "tech_ids": [t['tech_id'] for t in final_sample],
        "breakdown": {
            "early": len(early_sample),
            "mid": len(mid_sample),
            "late": len(late_sample),
            "hype": len(hype_sample)
        }
    }


async def simulate_document_filtering(client: Neo4jClient, min_docs: int = 15, limit: int = 100) -> Dict[str, Any]:
    """Simulate simple document-count filtering strategy."""

    query = f"""
    MATCH (t:Technology)
    OPTIONAL MATCH (t)-[:MENTIONED_IN]->(d:Document)
    WITH t, count(DISTINCT d) as doc_count
    WHERE doc_count >= {min_docs}
    RETURN t.id as tech_id, doc_count
    ORDER BY doc_count DESC
    LIMIT {limit}
    """

    techs = await client.run_query(query)

    doc_counts = [t['doc_count'] for t in techs]
    avg_docs = sum(doc_counts) / len(doc_counts) if doc_counts else 0

    return {
        "strategy": "Document Count Filter",
        "min_threshold": min_docs,
        "total_count": len(techs),
        "avg_doc_count": avg_docs,
        "min_doc_count": min(doc_counts) if doc_counts else 0,
        "max_doc_count": max(doc_counts) if doc_counts else 0,
        "tech_ids": [t['tech_id'] for t in techs]
    }


def print_results(dist_data: Dict[str, Any], strategy_a: Dict[str, Any], strategy_b: Dict[str, Any]):
    """Print formatted analysis results."""

    print("\n" + "="*80)
    print("DOCUMENT COUNT DISTRIBUTION ANALYSIS")
    print("="*80)

    # Section 1: Total and Distribution
    print(f"\n1. TOTAL TECHNOLOGY COUNT")
    print("-" * 80)
    print(f"Total technologies in graph: {dist_data['total']}")

    print(f"\n2. DOCUMENT COUNT DISTRIBUTION")
    print("-" * 80)
    print(f"{'Document Range':<20} {'Tech Count':<15} {'Percentage':<15}")
    print("-" * 50)
    for row in dist_data['distribution']:
        pct = (row['tech_count'] / dist_data['total'] * 100) if dist_data['total'] > 0 else 0
        print(f"{row['doc_range']:<20} {row['tech_count']:<15} {pct:>6.1f}%")

    # Section 2: Thresholds
    print(f"\n3. TECHNOLOGIES ABOVE DIFFERENT THRESHOLDS")
    print("-" * 80)
    thresholds = dist_data['thresholds']
    print(f"min_document_count >= 5:  {thresholds.get('min_5', 0):>4} technologies ({thresholds.get('min_5', 0)/dist_data['total']*100:.1f}%)")
    print(f"min_document_count >= 10: {thresholds.get('min_10', 0):>4} technologies ({thresholds.get('min_10', 0)/dist_data['total']*100:.1f}%)")
    print(f"min_document_count >= 15: {thresholds.get('min_15', 0):>4} technologies ({thresholds.get('min_15', 0)/dist_data['total']*100:.1f}%)")
    print(f"min_document_count >= 20: {thresholds.get('min_20', 0):>4} technologies ({thresholds.get('min_20', 0)/dist_data['total']*100:.1f}%)")
    print(f"min_document_count >= 25: {thresholds.get('min_25', 0):>4} technologies ({thresholds.get('min_25', 0)/dist_data['total']*100:.1f}%)")
    print(f"min_document_count >= 30: {thresholds.get('min_30', 0):>4} technologies ({thresholds.get('min_30', 0)/dist_data['total']*100:.1f}%)")

    # Section 3: Top Technologies
    print(f"\n4. TOP 30 TECHNOLOGIES BY DOCUMENT COUNT")
    print("-" * 80)
    print(f"{'Tech ID':<40} {'Docs':<10}")
    print("-" * 50)
    for tech in dist_data['top_techs'][:30]:
        print(f"{tech['tech_id']:<40} {tech['doc_count']:<10}")

    # Section 4: Strategy Comparison
    print(f"\n\n" + "="*80)
    print("STRATEGY COMPARISON")
    print("="*80)

    print(f"\nSTRATEGY A: {strategy_a['strategy']}")
    print("-" * 80)
    print(f"Sample size: {strategy_a['total_sampled']} -> Final: {strategy_a['final_count']}")
    print(f"Community breakdown:")
    print(f"  Early-stage: {strategy_a['breakdown']['early']}")
    print(f"  Mid-stage: {strategy_a['breakdown']['mid']}")
    print(f"  Late-stage: {strategy_a['breakdown']['late']}")
    print(f"  Hype-stage: {strategy_a['breakdown']['hype']}")
    print(f"Evidence quality:")
    print(f"  Average doc_count: {strategy_a['avg_doc_count']:.1f}")
    print(f"  Range: {strategy_a['min_doc_count']}-{strategy_a['max_doc_count']} documents")
    print(f"\nSample tech IDs: {strategy_a['tech_ids'][:10]}...")

    print(f"\n\nSTRATEGY B: {strategy_b['strategy']}")
    print("-" * 80)
    print(f"Min threshold: {strategy_b['min_threshold']} documents")
    print(f"Final count: {strategy_b['total_count']}")
    print(f"Evidence quality:")
    print(f"  Average doc_count: {strategy_b['avg_doc_count']:.1f}")
    print(f"  Range: {strategy_b['min_doc_count']}-{strategy_b['max_doc_count']} documents")
    print(f"\nSample tech IDs: {strategy_b['tech_ids'][:10]}...")

    # Section 5: Recommendation
    print(f"\n\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)

    # Decision logic
    a_count = strategy_a['final_count']
    b_count = strategy_b['total_count']
    a_avg = strategy_a['avg_doc_count']
    b_avg = strategy_b['avg_doc_count']

    print(f"\nAnalysis:")
    print(f"  - Strategy A yields {a_count} technologies with avg {a_avg:.1f} docs")
    print(f"  - Strategy B yields {b_count} technologies with avg {b_avg:.1f} docs")

    if b_count < 20:
        print(f"\n[!] CRITICAL: min_document_count=15 yields only {b_count} technologies!")
        print(f"    This is too few for meaningful hype cycle analysis.")
        print(f"\n[RECOMMENDATION] Use Strategy A (Community Sampling)")
        print(f"    - Maintains diversity across maturity stages")
        print(f"    - Yields {a_count} technologies (sufficient for analysis)")
        print(f"    - Configuration: sample_size=150 -> final_limit=100")
    elif a_count >= 80 and b_count >= 50:
        print(f"\n[OK] Both strategies yield sufficient data!")
        if a_avg > b_avg * 1.2:
            print(f"\n    Strategy A has 20%+ higher evidence quality ({a_avg:.1f} vs {b_avg:.1f})")
            print(f"    RECOMMENDATION: Use Strategy A (Community Sampling)")
        elif b_avg > a_avg * 1.2:
            print(f"\n    Strategy B has 20%+ higher evidence quality ({b_avg:.1f} vs {a_avg:.1f})")
            print(f"    RECOMMENDATION: Use Strategy B (Document Filter)")
        else:
            print(f"\n    Evidence quality is similar ({a_avg:.1f} vs {b_avg:.1f})")
            print(f"    RECOMMENDATION: Use Strategy A (Community Sampling)")
            print(f"    - Rationale: Maintains maturity stage diversity")
    else:
        print(f"\n[!] Strategy B yields {b_count} technologies (marginal)")
        print(f"\n[RECOMMENDATION] Use Strategy A (Community Sampling)")
        print(f"    - Better balance across lifecycle stages")
        print(f"    - Yields {a_count} technologies")


async def main():
    """Run complete analysis."""
    client = Neo4jClient()
    await client.connect()

    try:
        print("\n[1/3] Querying document distribution...")
        dist_data = await query_document_distribution(client)

        print("\n[2/3] Simulating community sampling (150 -> 100)...")
        strategy_a = await simulate_community_sampling(client, sample_size=150, final_limit=100)

        print("\n[3/3] Simulating document filtering (min_doc=15 -> 100)...")
        strategy_b = await simulate_document_filtering(client, min_docs=15, limit=100)

        # Print comprehensive results
        print_results(dist_data, strategy_a, strategy_b)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
