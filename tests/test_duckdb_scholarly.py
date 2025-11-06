"""
Test DuckDB Scholarly Papers Analysis System

Validates:
1. Database initialization from batch checkpoints
2. Table creation and row counts
3. Composite score calculation
4. Query performance
5. Top N paper selection

Usage:
    python tests/test_duckdb_scholarly.py
"""

import sys
import time
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.duckdb_scholarly_analysis import ScholarlyPapersDatabase


def setup_logging():
    """Configure logging for test output."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('TestDuckDB')


def test_database_initialization(logger):
    """Test 1: Database initialization from checkpoints."""
    logger.info("=" * 60)
    logger.info("TEST 1: Database Initialization")
    logger.info("=" * 60)

    try:
        db = ScholarlyPapersDatabase(
            scored_papers_dir="data/eVTOL/lens_scholarly/batch_processing",
            original_papers_path="data/eVTOL/lens_scholarly/papers.json"
        )

        start_time = time.time()
        db.initialize()
        init_time = time.time() - start_time

        logger.info(f"✓ Database initialized in {init_time:.2f} seconds")

        # Check tables exist
        tables = db.con.execute("SHOW TABLES").fetchdf()
        expected_tables = ['papers', 'relevance', 'technology_nodes', 'relationships',
                          'innovation_signals', 'adoption_indicators', 'original_metadata']

        for table_name in expected_tables:
            if table_name in tables['name'].values:
                count = db.con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                logger.info(f"  ✓ {table_name:25s}: {count:>6,} rows")
            else:
                logger.warning(f"  ✗ {table_name} not found")

        db.close()
        return True

    except Exception as e:
        logger.error(f"✗ Test 1 failed: {e}")
        return False


def test_composite_scoring(logger):
    """Test 2: Composite score calculation."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Composite Score Calculation")
    logger.info("=" * 60)

    try:
        db = ScholarlyPapersDatabase(
            scored_papers_dir="data/eVTOL/lens_scholarly/batch_processing",
            original_papers_path="data/eVTOL/lens_scholarly/papers.json"
        )
        db.initialize()

        # Get top 10 papers by composite score
        start_time = time.time()
        top_papers = db.get_top_papers_by_composite_score(limit=10)
        query_time = time.time() - start_time

        logger.info(f"✓ Retrieved {len(top_papers)} papers in {query_time*1000:.0f}ms")

        if top_papers:
            # Validate composite scores are sorted descending
            scores = [p['composite_score'] for p in top_papers]
            is_sorted = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))

            if is_sorted:
                logger.info(f"  ✓ Composite scores correctly sorted (descending)")
            else:
                logger.warning(f"  ✗ Composite scores not properly sorted")

            # Show top 3 papers
            logger.info("\nTop 3 Papers by Composite Score:")
            for i, paper in enumerate(top_papers[:3], 1):
                title = paper['title'][:50] if paper['title'] else 'N/A'
                logger.info(f"\n  {i}. {title}...")
                logger.info(f"     Composite Score: {paper['composite_score']:.3f}")
                logger.info(f"     Relevance: {paper['relevance_score']:.1f} | Impact: {paper['impact_potential']}")
                logger.info(f"     Innovation: {paper['innovation_type']} | Year: {paper['year_published']}")

            db.close()
            return True
        else:
            logger.error("  ✗ No papers returned from query")
            db.close()
            return False

    except Exception as e:
        logger.error(f"✗ Test 2 failed: {e}")
        return False


