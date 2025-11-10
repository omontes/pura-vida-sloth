"""
SEC Filing Parser Module

Extracts technology and company entities/relations from SEC EDGAR filings
for knowledge graph construction.
"""

from parsers.sec.sec_parser import SECFilingParser, load_industry_config

__all__ = ["SECFilingParser", "load_industry_config"]
