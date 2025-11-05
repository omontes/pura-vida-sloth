"""
Quick test script to debug Lens Patent API requests
"""
import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API token
api_token = os.getenv('LENS_API_TOKEN')
print(f"API Token: {api_token[:20]}..." if api_token else "NO TOKEN FOUND")

# Setup
base_url = "https://api.lens.org/patent/search"
headers = {
    'Authorization': f'Bearer {api_token}',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

# Test 1: Simple query without date filter
print("\n" + "="*60)
print("TEST 1: Simple company search (Boeing)")
print("="*60)

query1 = {
    "query": {
        "match": {
            "applicant.name": "Boeing"
        }
    },
    "size": 5
}

print(f"\nQuery: {json.dumps(query1, indent=2)}")

response1 = requests.post(base_url, headers=headers, json=query1)
print(f"\nStatus Code: {response1.status_code}")
print(f"Response: {response1.text[:500]}")

# Test 2: Query with date range (last 180 days)
print("\n" + "="*60)
print("TEST 2: Company search with date range (Boeing, last 180 days)")
print("="*60)

end_date = datetime.now()
start_date = end_date - timedelta(days=180)

query2 = {
    "query": {
        "bool": {
            "must": [
                {
                    "match": {
                        "applicant.name": "Boeing"
                    }
                },
                {
                    "range": {
                        "date_published": {
                            "gte": start_date.strftime("%Y-%m-%d"),
                            "lte": end_date.strftime("%Y-%m-%d")
                        }
                    }
                }
            ]
        }
    },
    "size": 5
}

print(f"\nQuery: {json.dumps(query2, indent=2)}")

response2 = requests.post(base_url, headers=headers, json=query2)
print(f"\nStatus Code: {response2.status_code}")
print(f"Response: {response2.text[:500]}")

if response2.status_code == 200:
    data = response2.json()
    print(f"\nTotal results: {data.get('total', 0)}")
    print(f"Results in response: {len(data.get('data', []))}")

    if data.get('data'):
        print("\nFirst patent:")
        first_patent = data['data'][0]
        print(f"  Lens ID: {first_patent.get('lens_id')}")
        print(f"  Doc Number: {first_patent.get('doc_number')}")
        title = first_patent.get('biblio', {}).get('invention_title', [])
        if title:
            print(f"  Title: {title[0].get('text', '')[:80]}")

print("\n" + "="*60)
print("Tests complete!")
print("="*60)
