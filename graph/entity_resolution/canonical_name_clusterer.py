"""
Phase 5.5: Canonical Name Clustering
Clusters canonical technologies using hybrid similarity to merge near-duplicates
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
from rapidfuzz import fuzz

from .schemas import CanonicalTechnology, TechnologyVariant
from .config import EntityResolutionConfig, get_pipeline_config


class CanonicalNameClusterer:
    """Clusters canonical technology names using hybrid similarity to detect and merge duplicates."""

    def __init__(self, config: EntityResolutionConfig):
        """
        Initialize canonical name clusterer.

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

        # Initialize BM25
        self.bm25 = None
        self.tokenized_corpus = None

        # Merge tracking
        self.merge_audit = []
        self.review_queue = []

    def _init_chromadb(self):
        """Initialize ChromaDB client and collection for canonical name clustering."""
        print("Initializing ChromaDB (in-memory for canonical clustering)...")

        self.client = chromadb.Client(Settings(
            anonymized_telemetry=False,
            allow_reset=True
        ))

        # Create embedding function using OpenAI
        embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self.openai_api_key,
            model_name=self.pipeline_config['embedding_model']
        )

        # Create collection
        collection_name = "temp_canonical_clustering"

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
        """Simple tokenization for BM25."""
        return text.lower().split()

    def _create_rich_text(self, tech: CanonicalTechnology) -> str:
        """
        Create rich text representation for embedding.

        Combines canonical_name + domain + description for better semantic matching.

        Args:
            tech: CanonicalTechnology object

        Returns:
            Rich text string for embedding
        """
        parts = [tech.canonical_name]

        if tech.domain:
            parts.append(f"Domain: {tech.domain}")

        if tech.description:
            # Limit description to 100 chars to keep embedding focused
            desc = tech.description[:100] if len(tech.description) > 100 else tech.description
            parts.append(desc)

        return ". ".join(parts)

    def add_technologies_to_chromadb(self, technologies: List[CanonicalTechnology]):
        """
        Add canonical technologies to ChromaDB collection and initialize BM25.

        Args:
            technologies: List of CanonicalTechnology objects
        """
        print(f"\nAdding {len(technologies)} canonical technologies to ChromaDB + BM25...")

        documents = []
        metadatas = []
        ids = []

        for i, tech in enumerate(technologies):
            # Use rich text (name + domain + description) for semantic embedding
            rich_text = self._create_rich_text(tech)
            documents.append(rich_text)

            # Store metadata
            metadatas.append({
                "canonical_name": tech.canonical_name,
                "domain": tech.domain or "Unknown",
                "id": tech.id,
                "variant_count": len(tech.variants),
                "created_by": tech.created_by
            })

            # Use tech ID as collection ID
            ids.append(f"tech_{i}")

        # Add to ChromaDB in batches
        batch_size = 100
        total_batches = (len(documents) + batch_size - 1) // batch_size

        print(f"  Processing in {total_batches} batches of {batch_size}...")

        for batch_idx in range(0, len(documents), batch_size):
            end_idx = min(batch_idx + batch_size, len(documents))
            batch_num = (batch_idx // batch_size) + 1

            print(f"  Batch {batch_num}/{total_batches}: Adding technologies {batch_idx} to {end_idx-1}...")

            self.collection.add(
                documents=documents[batch_idx:end_idx],
                metadatas=metadatas[batch_idx:end_idx],
                ids=ids[batch_idx:end_idx]
            )

        print(f"  [SUCCESS] Added {len(technologies)} technologies to ChromaDB")

        # Initialize BM25 with canonical names (not rich text)
        canonical_names = [tech.canonical_name for tech in technologies]
        self.tokenized_corpus = [self._tokenize(name) for name in canonical_names]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

        print(f"  [SUCCESS] Initialized BM25 with {len(canonical_names)} canonical names")

    def _get_bm25_scores(self, query: str, top_k: int = 20) -> List[Tuple[int, float]]:
        """Get BM25 keyword similarity scores."""
        if not self.bm25:
            return []

        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)

        # Get top K indices
        top_indices = scores.argsort()[-top_k:][::-1]

        # Normalize scores
        max_score = scores.max() if scores.max() > 0 else 1.0
        normalized_scores = [(int(idx), float(scores[idx] / max_score)) for idx in top_indices]

        return normalized_scores

    def build_similarity_graph(self, technologies: List[CanonicalTechnology],
                               threshold: float = 0.75) -> nx.Graph:
        """
        Build similarity graph using HYBRID search (BM25 + Semantic).

        Args:
            technologies: List of CanonicalTechnology objects
            threshold: Minimum similarity to create edge

        Returns:
            NetworkX graph with similarity edges
        """
        print(f"\nBuilding similarity graph using HYBRID search (threshold={threshold})...")

        # Use canonical-specific weights
        fuzzy_weight = self.pipeline_config.get('canonical_fuzzy_weight', 0.30)
        semantic_weight = self.pipeline_config.get('canonical_semantic_weight', 0.70)

        print(f"  Weighting: {fuzzy_weight*100}% Fuzzy + {semantic_weight*100}% Semantic")

        G = nx.Graph()

        # Add all technologies as nodes
        for i, tech in enumerate(technologies):
            G.add_node(i,
                      canonical_name=tech.canonical_name,
                      domain=tech.domain,
                      id=tech.id,
                      variant_count=len(tech.variants),
                      created_by=tech.created_by)

        # Process each technology
        total_edges = 0

        for i, tech in enumerate(technologies):
            if (i + 1) % 100 == 0:
                print(f"  Progress: {i+1}/{len(technologies)} technologies processed")

            # 1. Get BM25 keyword scores
            bm25_results = self._get_bm25_scores(tech.canonical_name, top_k=20)
            bm25_scores = {idx: score for idx, score in bm25_results}

            # 2. Get semantic scores from ChromaDB (using rich text)
            rich_text = self._create_rich_text(tech)
            chroma_results = self.collection.query(
                query_texts=[rich_text],
                n_results=min(20, len(technologies)),
                include=['distances', 'metadatas']
            )

            semantic_scores = {}
            if chroma_results and chroma_results['distances'] and len(chroma_results['distances']) > 0:
                distances = chroma_results['distances'][0]
                metadatas = chroma_results['metadatas'][0] if chroma_results['metadatas'] else []

                for distance, metadata in zip(distances, metadatas):
                    # Convert distance to similarity
                    similarity = 1.0 - distance

                    # Find index of matched technology
                    matched_name = metadata.get('canonical_name', '')
                    matched_idx = None
                    for k, t in enumerate(technologies):
                        if t.canonical_name == matched_name:
                            matched_idx = k
                            break

                    if matched_idx is not None:
                        semantic_scores[matched_idx] = similarity

            # 3. Combine Fuzzy + Semantic scores
            all_candidates = set(bm25_scores.keys()) | set(semantic_scores.keys())

            for candidate_idx in all_candidates:
                # Skip self-loops
                if candidate_idx == i:
                    continue

                # Get individual scores
                fuzzy_score = bm25_scores.get(candidate_idx, 0.0)
                semantic_score = semantic_scores.get(candidate_idx, 0.0)

                # Calculate hybrid score
                hybrid_score = fuzzy_weight * fuzzy_score + semantic_weight * semantic_score

                # Add edge if hybrid score >= threshold
                if hybrid_score >= threshold:
                    if not G.has_edge(i, candidate_idx):
                        G.add_edge(i, candidate_idx, similarity=hybrid_score)
                        total_edges += 1

        print(f"  Graph built: {len(technologies)} nodes, {total_edges} edges")
        return G

    def detect_communities(self, G: nx.Graph) -> List[Set[int]]:
        """Detect communities using Louvain algorithm."""
        print(f"\nDetecting communities using Louvain algorithm...")

        communities = nx.community.louvain_communities(G, seed=42)

        print(f"  Detected {len(communities)} communities")

        # Print community size distribution
        sizes = [len(c) for c in communities]
        if sizes:
            print(f"  Community sizes: min={min(sizes)}, max={max(sizes)}, avg={sum(sizes)/len(sizes):.1f}")

        return communities

    def _check_domain_compatibility(self, tech1: CanonicalTechnology,
                                    tech2: CanonicalTechnology) -> Tuple[bool, str]:
        """
        Check if two technologies have compatible domains.

        Returns:
            (is_compatible, reason)
        """
        domain1 = tech1.domain or "Unknown"
        domain2 = tech2.domain or "Unknown"

        # Same domain = always compatible
        if domain1 == domain2:
            return True, "Same domain"

        # Unknown domain = allow merge (domain not critical)
        if "Unknown" in [domain1, domain2]:
            return True, "Unknown domain (allowed)"

        # Check related domains (you can expand this)
        related_domains = {
            ("Energy Storage", "Propulsion"),
            ("Avionics", "Safety"),
            ("Airframe", "Manufacturing"),
            ("Infrastructure", "Avionics")
        }

        if (domain1, domain2) in related_domains or (domain2, domain1) in related_domains:
            return True, f"Related domains: {domain1}/{domain2}"

        # Different unrelated domains = warn but allow (might be valid)
        return False, f"Unrelated domains: {domain1}/{domain2}"

    def _check_variant_overlap(self, tech1: CanonicalTechnology,
                               tech2: CanonicalTechnology) -> Tuple[bool, str]:
        """
        Check if two technologies have overlapping variant names.

        Returns:
            (has_overlap, reason)
        """
        # Get all words from all variants
        words1 = set()
        for v in tech1.variants:
            words1.update(v.name.lower().split())

        words2 = set()
        for v in tech2.variants:
            words2.update(v.name.lower().split())

        # Check overlap
        overlap = words1 & words2
        overlap_ratio = len(overlap) / max(len(words1), len(words2)) if max(len(words1), len(words2)) > 0 else 0

        if overlap_ratio >= 0.3:  # 30% word overlap
            return True, f"Variant overlap: {overlap_ratio:.1%}"
        else:
            return False, f"Low variant overlap: {overlap_ratio:.1%}"

    def validate_merge(self, tech1: CanonicalTechnology, tech2: CanonicalTechnology,
                       similarity: float) -> Dict[str, Any]:
        """
        Validate a potential merge using quality gates.

        Returns:
            Validation result dict with decision and reasons
        """
        gates = {}

        # Gate 1: Domain compatibility
        domain_ok, domain_reason = self._check_domain_compatibility(tech1, tech2)
        gates['domain_compatibility'] = {
            'passed': domain_ok,
            'reason': domain_reason
        }

        # Gate 2: Variant overlap
        overlap_ok, overlap_reason = self._check_variant_overlap(tech1, tech2)
        gates['variant_overlap'] = {
            'passed': overlap_ok,
            'reason': overlap_reason
        }

        # Gate 3: Similarity threshold tiers
        if similarity >= 0.85:
            confidence = "high"
            auto_merge = True
        elif similarity >= 0.80:
            confidence = "medium"
            auto_merge = domain_ok and overlap_ok
        else:  # 0.75-0.80
            confidence = "low"
            auto_merge = False

        gates['similarity_tier'] = {
            'confidence': confidence,
            'similarity': similarity,
            'auto_merge': auto_merge
        }

        # Final decision
        all_gates_pass = domain_ok and overlap_ok
        decision = "auto_merge" if (auto_merge and all_gates_pass) else "review"

        return {
            'decision': decision,
            'gates': gates,
            'tech1_name': tech1.canonical_name,
            'tech2_name': tech2.canonical_name,
            'similarity': similarity
        }

    def merge_technologies(self, tech1: CanonicalTechnology,
                           tech2: CanonicalTechnology) -> CanonicalTechnology:
        """
        Merge two technologies into one.

        Chooses primary based on:
        1. Existing catalog over Phase 3 (created_by)
        2. Higher variant count
        3. Alphabetically first

        Args:
            tech1: First technology
            tech2: Second technology

        Returns:
            Merged technology
        """
        # Choose primary
        if tech1.created_by == "catalog" and tech2.created_by != "catalog":
            primary, secondary = tech1, tech2
        elif tech2.created_by == "catalog" and tech1.created_by != "catalog":
            primary, secondary = tech2, tech1
        elif len(tech1.variants) > len(tech2.variants):
            primary, secondary = tech1, tech2
        elif len(tech2.variants) > len(tech1.variants):
            primary, secondary = tech2, tech1
        else:
            # Alphabetically first
            primary, secondary = (tech1, tech2) if tech1.canonical_name < tech2.canonical_name else (tech2, tech1)

        # Merge variants (avoid duplicates)
        merged_variants = list(primary.variants)
        existing_variant_names = {v.name for v in merged_variants}

        for variant in secondary.variants:
            if variant.name not in existing_variant_names:
                merged_variants.append(variant)
                existing_variant_names.add(variant.name)

        # Create merged technology
        merged = CanonicalTechnology(
            id=primary.id,
            canonical_name=primary.canonical_name,
            domain=primary.domain,
            description=primary.description,
            variants=merged_variants,
            occurrence_count=primary.occurrence_count + secondary.occurrence_count,
            source_documents=list(set(primary.source_documents + secondary.source_documents)),
            created_by=primary.created_by
        )

        return merged

    def process_communities(self, technologies: List[CanonicalTechnology],
                           communities: List[Set[int]], G: nx.Graph) -> List[CanonicalTechnology]:
        """
        Process communities and merge technologies based on quality gates.

        Args:
            technologies: Original list of technologies
            communities: List of node index sets
            G: Similarity graph

        Returns:
            Merged list of technologies
        """
        print(f"\nProcessing {len(communities)} communities for merging...")

        merged_technologies = []
        merged_indices = set()

        auto_merge_count = 0
        review_count = 0

        for community in communities:
            community_list = list(community)

            # Single-member communities are already unique
            if len(community_list) == 1:
                idx = community_list[0]
                if idx not in merged_indices:
                    merged_technologies.append(technologies[idx])
                    merged_indices.add(idx)
                continue

            # Multi-member communities need merging
            # Start with first member as primary
            primary_idx = community_list[0]
            primary_tech = technologies[primary_idx]
            merged_indices.add(primary_idx)

            # Try to merge others into primary
            for idx in community_list[1:]:
                if idx in merged_indices:
                    continue

                tech = technologies[idx]

                # Get similarity from graph
                similarity = G[primary_idx][idx]['similarity'] if G.has_edge(primary_idx, idx) else 0.0

                # Validate merge
                validation = self.validate_merge(primary_tech, tech, similarity)

                if validation['decision'] == 'auto_merge':
                    # Merge
                    primary_tech = self.merge_technologies(primary_tech, tech)
                    merged_indices.add(idx)
                    auto_merge_count += 1

                    # Track audit
                    self.merge_audit.append({
                        'merged_from': tech.canonical_name,
                        'merged_into': primary_tech.canonical_name,
                        'similarity': similarity,
                        'validation': validation
                    })
                else:
                    # Add to review queue
                    self.review_queue.append({
                        'tech1': primary_tech.canonical_name,
                        'tech2': tech.canonical_name,
                        'similarity': similarity,
                        'validation': validation
                    })
                    review_count += 1

                    # Keep separate for now
                    merged_technologies.append(tech)
                    merged_indices.add(idx)

            # Add merged primary
            merged_technologies.append(primary_tech)

        # Add any technologies not in any community
        for i, tech in enumerate(technologies):
            if i not in merged_indices:
                merged_technologies.append(tech)

        print(f"  Auto-merged: {auto_merge_count} pairs")
        print(f"  Review queue: {review_count} pairs")
        print(f"  Final count: {len(merged_technologies)} technologies")

        return merged_technologies

    def run(self, catalog: List[CanonicalTechnology]) -> List[CanonicalTechnology]:
        """
        Run Phase 5.5: Cluster and merge canonical names.

        Args:
            catalog: Merged catalog from Phase 4

        Returns:
            Final deduplicated catalog
        """
        print(f"\n{'='*80}")
        print("PHASE 5.5: CANONICAL NAME CLUSTERING")
        print(f"{'='*80}")
        print(f"Clustering {len(catalog)} canonical technologies...")

        # Add technologies to ChromaDB
        self.add_technologies_to_chromadb(catalog)

        # Build similarity graph
        threshold = self.pipeline_config.get('canonical_cluster_threshold', 0.75)
        G = self.build_similarity_graph(catalog, threshold=threshold)

        # Detect communities
        communities = self.detect_communities(G)

        # Process communities and merge
        merged_catalog = self.process_communities(catalog, communities, G)

        # Save results
        self.save_catalog(merged_catalog)
        self.save_merge_audit()
        self.save_review_queue()

        # Print summary
        self._print_summary(len(catalog), len(merged_catalog))

        return merged_catalog

    def save_catalog(self, catalog: List[CanonicalTechnology]):
        """Save merged catalog to JSON file."""
        output_dir = self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "05_merged_catalog.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([c.model_dump() for c in catalog], f, indent=2, ensure_ascii=False)

        print(f"\nSaved merged catalog to: {output_file}")

    def save_merge_audit(self):
        """Save merge audit trail."""
        output_file = self.config.output_dir / "05_merge_audit.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.merge_audit, f, indent=2, ensure_ascii=False)

        print(f"Saved merge audit to: {output_file}")

    def save_review_queue(self):
        """Save review queue."""
        output_file = self.config.output_dir / "05_merge_review_queue.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.review_queue, f, indent=2, ensure_ascii=False)

        print(f"Saved review queue to: {output_file}")

    def _print_summary(self, original_count: int, final_count: int):
        """Print summary statistics."""
        print(f"\n{'='*80}")
        print("PHASE 5.5 SUMMARY")
        print(f"{'='*80}")

        print(f"Original technologies: {original_count}")
        print(f"Final technologies: {final_count}")
        print(f"Technologies merged: {original_count - final_count}")
        print(f"Reduction: {((original_count - final_count) / original_count * 100):.1f}%")

        print(f"\nMerge statistics:")
        print(f"  Auto-merged: {len(self.merge_audit)} pairs")
        print(f"  Review queue: {len(self.review_queue)} pairs")

        if self.merge_audit:
            print(f"\nTop 5 auto-merged pairs:")
            for i, merge in enumerate(sorted(self.merge_audit, key=lambda x: x['similarity'], reverse=True)[:5], 1):
                print(f"  {i}. '{merge['merged_from']}' -> '{merge['merged_into']}' (sim={merge['similarity']:.3f})")

        print(f"\n{'='*80}")


def load_merged_catalog(config: EntityResolutionConfig, filename: str) -> List[CanonicalTechnology]:
    """Load merged catalog from JSON file."""
    file_path = config.output_dir / filename

    if not file_path.exists():
        raise FileNotFoundError(f"Merged catalog file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return [CanonicalTechnology(**item) for item in data]
