"""
Relationship writer for Neo4j graph.

Handles creation of all 5 relationship types:
1. Technology → MENTIONED_IN → Document
2. Company → MENTIONED_IN → Document
3. Company → RELATED_TO_TECH → Technology
4. Technology → RELATED_TECH → Technology
5. Company → RELATED_COMPANY → Company

All relation relationships (3-5) store doc_ref for provenance tracking.
"""

import logging
from src.graph.neo4j_client import Neo4jClient
from src.schemas.relationships import (
    TechMention,
    CompanyMention,
    CompanyTechRelation,
    TechTechRelation,
    CompanyCompanyRelation,
)

logger = logging.getLogger(__name__)


class RelationshipWriter:
    """
    Writes relationships to Neo4j graph.

    Uses MERGE to prevent duplicates and supports batch operations.
    Document-centric: Each document creates separate relationship records.
    """

    def __init__(self, client: Neo4jClient):
        """
        Initialize relationship writer.

        Args:
            client: Connected Neo4j client
        """
        self.client = client

    async def write_tech_mention(self, mention: TechMention) -> None:
        """
        Write single Technology → MENTIONED_IN → Document relationship.

        Args:
            mention: TechMention schema instance
        """
        query = """
        MATCH (t:Technology {id: $tech_id})
        MATCH (d:Document {doc_id: $doc_id})
        MERGE (t)-[r:MENTIONED_IN {doc_id: $doc_id}]->(d)
        SET r.role = $role,
            r.strength = $strength,
            r.evidence_confidence = $evidence_confidence,
            r.evidence_text = $evidence_text
        RETURN r
        """

        params = {
            "tech_id": mention.tech_id,
            "doc_id": mention.doc_id,
            "role": mention.role,
            "strength": mention.strength,
            "evidence_confidence": mention.evidence_confidence,
            "evidence_text": mention.evidence_text,
        }

        await self.client.run_write_transaction(query, params)

    async def write_company_mention(self, mention: CompanyMention) -> None:
        """
        Write single Company → MENTIONED_IN → Document relationship.

        Args:
            mention: CompanyMention schema instance
        """
        query = """
        MATCH (c:Company {id: $company_id})
        MATCH (d:Document {doc_id: $doc_id})
        MERGE (c)-[r:MENTIONED_IN {doc_id: $doc_id}]->(d)
        SET r.role = $role,
            r.strength = $strength,
            r.evidence_confidence = $evidence_confidence,
            r.evidence_text = $evidence_text
        RETURN r
        """

        params = {
            "company_id": mention.company_id,
            "doc_id": mention.doc_id,
            "role": mention.role,
            "strength": mention.strength,
            "evidence_confidence": mention.evidence_confidence,
            "evidence_text": mention.evidence_text,
        }

        await self.client.run_write_transaction(query, params)

    async def write_company_tech_relation(self, relation: CompanyTechRelation) -> None:
        """
        Write single Company → RELATED_TO_TECH → Technology relationship.

        Stores doc_ref for provenance tracking.

        Args:
            relation: CompanyTechRelation schema instance
        """
        query = """
        MATCH (c:Company {id: $company_id})
        MATCH (t:Technology {id: $tech_id})
        MERGE (c)-[r:RELATED_TO_TECH {doc_ref: $doc_ref}]->(t)
        SET r.relation_type = $relation_type,
            r.evidence_confidence = $evidence_confidence,
            r.evidence_text = $evidence_text
        RETURN r
        """

        params = {
            "company_id": relation.company_id,
            "tech_id": relation.tech_id,
            "relation_type": relation.relation_type,
            "evidence_confidence": relation.evidence_confidence,
            "evidence_text": relation.evidence_text,
            "doc_ref": relation.doc_ref,
        }

        await self.client.run_write_transaction(query, params)

    async def write_tech_tech_relation(self, relation: TechTechRelation) -> None:
        """
        Write single Technology → RELATED_TECH → Technology relationship.

        Stores doc_ref for provenance tracking.

        Args:
            relation: TechTechRelation schema instance
        """
        query = """
        MATCH (t1:Technology {id: $source_tech_id})
        MATCH (t2:Technology {id: $target_tech_id})
        MERGE (t1)-[r:RELATED_TECH {doc_ref: $doc_ref}]->(t2)
        SET r.relation_type = $relation_type,
            r.evidence_confidence = $evidence_confidence,
            r.evidence_text = $evidence_text
        RETURN r
        """

        params = {
            "source_tech_id": relation.source_tech_id,
            "target_tech_id": relation.target_tech_id,
            "relation_type": relation.relation_type,
            "evidence_confidence": relation.evidence_confidence,
            "evidence_text": relation.evidence_text,
            "doc_ref": relation.doc_ref,
        }

        await self.client.run_write_transaction(query, params)

    async def write_company_company_relation(self, relation: CompanyCompanyRelation) -> None:
        """
        Write single Company → RELATED_COMPANY → Company relationship.

        Stores doc_ref for provenance tracking.

        Args:
            relation: CompanyCompanyRelation schema instance
        """
        query = """
        MATCH (c1:Company {id: $source_company_id})
        MATCH (c2:Company {id: $target_company_id})
        MERGE (c1)-[r:RELATED_COMPANY {doc_ref: $doc_ref}]->(c2)
        SET r.relation_type = $relation_type,
            r.evidence_confidence = $evidence_confidence,
            r.evidence_text = $evidence_text
        RETURN r
        """

        params = {
            "source_company_id": relation.source_company_id,
            "target_company_id": relation.target_company_id,
            "relation_type": relation.relation_type,
            "evidence_confidence": relation.evidence_confidence,
            "evidence_text": relation.evidence_text,
            "doc_ref": relation.doc_ref,
        }

        await self.client.run_write_transaction(query, params)

    async def write_tech_mentions_batch(self, mentions: list[TechMention]) -> int:
        """
        Write batch of Technology → MENTIONED_IN → Document relationships.

        Args:
            mentions: List of TechMention instances

        Returns:
            Number of relationships written
        """
        query = """
        UNWIND $batch AS mention
        MATCH (t:Technology {id: mention.tech_id})
        MATCH (d:Document {doc_id: mention.doc_id})
        MERGE (t)-[r:MENTIONED_IN {doc_id: mention.doc_id}]->(d)
        SET r.role = mention.role,
            r.strength = mention.strength,
            r.evidence_confidence = mention.evidence_confidence,
            r.evidence_text = mention.evidence_text
        """

        batch_data = [
            {
                "tech_id": m.tech_id,
                "doc_id": m.doc_id,
                "role": m.role,
                "strength": m.strength,
                "evidence_confidence": m.evidence_confidence,
                "evidence_text": m.evidence_text,
            }
            for m in mentions
        ]

        return await self.client.run_batch_write(query, batch_data)

    async def write_company_mentions_batch(self, mentions: list[CompanyMention]) -> int:
        """
        Write batch of Company → MENTIONED_IN → Document relationships.

        Args:
            mentions: List of CompanyMention instances

        Returns:
            Number of relationships written
        """
        query = """
        UNWIND $batch AS mention
        MATCH (c:Company {id: mention.company_id})
        MATCH (d:Document {doc_id: mention.doc_id})
        MERGE (c)-[r:MENTIONED_IN {doc_id: mention.doc_id}]->(d)
        SET r.role = mention.role,
            r.strength = mention.strength,
            r.evidence_confidence = mention.evidence_confidence,
            r.evidence_text = mention.evidence_text
        """

        batch_data = [
            {
                "company_id": m.company_id,
                "doc_id": m.doc_id,
                "role": m.role,
                "strength": m.strength,
                "evidence_confidence": m.evidence_confidence,
                "evidence_text": m.evidence_text,
            }
            for m in mentions
        ]

        return await self.client.run_batch_write(query, batch_data)

    async def write_company_tech_relations_batch(self, relations: list[CompanyTechRelation]) -> int:
        """
        Write batch of Company → RELATED_TO_TECH → Technology relationships.

        Args:
            relations: List of CompanyTechRelation instances

        Returns:
            Number of relationships written
        """
        query = """
        UNWIND $batch AS rel
        MATCH (c:Company {id: rel.company_id})
        MATCH (t:Technology {id: rel.tech_id})
        MERGE (c)-[r:RELATED_TO_TECH {doc_ref: rel.doc_ref}]->(t)
        SET r.relation_type = rel.relation_type,
            r.evidence_confidence = rel.evidence_confidence,
            r.evidence_text = rel.evidence_text
        """

        batch_data = [
            {
                "company_id": r.company_id,
                "tech_id": r.tech_id,
                "relation_type": r.relation_type,
                "evidence_confidence": r.evidence_confidence,
                "evidence_text": r.evidence_text,
                "doc_ref": r.doc_ref,
            }
            for r in relations
        ]

        return await self.client.run_batch_write(query, batch_data)

    async def write_tech_tech_relations_batch(self, relations: list[TechTechRelation]) -> int:
        """
        Write batch of Technology → RELATED_TECH → Technology relationships.

        Args:
            relations: List of TechTechRelation instances

        Returns:
            Number of relationships written
        """
        query = """
        UNWIND $batch AS rel
        MATCH (t1:Technology {id: rel.source_tech_id})
        MATCH (t2:Technology {id: rel.target_tech_id})
        MERGE (t1)-[r:RELATED_TECH {doc_ref: rel.doc_ref}]->(t2)
        SET r.relation_type = rel.relation_type,
            r.evidence_confidence = rel.evidence_confidence,
            r.evidence_text = rel.evidence_text
        """

        batch_data = [
            {
                "source_tech_id": r.source_tech_id,
                "target_tech_id": r.target_tech_id,
                "relation_type": r.relation_type,
                "evidence_confidence": r.evidence_confidence,
                "evidence_text": r.evidence_text,
                "doc_ref": r.doc_ref,
            }
            for r in relations
        ]

        return await self.client.run_batch_write(query, batch_data)

    async def write_company_company_relations_batch(self, relations: list[CompanyCompanyRelation]) -> int:
        """
        Write batch of Company → RELATED_COMPANY → Company relationships.

        Args:
            relations: List of CompanyCompanyRelation instances

        Returns:
            Number of relationships written
        """
        query = """
        UNWIND $batch AS rel
        MATCH (c1:Company {id: rel.source_company_id})
        MATCH (c2:Company {id: rel.target_company_id})
        MERGE (c1)-[r:RELATED_COMPANY {doc_ref: rel.doc_ref}]->(c2)
        SET r.relation_type = rel.relation_type,
            r.evidence_confidence = rel.evidence_confidence,
            r.evidence_text = rel.evidence_text
        """

        batch_data = [
            {
                "source_company_id": r.source_company_id,
                "target_company_id": r.target_company_id,
                "relation_type": r.relation_type,
                "evidence_confidence": r.evidence_confidence,
                "evidence_text": r.evidence_text,
                "doc_ref": r.doc_ref,
            }
            for r in relations
        ]

        return await self.client.run_batch_write(query, batch_data)
