"""
DuckDB Manager for Scholarly Papers Analysis (Industry-Agnostic)

Loads scored papers from batch checkpoints into DuckDB for fast SQL analytics.
Provides composite scoring combining LLM relevance + impact + innovation signals.

Usage:
    from src.utils.duckdb_scholarly_analysis import ScholarlyPapersDatabase

    db = ScholarlyPapersDatabase(
        scored_papers_dir="data/eVTOL/lens_scholarly/batch_processing",
        original_papers_path="data/eVTOL/lens_scholarly/papers.json"
    )
    db.initialize()  # One-time setup

    # Query top papers by composite score
    top_papers = db.get_top_papers_by_composite_score(limit=200)
"""

import duckdb
import logging
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
import pandas as pd
from datetime import datetime


class ScholarlyPapersDatabase:
    """
    Manages DuckDB database for scored scholarly papers.

    Provides fast SQL queries over batch checkpoint data with composite scoring.
    Industry-agnostic design - works with any scholarly dataset.
    """

    def __init__(
        self,
        scored_papers_dir: str = "data/eVTOL/lens_scholarly/batch_processing",
        original_papers_path: Optional[str] = None,
        db_path: Optional[str] = None
    ):
        """
        Initialize scholarly papers database manager.

        Args:
            scored_papers_dir: Directory containing batch checkpoints
            original_papers_path: Path to papers.json (for metadata enrichment)
            db_path: Path to DuckDB file. If None, creates in scored_papers_dir
        """
        self.scored_papers_dir = Path(scored_papers_dir)
        self.original_papers_path = Path(original_papers_path) if original_papers_path else None
        self.db_path = db_path or str(self.scored_papers_dir / "scholarly_papers.duckdb")
        self.con = None
        self.logger = logging.getLogger(__name__)

        # Batch checkpoint files
        self.checkpoint_pattern = "checkpoint_*.json"
        self.consolidated_file = None

    def connect(self):
        """Open connection to DuckDB database."""
        if self.con is None:
            self.con = duckdb.connect(self.db_path)
            self.logger.info(f"Connected to DuckDB: {self.db_path}")
        return self.con

    def close(self):
        """Close DuckDB connection."""
        if self.con:
            self.con.close()
            self.con = None
            self.logger.info("Closed DuckDB connection")

    def initialize(self, force_reload: bool = False):
        """
        Initialize DuckDB database from batch checkpoint files.

        Loads scored papers and creates normalized tables with indexes.
        Only runs once unless force_reload=True.

        Args:
            force_reload: If True, drops existing tables and reloads
        """
        self.connect()

        # Check if already initialized
        tables = self.con.execute("SHOW TABLES").fetchdf()
        if not tables.empty and not force_reload:
            self.logger.info("Database already initialized. Use force_reload=True to reload.")
            return

        self.logger.info("Initializing Scholarly Papers database from checkpoints...")

        # Drop existing tables if force reload
        if force_reload:
            for table_name in ['papers', 'relevance', 'technology_nodes', 'relationships',
                                'innovation_signals', 'adoption_indicators', 'original_metadata']:
                try:
                    self.con.execute(f"DROP TABLE IF EXISTS {table_name}")
                except:
                    pass

        # Step 1: Load scored papers from checkpoints
        self._load_scored_papers()

        # Step 2: Load original papers metadata (if provided)
        if self.original_papers_path and self.original_papers_path.exists():
            self._load_original_metadata()

        # Step 3: Create indexes
        self.logger.info("Creating indexes...")
        self._create_indexes()

        self.logger.info("Database initialization complete!")
        self._print_database_stats()

    def _load_scored_papers(self):
        """Load scored papers from batch checkpoints."""
        # Find consolidated file first
        consolidated_files = list(self.scored_papers_dir.glob("all_papers_scored_*.json"))

        if consolidated_files:
            # Use consolidated file (faster)
            self.consolidated_file = consolidated_files[0]
            self.logger.info(f"Loading from consolidated file: {self.consolidated_file.name}")
            scored_papers = self._load_json_file(self.consolidated_file)
        else:
            # Load from individual checkpoints
            self.logger.info("Loading from individual checkpoint files...")
            checkpoint_files = sorted(self.scored_papers_dir.glob("checkpoints/checkpoint_[0-9]*.json"))

            # Exclude "relevant" files (they're subsets)
            checkpoint_files = [f for f in checkpoint_files if 'relevant' not in f.name]

            scored_papers = []
            for checkpoint_file in checkpoint_files:
                papers = self._load_json_file(checkpoint_file)
                scored_papers.extend(papers)
                self.logger.info(f"  Loaded {len(papers)} papers from {checkpoint_file.name}")

        self.logger.info(f"Total scored papers loaded: {len(scored_papers)}")

        # Create main papers table
        self._create_papers_table(scored_papers)

        # Create normalized tables
        self._create_relevance_table(scored_papers)
        self._create_technology_nodes_table(scored_papers)
        self._create_relationships_table(scored_papers)
        self._create_innovation_signals_table(scored_papers)
        self._create_adoption_indicators_table(scored_papers)

    def _load_json_file(self, file_path: Path) -> List[Dict]:
        """Load JSON file (handles both single object and array)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle both array and single object
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
            else:
                self.logger.warning(f"Unexpected JSON structure in {file_path}")
                return []
        except Exception as e:
            self.logger.error(f"Failed to load {file_path}: {e}")
            return []

    def _create_papers_table(self, scored_papers: List[Dict]):
        """Create main papers table from paper_metadata."""
        papers_data = []
        for paper in scored_papers:
            metadata = paper.get('paper_metadata', {})
            papers_data.append({
                'lens_id': metadata.get('lens_id'),
                'title': metadata.get('title'),
                'year_published': metadata.get('year_published'),
                'publication_type': metadata.get('publication_type'),
                'journal': metadata.get('journal'),
                'doi': metadata.get('doi'),
                'url': metadata.get('url')
            })

        df = pd.DataFrame(papers_data)
        self.con.execute("CREATE TABLE papers AS SELECT * FROM df")
        self.logger.info(f"  Created papers table: {len(df)} rows")

    def _create_relevance_table(self, scored_papers: List[Dict]):
        """Create relevance assessment table."""
        relevance_data = []
        for paper in scored_papers:
            metadata = paper.get('paper_metadata', {})
            relevance = paper.get('relevance_assessment', {})

            relevance_data.append({
                'lens_id': metadata.get('lens_id'),
                'relevance_score': relevance.get('relevance_score'),
                'is_relevant': relevance.get('is_relevant'),
                'relevance_category': relevance.get('relevance_category'),
                'confidence': relevance.get('confidence'),
                'justification': relevance.get('justification')
            })

        df = pd.DataFrame(relevance_data)
        self.con.execute("CREATE TABLE relevance AS SELECT * FROM df")
        self.logger.info(f"  Created relevance table: {len(df)} rows")

    def _create_technology_nodes_table(self, scored_papers: List[Dict]):
        """Create technology nodes table (unnested from arrays)."""
        nodes_data = []
        for paper in scored_papers:
            lens_id = paper.get('paper_metadata', {}).get('lens_id')
            nodes = paper.get('technology_nodes', [])

            for node in nodes:
                nodes_data.append({
                    'lens_id': lens_id,
                    'node_id': node.get('node_id'),
                    'node_type': node.get('node_type'),
                    'name': node.get('name'),
                    'description': node.get('description'),
                    'maturity': node.get('maturity'),
                    'domain': node.get('domain')
                })

        df = pd.DataFrame(nodes_data)
        if not df.empty:
            self.con.execute("CREATE TABLE technology_nodes AS SELECT * FROM df")
            self.logger.info(f"  Created technology_nodes table: {len(df)} rows")
        else:
            # Create empty table with schema
            self.con.execute("""
                CREATE TABLE technology_nodes (
                    lens_id VARCHAR,
                    node_id VARCHAR,
                    node_type VARCHAR,
                    name VARCHAR,
                    description VARCHAR,
                    maturity VARCHAR,
                    domain VARCHAR
                )
            """)
            self.logger.info("  Created empty technology_nodes table")

    def _create_relationships_table(self, scored_papers: List[Dict]):
        """Create relationships table (unnested from arrays)."""
        relationships_data = []
        for paper in scored_papers:
            lens_id = paper.get('paper_metadata', {}).get('lens_id')
            relationships = paper.get('relationships', [])

            for rel in relationships:
                relationships_data.append({
                    'lens_id': lens_id,
                    'subject': rel.get('subject'),
                    'predicate': rel.get('predicate'),
                    'object': rel.get('object'),
                    'confidence': rel.get('confidence'),
                    'evidence': rel.get('evidence')
                })

        df = pd.DataFrame(relationships_data)
        if not df.empty:
            self.con.execute("CREATE TABLE relationships AS SELECT * FROM df")
            self.logger.info(f"  Created relationships table: {len(df)} rows")
        else:
            # Create empty table with schema
            self.con.execute("""
                CREATE TABLE relationships (
                    lens_id VARCHAR,
                    subject VARCHAR,
                    predicate VARCHAR,
                    object VARCHAR,
                    confidence DOUBLE,
                    evidence VARCHAR
                )
            """)
            self.logger.info("  Created empty relationships table")

    def _create_innovation_signals_table(self, scored_papers: List[Dict]):
        """Create innovation signals table."""
        signals_data = []
        for paper in scored_papers:
            lens_id = paper.get('paper_metadata', {}).get('lens_id')
            signals = paper.get('innovation_signals', {})

            signals_data.append({
                'lens_id': lens_id,
                'research_stage': signals.get('research_stage'),
                'innovation_type': signals.get('innovation_type'),
                'impact_potential': signals.get('impact_potential'),
                'technical_risk': signals.get('technical_risk')
            })

        df = pd.DataFrame(signals_data)
        self.con.execute("CREATE TABLE innovation_signals AS SELECT * FROM df")
        self.logger.info(f"  Created innovation_signals table: {len(df)} rows")

    def _create_adoption_indicators_table(self, scored_papers: List[Dict]):
        """Create adoption indicators table (unnested from arrays)."""
        indicators_data = []
        for paper in scored_papers:
            lens_id = paper.get('paper_metadata', {}).get('lens_id')
            indicators = paper.get('innovation_signals', {}).get('adoption_indicators', [])

            for indicator in indicators:
                indicators_data.append({
                    'lens_id': lens_id,
                    'indicator_text': indicator
                })

        df = pd.DataFrame(indicators_data)
        if not df.empty:
            self.con.execute("CREATE TABLE adoption_indicators AS SELECT * FROM df")
            self.logger.info(f"  Created adoption_indicators table: {len(df)} rows")
        else:
            # Create empty table with schema
            self.con.execute("""
                CREATE TABLE adoption_indicators (
                    lens_id VARCHAR,
                    indicator_text VARCHAR
                )
            """)
            self.logger.info("  Created empty adoption_indicators table")

    def _load_original_metadata(self):
        """Load original papers.json for metadata enrichment."""
        self.logger.info(f"Loading original metadata from: {self.original_papers_path.name}")

        try:
            with open(self.original_papers_path, 'r', encoding='utf-8') as f:
                original_papers = json.load(f)

            # Extract relevant metadata fields
            metadata_list = []
            for paper in original_papers:
                metadata_list.append({
                    'lens_id': paper.get('lens_id'),
                    'date_published': paper.get('date_published'),
                    'references_count': paper.get('references_count', 0),
                    'citing_patent_count': paper.get('citing_patent_count', 0),
                    'scholarly_citations_count': paper.get('scholarly_citations_count', 0),
                    'authors': json.dumps(paper.get('authors', [])),  # Store as JSON string
                    'fields_of_study': json.dumps(paper.get('fields_of_study', []))
                })

            df = pd.DataFrame(metadata_list)
            self.con.execute("CREATE TABLE original_metadata AS SELECT * FROM df")
            self.logger.info(f"  Created original_metadata table: {len(df)} rows")

        except Exception as e:
            self.logger.error(f"Failed to load original metadata: {e}")

    def _create_indexes(self):
        """Create indexes on frequently queried columns."""
        try:
            # Papers table
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_papers_lens_id ON papers(lens_id)")

            # Relevance table
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_relevance_lens_id ON relevance(lens_id)")
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_relevance_score ON relevance(relevance_score)")
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_relevance_category ON relevance(relevance_category)")

            # Technology nodes
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_nodes_lens_id ON technology_nodes(lens_id)")
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_nodes_domain ON technology_nodes(domain)")

            # Relationships
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_relationships_lens_id ON relationships(lens_id)")

            # Innovation signals
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_signals_lens_id ON innovation_signals(lens_id)")
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_signals_innovation_type ON innovation_signals(innovation_type)")
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_signals_impact ON innovation_signals(impact_potential)")

            # Original metadata (if exists)
            try:
                self.con.execute("CREATE INDEX IF NOT EXISTS idx_metadata_lens_id ON original_metadata(lens_id)")
            except:
                pass  # Table might not exist

            self.logger.info("  Created indexes for query optimization")

        except Exception as e:
            self.logger.warning(f"  Index creation warning: {e}")

    def _print_database_stats(self):
        """Print database statistics."""
        self.logger.info("=" * 60)
        self.logger.info("Scholarly Papers Database Statistics")
        self.logger.info("=" * 60)

        # Table sizes
        for table_name in ['papers', 'relevance', 'technology_nodes', 'relationships',
                           'innovation_signals', 'adoption_indicators', 'original_metadata']:
            try:
                count = self.con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                self.logger.info(f"{table_name:25s}: {count:>10,} rows")
            except:
                pass

        # Relevance distribution
        try:
            stats = self.con.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN is_relevant THEN 1 ELSE 0 END) as relevant,
                    MIN(relevance_score) as min_score,
                    MAX(relevance_score) as max_score,
                    AVG(relevance_score) as avg_score
                FROM relevance
            """).fetchone()

            self.logger.info(f"\nRelevance Stats:")
            self.logger.info(f"  Total papers: {stats[0]}")
            self.logger.info(f"  Relevant: {stats[1]} ({stats[1]/stats[0]*100:.1f}%)")
            self.logger.info(f"  Score range: {stats[2]:.1f} - {stats[3]:.1f} (avg: {stats[4]:.2f})")
        except:
            pass

        # Innovation type distribution
        try:
            innovation_dist = self.con.execute("""
                SELECT innovation_type, COUNT(*) as count
                FROM innovation_signals
                WHERE innovation_type != 'not_applicable'
                GROUP BY innovation_type
                ORDER BY count DESC
            """).fetchdf()

            if not innovation_dist.empty:
                self.logger.info(f"\nInnovation Types:")
                for _, row in innovation_dist.iterrows():
                    self.logger.info(f"  {row['innovation_type']:30s}: {row['count']:>5}")
        except:
            pass

        self.logger.info("=" * 60)

    def get_top_papers_by_composite_score(
        self,
        limit: int = 200,
        min_relevance_score: float = 8.0,
        weighting: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top N papers ranked by composite score.

        Composite Score = weighted combination of:
        - Relevance score (LLM assessment)
        - Impact potential (innovation signals)
        - References count (citation quality indicator)
        - Innovation type (breakthrough > incremental)
        - Recency (publication year)

        Args:
            limit: Number of papers to return
            min_relevance_score: Minimum relevance score threshold
            weighting: Custom weights dict (default: balanced weighting)

        Returns:
            List of paper dicts with composite_score field
        """
        self.connect()

        # Default weighting
        if weighting is None:
            weighting = {
                'relevance': 0.4,
                'impact': 0.2,
                'references': 0.2,
                'innovation': 0.1,
                'recency': 0.1
            }

        # Check if original_metadata table exists
        has_metadata = False
        try:
            self.con.execute("SELECT 1 FROM original_metadata LIMIT 1")
            has_metadata = True
        except:
            self.logger.warning("original_metadata table not found. Using simplified scoring.")

        # Build query based on available data
        if has_metadata:
            query = f"""
            WITH scored_papers AS (
                SELECT
                    p.lens_id,
                    p.title,
                    p.year_published,
                    p.publication_type,
                    p.journal,
                    p.doi,
                    p.url,
                    r.relevance_score,
                    r.relevance_category,
                    r.confidence,
                    i.innovation_type,
                    i.impact_potential,
                    i.research_stage,
                    m.references_count,
                    m.scholarly_citations_count,

                    -- Normalized scores (0-1 scale)
                    (r.relevance_score - 8.0) / (9.0 - 8.0) as norm_relevance,

                    CASE i.impact_potential
                        WHEN 'very_high' THEN 1.0
                        WHEN 'high' THEN 0.7
                        WHEN 'medium' THEN 0.4
                        ELSE 0.1
                    END as norm_impact,

                    CASE
                        WHEN m.references_count IS NULL THEN 0.5
                        ELSE LEAST(1.0, m.references_count / 100.0)
                    END as norm_references,

                    CASE i.innovation_type
                        WHEN 'breakthrough' THEN 1.0
                        WHEN 'incremental_breakthrough' THEN 0.7
                        WHEN 'incremental' THEN 0.4
                        ELSE 0.1
                    END as norm_innovation,

                    CASE
                        WHEN p.year_published IS NULL THEN 0.5
                        ELSE (CAST(p.year_published AS INTEGER) - 2010) / (2025.0 - 2010.0)
                    END as norm_recency

                FROM papers p
                JOIN relevance r ON p.lens_id = r.lens_id
                JOIN innovation_signals i ON p.lens_id = i.lens_id
                LEFT JOIN original_metadata m ON p.lens_id = m.lens_id
                WHERE r.relevance_score >= {min_relevance_score}
                  AND r.is_relevant = true
            )
            SELECT
                *,
                (
                    {weighting['relevance']} * norm_relevance +
                    {weighting['impact']} * norm_impact +
                    {weighting['references']} * norm_references +
                    {weighting['innovation']} * norm_innovation +
                    {weighting['recency']} * norm_recency
                ) as composite_score
            FROM scored_papers
            ORDER BY composite_score DESC
            LIMIT {limit}
            """
        else:
            # Simplified query without original metadata
            query = f"""
            WITH scored_papers AS (
                SELECT
                    p.lens_id,
                    p.title,
                    p.year_published,
                    p.publication_type,
                    p.journal,
                    p.doi,
                    p.url,
                    r.relevance_score,
                    r.relevance_category,
                    r.confidence,
                    i.innovation_type,
                    i.impact_potential,
                    i.research_stage,

                    -- Normalized scores (0-1 scale)
                    (r.relevance_score - 8.0) / (9.0 - 8.0) as norm_relevance,

                    CASE i.impact_potential
                        WHEN 'very_high' THEN 1.0
                        WHEN 'high' THEN 0.7
                        WHEN 'medium' THEN 0.4
                        ELSE 0.1
                    END as norm_impact,

                    CASE i.innovation_type
                        WHEN 'breakthrough' THEN 1.0
                        WHEN 'incremental_breakthrough' THEN 0.7
                        WHEN 'incremental' THEN 0.4
                        ELSE 0.1
                    END as norm_innovation,

                    CASE
                        WHEN p.year_published IS NULL THEN 0.5
                        ELSE (CAST(p.year_published AS INTEGER) - 2010) / (2025.0 - 2010.0)
                    END as norm_recency

                FROM papers p
                JOIN relevance r ON p.lens_id = r.lens_id
                JOIN innovation_signals i ON p.lens_id = i.lens_id
                WHERE r.relevance_score >= {min_relevance_score}
                  AND r.is_relevant = true
            )
            SELECT
                *,
                (
                    {weighting['relevance']} * norm_relevance +
                    {weighting['impact']} * norm_impact +
                    {weighting['innovation']} * norm_innovation +
                    {weighting['recency']} * norm_recency
                ) as composite_score
            FROM scored_papers
            ORDER BY composite_score DESC
            LIMIT {limit}
            """

        try:
            df = self.con.execute(query).fetchdf()
            self.logger.info(f"Retrieved {len(df)} papers by composite score")
            return df.to_dict('records')

        except Exception as e:
            self.logger.error(f"Query failed: {e}")
            raise

    def query_papers_by_relevance(
        self,
        min_score: float = 8.0,
        max_score: float = 10.0,
        categories: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Query papers by relevance score and category.

        Args:
            min_score: Minimum relevance score
            max_score: Maximum relevance score
            categories: List of relevance categories to include

        Returns:
            DataFrame with papers matching criteria
        """
        self.connect()

        category_filter = ""
        if categories:
            category_list = "', '".join(categories)
            category_filter = f"AND r.relevance_category IN ('{category_list}')"

        query = f"""
        SELECT
            p.lens_id,
            p.title,
            p.year_published,
            p.publication_type,
            r.relevance_score,
            r.relevance_category,
            r.confidence
        FROM papers p
        JOIN relevance r ON p.lens_id = r.lens_id
        WHERE r.relevance_score >= {min_score}
          AND r.relevance_score <= {max_score}
          {category_filter}
        ORDER BY r.relevance_score DESC
        """

        return self.con.execute(query).fetchdf()

    def get_knowledge_graph(self, lens_ids: List[str]) -> Dict[str, Any]:
        """
        Extract knowledge graph (nodes + relationships) for given papers.

        Args:
            lens_ids: List of paper lens_ids

        Returns:
            Dict with 'nodes' and 'relationships' lists
        """
        self.connect()

        ids_str = "', '".join(lens_ids)

        # Get nodes
        nodes_query = f"""
        SELECT * FROM technology_nodes
        WHERE lens_id IN ('{ids_str}')
        """
        nodes_df = self.con.execute(nodes_query).fetchdf()

        # Get relationships
        rels_query = f"""
        SELECT * FROM relationships
        WHERE lens_id IN ('{ids_str}')
        """
        rels_df = self.con.execute(rels_query).fetchdf()

        return {
            'nodes': nodes_df.to_dict('records'),
            'relationships': rels_df.to_dict('records')
        }


# Convenience function for quick access
def get_scholarly_papers_database(
    scored_papers_dir: str = "data/eVTOL/lens_scholarly/batch_processing",
    original_papers_path: Optional[str] = None
) -> ScholarlyPapersDatabase:
    """
    Get initialized Scholarly Papers database connection.

    Args:
        scored_papers_dir: Directory containing batch checkpoints
        original_papers_path: Path to papers.json (optional)

    Returns:
        ScholarlyPapersDatabase instance (connected and initialized)
    """
    db = ScholarlyPapersDatabase(
        scored_papers_dir=scored_papers_dir,
        original_papers_path=original_papers_path
    )
    db.initialize()  # Initialize if not already done
    return db


if __name__ == "__main__":
    # Test database initialization
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("Initializing Scholarly Papers database...")
    db = ScholarlyPapersDatabase(
        scored_papers_dir="data/eVTOL/lens_scholarly/batch_processing",
        original_papers_path="data/eVTOL/lens_scholarly/papers.json"
    )
    db.initialize()

    # Test query
    print("\nTesting composite scoring - Top 10 papers:")
    top_papers = db.get_top_papers_by_composite_score(limit=10)

    if top_papers:
        print(f"\nFound {len(top_papers)} papers")
        print("\nTop 5 by composite score:")
        for i, paper in enumerate(top_papers[:5], 1):
            title = paper['title'][:60] if paper['title'] else 'N/A'
            print(f"\n{i}. {title}")
            print(f"   Composite Score: {paper['composite_score']:.3f}")
            print(f"   Relevance: {paper['relevance_score']:.1f} | Impact: {paper['impact_potential']}")
            print(f"   Innovation: {paper['innovation_type']} | Year: {paper['year_published']}")
    else:
        print("\nNo papers found in dataset")

    db.close()
