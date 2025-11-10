"""
Government Contract Metadata Extractors
Author: Pura Vida Sloth Intelligence System

Helper functions for loading and extracting USASpending.gov contract data.
"""

import json
from typing import List, Dict, Any
from datetime import datetime


def load_contracts_from_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Load government contracts from JSON file.

    Args:
        file_path: Path to JSON file containing contract data

    Returns:
        List of contract dictionaries
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle both single object and array formats
    return data if isinstance(data, list) else [data]


def extract_contract_metadata(contract: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and normalize contract metadata from USASpending.gov format.

    Args:
        contract: Raw contract dictionary from USASpending.gov API

    Returns:
        Normalized metadata dictionary with all required fields
    """
    return {
        'award_id': contract.get('Award ID'),
        'award_type': contract.get('Award Type'),
        'recipient_name': contract.get('Recipient Name'),
        'award_amount': float(contract.get('Award Amount', 0)),
        'start_date': contract.get('Start Date'),
        'end_date': contract.get('End Date'),
        'description': contract.get('Description', ''),
        'awarding_agency': contract.get('Awarding Agency'),
        'awarding_sub_agency': contract.get('Awarding Sub-Agency'),
        'search_term': contract.get('Search Term'),
        'url': contract.get('URL')
    }


def calculate_contract_duration(start_date: str, end_date: str) -> int:
    """
    Calculate contract duration in days.

    Args:
        start_date: Contract start date (YYYY-MM-DD)
        end_date: Contract end date (YYYY-MM-DD)

    Returns:
        Duration in days
    """
    if not start_date or not end_date:
        return 0

    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        return (end - start).days
    except (ValueError, TypeError):
        return 0


def categorize_contract_size(award_amount: float) -> str:
    """
    Categorize contract by size.

    Args:
        award_amount: Contract value in USD

    Returns:
        Category: "small", "medium", or "large"
    """
    if award_amount < 100000:
        return "small"
    elif award_amount < 1000000:
        return "medium"
    else:
        return "large"


def derive_agency_type(awarding_agency: str) -> str:
    """
    Derive agency type from name.

    Args:
        awarding_agency: Federal agency name

    Returns:
        Agency type: "defense", "civil", "regulatory", or "unknown"
    """
    if not awarding_agency:
        return "unknown"

    agency_lower = awarding_agency.lower()

    if any(keyword in agency_lower for keyword in ["defense", "air force", "navy", "army", "military", "marines"]):
        return "defense"
    elif any(keyword in agency_lower for keyword in ["transportation", "faa", "federal aviation"]):
        return "regulatory"
    else:
        return "civil"


def build_document_id(award_id: str) -> str:
    """
    Generate standardized document ID for government contract.

    Args:
        award_id: USASpending.gov award identifier

    Returns:
        Document ID in format "gov_contract_{sanitized_award_id}"
    """
    # Sanitize award ID for document ID (remove special chars)
    sanitized = award_id.replace('/', '_').replace('-', '_').replace(' ', '_')

    return f"gov_contract_{sanitized}"


def build_contract_url(award_id: str) -> str:
    """
    Build USASpending.gov contract URL.

    Args:
        award_id: USASpending.gov award identifier

    Returns:
        Full USASpending.gov URL
    """
    return f"https://www.usaspending.gov/award/{award_id}"
