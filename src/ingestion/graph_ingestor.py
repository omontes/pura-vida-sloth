"""
Graph ingestor orchestrator for Phase 3.

Loads sample JSON files, validates with Pydantic, resolves entities,
and writes nodes and relationships to Neo4j.
"""

import json
import logging
from pathlib import Path
from typing import Any
from datetime import datetime
from tqdm import tqdm

from src.graph.neo4j_client import Neo4jClient
from src.graph.entity_resolver import EntityResolver
from src.graph.node_writer import NodeWriter
from src.graph.relationship_writer import RelationshipWriter
from src.schemas.entities import Technology, Company
from src.schemas.documents import (
    PatentDocument,
    TechnicalPaperDocument,
    SECFilingDocument,
    RegulationDocument,
    GitHubDocument,
    GovernmentContractDocument,
    NewsDocument,
)
from src.schemas.relationships import (
    TechMention,
    CompanyMention,
    CompanyTechRelation,
    TechTechRelation,
    CompanyCompanyRelation,
)

logger = logging.getLogger(__name__)


class GraphIngestor:
    """
    Main orchestrator for Phase 3 graph ingestion.

    Loads sample data, resolves entities, and writes to Neo4j.
    """

    # Mapping of doc_type to Pydantic schema
    DOC_TYPE_MAP = {
        "patent": PatentDocument,
        "technical_paper": TechnicalPaperDocument,
        "sec_filing": SECFilingDocument,
        "regulation": RegulationDocument,
        "github": GitHubDocument,
        "government_contract": GovernmentContractDocument,
        "news": NewsDocument,
    }

    def __init__(
        self,
        neo4j_client: Neo4jClient,
        entity_resolver: EntityResolver,
    ):
        """
        Initialize graph ingestor.

        Args:
            neo4j_client: Connected Neo4j client
            entity_resolver: Entity resolver for ID mapping
        """
        self.client = neo4j_client
        self.resolver = entity_resolver
        self.node_writer = NodeWriter(neo4j_client)
        self.rel_writer = RelationshipWriter(neo4j_client)

        # Current document metadata (for field mapping)
        self.current_metadata = {}

        # Statistics
        self.stats = {
            "documents_processed": 0,
            "documents_failed": 0,
            "tech_mentions_created": 0,
            "company_mentions_created": 0,
            "company_tech_relations_created": 0,
            "tech_tech_relations_created": 0,
            "company_company_relations_created": 0,
            "entities_unmatched": 0,
        }

    async def ingest_sample_files(
        self,
        samples_dir: str = "data/samples",
        limit: int | None = None,
    ) -> dict[str, Any]:
        """
        Ingest all sample JSON files from directory.

        Args:
            samples_dir: Directory containing sample JSON files
            limit: Optional limit on documents per file (for testing)

        Returns:
            Statistics dictionary
        """
        samples_path = Path(samples_dir)

        if not samples_path.exists():
            raise FileNotFoundError(f"Samples directory not found: {samples_dir}")

        # Get all JSON files
        json_files = sorted(samples_path.glob("*.json"))

        if not json_files:
            raise ValueError(f"No JSON files found in {samples_dir}")

        logger.info(f"Found {len(json_files)} sample files to ingest")

        # First, write all catalog entities to graph
        await self._write_catalog_entities()

        # Then process each file
        for json_file in json_files:
            logger.info(f"Processing {json_file.name}...")
            await self._ingest_file(json_file, limit=limit)

        # Log unmatched entity summary
        self.resolver.log_unmatched_summary()

        return self.stats

    async def _write_catalog_entities(self) -> None:
        """
        Write all companies and technologies from catalogs to Neo4j.

        This ensures all entities exist before creating relationships.
        """
        logger.info("Writing catalog entities to Neo4j...")

        # Get all companies and technologies
        companies_data = self.resolver.get_all_companies()
        technologies_data = self.resolver.get_all_technologies()

        # Convert to Pydantic models
        companies = [
            Company(
                id=c["id"],
                name=c["name"],
                aliases=c.get("aliases", []),
                ticker=c.get("ticker"),
                kind=c.get("kind"),
                sector=c.get("sector"),
                country=c.get("country"),
                description=c.get("description"),
                updated_at=datetime.utcnow(),
            )
            for c in companies_data
        ]

        technologies = [
            Technology(
                id=t["id"],
                name=t["name"],
                domain=t["domain"],
                description=t.get("description"),
                aliases=t.get("aliases", []),
                updated_at=datetime.utcnow(),
            )
            for t in technologies_data
        ]

        # Write in batches
        await self.node_writer.write_companies_batch(companies)
        await self.node_writer.write_technologies_batch(technologies)

        logger.info(f"Wrote {len(companies)} companies and {len(technologies)} technologies")

    async def _write_inline_entities(self, record: dict[str, Any]) -> None:
        """
        Write Technology and Company entities from document's inline arrays.

        These entities may not be in global catalogs. We write them first
        (before creating mention relationships) so they exist in the graph.
        Uses MERGE so duplicates across documents are handled automatically.

        Args:
            record: Document record containing technologies and companies arrays
        """
        inline_techs = record.get("technologies", [])
        inline_companies = record.get("companies", [])

        # Convert to Pydantic models
        technologies = [
            Technology(
                id=t["id"],
                name=t["name"],
                domain=t["domain"],
                description=t.get("description"),
                aliases=t.get("aliases", []),
                updated_at=datetime.utcnow(),
            )
            for t in inline_techs
        ]

        companies = [
            Company(
                id=c["id"],
                name=c["name"],
                aliases=c.get("aliases", []),
                ticker=c.get("ticker"),
                kind=c.get("kind"),
                sector=c.get("sector"),
                country=c.get("country"),
                description=c.get("description"),
                updated_at=datetime.utcnow(),
            )
            for c in inline_companies
        ]

        # Write to Neo4j (MERGE handles duplicates)
        if technologies:
            await self.node_writer.write_technologies_batch(technologies)
            # Register with resolver for mention matching
            for tech in inline_techs:
                self.resolver.add_inline_technology(
                    tech_id=tech["id"],
                    name=tech["name"],
                    aliases=tech.get("aliases", [])
                )

        if companies:
            await self.node_writer.write_companies_batch(companies)
            # Register with resolver for mention matching
            for company in inline_companies:
                self.resolver.add_inline_company(
                    company_id=company["id"],
                    name=company["name"],
                    aliases=company.get("aliases", [])
                )

    async def _ingest_file(self, file_path: Path, limit: int | None = None) -> None:
        """
        Ingest single JSON file with progress tracking.

        Args:
            file_path: Path to JSON file
            limit: Optional limit on number of documents
        """
        with open(file_path, "r", encoding="utf-8") as f:
            records = json.load(f)

        # Apply limit if specified
        if limit:
            records = records[:limit]

        logger.info(f"Loading {len(records)} records from {file_path.name}")

        # Progress bar with file name
        with tqdm(total=len(records), desc=f"{file_path.stem}", unit="doc") as pbar:
            for idx, record in enumerate(records, 1):
                try:
                    await self._ingest_record(record)
                    self.stats["documents_processed"] += 1
                except Exception as e:
                    logger.error(f"Failed to ingest record {idx}: {e}")
                    self.stats["documents_failed"] += 1
                finally:
                    pbar.update(1)

    async def _ingest_record(self, record: dict[str, Any]) -> None:
        """
        Ingest single document record.

        Args:
            record: Document record with document, mentions, and relations
        """
        # NEW STEP 1: Write inline entities to graph FIRST
        await self._write_inline_entities(record)

        # Store metadata for later use in _convert_to_document_model()
        self.current_metadata = record.get("document_metadata", {})

        # Extract components
        doc_data = record.get("document", {})
        tech_mentions = record.get("tech_mentions", [])
        company_mentions = record.get("company_mentions", [])
        company_tech_relations = record.get("company_tech_relations", [])
        tech_tech_relations = record.get("tech_tech_relations", [])
        company_company_relations = record.get("company_company_relations", [])

        # 2. Validate and write document
        doc_type = doc_data.get("doc_type")
        if doc_type not in self.DOC_TYPE_MAP:
            raise ValueError(f"Unknown doc_type: {doc_type}")

        # Convert document data to Pydantic model
        doc_schema = self.DOC_TYPE_MAP[doc_type]
        doc_model = self._convert_to_document_model(doc_data, doc_schema)

        # Write document node
        await self.node_writer.write_document(doc_model)

        # 2. Process technology mentions
        for mention_data in tech_mentions:
            tech_id = self.resolver.resolve_technology(mention_data["name"])
            if not tech_id:
                self.stats["entities_unmatched"] += 1
                continue

            mention = TechMention(
                tech_id=tech_id,
                doc_id=doc_data["doc_id"],
                role=mention_data["role"],
                strength=mention_data["strength"],
                evidence_confidence=mention_data["evidence_confidence"],
                evidence_text=mention_data["evidence_text"],
            )
            await self.rel_writer.write_tech_mention(mention)
            self.stats["tech_mentions_created"] += 1

        # 3. Process company mentions
        for mention_data in company_mentions:
            company_id = self.resolver.resolve_company(mention_data["name"])
            if not company_id:
                self.stats["entities_unmatched"] += 1
                continue

            mention = CompanyMention(
                company_id=company_id,
                doc_id=doc_data["doc_id"],
                role=mention_data["role"],
                strength=mention_data["strength"],
                evidence_confidence=mention_data["evidence_confidence"],
                evidence_text=mention_data["evidence_text"],
            )
            await self.rel_writer.write_company_mention(mention)
            self.stats["company_mentions_created"] += 1

        # 4. Process company-tech relations
        for rel_data in company_tech_relations:
            company_id = self.resolver.resolve_company(rel_data["company_name"])
            tech_id = self.resolver.resolve_technology(rel_data["technology_name"])

            if not company_id or not tech_id:
                self.stats["entities_unmatched"] += 1
                continue

            relation = CompanyTechRelation(
                company_id=company_id,
                tech_id=tech_id,
                relation_type=rel_data["relation_type"],
                evidence_confidence=rel_data["evidence_confidence"],
                evidence_text=rel_data["evidence_text"],
                doc_ref=rel_data["doc_ref"],
            )
            await self.rel_writer.write_company_tech_relation(relation)
            self.stats["company_tech_relations_created"] += 1

        # 5. Process tech-tech relations
        for rel_data in tech_tech_relations:
            source_tech_id = self.resolver.resolve_technology(rel_data["from_tech_name"])
            target_tech_id = self.resolver.resolve_technology(rel_data["to_tech_name"])

            if not source_tech_id or not target_tech_id:
                self.stats["entities_unmatched"] += 1
                continue

            relation = TechTechRelation(
                source_tech_id=source_tech_id,
                target_tech_id=target_tech_id,
                relation_type=rel_data["relation_type"],
                evidence_confidence=rel_data["evidence_confidence"],
                evidence_text=rel_data["evidence_text"],
                doc_ref=rel_data["doc_ref"],
            )
            await self.rel_writer.write_tech_tech_relation(relation)
            self.stats["tech_tech_relations_created"] += 1

        # 6. Process company-company relations
        for rel_data in company_company_relations:
            source_company_id = self.resolver.resolve_company(rel_data["from_company_name"])
            target_company_id = self.resolver.resolve_company(rel_data["to_company_name"])

            if not source_company_id or not target_company_id:
                self.stats["entities_unmatched"] += 1
                continue

            relation = CompanyCompanyRelation(
                source_company_id=source_company_id,
                target_company_id=target_company_id,
                relation_type=rel_data["relation_type"],
                evidence_confidence=rel_data["evidence_confidence"],
                evidence_text=rel_data["evidence_text"],
                doc_ref=rel_data["doc_ref"],
            )
            await self.rel_writer.write_company_company_relation(relation)
            self.stats["company_company_relations_created"] += 1

    def _convert_to_document_model(self, doc_data: dict[str, Any], schema_class):
        """
        Convert raw document data to Pydantic model.

        Handles field name mapping and type conversion.
        """
        # Start with common fields
        model_data = {
            "doc_id": doc_data.get("doc_id"),
            "doc_type": doc_data.get("doc_type"),
            "source": doc_data.get("source", "unknown"),
            "title": doc_data.get("title"),
            "url": doc_data.get("url"),
            "summary": doc_data.get("abstract") or doc_data.get("summary"),  # Handle both
            "content": doc_data.get("content"),
            "quality_score": doc_data.get("quality_score"),
            "relevance_score": doc_data.get("relevance_score"),
            "embedding": doc_data.get("embedding"),
        }

        # Handle date fields
        if "published_at" in doc_data:
            model_data["published_at"] = self._parse_date(doc_data["published_at"])
        elif "publication_date" in doc_data:
            model_data["published_at"] = self._parse_date(doc_data["publication_date"])

        # Add type-specific fields
        doc_type = doc_data.get("doc_type")
        metadata = self.current_metadata

        if doc_type == "patent":
            model_data.update({
                "patent_number": doc_data.get("patent_number"),
                "jurisdiction": doc_data.get("jurisdiction"),
                "type": doc_data.get("type"),
                "legal_status": doc_data.get("legal_status"),
                "filing_date": self._parse_date(doc_data.get("filing_date")),
                "grant_date": self._parse_date(doc_data.get("grant_date")),
                "assignee_name": doc_data.get("assignee_name") or doc_data.get("assignee"),
                "citation_count": doc_data.get("citation_count"),
                "simple_family_size": doc_data.get("simple_family_size"),
                "applicants": doc_data.get("applicants", []),
            })

        elif doc_type == "technical_paper":
            model_data.update({
                "doi": doc_data.get("doi"),
                "venue_type": doc_data.get("venue_type"),
                "peer_reviewed": doc_data.get("peer_reviewed"),
                "source_title": doc_data.get("source_title"),
                "year_published": doc_data.get("year_published"),
                "date_published": self._parse_date(doc_data.get("date_published")),
                "citation_count": doc_data.get("citation_count"),
                "patent_citations_count": doc_data.get("patent_citations_count"),
                "authors": doc_data.get("authors", []),
            })

        elif doc_type == "sec_filing":
            model_data.update({
                "filing_type": doc_data.get("filing_type"),
                "cik": doc_data.get("cik"),
                "accession_number": doc_data.get("accession_number"),
                "filing_date": self._parse_date(doc_data.get("filing_date")),
                "fiscal_year": doc_data.get("fiscal_year"),
                "fiscal_quarter": doc_data.get("fiscal_quarter"),
                "ticker": metadata.get("ticker") if metadata else None,
                "net_insider_value_usd": doc_data.get("net_insider_value_usd"),
                "total_shares_held": doc_data.get("total_shares_held"),
                "revenue_mentioned": metadata.get("revenue_mentioned") if metadata else None,
                "revenue_amount": metadata.get("revenue_amount") if metadata else None,
                "risk_factor_mentioned": metadata.get("risk_factor_mentioned") if metadata else None,
                "qoq_change_pct": doc_data.get("qoq_change_pct"),
            })

        elif doc_type == "regulation":
            model_data.update({
                "regulatory_body": doc_data.get("regulatory_body"),
                "sub_agency": doc_data.get("sub_agency"),
                "document_type": doc_data.get("document_type"),
                "decision_type": doc_data.get("decision_type"),
                "effective_date": self._parse_date(doc_data.get("effective_date")),
                "docket_number": doc_data.get("docket_number"),
                "federal_register_doc_id": doc_data.get("federal_register_doc_id"),
            })

        elif doc_type == "github":
            model_data.update({
                "github_id": doc_data.get("github_id"),
                "repo_name": doc_data.get("repo_name"),
                "owner": doc_data.get("owner"),
                "created_at": self._parse_date(doc_data.get("created_at")),
                "last_pushed_at": self._parse_date(doc_data.get("last_pushed_at")),
                "stars": doc_data.get("stars"),
                "forks": doc_data.get("forks"),
                "contributor_count": doc_data.get("contributor_count"),
            })

        elif doc_type == "government_contract":
            model_data.update({
                "award_id": doc_data.get("award_id"),
                "recipient_name": doc_data.get("recipient_name"),
                "award_amount": doc_data.get("award_amount"),
                "start_date": self._parse_date(doc_data.get("start_date")),
                "end_date": self._parse_date(doc_data.get("end_date")),
                "awarding_agency": doc_data.get("awarding_agency"),
                "awarding_sub_agency": doc_data.get("awarding_sub_agency"),
            })

        elif doc_type == "news":
            # Handle missing published_at from metadata
            if not model_data.get("published_at") and metadata:
                model_data["published_at"] = self._parse_date(metadata.get("seendate"))

            model_data.update({
                "domain": metadata.get("domain") if metadata else None,
                "outlet_tier": metadata.get("outlet_tier") if metadata else None,
                "seendate": self._parse_date(metadata.get("seendate")) if metadata else None,
                "tone": doc_data.get("tone"),
            })

        return schema_class(**model_data)

    def _parse_date(self, date_str: str | None) -> datetime | None:
        """Parse date string to datetime."""
        if not date_str:
            return None

        try:
            # Try ISO format first
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            try:
                # Try YYYY-MM-DD format
                return datetime.strptime(date_str, "%Y-%m-%d")
            except:
                logger.warning(f"Failed to parse date: {date_str}")
                return None
