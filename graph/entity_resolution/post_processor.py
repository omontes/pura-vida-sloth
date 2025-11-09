"""
Phase 8: Post-Processing Application
Applies technology normalization to existing patent/paper data
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from glob import glob

from .tech_classifier import TechnologyClassifier
from .config import EntityResolutionConfig


class TechnologyPostProcessor:
    """Post-processes documents to normalize technology mentions."""

    def __init__(self, config: EntityResolutionConfig, classifier: TechnologyClassifier):
        """
        Initialize post-processor.

        Args:
            config: Entity resolution configuration
            classifier: TechnologyClassifier instance
        """
        self.config = config
        self.classifier = classifier

    def normalize_document(self, document: Dict[str, Any],
                          threshold: float = 0.85) -> Dict[str, Any]:
        """
        Normalize technology mentions in a single document.

        For each tech_mention:
        1. Classify using tech_classifier
        2. If match found (>= threshold), replace with canonical name
        3. Keep original as variant metadata

        Args:
            document: Document dictionary
            threshold: Minimum similarity threshold

        Returns:
            Updated document with normalized tech_mentions
        """
        if 'tech_mentions' not in document or not document['tech_mentions']:
            return document

        normalized_mentions = []

        for mention in document['tech_mentions']:
            original_name = mention.get('name', '')

            # Classify
            result = self.classifier.classify(original_name, threshold=threshold)

            # Create normalized mention
            normalized_mention = mention.copy()

            if result.canonical_name:
                # Match found - use canonical name
                normalized_mention['name'] = result.canonical_name
                normalized_mention['canonical_id'] = result.canonical_id
                normalized_mention['original_name'] = original_name
                normalized_mention['normalization_confidence'] = result.similarity_score
                normalized_mention['normalization_method'] = result.match_method
            else:
                # No match - keep original
                normalized_mention['canonical_id'] = None
                normalized_mention['original_name'] = original_name
                normalized_mention['normalization_confidence'] = 0.0
                normalized_mention['normalization_method'] = "none"

            normalized_mentions.append(normalized_mention)

        # Update document
        document_normalized = document.copy()
        document_normalized['tech_mentions'] = normalized_mentions

        return document_normalized

    def process_file(self, input_file: Path, output_file: Path, threshold: float = 0.85):
        """
        Process a single JSON file.

        Args:
            input_file: Input file path
            output_file: Output file path
            threshold: Minimum similarity threshold
        """
        print(f"\nProcessing: {input_file.name}")

        # Load documents
        with open(input_file, 'r', encoding='utf-8') as f:
            documents = json.load(f)

        print(f"  Loaded {len(documents)} documents")

        # Extract all unique tech mention names
        tech_names = set()
        for doc in documents:
            for mention in doc.get('tech_mentions', []):
                tech_names.add(mention.get('name', ''))

        print(f"  Found {len(tech_names)} unique technology mentions")

        # Classify all unique names (batch)
        tech_names_list = list(tech_names)
        classification_results = self.classifier.classify_batch(tech_names_list, threshold=threshold)

        # Create lookup map: original_name -> LookupResult
        lookup_map = {result.query_mention: result for result in classification_results}

        # Normalize all documents
        normalized_documents = []
        for doc in documents:
            # For efficiency, use lookup map instead of classifying each mention
            normalized_doc = doc.copy()
            normalized_mentions = []

            for mention in doc.get('tech_mentions', []):
                original_name = mention.get('name', '')
                result = lookup_map.get(original_name)

                normalized_mention = mention.copy()

                if result and result.canonical_name:
                    normalized_mention['name'] = result.canonical_name
                    normalized_mention['canonical_id'] = result.canonical_id
                    normalized_mention['original_name'] = original_name
                    normalized_mention['normalization_confidence'] = result.similarity_score
                    normalized_mention['normalization_method'] = result.match_method
                else:
                    normalized_mention['canonical_id'] = None
                    normalized_mention['original_name'] = original_name
                    normalized_mention['normalization_confidence'] = 0.0
                    normalized_mention['normalization_method'] = "none"

                normalized_mentions.append(normalized_mention)

            normalized_doc['tech_mentions'] = normalized_mentions
            normalized_documents.append(normalized_doc)

        # Save normalized documents
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(normalized_documents, f, indent=2, ensure_ascii=False)

        print(f"  Saved to: {output_file.name}")

        # Statistics
        matched = sum(1 for r in classification_results if r.canonical_name is not None)
        print(f"  Normalization: {matched}/{len(tech_names)} unique mentions matched ({matched/len(tech_names)*100:.1f}%)")

    def run(self, pattern: str, output_suffix: str = "_NORMALIZED", threshold: float = 0.85):
        """
        Run Phase 8: Post-process files matching pattern.

        Args:
            pattern: Glob pattern for input files (e.g., "data/eVTOL/lens_patents/batch_processing/relevant_patents_scored_*.json")
            output_suffix: Suffix to add to output filename
            threshold: Minimum similarity threshold
        """
        print(f"\n{'='*80}")
        print("PHASE 8: POST-PROCESSING APPLICATION")
        print(f"{'='*80}")

        # Find matching files
        input_files = glob(pattern)

        if not input_files:
            print(f"No files found matching pattern: {pattern}")
            return

        print(f"Found {len(input_files)} files to process")

        # Process each file
        for input_path in input_files:
            input_file = Path(input_path)

            # Create output filename
            output_name = input_file.stem + output_suffix + input_file.suffix
            output_file = input_file.parent / output_name

            # Process file
            self.process_file(input_file, output_file, threshold=threshold)

        print(f"\n{'='*80}")
        print("PHASE 8 COMPLETE")
        print(f"{'='*80}")
        print(f"Processed {len(input_files)} files")
        print(f"Output files saved with suffix: {output_suffix}")


def create_post_processor(config: EntityResolutionConfig,
                          classifier: TechnologyClassifier) -> TechnologyPostProcessor:
    """
    Create post-processor instance.

    Args:
        config: Entity resolution configuration
        classifier: TechnologyClassifier instance

    Returns:
        TechnologyPostProcessor instance
    """
    return TechnologyPostProcessor(config, classifier)
