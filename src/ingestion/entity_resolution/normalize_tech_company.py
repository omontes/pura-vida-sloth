"""
Unified Tech + Company Normalization Pipeline
Normalizes technology and company mentions in SEC filing JSONs using both classifiers
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path

from .tech_classifier import TechnologyClassifier
from .company_classifier import CompanyClassifier
from .config import EntityResolutionConfig


class TechCompanyNormalizer:
    """Normalizes both technology and company mentions in documents."""

    def __init__(self, config: EntityResolutionConfig, tech_threshold: float = 0.5, company_threshold: float = 0.5):
        """
        Initialize normalizer with both classifiers.

        Args:
            config: Entity resolution configuration
            tech_threshold: Similarity threshold for tech classification (default: 0.5)
            company_threshold: Similarity threshold for company classification (default: 0.5)
        """
        self.config = config
        self.tech_threshold = tech_threshold
        self.company_threshold = company_threshold

        print("Initializing Tech + Company Normalizer...")
        print(f"  Tech threshold: {tech_threshold}")
        print(f"  Company threshold: {company_threshold}")

        # Initialize classifiers
        print("\nLoading technology classifier...")
        self.tech_classifier = TechnologyClassifier(config)

        print("\nLoading company classifier...")
        self.company_classifier = CompanyClassifier(config)

        print("\n[SUCCESS] Normalizer initialized!\n")

    def normalize_tech_mentions(self, tech_mentions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize technology mentions.

        Args:
            tech_mentions: List of tech mention dicts with 'name' field

        Returns:
            Updated list with normalization fields added
        """
        if not tech_mentions:
            return []

        for mention in tech_mentions:
            name = mention.get('name', '')

            if not name:
                # No name to normalize
                mention['normalized_name'] = None
                mention['tech_id'] = None
                mention['normalization_confidence'] = 'low'
                mention['normalization_score'] = 0.0
                continue

            # Classify the mention
            result = self.tech_classifier.classify(name, threshold=self.tech_threshold)

            # Add normalization fields
            mention['normalized_name'] = result.canonical_name if result.canonical_name else "Unknown"
            mention['tech_id'] = result.canonical_id
            mention['normalization_confidence'] = result.confidence
            mention['normalization_score'] = result.similarity_score
            mention['normalization_method'] = result.match_method

        return tech_mentions

    def normalize_company_mentions(self, company_mentions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize company mentions.

        Args:
            company_mentions: List of company mention dicts with 'name' field

        Returns:
            Updated list with normalization fields added
        """
        if not company_mentions:
            return []

        for mention in company_mentions:
            name = mention.get('name', '')

            if not name:
                # No name to normalize
                mention['normalized_name'] = None
                mention['company_id'] = None
                mention['normalization_confidence'] = 'low'
                mention['normalization_score'] = 0.0
                continue

            # Classify the mention
            result = self.company_classifier.classify(name, threshold=self.company_threshold)

            # Add normalization fields
            mention['normalized_name'] = result.canonical_name if result.canonical_name else "Unknown"
            mention['company_id'] = result.canonical_id
            mention['normalization_confidence'] = result.confidence
            mention['normalization_score'] = result.similarity_score
            mention['normalization_method'] = result.match_method

        return company_mentions

    def normalize_company_tech_relations(self, relations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize company-technology relations.

        Args:
            relations: List of relation dicts with 'company_name' and 'technology_name' fields

        Returns:
            Updated list with normalization fields added
        """
        if not relations:
            return []

        for relation in relations:
            # Normalize company name
            company_name = relation.get('company_name', '')
            if company_name:
                company_result = self.company_classifier.classify(company_name, threshold=self.company_threshold)
                relation['normalized_company_name'] = company_result.canonical_name if company_result.canonical_name else "Unknown"
                relation['company_id'] = company_result.canonical_id
                relation['company_normalization_confidence'] = company_result.confidence
                relation['company_normalization_score'] = company_result.similarity_score
            else:
                relation['normalized_company_name'] = None
                relation['company_id'] = None
                relation['company_normalization_confidence'] = 'low'
                relation['company_normalization_score'] = 0.0

            # Normalize technology name
            tech_name = relation.get('technology_name', '')
            if tech_name:
                tech_result = self.tech_classifier.classify(tech_name, threshold=self.tech_threshold)
                relation['normalized_tech_name'] = tech_result.canonical_name if tech_result.canonical_name else "Unknown"
                relation['tech_id'] = tech_result.canonical_id
                relation['tech_normalization_confidence'] = tech_result.confidence
                relation['tech_normalization_score'] = tech_result.similarity_score
            else:
                relation['normalized_tech_name'] = None
                relation['tech_id'] = None
                relation['tech_normalization_confidence'] = 'low'
                relation['tech_normalization_score'] = 0.0

        return relations

    def normalize_tech_tech_relations(self, relations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize technology-technology relations.

        Args:
            relations: List of relation dicts with tech name fields

        Returns:
            Updated list with normalization fields added
        """
        if not relations:
            return []

        for relation in relations:
            # Normalize source technology
            from_tech = relation.get('from_tech_name', '') or relation.get('source_tech', '')
            if from_tech:
                from_result = self.tech_classifier.classify(from_tech, threshold=self.tech_threshold)
                relation['normalized_from_tech'] = from_result.canonical_name if from_result.canonical_name else "Unknown"
                relation['from_tech_id'] = from_result.canonical_id
            else:
                relation['normalized_from_tech'] = None
                relation['from_tech_id'] = None

            # Normalize target technology
            to_tech = relation.get('to_tech_name', '') or relation.get('target_tech', '')
            if to_tech:
                to_result = self.tech_classifier.classify(to_tech, threshold=self.tech_threshold)
                relation['normalized_to_tech'] = to_result.canonical_name if to_result.canonical_name else "Unknown"
                relation['to_tech_id'] = to_result.canonical_id
            else:
                relation['normalized_to_tech'] = None
                relation['to_tech_id'] = None

        return relations

    def normalize_company_company_relations(self, relations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize company-company relations.

        Args:
            relations: List of relation dicts with 'from_company_name' and 'to_company_name' fields

        Returns:
            Updated list with normalization fields added
        """
        if not relations:
            return []

        for relation in relations:
            # Normalize source company
            from_company = relation.get('from_company_name', '')
            if from_company:
                from_result = self.company_classifier.classify(from_company, threshold=self.company_threshold)
                relation['normalized_from_company'] = from_result.canonical_name if from_result.canonical_name else "Unknown"
                relation['from_company_id'] = from_result.canonical_id
                relation['from_company_confidence'] = from_result.confidence
                relation['from_company_score'] = from_result.similarity_score
            else:
                relation['normalized_from_company'] = None
                relation['from_company_id'] = None
                relation['from_company_confidence'] = 'low'
                relation['from_company_score'] = 0.0

            # Normalize target company
            to_company = relation.get('to_company_name', '')
            if to_company:
                to_result = self.company_classifier.classify(to_company, threshold=self.company_threshold)
                relation['normalized_to_company'] = to_result.canonical_name if to_result.canonical_name else "Unknown"
                relation['to_company_id'] = to_result.canonical_id
                relation['to_company_confidence'] = to_result.confidence
                relation['to_company_score'] = to_result.similarity_score
            else:
                relation['normalized_to_company'] = None
                relation['to_company_id'] = None
                relation['to_company_confidence'] = 'low'
                relation['to_company_score'] = 0.0

        return relations

    def normalize_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize all tech and company mentions in a document.

        Args:
            document: SEC filing JSON with mentions and relations

        Returns:
            Updated document with normalized fields
        """
        # Normalize tech mentions
        if 'tech_mentions' in document:
            document['tech_mentions'] = self.normalize_tech_mentions(document['tech_mentions'])

        # Normalize company mentions
        if 'company_mentions' in document:
            document['company_mentions'] = self.normalize_company_mentions(document['company_mentions'])

        # Normalize company-tech relations
        if 'company_tech_relations' in document:
            document['company_tech_relations'] = self.normalize_company_tech_relations(document['company_tech_relations'])

        # Normalize tech-tech relations
        if 'tech_tech_relations' in document:
            document['tech_tech_relations'] = self.normalize_tech_tech_relations(document['tech_tech_relations'])

        # Normalize company-company relations
        if 'company_company_relations' in document:
            document['company_company_relations'] = self.normalize_company_company_relations(document['company_company_relations'])

        return document

    def normalize_batch(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize a batch of documents.

        Args:
            documents: List of SEC filing JSONs

        Returns:
            List of normalized documents
        """
        print(f"\nNormalizing {len(documents)} documents...")

        normalized_docs = []
        for i, doc in enumerate(documents, 1):
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(documents)}")

            normalized_doc = self.normalize_document(doc)
            normalized_docs.append(normalized_doc)

        print(f"[SUCCESS] Normalized {len(documents)} documents")

        return normalized_docs


def normalize_sec_filing(filing_json: Dict[str, Any],
                        config: EntityResolutionConfig,
                        tech_threshold: float = 0.5,
                        company_threshold: float = 0.5) -> Dict[str, Any]:
    """
    Convenience function to normalize a single SEC filing.

    Args:
        filing_json: SEC filing JSON dict
        config: Entity resolution configuration
        tech_threshold: Similarity threshold for tech classification
        company_threshold: Similarity threshold for company classification

    Returns:
        Normalized SEC filing JSON
    """
    normalizer = TechCompanyNormalizer(config, tech_threshold, company_threshold)
    return normalizer.normalize_document(filing_json)


def normalize_sec_filings_batch(filings: List[Dict[str, Any]],
                                config: EntityResolutionConfig,
                                tech_threshold: float = 0.5,
                                company_threshold: float = 0.5) -> List[Dict[str, Any]]:
    """
    Convenience function to normalize multiple SEC filings.

    Args:
        filings: List of SEC filing JSON dicts
        config: Entity resolution configuration
        tech_threshold: Similarity threshold for tech classification
        company_threshold: Similarity threshold for company classification

    Returns:
        List of normalized SEC filing JSONs
    """
    normalizer = TechCompanyNormalizer(config, tech_threshold, company_threshold)
    return normalizer.normalize_batch(filings)
