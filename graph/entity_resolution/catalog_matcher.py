"""
Phase 2A: Catalog Matching
Matches normalized tech mentions against existing canonical catalog
Uses hybrid approach: Exact + Fuzzy + Semantic matching
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from rapidfuzz import fuzz
import openai
from dotenv import load_dotenv

from .schemas import NormalizedMention, CatalogMatch
from .config import EntityResolutionConfig, get_pipeline_config


# Load environment variables
load_dotenv()


class CatalogMatcher:
    """Matches technology mentions against existing canonical catalog."""

    def __init__(self, config: EntityResolutionConfig):
        """
        Initialize catalog matcher.

        Args:
            config: Entity resolution configuration
        """
        self.config = config
        self.pipeline_config = get_pipeline_config()

        # Load OpenAI API key
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        openai.api_key = self.openai_api_key

        # Load existing catalog
        self.canonical_catalog = self._load_catalog()

        # Cache for embeddings
        self.embedding_cache = {}

    def _load_catalog(self) -> List[Dict[str, Any]]:
        """
        Load existing canonical technologies catalog.

        Returns:
            List of canonical technology entries
        """
        catalog_file = self.config.existing_catalog_file

        if not catalog_file.exists():
            print(f"Warning: Catalog file not found at {catalog_file}")
            print("Proceeding without existing catalog (all mentions will be unmatched)")
            return []

        print(f"Loading existing catalog from: {catalog_file}")

        with open(catalog_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract technologies array
        technologies = data.get('technologies', [])
        print(f"  Loaded {len(technologies)} canonical technologies")

        return technologies

    def _normalize_catalog_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant fields from catalog entry.

        Returns:
            {
                'id': str,
                'canonical_name': str,
                'aliases': List[str],
                'domain': str
            }
        """
        return {
            'id': entry.get('id', ''),
            'canonical_name': entry.get('name', ''),
            'aliases': entry.get('aliases', []),
            'domain': entry.get('domain', '')
        }

    def _exact_match(self, mention_name: str) -> Optional[Dict[str, Any]]:
        """
        Check for exact match against canonical names and aliases.

        Args:
            mention_name: Normalized mention name

        Returns:
            Matching catalog entry or None
        """
        mention_lower = mention_name.lower()

        for entry in self.canonical_catalog:
            normalized_entry = self._normalize_catalog_entry(entry)

            # Check canonical name
            if normalized_entry['canonical_name'].lower() == mention_lower:
                return normalized_entry

            # Check aliases
            for alias in normalized_entry['aliases']:
                if alias.lower() == mention_lower:
                    return normalized_entry

        return None

    def _fuzzy_match(self, mention_name: str, threshold: float = 0.85) -> List[Tuple[Dict[str, Any], float]]:
        """
        Fuzzy string matching using RapidFuzz.

        Args:
            mention_name: Normalized mention name
            threshold: Minimum similarity score (0-1)

        Returns:
            List of (catalog_entry, similarity_score) tuples
        """
        matches = []

        for entry in self.canonical_catalog:
            normalized_entry = self._normalize_catalog_entry(entry)

            # Match against canonical name
            canonical_score = fuzz.ratio(mention_name, normalized_entry['canonical_name'].lower()) / 100.0

            # Match against all aliases
            alias_scores = [
                fuzz.ratio(mention_name, alias.lower()) / 100.0
                for alias in normalized_entry['aliases']
            ]

            # Take best score
            best_score = max([canonical_score] + alias_scores)

            if best_score >= threshold:
                matches.append((normalized_entry, best_score))

        # Sort by score (descending)
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches

    def _get_embedding(self, text: str) -> List[float]:
        """
        Get OpenAI embedding for text (with caching).

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        # Check cache
        if text in self.embedding_cache:
            return self.embedding_cache[text]

        # Get embedding from OpenAI
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
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity (0-1)
        """
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _semantic_match(self, mention_name: str, threshold: float = 0.85) -> List[Tuple[Dict[str, Any], float]]:
        """
        Semantic matching using OpenAI embeddings.

        Args:
            mention_name: Normalized mention name
            threshold: Minimum similarity score (0-1)

        Returns:
            List of (catalog_entry, similarity_score) tuples
        """
        matches = []

        # Get embedding for mention
        mention_embedding = self._get_embedding(mention_name)
        if not mention_embedding:
            return matches

        for entry in self.canonical_catalog:
            normalized_entry = self._normalize_catalog_entry(entry)

            # Get embedding for canonical name
            canonical_embedding = self._get_embedding(normalized_entry['canonical_name'].lower())

            if canonical_embedding:
                similarity = self._cosine_similarity(mention_embedding, canonical_embedding)

                if similarity >= threshold:
                    matches.append((normalized_entry, similarity))

        # Sort by score (descending)
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches

    def match_mention(self, mention: NormalizedMention) -> Optional[CatalogMatch]:
        """
        Match a single normalized mention against catalog.

        Matching strategy:
        1. Exact match (highest priority)
        2. Combined fuzzy + semantic (weighted)
        3. Accept if combined score >= threshold

        Args:
            mention: NormalizedMention object

        Returns:
            CatalogMatch object or None if no match
        """
        mention_name = mention.normalized_name

        # 1. Exact match
        exact = self._exact_match(mention_name)
        if exact:
            return CatalogMatch(
                mention_name=mention.original_name,
                canonical_name=exact['canonical_name'],
                canonical_id=exact['id'],
                similarity_score=1.0,
                match_method="exact",
                confidence=1.0
            )

        # 2. Fuzzy matching
        fuzzy_matches = self._fuzzy_match(mention_name, threshold=0.75)  # Lower threshold for fuzzy

        # 3. Semantic matching
        semantic_matches = self._semantic_match(mention_name, threshold=0.75)  # Lower threshold for semantic

        # Combine fuzzy and semantic scores
        combined_scores = {}

        # Add fuzzy scores
        for entry, score in fuzzy_matches:
            entry_id = entry['id']
            combined_scores[entry_id] = {
                'entry': entry,
                'fuzzy_score': score,
                'semantic_score': 0.0
            }

        # Add semantic scores
        for entry, score in semantic_matches:
            entry_id = entry['id']
            if entry_id in combined_scores:
                combined_scores[entry_id]['semantic_score'] = score
            else:
                combined_scores[entry_id] = {
                    'entry': entry,
                    'fuzzy_score': 0.0,
                    'semantic_score': score
                }

        # Calculate combined scores (weighted)
        fuzzy_weight = self.pipeline_config['fuzzy_weight']
        semantic_weight = self.pipeline_config['semantic_weight']
        threshold = self.pipeline_config['similarity_threshold']

        best_match = None
        best_score = 0.0

        for entry_id, scores in combined_scores.items():
            combined = (fuzzy_weight * scores['fuzzy_score'] +
                       semantic_weight * scores['semantic_score'])

            if combined >= threshold and combined > best_score:
                best_score = combined
                best_match = scores['entry']

        if best_match:
            return CatalogMatch(
                mention_name=mention.original_name,
                canonical_name=best_match['canonical_name'],
                canonical_id=best_match['id'],
                similarity_score=best_score,
                match_method="combined",
                confidence=best_score
            )

        return None

    def match_all(self, mentions: List[NormalizedMention]) -> Tuple[List[CatalogMatch], List[NormalizedMention]]:
        """
        Match all normalized mentions against catalog.

        Args:
            mentions: List of NormalizedMention objects

        Returns:
            Tuple of (matched, unmatched) lists
        """
        print(f"\n{'='*80}")
        print("PHASE 2A: CATALOG MATCHING")
        print(f"{'='*80}")
        print(f"Matching {len(mentions)} normalized mentions against {len(self.canonical_catalog)} canonical technologies...")

        matched = []
        unmatched = []

        for i, mention in enumerate(mentions, 1):
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(mentions)}")

            match = self.match_mention(mention)

            if match:
                matched.append(match)
            else:
                unmatched.append(mention)

        print(f"\nMatching complete:")
        print(f"  Matched: {len(matched)} ({len(matched)/len(mentions)*100:.1f}%)")
        print(f"  Unmatched: {len(unmatched)} ({len(unmatched)/len(mentions)*100:.1f}%)")

        return matched, unmatched

    def save_results(self, matched: List[CatalogMatch], unmatched: List[NormalizedMention]):
        """
        Save matching results to JSON files.

        Args:
            matched: List of CatalogMatch objects
            unmatched: List of NormalizedMention objects
        """
        output_dir = self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save matched
        matched_file = output_dir / self.pipeline_config['output_files']['catalog_matches']
        with open(matched_file, 'w', encoding='utf-8') as f:
            json.dump([m.model_dump() for m in matched], f, indent=2, ensure_ascii=False)
        print(f"\nSaved matched mentions to: {matched_file}")

        # Save unmatched
        unmatched_file = output_dir / self.pipeline_config['output_files']['unmatched_mentions']
        with open(unmatched_file, 'w', encoding='utf-8') as f:
            json.dump([m.model_dump() for m in unmatched], f, indent=2, ensure_ascii=False)
        print(f"Saved unmatched mentions to: {unmatched_file}")

    def run(self, normalized_mentions: List[NormalizedMention]) -> Tuple[List[CatalogMatch], List[NormalizedMention]]:
        """
        Run Phase 2A: Match normalized mentions against catalog.

        Args:
            normalized_mentions: List of NormalizedMention objects

        Returns:
            Tuple of (matched, unmatched) lists
        """
        # Match all mentions
        matched, unmatched = self.match_all(normalized_mentions)

        # Save results
        self.save_results(matched, unmatched)

        # Print summary
        self._print_summary(matched, unmatched)

        return matched, unmatched

    def _print_summary(self, matched: List[CatalogMatch], unmatched: List[NormalizedMention]):
        """Print summary statistics."""
        print(f"\n{'='*80}")
        print("PHASE 2A SUMMARY")
        print(f"{'='*80}")

        total = len(matched) + len(unmatched)
        print(f"Total mentions: {total}")
        print(f"Matched: {len(matched)} ({len(matched)/total*100:.1f}%)")
        print(f"Unmatched: {len(unmatched)} ({len(unmatched)/total*100:.1f}%)")

        # Match method distribution
        print(f"\nMatch method distribution:")
        method_counts = {}
        for match in matched:
            method_counts[match.match_method] = method_counts.get(match.match_method, 0) + 1

        for method, count in sorted(method_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {method}: {count} ({count/len(matched)*100:.1f}%)")

        # Top matches
        print(f"\nTop 10 matched mentions:")
        for i, match in enumerate(matched[:10], 1):
            print(f"  {i}. {match.mention_name} → {match.canonical_name}")
            print(f"     Similarity: {match.similarity_score:.2f}, Method: {match.match_method}")

        # Sample unmatched
        if unmatched:
            print(f"\nSample unmatched mentions (need clustering):")
            for i, mention in enumerate(unmatched[:10], 1):
                print(f"  {i}. {mention.original_name} (occurrences: {mention.occurrence_count})")

        print(f"\n{'='*80}")


def load_normalized_mentions(config: EntityResolutionConfig, filename: str) -> List[NormalizedMention]:
    """
    Load normalized mentions from JSON file.

    Args:
        config: Entity resolution configuration
        filename: Filename in output directory

    Returns:
        List of NormalizedMention objects
    """
    file_path = config.output_dir / filename

    if not file_path.exists():
        raise FileNotFoundError(f"Normalized mentions file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return [NormalizedMention(**item) for item in data]