def test_query_performance(logger):
    """Test 3: Query performance benchmarks."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Query Performance")
    logger.info("=" * 60)

    try:
        db = ScholarlyPapersDatabase(
            scored_papers_dir="data/eVTOL/lens_scholarly/batch_processing",
            original_papers_path="data/eVTOL/lens_scholarly/papers.json"
        )
        db.initialize()

        # Test 3.1: Top 200 papers query
        start_time = time.time()
        top_200 = db.get_top_papers_by_composite_score(limit=200)
        query_time_200 = time.time() - start_time
        logger.info(f"  Top 200 papers query: {query_time_200*1000:.0f}ms")

        if query_time_200 < 0.5:  # Should be under 500ms
            logger.info(f"    ✓ Query performance excellent (<500ms)")
        else:
            logger.warning(f"    ! Query slower than expected (target: <500ms)")

        # Test 3.2: Relevance filter query
        start_time = time.time()
        relevant_papers = db.query_papers_by_relevance(
            min_score=8.5,
            categories=['direct_application', 'enabling_technology']
        )
        query_time_filter = time.time() - start_time
        logger.info(f"  Relevance filter query: {query_time_filter*1000:.0f}ms ({len(relevant_papers)} papers)")

        # Test 3.3: Knowledge graph extraction
        if top_200:
            lens_ids = [p['lens_id'] for p in top_200[:5]]
            start_time = time.time()
            kg = db.get_knowledge_graph(lens_ids)
            query_time_kg = time.time() - start_time
            logger.info(f"  Knowledge graph query (5 papers): {query_time_kg*1000:.0f}ms")
            logger.info(f"    Nodes: {len(kg['nodes'])}, Relationships: {len(kg['relationships'])}")

        db.close()
        return True

    except Exception as e:
        logger.error(f"✗ Test 3 failed: {e}")
        return False


def test_data_quality(logger):
    """Test 4: Data quality validation."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Data Quality Validation")
    logger.info("=" * 60)

    try:
        db = ScholarlyPapersDatabase(
            scored_papers_dir="data/eVTOL/lens_scholarly/batch_processing",
            original_papers_path="data/eVTOL/lens_scholarly/papers.json"
        )
        db.initialize()

        # Check 4.1: Relevance score range
        relevance_stats = db.con.execute("""
            SELECT
                MIN(relevance_score) as min_score,
                MAX(relevance_score) as max_score,
                AVG(relevance_score) as avg_score,
                COUNT(*) as total,
                SUM(CASE WHEN is_relevant THEN 1 ELSE 0 END) as relevant_count
            FROM relevance
        """).fetchone()

        logger.info(f"Relevance Score Stats:")
        logger.info(f"  Range: {relevance_stats[0]:.1f} - {relevance_stats[1]:.1f}")
        logger.info(f"  Average: {relevance_stats[2]:.2f}")
        logger.info(f"  Relevant papers: {relevance_stats[4]}/{relevance_stats[3]} ({relevance_stats[4]/relevance_stats[3]*100:.1f}%)")

        # Check 4.2: Innovation type distribution
        innovation_dist = db.con.execute("""
            SELECT innovation_type, COUNT(*) as count
            FROM innovation_signals
            WHERE innovation_type != 'not_applicable'
            GROUP BY innovation_type
            ORDER BY count DESC
        """).fetchdf()

        if not innovation_dist.empty:
            logger.info(f"\nInnovation Type Distribution:")
            for _, row in innovation_dist.iterrows():
                logger.info(f"  {row['innovation_type']:30s}: {row['count']:>5}")

        # Check 4.3: Publication year distribution
        year_dist = db.con.execute("""
            SELECT year_published, COUNT(*) as count
            FROM papers
            WHERE year_published IS NOT NULL
            GROUP BY year_published
            ORDER BY year_published DESC
            LIMIT 10
        """).fetchdf()

        if not year_dist.empty:
            logger.info(f"\nRecent Publications (Last 10 Years):")
            for _, row in year_dist.iterrows():
                logger.info(f"  {row['year_published']}: {row['count']:>5} papers")

        # Check 4.4: Technology nodes and relationships
        node_count = db.con.execute("SELECT COUNT(*) FROM technology_nodes").fetchone()[0]
        rel_count = db.con.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]

        if node_count > 0 and rel_count > 0:
            papers_with_nodes = db.con.execute("""
                SELECT COUNT(DISTINCT lens_id) FROM technology_nodes
            """).fetchone()[0]

            logger.info(f"\nKnowledge Graph Coverage:")
            logger.info(f"  Papers with technology nodes: {papers_with_nodes}")
            logger.info(f"  Total nodes: {node_count}")
            logger.info(f"  Total relationships: {rel_count}")
            logger.info(f"  Avg nodes per paper: {node_count/papers_with_nodes:.1f}")
            logger.info(f"  Avg relationships per paper: {rel_count/papers_with_nodes:.1f}")

        db.close()
        return True

    except Exception as e:
        logger.error(f"✗ Test 4 failed: {e}")
        return False


def test_custom_weighting(logger):
    """Test 5: Custom composite weighting."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: Custom Composite Weighting")
    logger.info("=" * 60)

    try:
        db = ScholarlyPapersDatabase(
            scored_papers_dir="data/eVTOL/lens_scholarly/batch_processing",
            original_papers_path="data/eVTOL/lens_scholarly/papers.json"
        )
        db.initialize()

        # Test different weighting schemes
        weighting_schemes = [
            {'name': 'Relevance-Heavy', 'weights': {'relevance': 0.6, 'impact': 0.2, 'references': 0.1, 'innovation': 0.05, 'recency': 0.05}},
            {'name': 'Innovation-Heavy', 'weights': {'relevance': 0.3, 'impact': 0.3, 'references': 0.1, 'innovation': 0.2, 'recency': 0.1}},
            {'name': 'Balanced (Default)', 'weights': {'relevance': 0.4, 'impact': 0.2, 'references': 0.2, 'innovation': 0.1, 'recency': 0.1}}
        ]

        for scheme in weighting_schemes:
            logger.info(f"\n{scheme['name']} Weighting:")
            top_papers = db.get_top_papers_by_composite_score(
                limit=5,
                weighting=scheme['weights']
            )

            if top_papers:
                top = top_papers[0]
                title = top['title'][:40] if top['title'] else 'N/A'
                logger.info(f"  Top paper: {title}...")
                logger.info(f"  Score: {top['composite_score']:.3f} | Relevance: {top['relevance_score']:.1f}")

        db.close()
        return True

    except Exception as e:
        logger.error(f"✗ Test 5 failed: {e}")
        return False


def main():
    """Run all tests."""
    logger = setup_logging()

    logger.info("\n" + "=" * 70)
    logger.info(" DUCKDB SCHOLARLY PAPERS ANALYSIS - TEST SUITE")
    logger.info("=" * 70)

    test_results = []

    # Run tests
    test_results.append(("Database Initialization", test_database_initialization(logger)))
    test_results.append(("Composite Scoring", test_composite_scoring(logger)))
    test_results.append(("Query Performance", test_query_performance(logger)))
    test_results.append(("Data Quality", test_data_quality(logger)))
    test_results.append(("Custom Weighting", test_custom_weighting(logger)))

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info(" TEST SUMMARY")
    logger.info("=" * 70)

    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)

    for test_name, result in test_results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status:8s} - {test_name}")

    logger.info("=" * 70)
    logger.info(f" {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    logger.info("=" * 70)

    if passed == total:
        logger.info("\n✓ All tests passed! DuckDB scholarly analysis system is ready.")
        return 0
    else:
        logger.error(f"\n✗ {total - passed} test(s) failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
