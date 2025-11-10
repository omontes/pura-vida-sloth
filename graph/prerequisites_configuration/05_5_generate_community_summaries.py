"""
Script 5.5: Generate Community Summaries (Batch Processing)
===========================================================

Purpose: Generate semantic descriptions for community detection variants using
concurrent batch processing for faster execution.

This script creates:
- Community nodes for 3 Louvain variants (v0-v2)
- LLM-generated summaries (1-2 sentences per community)
- Vector embeddings (768-dim) for each summary
- Rich metadata (member counts, top entities, doc type distribution)
- BELONGS_TO_COMMUNITY relationships linking members to communities
- Indexes on Community.id for fast queries

Models:
- GPT-4o-mini for summaries ($0.000150 per 1k input, $0.000600 per 1k output)
- text-embedding-3-small for embeddings ($0.00002 per 1k tokens)

Estimated cost: ~$0.01-0.05 depending on community counts

Runtime: ~3-5 minutes (concurrent processing)
Cost: $0.01-0.05 (OpenAI API)
Safe to run: YES (but requires approval - creates new nodes)

IMPORTANT: Requires Script 5 (compute_communities.py) to run first

Features:
- Concurrent processing with ThreadPoolExecutor (4 workers default)
- Checkpoint/resume capability (saves every 100 communities)
- Progress tracking with tqdm
- Test mode (--limit 10 for first 10 communities)
- Minimum member filtering (--min-members, default: 1 = all)
- Cleanup mode (--clean to delete existing Community nodes)
- Error handling with retry logic
- Merge functionality for checkpoint files

Usage:
    # Clean + filter small communities (recommended)
    python graph/prerequisites_configuration/05_5_generate_community_summaries.py --clean --min-members 5

    # Test with first 10 communities
    python graph/prerequisites_configuration/05_5_generate_community_summaries.py --clean --limit 10

    # Full run (all communities, no filtering)
    python graph/prerequisites_configuration/05_5_generate_community_summaries.py

    # Auto-approve mode
    python graph/prerequisites_configuration/05_5_generate_community_summaries.py --clean --min-members 5 --auto-approve
"""

import os
import json
import sys
import argparse
import time
import datetime
import traceback
from typing import List, Dict, Any, Optional, Tuple, Set
from neo4j import GraphDatabase
from dotenv import load_dotenv
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import islice
from tqdm import tqdm
import io
import contextlib

# Load environment variables
load_dotenv()


def chunked(it, size):
    """Partition an iterable into chunks (lists) of 'size' elements."""
    it = iter(it)
    while True:
        batch = list(islice(it, size))
        if not batch:
            break
        yield batch


class CommunityCheckpointManager:
    """Manages checkpoint state for batch processing of community summaries."""

    def __init__(self, checkpoint_file: str = ".checkpoint_community_batch.json"):
        """Initialize checkpoint manager."""
        self.checkpoint_file = checkpoint_file
        self.completed_ids: Set[str] = set()
        self.load()

    def load(self) -> None:
        """Load checkpoint state from disk if exists."""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.completed_ids = set(data.get("completed_ids", []))
                print(f"  Loaded checkpoint: {len(self.completed_ids)} communities already processed")
            except Exception as e:
                print(f"  Warning: Could not load checkpoint file: {e}")
                self.completed_ids = set()
        else:
            self.completed_ids = set()

    def save(self) -> None:
        """Save checkpoint state to disk."""
        try:
            data = {
                "completed_ids": sorted(list(self.completed_ids))
            }
            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"  Warning: Could not save checkpoint file: {e}")

    def is_completed(self, community_id: str) -> bool:
        """Check if community has been processed."""
        return community_id in self.completed_ids

    def mark_batch_completed(self, community_ids: List[str]) -> None:
        """Mark multiple communities as completed."""
        self.completed_ids.update(community_ids)
        self.save()

    def get_completed_count(self) -> int:
        """Get count of completed communities."""
        return len(self.completed_ids)


