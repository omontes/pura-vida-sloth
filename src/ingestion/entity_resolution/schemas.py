"""
Pydantic Schemas for Entity Resolution Pipeline
Defines data structures for technology normalization
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TechMention(BaseModel):
    """Original technology mention from document."""
    name: str
    role: str
    strength: float
    evidence_confidence: float
    evidence_text: str


class Document(BaseModel):
    """Document containing technology mentions."""
    doc_id: str
    doc_type: str  # "patent" or "technical_paper"
    title: str
    tech_mentions: List[TechMention]


class NormalizedMention(BaseModel):
    """Normalized technology mention with aggregated metadata."""
    original_name: str
    normalized_name: str
    occurrence_count: int
    roles: List[str] = Field(default_factory=list)
    avg_strength: float
    avg_confidence: float
    source_documents: List[str] = Field(default_factory=list)
    doc_types: List[str] = Field(default_factory=list)  # ["patent", "technical_paper"]


class TechnologyVariant(BaseModel):
    """Variant name for a canonical technology."""
    name: str
    similarity_score: float
    method: str  # "exact", "fuzzy", "semantic", "llm"


class CanonicalTechnology(BaseModel):
    """Canonical technology with variants and metadata."""
    id: str  # Unique identifier (e.g., "tiltrotor_system")
    canonical_name: str
    domain: Optional[str] = None
    description: Optional[str] = None
    variants: List[TechnologyVariant] = Field(default_factory=list)
    occurrence_count: int = 0
    source_documents: List[str] = Field(default_factory=list)
    created_by: str = "entity_resolution_pipeline"  # "catalog" or "entity_resolution_pipeline"


class CatalogMatch(BaseModel):
    """Match between mention and existing catalog entry."""
    mention_name: str
    canonical_name: str
    canonical_id: str
    similarity_score: float
    match_method: str  # "exact", "fuzzy", "semantic", "combined"
    confidence: float


class TechnologyCluster(BaseModel):
    """Cluster of similar technology mentions."""
    cluster_id: int
    mention_names: List[str]
    mention_metadata: Dict[str, Dict[str, Any]] = Field(default_factory=dict)  # per-variant metadata for LLM context
    similarity_scores: Dict[str, Dict[str, float]] = Field(default_factory=dict)  # mention -> {other_mention: score}
    avg_cluster_similarity: float
    size: int


class LLMCanonicalResult(BaseModel):
    """Result from LLM canonical name selection."""
    cluster_id: int
    input_variants: List[str]
    canonical_name: str
    domain: Optional[str] = None
    description: Optional[str] = None
    confidence: float
    reasoning: str


class TechnologyCatalog(BaseModel):
    """Complete technology catalog output."""
    version: str
    generated_at: str
    industry: str
    total_canonical_technologies: int
    total_variants: int
    technologies: List[CanonicalTechnology]


class ValidationReport(BaseModel):
    """Validation report for final catalog."""
    total_canonical_technologies: int
    total_variants: int
    total_source_documents: int
    coverage_percentage: float  # Percentage of original mentions mapped
    duplicate_canonical_names: List[str] = Field(default_factory=list)
    orphaned_variants: List[str] = Field(default_factory=list)  # Variants not mapped to any canonical
    quality_metrics: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    passed: bool


class LookupResult(BaseModel):
    """Result from technology lookup/classification."""
    query_mention: str
    canonical_name: Optional[str] = None
    canonical_id: Optional[str] = None
    similarity_score: float
    match_method: str  # "exact_variant", "hybrid_search", "fuzzy", "semantic"
    confidence: str  # "high" (>0.90), "medium" (0.75-0.90), "low" (<0.75)
    alternatives: List[Dict[str, Any]] = Field(default_factory=list)  # Other possible matches
