"""
Phase 2B: Hybrid Clustering with ChromaDB
Clusters unmatched technology mentions using BM25 + semantic embeddings
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import networkx as nx
from collections import defaultdict
from rank_bm25 import BM25Okapi

from .schemas import NormalizedMention, TechnologyCluster
from .config import EntityResolutionConfig, get_pipeline_config


class HybridClusterer:
    """Clusters technology mentions using ChromaDB hybrid search and graph algorithms."""

    def __init__(self, config: EntityResolutionConfig):
        """
        Initialize hybrid clusterer.

        Args:
            config: Entity resolution configuration
        """
        self.config = config
        self.pipeline_config = get_pipeline_config()

        # Get OpenAI API key for embeddings
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        # Initialize ChromaDB
        self.client = None
        self.collection = None
        self._init_chromadb()

        # Initialize BM25 (will be set in add_mentions_to_chromadb)
        self.bm25 = None
        self.tokenized_corpus = None

    def _init_chromadb(self):
        """Initialize ChromaDB client and collection for temporary clustering."""
        # Use in-memory client for temporary clustering (Phase 2B)
        # Phase 6 will use persistent storage
        print("Initializing ChromaDB (in-memory for clustering)...")

        self.client = chromadb.Client(Settings(
            anonymized_telemetry=False,
            allow_reset=True
        ))

        # Create embedding function using OpenAI
        embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self.openai_api_key,
            model_name=self.pipeline_config['embedding_model']
        )

        # Create or get collection
        collection_name = "temp_clustering_collection"

        # Reset if exists
        try:
            self.client.delete_collection(name=collection_name)
        except:
            pass

        self.collection = self.client.create_collection(
            name=collection_name,
            embedding_function=embedding_function,
            metadata={"hnsw:space": "cosine"}
        )

        print(f"  Created ChromaDB collection: {collection_name}")

    def _tokenize(self, text: str) -> List[str]:
        """
        Simple tokenization for BM25.

        Args:
            text: Text to tokenize

        Returns:
            List of tokens
        """
        # Simple whitespace + lowercase tokenization
        return text.lower().split()

    def add_mentions_to_chromadb(self, mentions: List[NormalizedMention]):
        """
        Add normalized mentions to ChromaDB collection and initialize BM25.

        Args:
            mentions: List of NormalizedMention objects
        """
        print(f"\nAdding {len(mentions)} mentions to ChromaDB + BM25...")

        documents = []
        metadatas = []
        ids = []

        for i, mention in enumerate(mentions):
            # Use normalized name as document text
            documents.append(mention.normalized_name)

            # Store metadata
            metadatas.append({
                "original_name": mention.original_name,
                "occurrence_count": mention.occurrence_count,
                "avg_strength": mention.avg_strength,
                "avg_confidence": mention.avg_confidence
            })

            # Use index as ID
            ids.append(f"mention_{i}")

        # Add to ChromaDB collection in batches (OpenAI API has limits)
        batch_size = 100
        total_batches = (len(documents) + batch_size - 1) // batch_size

        print(f"  Processing in {total_batches} batches of {batch_size}...")

        for batch_idx in range(0, len(documents), batch_size):
            end_idx = min(batch_idx + batch_size, len(documents))
            batch_num = (batch_idx // batch_size) + 1

            print(f"  Batch {batch_num}/{total_batches}: Adding mentions {batch_idx} to {end_idx-1}...")

            self.collection.add(
                documents=documents[batch_idx:end_idx],
                metadatas=metadatas[batch_idx:end_idx],
                ids=ids[batch_idx:end_idx]
            )

        print(f"  [SUCCESS] Added {len(mentions)} mentions to ChromaDB (semantic search)")

        # Initialize BM25 for keyword search
        self.tokenized_corpus = [self._tokenize(doc) for doc in documents]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

        print(f"  [SUCCESS] Initialized BM25 (keyword search) with {len(documents)} documents")

    def _get_bm25_scores(self, query: str, top_k: int = 20) -> List[Tuple[int, float]]:
        """
        Get BM25 keyword similarity scores for a query.

        Args:
            query: Query text
            top_k: Number of top results to return

        Returns:
            List of (doc_index, score) tuples
        """
        if not self.bm25:
            return []

        # Tokenize query
        tokenized_query = self._tokenize(query)

        # Get BM25 scores for all documents
        scores = self.bm25.get_scores(tokenized_query)

        # Get top K indices
        top_indices = scores.argsort()[-top_k:][::-1]

        # Normalize scores to 0-1 range
        max_score = scores.max() if scores.max() > 0 else 1.0
        normalized_scores = [(int(idx), float(scores[idx] / max_score)) for idx in top_indices]

        return normalized_scores

    def build_similarity_graph(self, mentions: List[NormalizedMention], threshold: float = 0.85) -> nx.Graph:
        """
        Build similarity graph using HYBRID search (BM25 + Semantic).

        For each mention:
        1. Query BM25 for keyword similarity
        2. Query ChromaDB for semantic similarity
        3. Combine scores: 0.4 * BM25 + 0.6 * Semantic
        4. Add edges where combined similarity >= threshold

        Args:
            mentions: List of NormalizedMention objects
            threshold: Minimum similarity to create edge

        Returns:
            NetworkX graph with similarity edges
        """
        print(f"\nBuilding similarity graph using HYBRID search (threshold={threshold})...")
        print(f"  Weighting: {self.pipeline_config['fuzzy_weight']*100}% BM25 + {self.pipeline_config['semantic_weight']*100}% Semantic")

        G = nx.Graph()

        # Add all mentions as nodes
        for i, mention in enumerate(mentions):
            G.add_node(i,
                      normalized_name=mention.normalized_name,
                      original_name=mention.original_name,
                      occurrence_count=mention.occurrence_count)

        # Process each mention
        total_edges = 0
        bm25_weight = self.pipeline_config['fuzzy_weight']
        semantic_weight = self.pipeline_config['semantic_weight']

        for i, mention in enumerate(mentions):
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i+1}/{len(mentions)} mentions processed")

            # 1. Get BM25 keyword scores
            bm25_results = self._get_bm25_scores(mention.normalized_name, top_k=20)
            bm25_scores = {idx: score for idx, score in bm25_results}

            # 2. Get semantic scores from ChromaDB
            chroma_results = self.collection.query(
                query_texts=[mention.normalized_name],
                n_results=min(20, len(mentions)),
                include=['distances', 'metadatas']
            )

            semantic_scores = {}
            if chroma_results and chroma_results['distances'] and len(chroma_results['distances']) > 0:
                distances = chroma_results['distances'][0]
                metadatas = chroma_results['metadatas'][0] if chroma_results['metadatas'] else []

                for distance, metadata in zip(distances, metadatas):
                    # Convert distance to similarity
                    similarity = 1.0 - distance

                    # Find index of matched mention
                    matched_name = metadata.get('original_name', '')
                    matched_idx = None
                    for k, m in enumerate(mentions):
                        if m.original_name == matched_name:
                            matched_idx = k
                            break

                    if matched_idx is not None:
                        semantic_scores[matched_idx] = similarity

            # 3. Combine BM25 + Semantic scores
            all_candidates = set(bm25_scores.keys()) | set(semantic_scores.keys())

            for candidate_idx in all_candidates:
                # Skip self-loops
                if candidate_idx == i:
                    continue

                # Get individual scores (default to 0 if not found)
                bm25_score = bm25_scores.get(candidate_idx, 0.0)
                semantic_score = semantic_scores.get(candidate_idx, 0.0)

                # Calculate hybrid score
                hybrid_score = bm25_weight * bm25_score + semantic_weight * semantic_score

                # Add edge if hybrid score >= threshold
                if hybrid_score >= threshold:
                    # Only add edge once (undirected graph)
                    if not G.has_edge(i, candidate_idx):
                        G.add_edge(i, candidate_idx, similarity=hybrid_score)
                        total_edges += 1

        print(f"  Graph built: {len(mentions)} nodes, {total_edges} edges")
        return G

    def detect_communities(self, G: nx.Graph) -> List[Set[int]]:
        """
        Detect communities using Louvain algorithm.

        Args:
            G: NetworkX graph with similarity edges

        Returns:
            List of sets, each set contains node indices in a community
        """
        print(f"\nDetecting communities using Louvain algorithm...")

        # Use Louvain community detection
        communities = nx.community.louvain_communities(G, seed=42)

        print(f"  Detected {len(communities)} communities")

        # Print community size distribution
        sizes = [len(c) for c in communities]
        print(f"  Community sizes: min={min(sizes)}, max={max(sizes)}, avg={sum(sizes)/len(sizes):.1f}")

        return communities

    def create_clusters(self, mentions: List[NormalizedMention], communities: List[Set[int]],
                       G: nx.Graph) -> List[TechnologyCluster]:
        """
        Create TechnologyCluster objects from communities.

        Args:
            mentions: Original list of mentions
            communities: List of node index sets
            G: Similarity graph

        Returns:
            List of TechnologyCluster objects
        """
        print(f"\nCreating {len(communities)} clusters...")

        clusters = []

        for cluster_id, community in enumerate(communities):
            # Get mention names in this cluster
            mention_names = [mentions[i].original_name for i in community]

            # Build mention_metadata dict with rich context for LLM
            mention_metadata = {}
            for i in community:
                mention = mentions[i]
                mention_metadata[mention.original_name] = {
                    "occurrence_count": mention.occurrence_count,
                    "avg_strength": mention.avg_strength,
                    "avg_confidence": mention.avg_confidence,
                    "roles": mention.roles,
                    "doc_types": mention.doc_types,
                    "source_doc_count": len(mention.source_documents)
                }

            # Calculate similarity scores within cluster
            similarity_scores = {}
            total_similarity = 0.0
            edge_count = 0

            for i in community:
                similarity_scores[mentions[i].original_name] = {}

                for j in community:
                    if i != j and G.has_edge(i, j):
                        sim = G[i][j]['similarity']
                        similarity_scores[mentions[i].original_name][mentions[j].original_name] = sim
                        total_similarity += sim
                        edge_count += 1

            # Calculate average cluster similarity
            avg_similarity = total_similarity / edge_count if edge_count > 0 else 1.0

            cluster = TechnologyCluster(
                cluster_id=cluster_id,
                mention_names=mention_names,
                mention_metadata=mention_metadata,
                similarity_scores=similarity_scores,
                avg_cluster_similarity=avg_similarity,
                size=len(mention_names)
            )

            clusters.append(cluster)

        # Sort by size (descending)
        clusters.sort(key=lambda x: x.size, reverse=True)

        return clusters

    def run(self, unmatched_mentions: List[NormalizedMention]) -> List[TechnologyCluster]:
        """
        Run Phase 2B: Cluster unmatched mentions using hybrid approach.

        Args:
            unmatched_mentions: List of NormalizedMention objects from Phase 2A

        Returns:
            List of TechnologyCluster objects
        """
        print(f"\n{'='*80}")
        print("PHASE 2B: HYBRID CLUSTERING")
        print(f"{'='*80}")
        print(f"Clustering {len(unmatched_mentions)} unmatched mentions...")

        # Add mentions to ChromaDB
        self.add_mentions_to_chromadb(unmatched_mentions)

        # Build similarity graph
        threshold = self.pipeline_config['cluster_min_similarity']
        G = self.build_similarity_graph(unmatched_mentions, threshold=threshold)

        # Detect communities
        communities = self.detect_communities(G)

        # Create clusters
        clusters = self.create_clusters(unmatched_mentions, communities, G)

        # Save results
        self.save_clusters(clusters)

        # Print summary
        self._print_summary(clusters)

        return clusters

    def save_clusters(self, clusters: List[TechnologyCluster]):
        """
        Save clusters to JSON file.

        Args:
            clusters: List of TechnologyCluster objects
        """
        output_dir = self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / self.pipeline_config['output_files']['mention_clusters']

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([c.model_dump() for c in clusters], f, indent=2, ensure_ascii=False)

        print(f"\nSaved clusters to: {output_file}")

    def _print_summary(self, clusters: List[TechnologyCluster]):
        """Print summary statistics."""
        print(f"\n{'='*80}")
        print("PHASE 2B SUMMARY")
        print(f"{'='*80}")

        print(f"Total clusters: {len(clusters)}")

        total_mentions = sum(c.size for c in clusters)
        print(f"Total mentions clustered: {total_mentions}")

        # Cluster size distribution
        sizes = [c.size for c in clusters]
        print(f"\nCluster size distribution:")
        print(f"  Min: {min(sizes)}")
        print(f"  Max: {max(sizes)}")
        print(f"  Avg: {sum(sizes)/len(sizes):.1f}")
        print(f"  Median: {sorted(sizes)[len(sizes)//2]}")

        # Similarity distribution
        similarities = [c.avg_cluster_similarity for c in clusters]
        print(f"\nAverage cluster similarity:")
        print(f"  Min: {min(similarities):.2f}")
        print(f"  Max: {max(similarities):.2f}")
        print(f"  Avg: {sum(similarities)/len(similarities):.2f}")

        # Top 10 largest clusters
        print(f"\nTop 10 largest clusters:")
        for i, cluster in enumerate(clusters[:10], 1):
            print(f"  {i}. Cluster {cluster.cluster_id}: {cluster.size} mentions, avg_sim={cluster.avg_cluster_similarity:.2f}")
            print(f"     Variants: {', '.join(cluster.mention_names[:3])}")
            if cluster.size > 3:
                print(f"     ... and {cluster.size - 3} more")

        print(f"\n{'='*80}")


def load_unmatched_mentions(config: EntityResolutionConfig, filename: str) -> List[NormalizedMention]:
    """
    Load unmatched mentions from JSON file.

    Args:
        config: Entity resolution configuration
        filename: Filename in output directory

    Returns:
        List of NormalizedMention objects
    """
    file_path = config.output_dir / filename

    if not file_path.exists():
        raise FileNotFoundError(f"Unmatched mentions file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return [NormalizedMention(**item) for item in data]