def save_checkpoint_files(
    results: List[Dict[str, Any]],
    start_idx: int,
    end_idx: int,
    checkpoint_dir: str
) -> str:
    """
    Save checkpoint file for a batch of community results.

    Args:
        results: List of community summary results
        start_idx: Starting index of this batch
        end_idx: Ending index of this batch
        checkpoint_dir: Directory to save checkpoint files

    Returns:
        Path to saved checkpoint file
    """
    os.makedirs(checkpoint_dir, exist_ok=True)

    # Format indices with leading zeros for sorting
    start_str = f"{start_idx:04d}"
    end_str = f"{end_idx:04d}"

    # Save results
    checkpoint_file = os.path.join(checkpoint_dir, f"communities_{start_str}-{end_str}.json")
    with open(checkpoint_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return checkpoint_file


def merge_checkpoints(checkpoint_dir: str, output_file: str) -> Dict[str, Any]:
    """
    Merge all checkpoint files into final output file.

    Args:
        checkpoint_dir: Directory containing checkpoint files
        output_file: Path for merged output file

    Returns:
        Dictionary with statistics
    """
    if not os.path.exists(checkpoint_dir):
        return {"total": 0, "duplicates_removed": 0}

    # Find all checkpoint files
    checkpoint_files = sorted([
        f for f in os.listdir(checkpoint_dir)
        if f.startswith("communities_") and f.endswith(".json")
    ])

    # Load all results
    all_results = []
    for filename in checkpoint_files:
        filepath = os.path.join(checkpoint_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                batch = json.load(f)
                all_results.extend(batch)
        except Exception as e:
            print(f"  Warning: Could not load checkpoint {filename}: {e}")

    # Deduplicate by community_id (in case of overlapping checkpoints)
    seen = set()
    deduped = []
    for result in all_results:
        comm_id = result.get("community_id", "")
        if comm_id and comm_id not in seen:
            seen.add(comm_id)
            deduped.append(result)

    # Save merged file
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(deduped, f, indent=2, ensure_ascii=False)

    print(f"    Total communities: {len(deduped)}")
    print(f"    Duplicates removed: {len(all_results) - len(deduped)}")

    return {
        "total": len(deduped),
        "duplicates_removed": len(all_results) - len(deduped)
    }


class CommunitySummarizer:
    """Generate LLM-based summaries for community detection variants."""

    def __init__(self, neo4j_uri: str, neo4j_username: str, neo4j_password: str,
                 neo4j_database: str, openai_api_key: str):
        """Initialize clients."""
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
        self.database = neo4j_database
        self.openai_client = OpenAI(api_key=openai_api_key)

        # Community variant metadata (ONLY Louvain v0-v2)
        self.variants = [
            {"version": 0, "algorithm": "Louvain", "resolution": 0.8},
            {"version": 1, "algorithm": "Louvain", "resolution": 1.0},
            {"version": 2, "algorithm": "Louvain", "resolution": 1.2},
        ]

    def get_community_list(self, version: int) -> List[int]:
        """Get list of all community IDs for a given version."""
        cypher = f"""
        MATCH (n)
        WHERE n.community_v{version} IS NOT NULL
        RETURN DISTINCT n.community_v{version} AS community_id
        ORDER BY community_id
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(cypher)
            return [record['community_id'] for record in result]

    def get_community_metadata(self, version: int, community_id: int) -> Optional[Dict[str, Any]]:
        """Gather metadata for a community."""
        cypher = f"""
        MATCH (n)
        WHERE n.community_v{version} = $community_id
        WITH n, labels(n) AS node_labels
        RETURN
            count(n) AS member_count,
            collect(DISTINCT CASE WHEN 'Technology' IN node_labels THEN n.name END) AS all_technologies,
            collect(DISTINCT CASE WHEN 'Company' IN node_labels THEN n.name END) AS all_companies,
            collect(DISTINCT CASE WHEN 'Document' IN node_labels THEN n.doc_type END) AS all_doc_types,
            collect(DISTINCT CASE WHEN 'Document' IN node_labels THEN n.title END)[0..5] AS sample_doc_titles,
            sum(CASE WHEN 'Technology' IN node_labels THEN 1 ELSE 0 END) AS tech_count,
            sum(CASE WHEN 'Company' IN node_labels THEN 1 ELSE 0 END) AS company_count,
            sum(CASE WHEN 'Document' IN node_labels THEN 1 ELSE 0 END) AS doc_count
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(cypher, {"community_id": community_id}).single()

            if not result:
                return None

            # Clean up nulls from lists
            all_technologies = [t for t in result['all_technologies'] if t is not None]
            all_companies = [c for c in result['all_companies'] if c is not None]
            all_doc_types = [d for d in result['all_doc_types'] if d is not None]
            sample_titles = [t for t in result['sample_doc_titles'] if t is not None]

            # Get doc type distribution
            doc_type_distribution = {}
            for doc_type in all_doc_types:
                if doc_type not in doc_type_distribution:
                    doc_type_distribution[doc_type] = 0
                doc_type_distribution[doc_type] += 1

            # Top 5 technologies and companies (limited to what we have)
            top_technologies = all_technologies[:5]
            top_companies = all_companies[:5]

            return {
                "member_count": result['member_count'],
                "tech_count": result['tech_count'],
                "company_count": result['company_count'],
                "doc_count": result['doc_count'],
                "top_technologies": top_technologies,
                "top_companies": top_companies,
                "doc_type_distribution": doc_type_distribution,
                "sample_doc_titles": sample_titles,
            }

    def generate_summary(self, metadata: Dict[str, Any]) -> str:
        """Generate LLM summary for a community."""
        # Build prompt
        tech_str = ", ".join(metadata['top_technologies']) if metadata['top_technologies'] else "None"
        company_str = ", ".join(metadata['top_companies']) if metadata['top_companies'] else "None"
        doc_str = "\n- ".join(metadata['sample_doc_titles'][:3]) if metadata['sample_doc_titles'] else "None"

        prompt = f"""You are analyzing a community of {metadata['member_count']} nodes in a technology graph.

Members include:
- Technologies: {tech_str}
- Companies: {company_str}
- Sample documents:
{doc_str}

Summarize this community in 1-2 sentences focusing on:
1. The main technological domain
2. Key companies or research areas
3. Common themes

Keep it concise and descriptive."""

        # Suppress output during API call
        with contextlib.redirect_stdout(io.StringIO()):
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=100
            )
        return response.choices[0].message.content.strip()

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate vector embedding for community summary.

        Args:
            text: Summary text to embed

        Returns:
            768-dimensional embedding vector
        """
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                response = self.openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text,
                    dimensions=768
                )
            return response.data[0].embedding
        except Exception as e:
            print(f"  [WARN]  OpenAI embedding error: {e}")
            raise

    def create_community_node(self, version: int, community_id: int,
                             metadata: Dict[str, Any], summary: str,
                             embedding: List[float],
                             variant_info: Dict[str, Any]) -> bool:
        """Create Community node in Neo4j with embedding. Returns True if successful."""
        cypher = """
        MERGE (c:Community {id: $id})
        SET c.version = $version,
            c.community_id = $community_id,
            c.algorithm = $algorithm,
            c.resolution = $resolution,
            c.member_count = $member_count,
            c.tech_count = $tech_count,
            c.company_count = $company_count,
            c.doc_count = $doc_count,
            c.summary = $summary,
            c.embedding = $embedding,
            c.top_technologies = $top_technologies,
            c.top_companies = $top_companies,
            c.doc_type_distribution = $doc_type_distribution
        RETURN c.id AS id
        """

        community_node_id = f"v{version}_{community_id}"

        try:
            # Convert doc_type_distribution dict to JSON string (Neo4j doesn't support nested maps)
            doc_type_dist_json = json.dumps(metadata['doc_type_distribution'])

            with self.driver.session(database=self.database) as session:
                result = session.run(cypher, {
                    "id": community_node_id,
                    "version": version,
                    "community_id": community_id,
                    "algorithm": variant_info['algorithm'],
                    "resolution": variant_info['resolution'],
                    "member_count": metadata['member_count'],
                    "tech_count": metadata['tech_count'],
                    "company_count": metadata['company_count'],
                    "doc_count": metadata['doc_count'],
                    "summary": summary,
                    "embedding": embedding,
                    "top_technologies": metadata['top_technologies'],
                    "top_companies": metadata['top_companies'],
                    "doc_type_distribution": doc_type_dist_json  # Store as JSON string
                })
                return result.single() is not None
        except Exception as e:
            print(f"  [ERROR] Failed to create community node {community_node_id}: {e}")
            return False

    def create_relationships(self, version: int, community_id: int) -> int:
        """Create BELONGS_TO_COMMUNITY relationships. Returns count of linked nodes."""
        cypher = f"""
        MATCH (c:Community {{id: $community_node_id}})
        MATCH (n)
        WHERE n.community_v{version} = $community_id
        MERGE (n)-[:BELONGS_TO_COMMUNITY]->(c)
        RETURN count(n) AS linked_count
        """

        community_node_id = f"v{version}_{community_id}"

        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(cypher, {
                    "community_node_id": community_node_id,
                    "community_id": community_id
                }).single()
                return result['linked_count'] if result else 0
        except Exception as e:
            print(f"  [ERROR] Failed to create relationships for {community_node_id}: {e}")
            return 0

    def close(self):
        """Close Neo4j driver."""
        self.driver.close()


def safe_process_community(
    summarizer: CommunitySummarizer,
    version: int,
    community_id: int,
    variant_info: Dict[str, Any],
    retries: int = 0,
    max_retries: int = 2
) -> Tuple[bool, Dict[str, Any]]:
    """
    Process a single community with retry logic.

    Args:
        summarizer: Initialized CommunitySummarizer
        version: Community version (0-2)
        community_id: Numeric community ID
        variant_info: Variant metadata (algorithm, resolution)
        retries: Current retry count
        max_retries: Maximum retry attempts

    Returns:
        Tuple of (success: bool, result: dict or error: dict)
    """
    community_node_id = f"v{version}_{community_id}"

    attempt = 0
    while attempt <= max_retries:
        try:
            # Gather metadata
            metadata = summarizer.get_community_metadata(version, community_id)
            if not metadata:
                return False, {
                    "community_id": community_node_id,
                    "error": "No members found"
                }

            # Generate summary
            summary = summarizer.generate_summary(metadata)

            # Generate embedding from summary
            embedding = summarizer.generate_embedding(summary)

            # Create Community node with embedding
            node_created = summarizer.create_community_node(
                version, community_id, metadata, summary, embedding, variant_info
            )

            if not node_created:
                raise Exception("Failed to create Community node")

            # Create relationships
            linked_count = summarizer.create_relationships(version, community_id)

            return True, {
                "community_id": community_node_id,
                "version": version,
                "numeric_id": community_id,
                "algorithm": variant_info['algorithm'],
                "resolution": variant_info['resolution'],
                "member_count": metadata['member_count'],
                "linked_count": linked_count,
                "summary": summary
            }

        except Exception as e:
            attempt += 1
            if attempt > max_retries:
                return False, {
                    "community_id": community_node_id,
                    "error": f"{type(e).__name__}: {str(e)}",
                    "traceback": traceback.format_exc()
                }
            # Exponential backoff
            time.sleep(2 ** (attempt - 1))

    return False, {
        "community_id": community_node_id,
        "error": "Max retries exceeded"
    }


def cleanup_existing_communities() -> int:
    """
    Delete all existing Community nodes and BELONGS_TO_COMMUNITY relationships.

    Returns:
        Number of Community nodes deleted
    """
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    driver = GraphDatabase.driver(uri, auth=(username, password))

    cypher = """
    MATCH (c:Community)
    WITH count(c) AS community_count
    MATCH (c:Community)
    DETACH DELETE c
    RETURN community_count
    """

    with driver.session(database=database) as session:
        result = session.run(cypher).single()
        deleted_count = result['community_count'] if result else 0

    driver.close()
    return deleted_count


def create_community_indexes() -> bool:
    """
    Create indexes for Community nodes to enable fast queries.

    Returns:
        True if successful, False otherwise
    """
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    driver = GraphDatabase.driver(uri, auth=(username, password))

    cypher = """
    CREATE INDEX community_id IF NOT EXISTS FOR (c:Community) ON (c.id)
    """

    try:
        with driver.session(database=database) as session:
            session.run(cypher)
        driver.close()
        return True
    except Exception as e:
        print(f"  [WARN]  Error creating index: {e}")
        driver.close()
        return False


def estimate_cost(min_members: int = 1) -> Dict[str, Any]:
    """
    Estimate community summary generation cost with optional member filtering.

    Args:
        min_members: Minimum community size to include (default: 1 = all)

    Returns:
        Dictionary with cost estimates and statistics
    """
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    driver = GraphDatabase.driver(uri, auth=(username, password))

    total_communities = 0
    total_communities_unfiltered = 0
    variant_counts = []

    with driver.session(database=database) as session:
        # Count communities for v0-v2 only (Louvain variants)
        for version in range(3):
            # Count all communities (unfiltered)
            result_all = session.run(f"""
                MATCH (n)
                WHERE n.community_v{version} IS NOT NULL
                RETURN count(DISTINCT n.community_v{version}) AS count
            """).single()
            count_all = result_all['count'] if result_all else 0
            total_communities_unfiltered += count_all

            # Count communities with >= min_members
            if min_members > 1:
                result_filtered = session.run(f"""
                    MATCH (n)
                    WHERE n.community_v{version} IS NOT NULL
                    WITH n.community_v{version} AS comm_id
                    MATCH (m)
                    WHERE m.community_v{version} = comm_id
                    WITH comm_id, count(m) AS size
                    WHERE size >= $min_members
                    RETURN count(DISTINCT comm_id) AS count
                """, {"min_members": min_members}).single()
                count_filtered = result_filtered['count'] if result_filtered else 0
            else:
                count_filtered = count_all

            variant_counts.append(count_filtered)
            total_communities += count_filtered

    driver.close()

    # Estimate tokens
    # Summary: ~150 tokens per community (prompt + response)
    summary_input_tokens = total_communities * 120
    summary_output_tokens = total_communities * 30

    # Embeddings: ~30 tokens per summary for embedding input
    embedding_tokens = total_communities * 30

    # GPT-4o-mini pricing: $0.000150/1k input, $0.000600/1k output
    summary_cost = (summary_input_tokens / 1000) * 0.000150 + (summary_output_tokens / 1000) * 0.000600

    # text-embedding-3-small pricing: $0.00002/1k tokens
    embedding_cost = (embedding_tokens / 1000) * 0.00002

    total_cost = summary_cost + embedding_cost

    return {
        "variant_counts": variant_counts,
        "total_communities": total_communities,
        "total_communities_unfiltered": total_communities_unfiltered,
        "filtered_out": total_communities_unfiltered - total_communities,
        "min_members": min_members,
        "estimated_summary_input_tokens": summary_input_tokens,
        "estimated_summary_output_tokens": summary_output_tokens,
        "estimated_embedding_tokens": embedding_tokens,
        "estimated_summary_cost_usd": round(summary_cost, 4),
        "estimated_embedding_cost_usd": round(embedding_cost, 4),
        "estimated_cost_usd": round(total_cost, 4),
        "estimated_runtime_minutes": round((total_communities * 0.15) / 60, 1)  # Slightly longer with embeddings
    }


def batch_process_communities(
    limit: Optional[int] = None,
    max_workers: int = 4,
    subbatch_size: int = 8,
    checkpoint_interval: int = 100,
    resume: bool = True,
    auto_approve: bool = False,
    min_members: int = 1,
    clean: bool = False
):
    """
    Batch process community summaries with concurrent execution.

    Args:
        limit: Maximum number of communities to process per variant (None = all)
        max_workers: Number of concurrent workers
        subbatch_size: Communities per sub-batch
        checkpoint_interval: Save checkpoint every N communities
        resume: Resume from existing checkpoints if True
        auto_approve: Skip confirmation prompt
        min_members: Minimum community size to process (default: 1 = all)
        clean: Delete existing Community nodes before processing
    """
    print("="*80)
    print("GENERATING COMMUNITY SUMMARIES (BATCH PROCESSING)")
    print("="*80)

    # Load environment
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not all([uri, password, openai_api_key]):
        raise ValueError("Missing required environment variables")

    # Cleanup existing communities if requested
    if clean:
        print("\n[CLEANUP] Removing existing Community nodes...")
        deleted_count = cleanup_existing_communities()
        print(f"  Deleted {deleted_count} Community nodes")

        print("\n[INDEXES] Creating Community indexes...")
        index_created = create_community_indexes()
        if index_created:
            print(f"  ✓ Community index created successfully")
        else:
            print(f"  [WARN]  Index creation failed (may already exist)")

    # Estimate cost first
    step_num = "[1/5]" if not clean else "[1/7]"
    print(f"\n{step_num} Estimating cost...")
    estimate = estimate_cost(min_members=min_members)

    for i, count in enumerate(estimate['variant_counts']):
        print(f"  v{i}: {count} communities")

    if estimate['filtered_out'] > 0:
        print(f"  Filtered out (< {min_members} members): {estimate['filtered_out']}")

    print(f"  Total to process: {estimate['total_communities']}")
    print(f"  Estimated summary cost: ${estimate['estimated_summary_cost_usd']}")
    print(f"  Estimated embedding cost: ${estimate['estimated_embedding_cost_usd']}")
    print(f"  Total estimated cost: ${estimate['estimated_cost_usd']}")
    print(f"  Estimated runtime: {estimate['estimated_runtime_minutes']} minutes (sequential)")
    print(f"  With {max_workers} workers: ~{round(estimate['estimated_runtime_minutes'] / max_workers, 1)} minutes")

    if estimate['total_communities'] == 0:
        print("\n[ERROR] No communities found!")
        print("  Make sure Script 5 (compute_communities.py) has been run first.")
        return

    if limit:
        print(f"\n[TEST MODE] Processing first {limit} communities per variant")

    # Confirm before proceeding
    if not auto_approve:
        print("\n[WARN]  This operation will call OpenAI API and incur costs.")
        response = input("Proceed? (yes/no): ").strip().lower()
        if response != 'yes':
            print("[ERROR] Aborted by user")
            return
    else:
        print("\n[AUTO-APPROVE] Proceeding automatically...")

    # Initialize summarizer
    print("\n[2/5] Initializing summarizer...")
    summarizer = CommunitySummarizer(uri, username, password, database, openai_api_key)
    print(f"  Model: gpt-4o-mini")
    print(f"  Max Workers: {max_workers}")
    print(f"  Sub-batch Size: {subbatch_size}")

    # Setup checkpoint system
    checkpoint_dir = "graph/prerequisites_configuration/batch_processing/checkpoints"
    os.makedirs(checkpoint_dir, exist_ok=True)

    checkpoint_file = "graph/prerequisites_configuration/.checkpoint_community_batch.json"
    checkpoint_mgr = CommunityCheckpointManager(checkpoint_file)

    print(f"\n[CHECKPOINT] Checkpoint system active")
    print(f"  Checkpoint interval: Every {checkpoint_interval} communities")
    print(f"  Checkpoint directory: {checkpoint_dir}")

    # Prepare inputs
    print("\n[3/5] Preparing inputs...")
    inputs: List[Dict[str, Any]] = []
    total_found = 0
    filtered_by_size = 0

    for variant in summarizer.variants:
        version = variant['version']
        community_ids = summarizer.get_community_list(version)
        total_found += len(community_ids)

        # Apply limit if specified
        if limit:
            community_ids = community_ids[:limit]

        for community_id in community_ids:
            community_node_id = f"v{version}_{community_id}"

            # Skip if already completed and resume is enabled
            if resume and checkpoint_mgr.is_completed(community_node_id):
                continue

            # Filter by minimum members if specified
            if min_members > 1:
                metadata = summarizer.get_community_metadata(version, community_id)
                if metadata and metadata['member_count'] < min_members:
                    filtered_by_size += 1
                    continue

            inputs.append({
                "version": version,
                "community_id": community_id,
                "variant_info": variant,
                "community_node_id": community_node_id
            })

    total_to_process = len(inputs)
    already_completed = checkpoint_mgr.get_completed_count()

    if min_members > 1:
        print(f"  Total communities found: {total_found}")
        print(f"  Filtered out (< {min_members} members): {filtered_by_size}")
    if already_completed > 0 and resume:
        print(f"  Previously completed: {already_completed} communities")
    print(f"  Remaining to process: {total_to_process} communities")

    if total_to_process == 0:
        print("\n  All communities already processed! Merging existing checkpoints...")
        output_file = "graph/prerequisites_configuration/batch_processing/all_communities.json"
        merge_checkpoints(checkpoint_dir, output_file)
        print(f"\n  Checkpoint merge complete!")
        summarizer.close()
        return

    # Process in concurrent sub-batches
    print(f"\n[4/5] Processing communities in concurrent sub-batches...")
    print("-" * 80)

    results: List[Dict[str, Any]] = []
    error_communities: List[Dict[str, Any]] = []

    t0_global = time.perf_counter()

    # Track checkpoint batch
    checkpoint_batch_results = []
    checkpoint_batch_ids = []

    with tqdm(total=total_to_process, desc="Processing communities", unit="community") as pbar:
        base = 0
        for sub in chunked(inputs, subbatch_size):
            # Execute this sub-batch concurrently
            futures = {}
            t_subbatch = time.perf_counter()

            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                for j, item in enumerate(sub):
                    idx_global = base + j
                    futures[ex.submit(
                        safe_process_community,
                        summarizer,
                        item["version"],
                        item["community_id"],
                        item["variant_info"],
                        0,  # retries
                        2   # max_retries
                    )] = (idx_global, item)

                for future in as_completed(futures):
                    idx_global, item = futures[future]
                    try:
                        ok, data = future.result()
                        if ok:
                            results.append(data)
                            checkpoint_batch_results.append(data)
                            checkpoint_batch_ids.append(item["community_node_id"])

                            # Save checkpoint when interval is reached
                            if len(checkpoint_batch_results) >= checkpoint_interval:
                                # Calculate actual range
                                start_idx = base - len(checkpoint_batch_results) + 1
                                end_idx = base

                                # Save checkpoint files
                                save_checkpoint_files(
                                    results=checkpoint_batch_results,
                                    start_idx=start_idx,
                                    end_idx=end_idx,
                                    checkpoint_dir=checkpoint_dir
                                )

                                # Mark as completed
                                checkpoint_mgr.mark_batch_completed(checkpoint_batch_ids)

                                # Reset checkpoint batch
                                checkpoint_batch_results = []
                                checkpoint_batch_ids = []
                        else:
                            error_communities.append(data)
                    except Exception as e:
                        # Unexpected error getting future result
                        error_communities.append({
                            "community_id": item["community_node_id"],
                            "error": f"FUTURE_FAILURE: {type(e).__name__}: {str(e)}",
                            "traceback": traceback.format_exc()
                        })
                    finally:
                        pbar.update(1)

            # Calculate ETA
            iter_sec = time.perf_counter() - t_subbatch
            done = min(base + len(sub), total_to_process)
            elapsed = time.perf_counter() - t0_global
            avg = elapsed / max(1, done)
            remaining_sec = avg * (total_to_process - done)
            eta = datetime.timedelta(seconds=max(0, int(remaining_sec)))

            pbar.set_postfix(batch_s=f"{iter_sec:.1f}", avg_s=f"{avg:.2f}", eta=str(eta))

            base += len(sub)

        # Save any remaining communities in checkpoint batch
        if checkpoint_batch_results and checkpoint_batch_ids:
            start_idx = base - len(checkpoint_batch_results)
            end_idx = base - 1

            save_checkpoint_files(
                results=checkpoint_batch_results,
                start_idx=start_idx,
                end_idx=end_idx,
                checkpoint_dir=checkpoint_dir
            )

            checkpoint_mgr.mark_batch_completed(checkpoint_batch_ids)

    elapsed_total = time.perf_counter() - t0_global
    print("\n" + "-" * 80)
    print(f"Processing complete in {datetime.timedelta(seconds=int(elapsed_total))}")

    # Merge checkpoints and save final results
    print(f"\n[5/5] Merging checkpoints and saving final results...")

    output_file = "graph/prerequisites_configuration/batch_processing/all_communities.json"
    merge_stats = merge_checkpoints(checkpoint_dir, output_file)

    # Load merged results for statistics
    with open(output_file, "r", encoding="utf-8") as f:
        all_results = json.load(f)

    # Calculate statistics
    total_processed = len(all_results)
    total_errors = len(error_communities)

    print(f"\n  Total processed: {total_processed}")
    print(f"  Errors: {total_errors}")
    print(f"  ✓ Saved all results: {output_file}")

    # Save errors
    if error_communities:
        error_file = "graph/prerequisites_configuration/batch_processing/processing_errors.json"
        with open(error_file, "w", encoding="utf-8") as f:
            json.dump(error_communities, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Saved error log: {error_file}")

    # Summary by variant
    variant_stats = {}
    for result in all_results:
        version = result.get("version", -1)
        if version not in variant_stats:
            variant_stats[version] = 0
        variant_stats[version] += 1

    print(f"\n  Community Breakdown:")
    for version in sorted(variant_stats.keys()):
        print(f"    v{version}: {variant_stats[version]} communities")

    # Cost estimate
    estimated_tokens = total_processed * 150
    estimated_cost = (estimated_tokens / 1_000_000) * 0.30
    print(f"\n  Estimated cost: ${estimated_cost:.3f} USD")

    print("\n" + "="*80)
    print("COMMUNITY SUMMARIES GENERATED")
    print("="*80)
    print()
    print("[OK] Community summary generation complete!")
    print()
    print("Next steps:")
    print("  1. Run Script 6 (compute_graph_algorithms.py)")
    print("  2. Run Script 7 (validate_prerequisites.py)")
    print()

    summarizer.close()


def main():
    """Command-line interface for batch processing."""
    parser = argparse.ArgumentParser(
        description="Batch process community summaries with concurrent execution"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of communities to process per variant (default: None = all)"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of concurrent workers (default: 4)"
    )

    parser.add_argument(
        "--subbatch",
        type=int,
        default=8,
        help="Communities per sub-batch (default: 8)"
    )

    parser.add_argument(
        "--checkpoint",
        type=int,
        default=100,
        help="Save checkpoint every N communities (default: 100)"
    )

    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable resume from existing checkpoints (default: resume enabled)"
    )

    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve without prompting"
    )

    parser.add_argument(
        "--min-members",
        type=int,
        default=1,
        help="Minimum community size to process (default: 1 = all)"
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete existing Community nodes before processing"
    )

    args = parser.parse_args()

    # Run batch processing
    batch_process_communities(
        limit=args.limit,
        max_workers=args.workers,
        subbatch_size=args.subbatch,
        checkpoint_interval=args.checkpoint,
        resume=not args.no_resume,
        auto_approve=args.auto_approve,
        min_members=args.min_members,
        clean=args.clean
    )


if __name__ == "__main__":
    main()
