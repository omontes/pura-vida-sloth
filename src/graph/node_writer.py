"""
Node writer for Neo4j graph.

Handles creation of Technology, Company, and Document nodes.
Uses MERGE to avoid duplicates and supports batch operations.
"""

import logging
from typing import Any
from datetime import datetime

from src.graph.neo4j_client import Neo4jClient
from src.schemas.entities import Technology, Company
from src.schemas.documents import (
    BaseDocument,
    PatentDocument,
    TechnicalPaperDocument,
    SECFilingDocument,
    RegulationDocument,
    GitHubDocument,
    GovernmentContractDocument,
    NewsDocument,
)

logger = logging.getLogger(__name__)


class NodeWriter:
    """
    Writes entity and document nodes to Neo4j.

    Uses MERGE to prevent duplicates and supports batch operations.
    """

    def __init__(self, client: Neo4jClient):
        """
        Initialize node writer.

        Args:
            client: Connected Neo4j client
        """
        self.client = client

    async def write_technology(self, tech: Technology) -> None:
        """
        Write single Technology node.

        Args:
            tech: Technology schema instance
        """
        query = """
        MERGE (t:Technology {id: $id})
        SET t.name = $name,
            t.domain = $domain,
            t.description = $description,
            t.aliases = $aliases,
            t.updated_at = datetime($updated_at)
        RETURN t
        """

        params = {
            "id": tech.id,
            "name": tech.name,
            "domain": tech.domain,
            "description": tech.description,
            "aliases": tech.aliases,
            "updated_at": tech.updated_at.isoformat() if tech.updated_at else datetime.utcnow().isoformat(),
        }

        await self.client.run_write_transaction(query, params)

    async def write_company(self, company: Company) -> None:
        """
        Write single Company node.

        Args:
            company: Company schema instance
        """
        query = """
        MERGE (c:Company {id: $id})
        SET c.name = $name,
            c.aliases = $aliases,
            c.ticker = $ticker,
            c.kind = $kind,
            c.sector = $sector,
            c.country = $country,
            c.description = $description,
            c.updated_at = datetime($updated_at)
        RETURN c
        """

        params = {
            "id": company.id,
            "name": company.name,
            "aliases": company.aliases,
            "ticker": company.ticker,
            "kind": company.kind,
            "sector": company.sector,
            "country": company.country,
            "description": company.description,
            "updated_at": company.updated_at.isoformat()
            if company.updated_at
            else datetime.utcnow().isoformat(),
        }

        await self.client.run_write_transaction(query, params)

    async def write_document(
        self,
        doc: (
            PatentDocument
            | TechnicalPaperDocument
            | SECFilingDocument
            | RegulationDocument
            | GitHubDocument
            | GovernmentContractDocument
            | NewsDocument
        ),
    ) -> None:
        """
        Write single Document node (any type).

        Args:
            doc: Document schema instance
        """
        # Build properties dictionary
        props = self._build_document_properties(doc)

        # Build SET clause dynamically
        set_clauses = []
        for key in props.keys():
            if key != "doc_id":  # doc_id is in MERGE
                set_clauses.append(f"d.{key} = ${key}")

        set_clause = ", ".join(set_clauses)

        query = f"""
        MERGE (d:Document {{doc_id: $doc_id}})
        SET {set_clause}
        RETURN d
        """

        await self.client.run_write_transaction(query, props)

    def _build_document_properties(self, doc: BaseDocument) -> dict[str, Any]:
        """
        Build properties dictionary for document node.

        Handles all 7 document types with type-specific fields.
        """
        # Start with common fields
        props = {
            "doc_id": doc.doc_id,
            "doc_type": doc.doc_type,
            "source": doc.source,
            "title": doc.title,
            "url": doc.url,
            "published_at": doc.published_at.isoformat() if doc.published_at else None,
            "summary": doc.summary,
            "content": doc.content,
            "quality_score": doc.quality_score,
            "relevance_score": doc.relevance_score,
            "embedding": doc.embedding,
        }

        # Add type-specific fields
        if isinstance(doc, PatentDocument):
            props.update(
                {
                    "patent_number": doc.patent_number,
                    "jurisdiction": doc.jurisdiction,
                    "type": doc.type,
                    "legal_status": doc.legal_status,
                    "filing_date": doc.filing_date.isoformat() if doc.filing_date else None,
                    "grant_date": doc.grant_date.isoformat() if doc.grant_date else None,
                    "assignee_name": doc.assignee_name,
                    "citation_count": doc.citation_count,
                    "simple_family_size": doc.simple_family_size,
                    "applicants": doc.applicants,
                }
            )

        elif isinstance(doc, TechnicalPaperDocument):
            props.update(
                {
                    "doi": doc.doi,
                    "venue_type": doc.venue_type,
                    "peer_reviewed": doc.peer_reviewed,
                    "source_title": doc.source_title,
                    "year_published": doc.year_published,
                    "date_published": doc.date_published.isoformat() if doc.date_published else None,
                    "citation_count": doc.citation_count,
                    "patent_citations_count": doc.patent_citations_count,
                    "authors": doc.authors,
                }
            )

        elif isinstance(doc, SECFilingDocument):
            props.update(
                {
                    "filing_type": doc.filing_type,
                    "cik": doc.cik,
                    "accession_number": doc.accession_number,
                    "filing_date": doc.filing_date.isoformat() if doc.filing_date else None,
                    "fiscal_year": doc.fiscal_year,
                    "fiscal_quarter": doc.fiscal_quarter,
                    "ticker": doc.ticker,
                    "net_insider_value_usd": doc.net_insider_value_usd,
                    "total_shares_held": doc.total_shares_held,
                    "revenue_mentioned": doc.revenue_mentioned,
                    "revenue_amount": doc.revenue_amount,
                    "risk_factor_mentioned": doc.risk_factor_mentioned,
                    "qoq_change_pct": doc.qoq_change_pct,
                }
            )

        elif isinstance(doc, RegulationDocument):
            props.update(
                {
                    "regulatory_body": doc.regulatory_body,
                    "sub_agency": doc.sub_agency,
                    "document_type": doc.document_type,
                    "decision_type": doc.decision_type,
                    "effective_date": doc.effective_date.isoformat() if doc.effective_date else None,
                    "docket_id": doc.docket_id,
                }
            )

        elif isinstance(doc, GitHubDocument):
            props.update(
                {
                    "github_id": doc.github_id,
                    "repo_name": doc.repo_name,
                    "owner": doc.owner,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "last_pushed_at": doc.last_pushed_at.isoformat() if doc.last_pushed_at else None,
                    "stars": doc.stars,
                    "forks": doc.forks,
                    "contributor_count": doc.contributor_count,
                }
            )

        elif isinstance(doc, GovernmentContractDocument):
            props.update(
                {
                    "award_id": doc.award_id,
                    "recipient_name": doc.recipient_name,
                    "award_amount": doc.award_amount,
                    "start_date": doc.start_date.isoformat() if doc.start_date else None,
                    "end_date": doc.end_date.isoformat() if doc.end_date else None,
                    "awarding_agency": doc.awarding_agency,
                    "awarding_sub_agency": doc.awarding_sub_agency,
                }
            )

        elif isinstance(doc, NewsDocument):
            props.update(
                {
                    "domain": doc.domain,
                    "outlet_tier": doc.outlet_tier,
                    "seendate": doc.seendate.isoformat() if doc.seendate else None,
                    "tone": doc.tone,
                }
            )

        return props

    async def write_technologies_batch(self, technologies: list[Technology]) -> int:
        """
        Write batch of Technology nodes.

        Args:
            technologies: List of Technology instances

        Returns:
            Number of nodes written
        """
        query = """
        UNWIND $batch AS tech
        MERGE (t:Technology {id: tech.id})
        SET t.name = tech.name,
            t.domain = tech.domain,
            t.description = tech.description,
            t.aliases = tech.aliases,
            t.updated_at = datetime(tech.updated_at)
        """

        batch_data = [
            {
                "id": t.id,
                "name": t.name,
                "domain": t.domain,
                "description": t.description,
                "aliases": t.aliases,
                "updated_at": t.updated_at.isoformat() if t.updated_at else datetime.utcnow().isoformat(),
            }
            for t in technologies
        ]

        return await self.client.run_batch_write(query, batch_data)

    async def write_companies_batch(self, companies: list[Company]) -> int:
        """
        Write batch of Company nodes.

        Args:
            companies: List of Company instances

        Returns:
            Number of nodes written
        """
        query = """
        UNWIND $batch AS comp
        MERGE (c:Company {id: comp.id})
        SET c.name = comp.name,
            c.aliases = comp.aliases,
            c.ticker = comp.ticker,
            c.kind = comp.kind,
            c.sector = comp.sector,
            c.country = comp.country,
            c.description = comp.description,
            c.updated_at = datetime(comp.updated_at)
        """

        batch_data = [
            {
                "id": c.id,
                "name": c.name,
                "aliases": c.aliases,
                "ticker": c.ticker,
                "kind": c.kind,
                "sector": c.sector,
                "country": c.country,
                "description": c.description,
                "updated_at": c.updated_at.isoformat() if c.updated_at else datetime.utcnow().isoformat(),
            }
            for c in companies
        ]

        return await self.client.run_batch_write(query, batch_data)
