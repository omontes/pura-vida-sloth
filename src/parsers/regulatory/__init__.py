"""
Regulatory Document Parser Module
Author: Pura Vida Sloth Intelligence System

Parses Federal Register regulatory documents to extract:
- Technologies and companies
- Regulatory decisions and requirements
- Entity relationships for knowledge graph construction
"""

from parsers.regulatory.regulatory_parser import RegulatoryDocumentParser

__all__ = ["RegulatoryDocumentParser"]
