"""
GitHub Repository Metadata Extractors
Author: Pura Vida Sloth Intelligence System

Helper functions for loading and extracting GitHub repository data.
"""

import json
from typing import List, Dict, Any


def load_repositories_from_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Load GitHub repositories from JSON file.

    Args:
        file_path: Path to JSON file containing repository data

    Returns:
        List of repository dictionaries
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle both single object and array formats
    return data if isinstance(data, list) else [data]


def extract_repository_metadata(repo: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and normalize GitHub repository metadata.

    Args:
        repo: Raw repository dictionary from GitHub API

    Returns:
        Normalized metadata dictionary with all required fields
    """
    # Handle metrics nesting (from github_tracker.py)
    metrics = repo.get('metrics', {})

    return {
        'github_id': repo.get('id'),
        'repo_name': repo.get('name'),  # "owner/repo" format
        'owner': repo.get('owner'),
        'description': repo.get('description', ''),
        'url': repo.get('url'),
        'created_at': repo.get('created_at'),
        'updated_at': repo.get('updated_at'),
        'last_pushed_at': repo.get('pushed_at'),
        'language': repo.get('language'),
        'stars': repo.get('stars', 0),
        'forks': repo.get('forks', 0),
        'watchers': repo.get('watchers', 0),
        'open_issues': repo.get('open_issues', 0),
        'size': repo.get('size', 0),
        'topics': repo.get('topics', []),
        'license': repo.get('license'),
        'contributor_count': metrics.get('contributor_count', 0),
        'days_since_last_update': metrics.get('days_since_last_update', 0),
        'is_active': metrics.get('is_active', False),
        'popularity_score': metrics.get('popularity_score', 0.0)
    }


def build_document_id(owner: str, repo_name: str) -> str:
    """
    Generate standardized document ID for GitHub repository.

    Args:
        owner: Repository owner
        repo_name: Repository name (can be "owner/repo" format)

    Returns:
        Document ID in format "github_{owner}_{repo}"
    """
    # Extract repo name if in "owner/repo" format
    if '/' in repo_name:
        repo_name = repo_name.split('/')[-1]

    # Sanitize for document ID (remove special chars)
    owner_clean = owner.replace('-', '_').replace('.', '_')
    repo_clean = repo_name.replace('-', '_').replace('.', '_')

    return f"github_{owner_clean}_{repo_clean}"


def format_github_url(owner: str, repo_name: str) -> str:
    """
    Build GitHub repository URL.

    Args:
        owner: Repository owner
        repo_name: Repository name (can be "owner/repo" format)

    Returns:
        Full GitHub URL
    """
    # Extract repo name if in "owner/repo" format
    if '/' in repo_name:
        repo_name = repo_name.split('/')[-1]

    return f"https://github.com/{owner}/{repo_name}"
