"""
Pydantic schemas for Neo4j relationships.

Supports 5 relationship types:
1. Technology → MENTIONED_IN → Document
2. Company → MENTIONED_IN → Document
3. Company → RELATED_TO_TECH → Technology
4. Technology → RELATED_TECH → Technology
5. Company → RELATED_COMPANY → Company

Based on SCHEMA_V2_COMPLETE.md specification.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


class TechMention(BaseModel):
    """
    Technology → MENTIONED_IN → Document relationship.

    Links technologies to documents where they are mentioned.
    """

    # Nodes
    tech_id: str = Field(..., description="Technology canonical ID")
    doc_id: str = Field(..., description="Document ID")

    # Relationship properties
    role: Literal[
        "subject",
        "invented",
        "studied",
        "commercialized",
        "implemented",
        "procured",
        "regulated",
    ] = Field(..., description="Role of technology in document")
    strength: float = Field(..., ge=0, le=1, description="Mention strength (0-1)")
    evidence_confidence: float = Field(..., ge=0, le=1, description="Confidence in evidence (0-1)")
    evidence_text: str = Field(..., max_length=200, description="Supporting text (max 200 chars)")

    @field_validator("evidence_text")
    @classmethod
    def truncate_evidence(cls, v: str) -> str:
        """Ensure evidence text is max 200 characters."""
        return v[:200] if len(v) > 200 else v


class CompanyMention(BaseModel):
    """
    Company → MENTIONED_IN → Document relationship.

    Links companies to documents where they are mentioned.
    """

    # Nodes
    company_id: str = Field(..., description="Company canonical ID")
    doc_id: str = Field(..., description="Document ID")

    # Relationship properties
    role: Literal[
        "owner",
        "developer",
        "operator",
        "contractor",
        "issuer",
        "competitor",
        "sponsor",
        "investment_target",
        "employer",
    ] = Field(..., description="Role of company in document")
    strength: float = Field(..., ge=0, le=1, description="Mention strength (0-1)")
    evidence_confidence: float = Field(..., ge=0, le=1, description="Confidence in evidence (0-1)")
    evidence_text: str = Field(..., max_length=200, description="Supporting text (max 200 chars)")

    @field_validator("evidence_text")
    @classmethod
    def truncate_evidence(cls, v: str) -> str:
        """Ensure evidence text is max 200 characters."""
        return v[:200] if len(v) > 200 else v


class CompanyTechRelation(BaseModel):
    """
    Company → RELATED_TO_TECH → Technology relationship.

    Links companies to technologies they interact with.
    Critical: Stores doc_ref for provenance tracking.
    """

    # Nodes
    company_id: str = Field(..., description="Company canonical ID")
    tech_id: str = Field(..., description="Technology canonical ID")

    # Relationship properties
    relation_type: Literal[
        "develops",
        "uses",
        "invests_in",
        "researches",
        "owns_ip",
    ] = Field(..., description="Type of company-tech relationship")
    evidence_confidence: float = Field(..., ge=0, le=1, description="Confidence in evidence (0-1)")
    evidence_text: str = Field(..., max_length=200, description="Supporting text (max 200 chars)")
    doc_ref: str = Field(..., description="Source document ID (provenance)")

    @field_validator("evidence_text")
    @classmethod
    def truncate_evidence(cls, v: str) -> str:
        """Ensure evidence text is max 200 characters."""
        return v[:200] if len(v) > 200 else v


class TechTechRelation(BaseModel):
    """
    Technology → RELATED_TECH → Technology relationship.

    Links technologies to each other (competition, enablement, etc.).
    Critical: Stores doc_ref for provenance tracking.
    """

    # Nodes
    source_tech_id: str = Field(..., description="Source technology canonical ID")
    target_tech_id: str = Field(..., description="Target technology canonical ID")

    # Relationship properties
    relation_type: Literal[
        "competes_with",
        "alternative_to",
        "enables",
        "supersedes",
        "component_of",
        "integrated_with",
        "derived_from",
        "precursor_to",
        "synergistic_with",
        "incompatible_with",
        "regulated_by",
        "standardizes",
        "certified_for",
        "successor_to",
    ] = Field(..., description="Type of tech-tech relationship")
    evidence_confidence: float = Field(..., ge=0, le=1, description="Confidence in evidence (0-1)")
    evidence_text: str = Field(..., max_length=200, description="Supporting text (max 200 chars)")
    doc_ref: str = Field(..., description="Source document ID (provenance)")

    @field_validator("evidence_text")
    @classmethod
    def truncate_evidence(cls, v: str) -> str:
        """Ensure evidence text is max 200 characters."""
        return v[:200] if len(v) > 200 else v


class CompanyCompanyRelation(BaseModel):
    """
    Company → RELATED_COMPANY → Company relationship.

    Links companies to each other (partnerships, competition, etc.).
    Critical: Stores doc_ref for provenance tracking.
    """

    # Nodes
    source_company_id: str = Field(..., description="Source company canonical ID")
    target_company_id: str = Field(..., description="Target company canonical ID")

    # Relationship properties
    relation_type: Literal[
        "partners_with",
        "invests_in",
        "acquires",
        "competes_with",
        "supplies",
        "licenses_from",
    ] = Field(..., description="Type of company-company relationship")
    evidence_confidence: float = Field(..., ge=0, le=1, description="Confidence in evidence (0-1)")
    evidence_text: str = Field(..., max_length=200, description="Supporting text (max 200 chars)")
    doc_ref: str = Field(..., description="Source document ID (provenance)")

    @field_validator("evidence_text")
    @classmethod
    def truncate_evidence(cls, v: str) -> str:
        """Ensure evidence text is max 200 characters."""
        return v[:200] if len(v) > 200 else v
