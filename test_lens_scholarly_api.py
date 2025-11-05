"""
Test Lens Scholarly Works API access
Check if current LENS_API_TOKEN works for scholarly endpoint
"""
import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API token (same token as patents)
api_token = os.getenv('LENS_API_TOKEN')
print(f"API Token: {api_token[:20]}..." if api_token else "NO TOKEN FOUND")

# Lens Scholarly Works endpoint
scholarly_url = "https://api.lens.org/scholar/search"

headers = {
    'Authorization': f'Bearer {api_token}',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

# Test query - search for eVTOL research papers
end_date = datetime.now()
start_date = end_date - timedelta(days=180)

query = {
    "query": {
        "bool": {
            "must": [
                {
                    "match": {
                        "title": "electric vertical takeoff"
                    }
                }
            ]
        }
    },
    "size": 5
}

print("=" * 60)
print("TEST: Lens Scholarly Works API Access")
print("=" * 60)
print(f"\nEndpoint: {scholarly_url}")
print(f"Query: Searching for 'electric vertical takeoff' in titles")
print(f"\nSending request...")

try:
    response = requests.post(scholarly_url, headers=headers, json=query, timeout=30)

    print(f"\nStatus Code: {response.status_code}")

    if response.status_code == 200:
        print("\n[SUCCESS] Token works for scholarly works API")

        data = response.json()
        print(f"\nTotal results: {data.get('total', 0)}")
        print(f"Results in response: {len(data.get('data', []))}")

        if data.get('data'):
            print("\n" + "=" * 60)
            print("First scholarly work:")
            print("=" * 60)
            first_work = data['data'][0]

            print(f"\nLens ID: {first_work.get('lens_id')}")
            print(f"Title: {first_work.get('title', 'N/A')}")
            print(f"Year: {first_work.get('year_published', 'N/A')}")

            # Check for funding data
            funding = first_work.get('funding', [])
            if funding:
                print(f"\nFunding: {len(funding)} grants found!")
                for grant in funding[:2]:
                    print(f"  - Organization: {grant.get('organisation', 'N/A')}")
                    print(f"    Grant ID: {grant.get('funding_id', 'N/A')}")
            else:
                print("\nFunding: No funding data in this record")

            # Check for authors
            authors = first_work.get('authors', [])
            if authors:
                print(f"\nAuthors: {len(authors)} authors")
                for author in authors[:3]:
                    print(f"  - {author.get('display_name', 'N/A')}")

            # Check for field of study
            fields = first_work.get('fields_of_study', [])
            if fields:
                print(f"\nFields of Study: {', '.join(fields[:5])}")

            # Check citation data
            cited_by = first_work.get('scholarly_citations_count', 0)
            patent_cites = first_work.get('patent_citations_count', 0)
            print(f"\nCitations:")
            print(f"  - Scholarly: {cited_by}")
            print(f"  - Patents: {patent_cites}")

            print("\n" + "=" * 60)
            print("Available fields in response:")
            print("=" * 60)
            print(", ".join(sorted(first_work.keys())))

    elif response.status_code == 401:
        print("\n[ERROR] AUTHENTICATION FAILED")
        print("Token does not have access to scholarly works API")
        print("\nAction required:")
        print("1. Go to: https://www.lens.org/lens/user/subscriptions")
        print("2. Request access to 'Scholarly Works API'")
        print("3. Generate new token with scholarly access")

    elif response.status_code == 403:
        print("\n[ERROR] FORBIDDEN")
        print("Token does not have permission for scholarly works")
        print("\nYour token may only have patent access")
        print("Request scholarly works access at: https://www.lens.org/lens/user/subscriptions")

    else:
        print(f"\n[ERROR] HTTP {response.status_code}")
        try:
            error_data = response.json()
            print(f"Error details: {json.dumps(error_data, indent=2)}")
        except:
            print(f"Error response: {response.text}")

except Exception as e:
    print(f"\n[EXCEPTION] {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
