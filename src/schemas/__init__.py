"""
Pydantic schemas for Neo4j graph entities and relationships.

Phase 3: Graph Ingestion
Validates all data structures before writing to Neo4j.
"""

from .entities import Technology, Company
from .documents import (
    BaseDocument,
    PatentDocument,
    TechnicalPaperDocument,
    SECFilingDocument,
    RegulationDocument,
    GitHubDocument,
    GovernmentContractDocument,
    NewsDocument,
)
from .relationships import (
    TechMention,
    CompanyMention,
    CompanyTechRelation,
    TechTechRelation,
    CompanyCompanyRelation,
)

__all__ = [
    # Entities
    "Technology",
    "Company",
    # Documents
    "BaseDocument",
    "PatentDocument",
    "TechnicalPaperDocument",
    "SECFilingDocument",
    "RegulationDocument",
    "GitHubDocument",
    "GovernmentContractDocument",
    "NewsDocument",
    # Relationships
    "TechMention",
    "CompanyMention",
    "CompanyTechRelation",
    "TechTechRelation",
    "CompanyCompanyRelation",
]
