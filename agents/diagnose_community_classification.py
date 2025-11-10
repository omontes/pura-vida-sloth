"""
Diagnose Community Classification Thresholds

Run this to see how communities are being classified and test different thresholds.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.neo4j_client import Neo4jClient
from agents.shared.queries import community_queries
from agents.agent_01_tech_discovery.agent import classify_communities_by_maturity


async def diagnose_classification():
    """Check community classification with current and alternative thresholds."""
    print("\n" + "="*80)
    print("COMMUNITY CLASSIFICATION DIAGNOSTICS")
    print("="*80)

    client = Neo4jClient()
    await client.connect()

    try:
        # Get all communities (try both v0 and v1)
        communities_v0 = await community_queries.get_all_communities_for_version(
            client.driver,
            version=0,
            min_member_count=5
        )
        communities_v1 = await community_queries.get_all_communities_for_version(
            client.driver,
            version=1,
            min_member_count=5
        )

        # Use whichever version has communities
        if len(communities_v1) > 0:
            communities = communities_v1
            version_used = 1
        else:
            communities = communities_v0
            version_used = 0

        print(f"\n[INFO] Found {len(communities)} communities (version=v{version_used}, min_members=5)")

        # Classify with current thresholds
        print("\n" + "-"*80)
        print("CURRENT THRESHOLDS:")
        print("  Early-stage: patent:news > 2 AND contracts < 5")
        print("  Hype-stage: news:patent > 2 AND contracts < 5")
        print("  Late-stage: contracts > 10 AND patents > 5")
        print("  Mid-stage: Everything else")
        print("-"*80)

        early, mid, late, hype = classify_communities_by_maturity(communities)

        print(f"\n[CURRENT CLASSIFICATION]")
        print(f"  Early-stage (Innovation Trigger): {len(early)} communities")
        print(f"  Mid-stage (Slope): {len(mid)} communities")
        print(f"  Late-stage (Plateau): {len(late)} communities")
        print(f"  Hype-stage (Peak): {len(hype)} communities")

        # Show sample communities from each bucket
        print("\n[SAMPLE COMMUNITIES]")

        if early:
            print(f"\nEarly-stage sample (top 3):")
            for comm in early[:3]:
                doc_dist = comm.get('doc_type_distribution', {})
                patents = doc_dist.get('patent', 0)
                news = doc_dist.get('news', 0)
                contracts = doc_dist.get('government_contract', 0)
                print(f"  {comm['id']}: patents={patents}, news={news}, contracts={contracts}, ratio={patents/(news+1):.2f}")

        if mid:
            print(f"\nMid-stage sample (top 3):")
            for comm in mid[:3]:
                doc_dist = comm.get('doc_type_distribution', {})
                patents = doc_dist.get('patent', 0)
                news = doc_dist.get('news', 0)
                contracts = doc_dist.get('government_contract', 0)
                print(f"  {comm['id']}: patents={patents}, news={news}, contracts={contracts}, ratio={patents/(news+1):.2f}")

        if late:
            print(f"\nLate-stage sample (top 3):")
            for comm in late[:3]:
                doc_dist = comm.get('doc_type_distribution', {})
                patents = doc_dist.get('patent', 0)
                news = doc_dist.get('news', 0)
                contracts = doc_dist.get('government_contract', 0)
                print(f"  {comm['id']}: patents={patents}, news={news}, contracts={contracts}, contracts_count={contracts}")

        if hype:
            print(f"\nHype-stage sample (top 3):")
            for comm in hype[:3]:
                doc_dist = comm.get('doc_type_distribution', {})
                patents = doc_dist.get('patent', 0)
                news = doc_dist.get('news', 0)
                contracts = doc_dist.get('government_contract', 0)
                print(f"  {comm['id']}: patents={patents}, news={news}, contracts={contracts}, ratio={news/(patents+1):.2f}")

        # Test alternative thresholds
        print("\n" + "="*80)
        print("TESTING ALTERNATIVE THRESHOLDS")
        print("="*80)

        # More relaxed thresholds
        print("\n[RELAXED THRESHOLDS]")
        print("  Early-stage: patent:news > 1.5 AND contracts < 8")
        print("  Hype-stage: news:patent > 1.5 AND contracts < 8")
        print("  Late-stage: contracts > 5 AND patents > 3")
        print("  Mid-stage: Everything else")

        early_alt = []
        mid_alt = []
        late_alt = []
        hype_alt = []

        for comm in communities:
            doc_dist = comm.get('doc_type_distribution', {})
            if isinstance(doc_dist, str):
                import json
                try:
                    doc_dist = json.loads(doc_dist)
                except:
                    doc_dist = {}

            patents = doc_dist.get('patent', 0)
            news = doc_dist.get('news', 0)
            contracts = doc_dist.get('government_contract', 0)

            if patents == 0 and news == 0:
                continue

            patent_news_ratio = patents / (news + 1)
            news_patent_ratio = news / (patents + 1)

            # RELAXED thresholds
            if patent_news_ratio > 1.5 and contracts < 8:
                early_alt.append(comm)
            elif news_patent_ratio > 1.5 and contracts < 8:
                hype_alt.append(comm)
            elif contracts > 5 and patents > 3:
                late_alt.append(comm)
            else:
                mid_alt.append(comm)

        print(f"\n[RELAXED CLASSIFICATION]")
        print(f"  Early-stage: {len(early_alt)} communities ({len(early_alt) - len(early):+d})")
        print(f"  Mid-stage: {len(mid_alt)} communities ({len(mid_alt) - len(mid):+d})")
        print(f"  Late-stage: {len(late_alt)} communities ({len(late_alt) - len(late):+d})")
        print(f"  Hype-stage: {len(hype_alt)} communities ({len(hype_alt) - len(hype):+d})")

        # Show distribution of doc types across all communities
        print("\n" + "="*80)
        print("DOCUMENT TYPE DISTRIBUTION ACROSS ALL COMMUNITIES")
        print("="*80)

        total_patents = 0
        total_news = 0
        total_contracts = 0
        total_papers = 0

        for comm in communities:
            doc_dist = comm.get('doc_type_distribution', {})
            if isinstance(doc_dist, str):
                import json
                try:
                    doc_dist = json.loads(doc_dist)
                except:
                    doc_dist = {}

            total_patents += doc_dist.get('patent', 0)
            total_news += doc_dist.get('news', 0)
            total_contracts += doc_dist.get('government_contract', 0)
            total_papers += doc_dist.get('technical_paper', 0)

        print(f"\nTotal across all {len(communities)} communities:")
        print(f"  Patents: {total_patents}")
        print(f"  News: {total_news}")
        print(f"  Papers: {total_papers}")
        print(f"  Contracts: {total_contracts}")
        print(f"\nRatios:")
        print(f"  Patent:News = {total_patents / (total_news + 1):.2f}")
        print(f"  News:Patent = {total_news / (total_patents + 1):.2f}")

        print("\n" + "="*80)
        print("RECOMMENDATIONS")
        print("="*80)

        if len(early) == 0 and len(hype) == 0 and len(late) == 0:
            print("\n[WARNING] PROBLEM: All communities classified as mid-stage!")
            print("\n[SOLUTION] Thresholds are TOO STRICT. Consider:")
            print("   - Lower patent:news ratio from 2.0 to 1.5")
            print("   - Increase contract threshold from <5 to <8 for early/hype")
            print("   - Lower late-stage threshold from contracts>10 to contracts>5")
        elif len(early) < 3 or len(hype) < 3:
            print("\n[WARNING] PROBLEM: Very few early/hype communities!")
            print("\n[SOLUTION] Slightly relax thresholds to improve diversity")
        else:
            print("\n[SUCCESS] Classification looks reasonable!")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(diagnose_classification())
