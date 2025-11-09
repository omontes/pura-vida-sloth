"""
Pydantic schemas for Document nodes.

Supports 7 document types:
- patent
- technical_paper
- sec_filing
- regulation
- github
- government_contract
- news

Based on SCHEMA_V2_COMPLETE.md specification.
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class BaseDocument(BaseModel):
    """
    Base document schema with common fields for all document types.

    NOTE: quality_score and relevance_score are STORED but NOT derived.
    They come from Phase 2 processing (NOT Phase 3).
    """

    doc_id: str = Field(..., description="Unique document identifier (e.g., 'patent_US1234567')")
    doc_type: Literal[
        "patent",
        "technical_paper",
        "sec_filing",
        "regulation",
        "github",
        "government_contract",
        "news",
    ] = Field(..., description="Document type")
    source: str = Field(..., description="Data source (e.g., 'lens.org', 'sec.gov')")
    title: str = Field(..., description="Document title")
    url: Optional[str] = Field(None, description="Source URL")
    published_at: Optional[datetime] = Field(None, description="Publication date")
    summary: Optional[str] = Field(None, description="Document summary/abstract")
    content: Optional[str] = Field(None, description="Full document text content")
    quality_score: Optional[float] = Field(None, ge=0, le=1, description="Quality score (0-1) from Phase 2")
    relevance_score: Optional[float] = Field(None, ge=0, le=1, description="Relevance score (0-1) from Phase 2")
    embedding: Optional[list[float]] = Field(None, description="Vector embedding for similarity search")


class PatentDocument(BaseDocument):
    """
    Patent document schema.

    Extends BaseDocument with patent-specific fields.
    """

    doc_type: Literal["patent"] = "patent"

    # Patent-specific fields
    patent_number: Optional[str] = Field(None, description="Patent number (e.g., 'US1234567')")
    jurisdiction: Optional[str] = Field(None, description="Patent jurisdiction (e.g., 'US', 'EP', 'WO')")
    type: Optional[str] = Field(None, description="Patent type (e.g., 'utility', 'design')")
    legal_status: Optional[str] = Field(None, description="Legal status (e.g., 'granted', 'pending', 'expired')")
    filing_date: Optional[datetime] = Field(None, description="Filing date")
    grant_date: Optional[datetime] = Field(None, description="Grant date")
    assignee_name: Optional[str] = Field(None, description="Assignee/owner name")
    citation_count: Optional[int] = Field(None, ge=0, description="Forward citation count")
    simple_family_size: Optional[int] = Field(None, ge=0, description="Patent family size")
    applicants: list[str] = Field(default_factory=list, description="Applicant names")


class TechnicalPaperDocument(BaseDocument):
    """
    Technical/research paper schema.

    Extends BaseDocument with academic paper fields.
    """

    doc_type: Literal["technical_paper"] = "technical_paper"

    # Paper-specific fields
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    venue_type: Optional[str] = Field(None, description="Publication venue type (e.g., 'journal', 'conference')")
    peer_reviewed: Optional[bool] = Field(None, description="Whether peer-reviewed")
    source_title: Optional[str] = Field(None, description="Journal/conference name")
    year_published: Optional[int] = Field(None, ge=1900, le=2100, description="Publication year")
    date_published: Optional[datetime] = Field(None, description="Exact publication date")
    citation_count: Optional[int] = Field(None, ge=0, description="Citation count")
    patent_citations_count: Optional[int] = Field(None, ge=0, description="Patent citation count")
    authors: list[str] = Field(default_factory=list, description="Author names")


class SECFilingDocument(BaseDocument):
    """
    SEC filing document schema.

    Supports Form 4 (insider trading), 13F (institutional holdings), 10-K/10-Q, etc.
    """

    doc_type: Literal["sec_filing"] = "sec_filing"

    # SEC-specific fields
    filing_type: Optional[str] = Field(None, description="Filing type (e.g., '4', '13F', '10-K', '10-Q')")
    cik: Optional[str] = Field(None, description="Central Index Key")
    accession_number: Optional[str] = Field(None, description="SEC accession number")
    filing_date: Optional[datetime] = Field(None, description="Filing date")
    fiscal_year: Optional[int] = Field(None, ge=1900, le=2100, description="Fiscal year")
    fiscal_quarter: Optional[int] = Field(None, ge=1, le=4, description="Fiscal quarter (1-4)")
    ticker: Optional[str] = Field(None, description="Company stock ticker")

    # Form 4 specific (insider trading)
    net_insider_value_usd: Optional[float] = Field(None, description="Net insider transaction value (USD)")
    total_shares_held: Optional[int] = Field(None, ge=0, description="Total shares held post-transaction")

    # 10-K/10-Q specific
    revenue_mentioned: Optional[bool] = Field(None, description="Whether revenue is mentioned")
    revenue_amount: Optional[float] = Field(None, ge=0, description="Revenue amount (USD)")
    risk_factor_mentioned: Optional[bool] = Field(None, description="Whether risk factors mentioned")

    # 13F specific
    qoq_change_pct: Optional[float] = Field(None, description="Quarter-over-quarter change percentage")


class RegulationDocument(BaseDocument):
    """
    Regulatory document schema.

    Government regulations, certifications, approvals.
    """

    doc_type: Literal["regulation"] = "regulation"

    # Regulation-specific fields
    regulatory_body: Optional[str] = Field(None, description="Regulatory agency (e.g., 'FAA', 'FDA')")
    sub_agency: Optional[str] = Field(None, description="Sub-agency or division")
    document_type: Optional[str] = Field(None, description="Document type (e.g., 'rule', 'certification')")
    decision_type: Optional[str] = Field(None, description="Decision type (e.g., 'approved', 'denied')")
    effective_date: Optional[datetime] = Field(None, description="Effective date")
    docket_number: Optional[str] = Field(None, description="Regulatory docket number")
    federal_register_doc_id: Optional[str] = Field(None, description="Federal Register document ID")


class GitHubDocument(BaseDocument):
    """
    GitHub repository schema.

    Represents open-source repositories related to technologies.
    """

    doc_type: Literal["github"] = "github"

    # GitHub-specific fields
    github_id: Optional[int] = Field(None, description="GitHub repository ID")
    repo_name: Optional[str] = Field(None, description="Repository name")
    owner: Optional[str] = Field(None, description="Repository owner")
    created_at: Optional[datetime] = Field(None, description="Repository creation date")
    last_pushed_at: Optional[datetime] = Field(None, description="Last push date")
    stars: Optional[int] = Field(None, ge=0, description="Star count")
    forks: Optional[int] = Field(None, ge=0, description="Fork count")
    contributor_count: Optional[int] = Field(None, ge=0, description="Number of contributors")


class GovernmentContractDocument(BaseDocument):
    """
    Government contract schema.

    Federal/state contracts awarded to companies.
    """

    doc_type: Literal["government_contract"] = "government_contract"

    # Contract-specific fields
    award_id: Optional[str] = Field(None, description="Contract award ID")
    recipient_name: Optional[str] = Field(None, description="Recipient company name")
    award_amount: Optional[float] = Field(None, ge=0, description="Award amount (USD)")
    start_date: Optional[datetime] = Field(None, description="Contract start date")
    end_date: Optional[datetime] = Field(None, description="Contract end date")
    awarding_agency: Optional[str] = Field(None, description="Awarding agency")
    awarding_sub_agency: Optional[str] = Field(None, description="Awarding sub-agency")


class NewsDocument(BaseDocument):
    """
    News article schema.

    News and media coverage (lagging indicator).
    """

    doc_type: Literal["news"] = "news"

    # News-specific fields
    domain: Optional[str] = Field(None, description="News outlet domain")
    outlet_tier: Optional[str] = Field(None, description="Outlet tier (e.g., 'tier1', 'tier2', 'tier3')")
    seendate: Optional[datetime] = Field(None, description="Date article was seen/indexed")
    tone: Optional[float] = Field(None, ge=-1, le=1, description="Sentiment tone (-1 to 1)")
