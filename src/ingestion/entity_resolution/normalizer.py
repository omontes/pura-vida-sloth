"""
Phase 1: Data Loading & Normalization
Extracts and normalizes technology mentions from documents
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict

from .schemas import Document, TechMention, NormalizedMention
from .config import EntityResolutionConfig


class TechMentionNormalizer:
    """Normalizes technology mentions from documents."""

    def __init__(self, config: EntityResolutionConfig):
        """
        Initialize normalizer with configuration.

        Args:
            config: Entity resolution configuration
        """
        self.config = config

    def normalize_text(self, text: str) -> str:
        """
        Normalize technology name text.

        Normalization steps:
        1. Strip leading/trailing whitespace
        2. Convert to lowercase
        3. Replace multiple spaces with single space
        4. Remove special characters (keep letters, numbers, spaces, hyphens, parentheses)

        Args:
            text: Original technology name

        Returns:
            Normalized technology name
        """
        # Strip whitespace
        normalized = text.strip()

        # Convert to lowercase
        normalized = normalized.lower()

        # Replace multiple spaces with single space
        normalized = re.sub(r'\s+', ' ', normalized)

        # Keep only letters, numbers, spaces, hyphens, and parentheses
        # This preserves terms like "400+ Wh/kg" or "Software-in-the-Loop (SIL)"
        normalized = re.sub(r'[^a-z0-9\s\-\(\)/+]', '', normalized)

        # Clean up any double spaces created by character removal
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized

    def load_documents(self, limit: int = None) -> List[Document]:
        """
        Load documents from technologies_patents_papers.json.

        Args:
            limit: Maximum number of documents to load (None = all)

        Returns:
            List of Document objects
        """
        input_file = self.config.technologies_input_file

        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        print(f"Loading documents from: {input_file}")

        with open(input_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        if limit:
            raw_data = raw_data[:limit]
            print(f"  Limited to first {limit} documents")

        documents = []
        for item in raw_data:
            try:
                # Convert tech_mentions to TechMention objects
                tech_mentions = [
                    TechMention(**mention)
                    for mention in item.get('tech_mentions', [])
                ]

                doc = Document(
                    doc_id=item['doc_id'],
                    doc_type=item['doc_type'],
                    title=item['title'],
                    tech_mentions=tech_mentions
                )
                documents.append(doc)
            except Exception as e:
                print(f"  Warning: Skipping document {item.get('doc_id', 'unknown')}: {e}")
                continue

        print(f"  Loaded {len(documents)} documents")
        return documents

    def extract_and_normalize(self, documents: List[Document]) -> List[NormalizedMention]:
        """
        Extract all technology mentions and normalize them.

        Aggregates:
        - Occurrence count
        - Roles (unique list)
        - Average strength
        - Average confidence
        - Source documents
        - Document types

        Args:
            documents: List of Document objects

        Returns:
            List of NormalizedMention objects
        """
        # Aggregate mentions by normalized name
        mention_data = defaultdict(lambda: {
            'original_names': [],
            'roles': [],
            'strengths': [],
            'confidences': [],
            'source_docs': [],
            'doc_types': []
        })

        print(f"\nExtracting technology mentions from {len(documents)} documents...")

        total_mentions = 0
        for doc in documents:
            for mention in doc.tech_mentions:
                total_mentions += 1

                # Normalize the technology name
                normalized_name = self.normalize_text(mention.name)

                # Aggregate data
                mention_data[normalized_name]['original_names'].append(mention.name)
                mention_data[normalized_name]['roles'].append(mention.role)
                mention_data[normalized_name]['strengths'].append(mention.strength)
                mention_data[normalized_name]['confidences'].append(mention.evidence_confidence)
                mention_data[normalized_name]['source_docs'].append(doc.doc_id)
                mention_data[normalized_name]['doc_types'].append(doc.doc_type)

        print(f"  Total mentions processed: {total_mentions}")
        print(f"  Unique normalized names: {len(mention_data)}")

        # Convert to NormalizedMention objects
        normalized_mentions = []
        for normalized_name, data in mention_data.items():
            # Get most common original name (tie-breaker: alphabetical)
            original_name = max(set(data['original_names']), key=data['original_names'].count)

            mention = NormalizedMention(
                original_name=original_name,
                normalized_name=normalized_name,
                occurrence_count=len(data['original_names']),
                roles=list(set(data['roles'])),  # Unique roles
                avg_strength=sum(data['strengths']) / len(data['strengths']),
                avg_confidence=sum(data['confidences']) / len(data['confidences']),
                source_documents=list(set(data['source_docs'])),  # Unique docs
                doc_types=list(set(data['doc_types']))  # Unique doc types
            )
            normalized_mentions.append(mention)

        # Sort by occurrence count (descending)
        normalized_mentions.sort(key=lambda x: x.occurrence_count, reverse=True)

        return normalized_mentions

    def save_normalized_mentions(self, mentions: List[NormalizedMention], output_file: str):
        """
        Save normalized mentions to JSON file.

        Args:
            mentions: List of NormalizedMention objects
            output_file: Output filename (in output directory)
        """
        output_path = self.config.output_dir / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict for JSON serialization
        data = [mention.model_dump() for mention in mentions]

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\nSaved normalized mentions to: {output_path}")
        print(f"  Total unique technologies: {len(mentions)}")

    def run(self, limit: int = None, output_file: str = "01_normalized_mentions.json") -> List[NormalizedMention]:
        """
        Run Phase 1: Load documents, extract and normalize mentions.

        Args:
            limit: Maximum number of documents to process (None = all)
            output_file: Output filename

        Returns:
            List of NormalizedMention objects
        """
        print("=" * 80)
        print("PHASE 1: DATA LOADING & NORMALIZATION")
        print("=" * 80)

        # Load documents
        documents = self.load_documents(limit=limit)

        # Extract and normalize mentions
        normalized_mentions = self.extract_and_normalize(documents)

        # Save results
        self.save_normalized_mentions(normalized_mentions, output_file)

        # Print summary statistics
        self._print_summary(normalized_mentions)

        return normalized_mentions

    def _print_summary(self, mentions: List[NormalizedMention]):
        """Print summary statistics."""
        print("\n" + "=" * 80)
        print("PHASE 1 SUMMARY")
        print("=" * 80)

        total_occurrences = sum(m.occurrence_count for m in mentions)
        avg_occurrences = total_occurrences / len(mentions) if mentions else 0

        print(f"Total unique technologies: {len(mentions)}")
        print(f"Total occurrences: {total_occurrences}")
        print(f"Average occurrences per technology: {avg_occurrences:.2f}")

        print(f"\nTop 10 most mentioned technologies:")
        for i, mention in enumerate(mentions[:10], 1):
            print(f"  {i}. {mention.original_name} ({mention.occurrence_count} occurrences)")

        print(f"\nRole distribution:")
        role_counts = defaultdict(int)
        for mention in mentions:
            for role in mention.roles:
                role_counts[role] += 1

        for role, count in sorted(role_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {role}: {count}")

        print("\n" + "=" * 80)


def main():
    """Test Phase 1 with incremental limits."""
    # Load configuration
    config = EntityResolutionConfig(industry="eVTOL")

    # Initialize normalizer
    normalizer = TechMentionNormalizer(config)

    # Test with 10 documents first
    print("\n\nTEST 1: Processing 10 documents...")
    normalizer.run(limit=10, output_file="01_normalized_mentions_test10.json")

    # Ask user to proceed with full dataset
    response = input("\nProceed with full dataset? (y/n): ")
    if response.lower() == 'y':
        print("\n\nFULL RUN: Processing all documents...")
        normalizer.run(limit=None, output_file="01_normalized_mentions.json")
    else:
        print("Skipping full run.")


if __name__ == "__main__":
    main()
