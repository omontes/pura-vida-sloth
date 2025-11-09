"""
Entity Resolution Configuration Module
Loads industry-agnostic configuration for technology normalization pipeline
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class EntityResolutionConfig:
    """Configuration loader for entity resolution pipeline."""

    def __init__(self, industry: str = "eVTOL"):
        """
        Initialize configuration for a specific industry.

        Args:
            industry: Industry name (e.g., "eVTOL")
        """
        self.industry = industry
        self.config = self._load_industry_config()

    def _load_industry_config(self) -> Dict[str, Any]:
        """Load industry configuration from JSON file."""
        config_path = Path(f"configs/{self.industry.lower()}_config.json")

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @property
    def data_dir(self) -> Path:
        """Get data directory for this industry."""
        base_dir = Path(self.config.get("output_config", {}).get("base_dir", "./data"))
        industry_folder = self.config.get("output_config", {}).get("industry_folder", self.industry)
        return base_dir / industry_folder

    @property
    def technologies_input_file(self) -> Path:
        """Get path to technologies_patents_papers.json input file."""
        return self.data_dir / "technologies" / "technologies_patents_papers.json"

    @property
    def existing_catalog_file(self) -> Path:
        """Get path to existing canonical technologies catalog."""
        return self.data_dir / "technologies" / "technologies.json"

    @property
    def output_dir(self) -> Path:
        """Get output directory for entity resolution results."""
        return Path("graph/entity_resolution/output")

    @property
    def chromadb_dir(self) -> Path:
        """Get ChromaDB persistence directory."""
        return Path("graph/entity_resolution/chromadb")

    def get_keywords(self, category: Optional[str] = None) -> list:
        """
        Get keywords for the industry.

        Args:
            category: Specific category (e.g., 'core', 'technology', 'scholarly_core')
                     If None, returns all keywords combined

        Returns:
            List of keywords
        """
        keywords_config = self.config.get("keywords", {})

        if category:
            return keywords_config.get(category, [])

        # Return all keywords combined (flattened)
        all_keywords = []
        for keyword_list in keywords_config.values():
            all_keywords.extend(keyword_list)
        return list(set(all_keywords))  # Remove duplicates

    def get_companies(self, status: Optional[str] = None) -> Dict[str, str]:
        """
        Get companies for the industry.

        Args:
            status: Company status ('public', 'private', 'public_inactive')
                   If None, returns all companies

        Returns:
            Dictionary of ticker/ID -> company name
        """
        companies_config = self.config.get("companies", {})

        if status:
            return companies_config.get(status, {})

        # Return all companies combined
        all_companies = {}
        for company_dict in companies_config.values():
            all_companies.update(company_dict)
        return all_companies


# Pipeline-specific configuration
PIPELINE_CONFIG = {
    # Similarity thresholds
    "similarity_threshold": 0.85,  # Auto-accept threshold (balanced)
    "fuzzy_weight": 0.4,  # Weight for fuzzy string matching
    "semantic_weight": 0.6,  # Weight for semantic embedding similarity

    # Clustering parameters
    "cluster_min_similarity": 0.75,  # Minimum similarity to form cluster edge (lowered to capture more variants)
    "cluster_algorithm": "louvain",  # Community detection algorithm

    # Phase 5.5: Canonical Name Clustering
    "canonical_cluster_threshold": 0.75,  # Threshold for canonical name clustering
    "canonical_fuzzy_weight": 0.30,  # Lower weight for fuzzy (canonical names already clean)
    "canonical_semantic_weight": 0.70,  # Higher weight for semantic (meaning matters more)
    "use_domain_filtering": True,  # Check domain compatibility before merging
    "min_confidence_for_clustering": 0.75,  # Only cluster Phase 3 results with confidence >= 0.75

    # LLM configuration
    "llm_model": "gpt-4o-mini",
    "llm_temperature": 0.0,
    "llm_batch_size": 10,  # Process 10 clusters at a time

    # Async processing configuration
    "enable_async": True,  # Use async concurrent processing
    "max_concurrent_requests": 20,  # Max parallel LLM requests (balances speed vs rate limits)

    # ChromaDB configuration
    "chromadb_collection_name": "evtol_technologies_v2",
    "embedding_model": "text-embedding-3-small",  # OpenAI embedding model
    "chromadb_search_top_k": 3,  # Top K results for hybrid search

    # Incremental testing limits
    "test_limits": {
        "phase1_normalization": 10,
        "phase2a_catalog_matching": 20,
        "phase2b_clustering": 50,
        "phase3_llm_single": 1,
        "phase3_llm_batch": 10
    },

    # Output files
    "output_files": {
        "normalized_mentions": "01_normalized_mentions.json",
        "catalog_matches": "02a_catalog_matches.json",
        "unmatched_mentions": "02a_unmatched_mentions.json",
        "mention_clusters": "02b_mention_clusters.json",
        "llm_canonical_names": "03_llm_canonical_names.json",
        "merged_catalog": "04_merged_catalog.json",
        "validation_report": "05_validation_report.json",
        "final_catalog": "canonical_technologies_v2.json"
    }
}


def get_pipeline_config() -> Dict[str, Any]:
    """Get pipeline configuration dictionary."""
    return PIPELINE_CONFIG


def load_industry_config(industry: str = "eVTOL") -> EntityResolutionConfig:
    """
    Load industry configuration.

    Args:
        industry: Industry name

    Returns:
        EntityResolutionConfig instance
    """
    return EntityResolutionConfig(industry)
