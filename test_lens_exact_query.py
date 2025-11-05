"""
Test the EXACT query structure from lens_patents.py downloader
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

# Setup
base_url = "https://api.lens.org/patent/search"
headers = {
    'Authorization': f'Bearer {api_token}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'User-Agent': 'Strategic Intelligence Harvester/1.0'
}

# Test with EXACT query from lens_patents.py
end_date = datetime.now()
start_date = end_date - timedelta(days=180)

assignee = "Joby Aero, Inc."

query = {
    "query": {
        "bool": {
            "must": [
                {
                    "match": {
                        "applicant.name": assignee
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
    "include": [
        "lens_id",
        "doc_number",
        "jurisdiction",
        "kind",
        "date_published",
        "biblio.invention_title",
        "abstract",
        "biblio.parties.applicants",
        "biblio.parties.inventors",
        "biblio.application_reference.date",
        "legal_status.grant_date",
        "legal_status.granted",
        "legal_status.patent_status",
        "biblio.classifications_cpc",
        "biblio.references_cited"
    ],
    "size": 100,
    "scroll": "1m"
}

print("="*60)
print(f"Testing query for: {assignee}")
print(f"Date range: {start_date.date()} to {end_date.date()}")
print("="*60)

print(f"\nQuery structure:")
print(json.dumps(query, indent=2))

print(f"\nSending request...")
response = requests.post(base_url, headers=headers, json=query, timeout=30)

print(f"\nStatus Code: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"\nSUCCESS!")
    print(f"Total results: {data.get('total', 0)}")
    print(f"Results in response: {len(data.get('data', []))}")
    print(f"Scroll ID: {data.get('scroll_id', 'N/A')[:50]}...")

    if data.get('data'):
        print("\nFirst patent:")
        first_patent = data['data'][0]
        print(f"  Lens ID: {first_patent.get('lens_id')}")
        print(f"  Doc Number: {first_patent.get('doc_number')}")
        title = first_patent.get('biblio', {}).get('invention_title', [])
        if title:
            print(f"  Title: {title[0].get('text', '')[:80]}")
else:
    print(f"\nERROR!")
    try:
        error_data = response.json()
        print(f"Error details: {json.dumps(error_data, indent=2)}")
    except:
        print(f"Error response: {response.text}")

print("\n" + "="*60)
