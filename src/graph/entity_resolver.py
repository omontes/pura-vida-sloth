"""
Entity resolver with exact keyword matching.

Resolves entity mentions to canonical IDs using catalog lookups.
This is v1 (exact matching) - future versions will use embeddings + ChromaDB.
"""

import json
import logging
from pathlib import Path
from typing import Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class EntityResolver:
    """
    Entity resolver using exact keyword matching against catalogs.

    Features:
    - Case-insensitive exact matching
    - Matches on canonical name and all aliases
    - Logs unmatched entities for catalog expansion
    - Thread-safe (uses immutable lookups after init)

    Future improvements (v2):
    - Fuzzy matching with Levenshtein distance
    - Embedding-based similarity search (ChromaDB)
    - Dynamic catalog expansion
    """

    def __init__(
        self,
        companies_catalog_path: str = "data/catalog/companies.json",
        technologies_catalog_path: str = "data/catalog/technologies.json",
    ):
        """
        Initialize entity resolver with catalog files.

        Args:
            companies_catalog_path: Path to companies catalog JSON
            technologies_catalog_path: Path to technologies catalog JSON
        """
        self.companies_catalog_path = Path(companies_catalog_path)
        self.technologies_catalog_path = Path(technologies_catalog_path)

        # Lookup dictionaries (lowercase name -> canonical ID)
        self.company_lookup: dict[str, str] = {}
        self.technology_lookup: dict[str, str] = {}

        # Track unmatched entities for catalog expansion
        self.unmatched_companies: defaultdict[str, int] = defaultdict(int)
        self.unmatched_technologies: defaultdict[str, int] = defaultdict(int)

        # Load catalogs
        self._load_catalogs()

    def _load_catalogs(self) -> None:
        """Load and index company and technology catalogs."""

        # Load companies
        if self.companies_catalog_path.exists():
            with open(self.companies_catalog_path, "r") as f:
                catalog_data = json.load(f)

            # Handle nested structure (catalog files have "companies" key)
            companies = catalog_data.get("companies", catalog_data) if isinstance(catalog_data, dict) else catalog_data

            for company in companies:
                company_id = company["id"]

                # Add canonical name
                self.company_lookup[company["name"].lower()] = company_id

                # Add all aliases
                for alias in company.get("aliases", []):
                    self.company_lookup[alias.lower()] = company_id

            logger.info(f"Loaded {len(companies)} companies with {len(self.company_lookup)} lookup keys")
        else:
            logger.warning(f"Companies catalog not found: {self.companies_catalog_path}")

        # Load technologies
        if self.technologies_catalog_path.exists():
            with open(self.technologies_catalog_path, "r") as f:
                catalog_data = json.load(f)

            # Handle nested structure (catalog files have "technologies" key)
            technologies = catalog_data.get("technologies", catalog_data) if isinstance(catalog_data, dict) else catalog_data

            for tech in technologies:
                tech_id = tech["id"]

                # Add canonical name
                self.technology_lookup[tech["name"].lower()] = tech_id

                # Add all aliases
                for alias in tech.get("aliases", []):
                    self.technology_lookup[alias.lower()] = tech_id

            logger.info(
                f"Loaded {len(technologies)} technologies with {len(self.technology_lookup)} lookup keys"
            )
        else:
            logger.warning(f"Technologies catalog not found: {self.technologies_catalog_path}")

    def resolve_company(self, mention: str) -> Optional[str]:
        """
        Resolve company mention to canonical ID.

        Args:
            mention: Company name as mentioned in document

        Returns:
            Canonical company ID or None if not found
        """
        mention_lower = mention.lower().strip()

        if mention_lower in self.company_lookup:
            return self.company_lookup[mention_lower]

        # Track unmatched
        self.unmatched_companies[mention] += 1
        return None

    def resolve_technology(self, mention: str) -> Optional[str]:
        """
        Resolve technology mention to canonical ID.

        Args:
            mention: Technology name as mentioned in document

        Returns:
            Canonical technology ID or None if not found
        """
        mention_lower = mention.lower().strip()

        if mention_lower in self.technology_lookup:
            return self.technology_lookup[mention_lower]

        # Track unmatched
        self.unmatched_technologies[mention] += 1
        return None

    def get_unmatched_stats(self) -> dict[str, dict[str, int]]:
        """
        Get statistics on unmatched entities.

        Returns:
            Dictionary with unmatched companies and technologies
        """
        return {
            "companies": dict(self.unmatched_companies),
            "technologies": dict(self.unmatched_technologies),
        }

    def log_unmatched_summary(self) -> None:
        """Log summary of unmatched entities for catalog expansion."""
        if self.unmatched_companies:
            logger.warning(
                f"Unmatched companies: {len(self.unmatched_companies)} unique mentions, "
                f"{sum(self.unmatched_companies.values())} total occurrences"
            )
            # Log top 10 unmatched
            top_unmatched = sorted(
                self.unmatched_companies.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10]
            for mention, count in top_unmatched:
                logger.warning(f"  - '{mention}': {count} occurrences")

        if self.unmatched_technologies:
            logger.warning(
                f"Unmatched technologies: {len(self.unmatched_technologies)} unique mentions, "
                f"{sum(self.unmatched_technologies.values())} total occurrences"
            )
            # Log top 10 unmatched
            top_unmatched = sorted(
                self.unmatched_technologies.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10]
            for mention, count in top_unmatched:
                logger.warning(f"  - '{mention}': {count} occurrences")

    def get_company_details(self, company_id: str) -> Optional[dict]:
        """
        Get full company details from catalog.

        Args:
            company_id: Canonical company ID

        Returns:
            Company details dictionary or None
        """
        if not self.companies_catalog_path.exists():
            return None

        with open(self.companies_catalog_path, "r") as f:
            catalog_data = json.load(f)

        companies = catalog_data.get("companies", catalog_data) if isinstance(catalog_data, dict) else catalog_data

        for company in companies:
            if company["id"] == company_id:
                return company

        return None

    def get_technology_details(self, tech_id: str) -> Optional[dict]:
        """
        Get full technology details from catalog.

        Args:
            tech_id: Canonical technology ID

        Returns:
            Technology details dictionary or None
        """
        if not self.technologies_catalog_path.exists():
            return None

        with open(self.technologies_catalog_path, "r") as f:
            catalog_data = json.load(f)

        technologies = catalog_data.get("technologies", catalog_data) if isinstance(catalog_data, dict) else catalog_data

        for tech in technologies:
            if tech["id"] == tech_id:
                return tech

        return None

    def get_all_companies(self) -> list[dict]:
        """Get all companies from catalog."""
        if not self.companies_catalog_path.exists():
            return []

        with open(self.companies_catalog_path, "r") as f:
            catalog_data = json.load(f)

        return catalog_data.get("companies", catalog_data) if isinstance(catalog_data, dict) else catalog_data

    def get_all_technologies(self) -> list[dict]:
        """Get all technologies from catalog."""
        if not self.technologies_catalog_path.exists():
            return []

        with open(self.technologies_catalog_path, "r") as f:
            catalog_data = json.load(f)

        return catalog_data.get("technologies", catalog_data) if isinstance(catalog_data, dict) else catalog_data
