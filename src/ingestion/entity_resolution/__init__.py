"""
Entity Resolution Pipeline for Technology Normalization
Maps technology mentions to canonical forms
"""

from .config import EntityResolutionConfig, load_industry_config, get_pipeline_config
from .schemas import (
    TechMention,
    Document,
    NormalizedMention,
    TechnologyVariant,
    CanonicalTechnology,
    CatalogMatch,
    TechnologyCluster,
    LLMCanonicalResult,
    TechnologyCatalog,
    ValidationReport,
    LookupResult
)
from .normalizer import TechMentionNormalizer

__all__ = [
    # Config
    'EntityResolutionConfig',
    'load_industry_config',
    'get_pipeline_config',

    # Schemas
    'TechMention',
    'Document',
    'NormalizedMention',
    'TechnologyVariant',
    'CanonicalTechnology',
    'CatalogMatch',
    'TechnologyCluster',
    'LLMCanonicalResult',
    'TechnologyCatalog',
    'ValidationReport',
    'LookupResult',

    # Phase 1
    'TechMentionNormalizer',
]
