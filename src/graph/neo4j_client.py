"""
Neo4j async client wrapper.

Provides connection pooling, query execution, and schema management.
Reads credentials from environment variables.
"""

import os
from typing import Any, Optional
import logging
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import Neo4jError
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


class Neo4jClient:
    """
    Async Neo4j client with connection pooling.

    Usage:
        async with Neo4jClient() as client:
            await client.run_query("CREATE (n:Test) RETURN n")
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        """
        Initialize Neo4j client.

        Args:
            uri: Neo4j URI (defaults to NEO4J_URI env var)
            username: Neo4j username (defaults to NEO4J_USERNAME env var)
            password: Neo4j password (defaults to NEO4J_PASSWORD env var)
            database: Neo4j database (defaults to NEO4J_DATABASE env var or 'neo4j')
        """
        self.uri = uri or os.getenv("NEO4J_URI")
        self.username = username or os.getenv("NEO4J_USERNAME")
        self.password = password or os.getenv("NEO4J_PASSWORD")
        self.database = database or os.getenv("NEO4J_DATABASE", "neo4j")

        if not all([self.uri, self.username, self.password]):
            raise ValueError(
                "Missing Neo4j credentials. Set NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD env vars"
            )

        self.driver: Optional[AsyncDriver] = None
        logger.info(f"Neo4j client initialized for database: {self.database}")

    async def __aenter__(self) -> "Neo4jClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> None:
        """Establish connection to Neo4j."""
        if self.driver is None:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password),
            )
            # Verify connectivity
            await self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.uri}")

    async def close(self) -> None:
        """Close Neo4j connection."""
        if self.driver:
            await self.driver.close()
            self.driver = None
            logger.info("Neo4j connection closed")

    async def run_query(
        self,
        query: str,
        parameters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """
        Run a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """
        if not self.driver:
            raise RuntimeError("Neo4j driver not connected. Call connect() first.")

        async with self.driver.session(database=self.database) as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    async def run_write_transaction(
        self,
        query: str,
        parameters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """
        Run a write transaction.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """
        if not self.driver:
            raise RuntimeError("Neo4j driver not connected. Call connect() first.")

        async def _execute_write(tx):
            result = await tx.run(query, parameters or {})
            return await result.data()

        async with self.driver.session(database=self.database) as session:
            records = await session.execute_write(_execute_write)
            return records

    async def run_batch_write(
        self,
        query: str,
        batch_data: list[dict[str, Any]],
        batch_size: int = 100,
    ) -> int:
        """
        Run batch write operation with automatic chunking.

        Args:
            query: Cypher query with $batch parameter
            batch_data: List of parameter dictionaries
            batch_size: Records per transaction (default 100)

        Returns:
            Total number of records written
        """
        if not self.driver:
            raise RuntimeError("Neo4j driver not connected. Call connect() first.")

        total_written = 0

        # Process in batches
        for i in range(0, len(batch_data), batch_size):
            batch = batch_data[i : i + batch_size]

            async def _execute_batch(tx):
                result = await tx.run(query, {"batch": batch})
                summary = await result.consume()
                return summary.counters.nodes_created + summary.counters.relationships_created

            async with self.driver.session(database=self.database) as session:
                written = await session.execute_write(_execute_batch)
                total_written += written

        logger.info(f"Batch write completed: {total_written} records written")
        return total_written

    async def create_constraints(self) -> None:
        """
        Create unique constraints for entity nodes.

        Constraints ensure data integrity and create implicit indexes.
        """
        constraints = [
            "CREATE CONSTRAINT technology_id IF NOT EXISTS FOR (t:Technology) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE",
        ]

        for constraint in constraints:
            try:
                await self.run_write_transaction(constraint)
                logger.info(f"Created constraint: {constraint[:50]}...")
            except Neo4jError as e:
                # Constraint might already exist
                logger.warning(f"Constraint creation warning: {e}")

    async def create_indexes(self) -> None:
        """
        Create indexes for common query patterns.

        Indexes improve query performance for filtering and sorting.
        """
        indexes = [
            "CREATE INDEX technology_domain IF NOT EXISTS FOR (t:Technology) ON (t.domain)",
            "CREATE INDEX document_type IF NOT EXISTS FOR (d:Document) ON (d.doc_type)",
            "CREATE INDEX document_date IF NOT EXISTS FOR (d:Document) ON (d.published_at)",
            "CREATE INDEX company_kind IF NOT EXISTS FOR (c:Company) ON (c.kind)",
            "CREATE INDEX company_country IF NOT EXISTS FOR (c:Company) ON (c.country)",
        ]

        for index in indexes:
            try:
                await self.run_write_transaction(index)
                logger.info(f"Created index: {index[:50]}...")
            except Neo4jError as e:
                # Index might already exist
                logger.warning(f"Index creation warning: {e}")

    async def clear_database(self) -> None:
        """
        Clear all nodes and relationships from database.

        WARNING: This is destructive! Use only for testing.
        """
        query = "MATCH (n) DETACH DELETE n"
        await self.run_write_transaction(query)
        logger.warning("Database cleared! All nodes and relationships deleted.")

    async def get_stats(self) -> dict[str, int]:
        """
        Get database statistics.

        Returns:
            Dictionary with node/relationship counts
        """
        stats_query = """
        MATCH (n)
        WITH labels(n) as labels
        UNWIND labels as label
        RETURN label, count(*) as count
        ORDER BY count DESC
        """

        results = await self.run_query(stats_query)

        stats = {"total_nodes": sum(r["count"] for r in results)}

        for record in results:
            stats[f"{record['label']}_count"] = record["count"]

        # Get relationship count
        rel_query = "MATCH ()-[r]->() RETURN count(r) as count"
        rel_result = await self.run_query(rel_query)
        stats["total_relationships"] = rel_result[0]["count"] if rel_result else 0

        return stats
