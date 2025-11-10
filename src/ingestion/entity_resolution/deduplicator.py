"""
Phase 4: Deduplication & Merging
Merges catalog matches with LLM canonical names, resolving duplicates
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from rapidfuzz import fuzz
import openai
import os
from dotenv import load_dotenv

from .schemas import CatalogMatch, LLMCanonicalResult, CanonicalTechnology, TechnologyVariant
from .config import EntityResolutionConfig, get_pipeline_config

# Load environment variables
load_dotenv()


class TechnologyDeduplicator:
    """Deduplicates and merges technology catalog."""

    def __init__(self, config: EntityResolutionConfig):
        """
        Initialize deduplicator.

        Args:
            config: Entity resolution configuration
        """
        self.config = config
        self.pipeline_config = get_pipeline_config()

        # Load OpenAI API key for embeddings
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        openai.api_key = self.openai_api_key

        # Embedding cache
        self.embedding_cache = {}

    def _generate_tech_id(self, canonical_name: str) -> str:
        """
        Generate unique ID for technology.

        Args:
            canonical_name: Canonical technology name

        Returns:
            Unique ID (snake_case)
        """
        # Convert to lowercase, replace spaces/special chars with underscores
        tech_id = canonical_name.lower()
        tech_id = re.sub(r'[^a-z0-9]+', '_', tech_id)
        tech_id = tech_id.strip('_')

        return tech_id

    def load_existing_catalog(self) -> List[CanonicalTechnology]:
        """
        Load existing canonical technologies from catalog.

        Returns:
            List of CanonicalTechnology objects
        """
        catalog_file = self.config.existing_catalog_file

        if not catalog_file.exists():
            print(f"No existing catalog found at {catalog_file}")
            return []

        print(f"Loading existing catalog from: {catalog_file}")

        with open(catalog_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        technologies = []
        for item in data.get('technologies', []):
            # Convert aliases to TechnologyVariant objects
            variants = [
                TechnologyVariant(
                    name=alias,
                    similarity_score=1.0,  # Exact aliases
                    method="catalog_alias"
                )
                for alias in item.get('aliases', [])
            ]

            tech = CanonicalTechnology(
                id=item.get('id', self._generate_tech_id(item.get('name', ''))),
                canonical_name=item.get('name', ''),
                domain=item.get('domain'),
                description=item.get('description'),
                variants=variants,
                occurrence_count=0,  # Will be updated from matches
                source_documents=[],
                created_by="catalog"
            )
            technologies.append(tech)

        print(f"  Loaded {len(technologies)} existing canonical technologies")
        return technologies

    def add_catalog_matches(self, catalog: List[CanonicalTechnology],
                           matches: List[CatalogMatch]) -> List[CanonicalTechnology]:
        """
        Add matched mentions as variants to existing catalog entries.

        Args:
            catalog: List of existing CanonicalTechnology objects
            matches: List of CatalogMatch objects from Phase 2A

        Returns:
            Updated catalog
        """
        print(f"\nAdding {len(matches)} catalog matches as variants...")

        # Create lookup by canonical_id
        catalog_dict = {tech.id: tech for tech in catalog}

        for match in matches:
            if match.canonical_id in catalog_dict:
                tech = catalog_dict[match.canonical_id]

                # Add as variant if not already present
                variant_names = [v.name for v in tech.variants]
                if match.mention_name not in variant_names:
                    variant = TechnologyVariant(
                        name=match.mention_name,
                        similarity_score=match.similarity_score,
                        method=match.match_method
                    )
                    tech.variants.append(variant)

        return list(catalog_dict.values())

    def _get_embedding(self, text: str) -> List[float]:
        """Get OpenAI embedding for text (with caching)."""
        if text in self.embedding_cache:
            return self.embedding_cache[text]

        try:
            response = openai.embeddings.create(
                model=self.pipeline_config['embedding_model'],
                input=text
            )
            embedding = response.data[0].embedding
            self.embedding_cache[text] = embedding
            return embedding
        except Exception as e:
            print(f"Warning: Failed to get embedding for '{text}': {e}")
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def find_duplicate(self, new_tech_name: str,
                      existing_catalog: List[CanonicalTechnology]) -> Optional[CanonicalTechnology]:
        """
        Check if new technology duplicates an existing one.

        Uses fuzzy + semantic matching (same as Phase 2A).

        Args:
            new_tech_name: New technology canonical name
            existing_catalog: List of existing technologies

        Returns:
            Matching CanonicalTechnology or None
        """
        threshold = self.pipeline_config['similarity_threshold']
        fuzzy_weight = self.pipeline_config['fuzzy_weight']
        semantic_weight = self.pipeline_config['semantic_weight']

        best_match = None
        best_score = 0.0

        # Get embedding for new tech
        new_embedding = self._get_embedding(new_tech_name.lower())

        for tech in existing_catalog:
            # Fuzzy score
            fuzzy_score = fuzz.ratio(new_tech_name.lower(), tech.canonical_name.lower()) / 100.0

            # Semantic score
            tech_embedding = self._get_embedding(tech.canonical_name.lower())
            semantic_score = self._cosine_similarity(new_embedding, tech_embedding)

            # Combined score
            combined = fuzzy_weight * fuzzy_score + semantic_weight * semantic_score

            if combined >= threshold and combined > best_score:
                best_score = combined
                best_match = tech

        return best_match

    def merge_llm_results(self, catalog: List[CanonicalTechnology],
                         llm_results: List[LLMCanonicalResult]) -> List[CanonicalTechnology]:
        """
        Merge LLM canonical names into catalog.

        For each LLM result:
        1. Check if it duplicates existing catalog entry
        2. If yes: Add variants to existing entry
        3. If no: Create new canonical technology

        Args:
            catalog: Existing catalog
            llm_results: LLM canonical results from Phase 3

        Returns:
            Updated catalog
        """
        print(f"\nMerging {len(llm_results)} LLM canonical names...")

        new_technologies = []
        merged_count = 0
        new_count = 0

        for result in llm_results:
            # Check for duplicate against BOTH existing catalog AND newly processed LLM results
            combined_catalog = catalog + new_technologies
            duplicate = self.find_duplicate(result.canonical_name, combined_catalog)

            if duplicate:
                # Merge into existing
                print(f"  Duplicate found: '{result.canonical_name}' -> '{duplicate.canonical_name}'")
                merged_count += 1

                # Add all variants
                for variant_name in result.input_variants:
                    variant_names = [v.name for v in duplicate.variants]
                    if variant_name not in variant_names:
                        variant = TechnologyVariant(
                            name=variant_name,
                            similarity_score=result.confidence,
                            method="llm"
                        )
                        duplicate.variants.append(variant)

            else:
                # Create new canonical technology
                new_count += 1

                variants = [
                    TechnologyVariant(
                        name=variant_name,
                        similarity_score=result.confidence,
                        method="llm"
                    )
                    for variant_name in result.input_variants
                ]

                new_tech = CanonicalTechnology(
                    id=self._generate_tech_id(result.canonical_name),
                    canonical_name=result.canonical_name,
                    domain=result.domain,
                    description=result.description,
                    variants=variants,
                    occurrence_count=len(result.input_variants),
                    source_documents=[],
                    created_by="entity_resolution_pipeline"
                )

                new_technologies.append(new_tech)

        print(f"  Merged: {merged_count}")
        print(f"  New: {new_count}")

        # Combine catalog + new technologies
        return catalog + new_technologies

    def run(self, catalog_matches: List[CatalogMatch],
           llm_results: List[LLMCanonicalResult]) -> List[CanonicalTechnology]:
        """
        Run Phase 4: Deduplicate and merge catalog.

        Args:
            catalog_matches: Matches from Phase 2A
            llm_results: LLM canonical names from Phase 3

        Returns:
            Merged canonical catalog
        """
        print(f"\n{'='*80}")
        print("PHASE 4: DEDUPLICATION & MERGING")
        print(f"{'='*80}")

        # Load existing catalog
        catalog = self.load_existing_catalog()

        # Add catalog matches as variants
        catalog = self.add_catalog_matches(catalog, catalog_matches)

        # Merge LLM results
        catalog = self.merge_llm_results(catalog, llm_results)

        # Save results
        self.save_catalog(catalog)

        # Print summary
        self._print_summary(catalog)

        return catalog

    def save_catalog(self, catalog: List[CanonicalTechnology]):
        """Save merged catalog to JSON file."""
        output_dir = self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / self.pipeline_config['output_files']['merged_catalog']

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([c.model_dump() for c in catalog], f, indent=2, ensure_ascii=False)

        print(f"\nSaved merged catalog to: {output_file}")

    def _print_summary(self, catalog: List[CanonicalTechnology]):
        """Print summary statistics."""
        print(f"\n{'='*80}")
        print("PHASE 4 SUMMARY")
        print(f"{'='*80}")

        total_canonical = len(catalog)
        total_variants = sum(len(tech.variants) for tech in catalog)

        print(f"Total canonical technologies: {total_canonical}")
        print(f"Total variants: {total_variants}")

        # Source distribution
        catalog_count = sum(1 for tech in catalog if tech.created_by == "catalog")
        pipeline_count = sum(1 for tech in catalog if tech.created_by == "entity_resolution_pipeline")

        print(f"\nSource distribution:")
        print(f"  From existing catalog: {catalog_count}")
        print(f"  From entity resolution: {pipeline_count}")

        # Domain distribution
        domain_counts = {}
        for tech in catalog:
            domain = tech.domain or "Unknown"
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

        print(f"\nDomain distribution:")
        for domain, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {domain}: {count}")

        # Sample technologies
        print(f"\nSample canonical technologies:")
        for i, tech in enumerate(catalog[:10], 1):
            variant_count = len(tech.variants)
            print(f"  {i}. {tech.canonical_name} ({variant_count} variants)")
            print(f"     Domain: {tech.domain}, Source: {tech.created_by}")

        print(f"\n{'='*80}")


def load_catalog_matches(config: EntityResolutionConfig, filename: str) -> List[CatalogMatch]:
    """Load catalog matches from JSON file."""
    file_path = config.output_dir / filename

    if not file_path.exists():
        raise FileNotFoundError(f"Catalog matches file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return [CatalogMatch(**item) for item in data]


def load_llm_results(config: EntityResolutionConfig, filename: str) -> List[LLMCanonicalResult]:
    """Load LLM canonical results from JSON file."""
    file_path = config.output_dir / filename

    if not file_path.exists():
        raise FileNotFoundError(f"LLM results file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return [LLMCanonicalResult(**item) for item in data]
