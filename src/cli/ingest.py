"""
CLI interface for Phase 3 graph ingestion.

Usage:
    python -m src.cli.ingest --samples-dir data/samples --limit 10
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

from src.graph.neo4j_client import Neo4jClient
from src.graph.entity_resolver import EntityResolver
from src.ingestion.graph_ingestor import GraphIngestor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/ingestion.log", mode="a"),
    ],
)

logger = logging.getLogger(__name__)


async def main(args):
    """Main ingestion workflow."""

    logger.info("=" * 80)
    logger.info("PHASE 3: GRAPH INGESTION")
    logger.info("=" * 80)

    # Initialize components
    logger.info("Initializing Neo4j client...")
    neo4j_client = Neo4jClient()

    logger.info("Initializing entity resolver...")
    entity_resolver = EntityResolver(
        companies_catalog_path=args.companies_catalog,
        technologies_catalog_path=args.technologies_catalog,
    )

    try:
        # Connect to Neo4j
        await neo4j_client.connect()

        # Setup schema (constraints and indexes)
        if args.setup_schema:
            logger.info("Setting up Neo4j schema (constraints and indexes)...")
            await neo4j_client.create_constraints()
            await neo4j_client.create_indexes()

        # Clear database if requested
        if args.clear:
            logger.warning("Clearing Neo4j database...")
            await neo4j_client.clear_database()

        # Initialize ingestor
        ingestor = GraphIngestor(neo4j_client, entity_resolver)

        # Run ingestion
        logger.info(f"Starting ingestion from: {args.samples_dir}")
        if args.limit:
            logger.info(f"Limit: {args.limit} documents per file")

        stats = await ingestor.ingest_sample_files(
            samples_dir=args.samples_dir,
            limit=args.limit,
        )

        # Display results
        logger.info("=" * 80)
        logger.info("INGESTION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Documents processed: {stats['documents_processed']}")
        logger.info(f"Documents failed: {stats['documents_failed']}")
        logger.info(f"Tech mentions created: {stats['tech_mentions_created']}")
        logger.info(f"Company mentions created: {stats['company_mentions_created']}")
        logger.info(f"Company-tech relations: {stats['company_tech_relations_created']}")
        logger.info(f"Tech-tech relations: {stats['tech_tech_relations_created']}")
        logger.info(f"Company-company relations: {stats['company_company_relations_created']}")
        logger.info(f"Entities unmatched: {stats['entities_unmatched']}")

        # Display database stats
        if args.show_stats:
            logger.info("=" * 80)
            logger.info("DATABASE STATISTICS")
            logger.info("=" * 80)
            db_stats = await neo4j_client.get_stats()
            for key, value in db_stats.items():
                logger.info(f"{key}: {value}")

    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        # Close Neo4j connection
        await neo4j_client.close()
        logger.info("Neo4j connection closed")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Phase 3: Ingest sample data into Neo4j graph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest 1 document per file (testing)
  python -m src.cli.ingest --limit 1 --setup-schema --show-stats

  # Ingest 10 documents per file
  python -m src.cli.ingest --limit 10

  # Ingest all sample data
  python -m src.cli.ingest --setup-schema --show-stats

  # Clear database and re-ingest
  python -m src.cli.ingest --clear --setup-schema --limit 10
        """,
    )

    parser.add_argument(
        "--samples-dir",
        type=str,
        default="data/samples",
        help="Directory containing sample JSON files (default: data/samples)",
    )

    parser.add_argument(
        "--companies-catalog",
        type=str,
        default="data/catalog/companies.json",
        help="Path to companies catalog (default: data/catalog/companies.json)",
    )

    parser.add_argument(
        "--technologies-catalog",
        type=str,
        default="data/catalog/technologies.json",
        help="Path to technologies catalog (default: data/catalog/technologies.json)",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of documents per file (for testing)",
    )

    parser.add_argument(
        "--setup-schema",
        action="store_true",
        help="Create Neo4j constraints and indexes before ingestion",
    )

    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear database before ingestion (WARNING: destructive!)",
    )

    parser.add_argument(
        "--show-stats",
        action="store_true",
        help="Show database statistics after ingestion",
    )

    return parser.parse_args()


if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)

    # Parse arguments
    args = parse_args()

    # Run async main
    asyncio.run(main(args))
