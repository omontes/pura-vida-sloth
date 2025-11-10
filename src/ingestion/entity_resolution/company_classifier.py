"""
Company Classification/Lookup Function
Classifies company mentions using hybrid search against companies catalog
"""

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from typing import Optional, List, Dict
import os
import json

from .schemas import LookupResult
from .config import EntityResolutionConfig, get_pipeline_config


class CompanyClassifier:
    """Classifies company mentions using hybrid search."""

    def __init__(self, config: EntityResolutionConfig):
        """
        Initialize company classifier.

        Args:
            config: Entity resolution configuration
        """
        self.config = config
        self.pipeline_config = get_pipeline_config()

        # Load OpenAI API key
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        # Load ChromaDB collection
        self.client = None
        self.collection = None
        self._load_chromadb()

        # Load catalog for exact matching and ticker lookup
        self.companies_catalog = self._load_catalog()
        self.ticker_index = self._build_ticker_index()

    def _load_chromadb(self):
        """Load persistent ChromaDB collection."""
        persist_directory = str(self.config.chromadb_dir)
        collection_name = self.pipeline_config['chromadb_company_collection_name']

        print(f"Loading ChromaDB company collection...")
        print(f"  Directory: {persist_directory}")
        print(f"  Collection: {collection_name}")

        # Load persistent client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

        # Get embedding function
        embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self.openai_api_key,
            model_name=self.pipeline_config['embedding_model']
        )

        # Get collection
        self.collection = self.client.get_collection(
            name=collection_name,
            embedding_function=embedding_function
        )

        print(f"  Collection loaded: {self.collection.count()} companies")

    def _load_catalog(self) -> Optional[dict]:
        """Load companies catalog for exact matching."""
        try:
            # Load from data directory (companies.json)
            companies_path = self.config.data_dir / "companies" / "companies.json"

            if not companies_path.exists():
                print(f"  Warning: Companies catalog not found at {companies_path}")
                return None

            with open(companies_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            print(f"  Companies catalog loaded: {data.get('total_companies', 0)} companies")
            return data
        except Exception as e:
            print(f"  Warning: Could not load companies catalog: {e}")
            return None

    def _build_ticker_index(self) -> Dict[str, str]:
        """
        Build reverse index for ticker symbols.

        Returns:
            Dict mapping ticker → company_id
        """
        ticker_index = {}

        if not self.companies_catalog:
            return ticker_index

        for company in self.companies_catalog.get('companies', []):
            company_name = company['name']
            company_id = company['id']

            # Check if company name contains a ticker in parentheses
            # Example: "Archer Aviation (ACHR)" or "Joby Aviation (JOBY)"
            if '(' in company_name and ')' in company_name:
                start = company_name.rfind('(')
                end = company_name.rfind(')')
                ticker = company_name[start+1:end].strip().upper()
                if ticker and len(ticker) <= 5:  # Typical ticker length
                    ticker_index[ticker] = company_id

            # Also check aliases for ticker patterns
            for alias in company.get('aliases', []):
                # If alias is all caps and short, likely a ticker
                if alias.isupper() and 1 <= len(alias) <= 5:
                    ticker_index[alias] = company_id

        print(f"  Built ticker index: {len(ticker_index)} tickers")
        return ticker_index

    def ticker_match(self, query: str) -> Optional[LookupResult]:
        """
        Check if query is a stock ticker.

        Args:
            query: Query text

        Returns:
            LookupResult if ticker match found, else None
        """
        if not self.ticker_index:
            return None

        # Check if query looks like a ticker (all caps, 1-5 chars)
        query_upper = query.strip().upper()

        if query_upper in self.ticker_index:
            company_id = self.ticker_index[query_upper]

            # Find the company details
            for company in self.companies_catalog.get('companies', []):
                if company['id'] == company_id:
                    return LookupResult(
                        query_mention=query,
                        canonical_name=company['name'],
                        canonical_id=company_id,
                        similarity_score=1.0,
                        match_method="ticker_exact",
                        confidence="high",
                        alternatives=[]
                    )

        return None

    def exact_variant_match(self, query: str) -> Optional[LookupResult]:
        """
        Check for exact match against company names and aliases.

        Args:
            query: Company mention

        Returns:
            LookupResult if exact match found, else None
        """
        if not self.companies_catalog:
            return None

        query_lower = query.lower().strip()

        for company in self.companies_catalog.get('companies', []):
            # Check canonical name
            if company['name'].lower() == query_lower:
                return LookupResult(
                    query_mention=query,
                    canonical_name=company['name'],
                    canonical_id=company['id'],
                    similarity_score=1.0,
                    match_method="exact_canonical",
                    confidence="high",
                    alternatives=[]
                )

            # Check aliases
            for alias in company.get('aliases', []):
                if alias.lower() == query_lower:
                    return LookupResult(
                        query_mention=query,
                        canonical_name=company['name'],
                        canonical_id=company['id'],
                        similarity_score=1.0,
                        match_method="exact_alias",
                        confidence="high",
                        alternatives=[]
                    )

        return None

    def hybrid_search(self, query: str, threshold: float = 0.75) -> Optional[LookupResult]:
        """
        Perform hybrid search using ChromaDB.

        Args:
            query: Company mention
            threshold: Minimum similarity threshold (default: 0.75)

        Returns:
            LookupResult if match found, else None
        """
        top_k = self.pipeline_config['chromadb_search_top_k']

        # Query ChromaDB
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            include=['distances', 'metadatas']
        )

        if not results or not results['distances'] or len(results['distances']) == 0:
            return None

        distances = results['distances'][0]
        metadatas = results['metadatas'][0]

        # Best match
        best_distance = distances[0]
        best_metadata = metadatas[0]

        # Convert distance to similarity
        similarity = 1.0 - best_distance

        # Check threshold
        if similarity < threshold:
            return None

        # Determine confidence
        if similarity >= 0.90:
            confidence = "high"
        elif similarity >= 0.75:
            confidence = "medium"
        else:
            confidence = "low"

        # Build alternatives list
        alternatives = []
        for i in range(1, min(3, len(distances))):
            alt_sim = 1.0 - distances[i]
            if alt_sim >= threshold:
                alternatives.append({
                    "canonical_name": metadatas[i].get('canonical_name', ''),
                    "canonical_id": metadatas[i].get('company_id', ''),
                    "similarity_score": alt_sim,
                    "kind": metadatas[i].get('kind', 'unknown')
                })

        return LookupResult(
            query_mention=query,
            canonical_name=best_metadata.get('canonical_name', ''),
            canonical_id=best_metadata.get('company_id', ''),
            similarity_score=similarity,
            match_method="hybrid_search",
            confidence=confidence,
            alternatives=alternatives
        )

    def classify(self, mention: str, threshold: float = 0.5) -> LookupResult:
        """
        Classify a company mention.

        Lookup pipeline:
        1. Ticker match (fastest, for stock symbols)
        2. Exact variant match (canonical name + aliases)
        3. ChromaDB hybrid search
        4. Return "Unknown" if no match

        Args:
            mention: Company mention to classify
            threshold: Minimum similarity threshold (default: 0.5 for companies)

        Returns:
            LookupResult object
        """
        # 1. Ticker match
        ticker_match = self.ticker_match(mention)
        if ticker_match:
            return ticker_match

        # 2. Exact variant match
        exact_match = self.exact_variant_match(mention)
        if exact_match:
            return exact_match

        # 3. Hybrid search
        hybrid_match = self.hybrid_search(mention, threshold=threshold)
        if hybrid_match:
            return hybrid_match

        # 4. No match found
        return LookupResult(
            query_mention=mention,
            canonical_name=None,
            canonical_id=None,
            similarity_score=0.0,
            match_method="none",
            confidence="low",
            alternatives=[]
        )

    def classify_batch(self, mentions: List[str],
                      threshold: float = 0.5) -> List[LookupResult]:
        """
        Classify a batch of company mentions.

        Args:
            mentions: List of company mentions
            threshold: Minimum similarity threshold

        Returns:
            List of LookupResult objects
        """
        print(f"\nClassifying {len(mentions)} company mentions...")

        results = []
        for i, mention in enumerate(mentions, 1):
            if i % 100 == 0:
                print(f"  Progress: {i}/{len(mentions)}")

            result = self.classify(mention, threshold=threshold)
            results.append(result)

        # Summary
        matched = sum(1 for r in results if r.canonical_name is not None)
        high_conf = sum(1 for r in results if r.confidence == "high")
        medium_conf = sum(1 for r in results if r.confidence == "medium")
        low_conf = sum(1 for r in results if r.confidence == "low")

        print(f"\nClassification summary:")
        print(f"  Total: {len(results)}")
        print(f"  Matched: {matched} ({matched/len(results)*100:.1f}%)")
        print(f"  High confidence: {high_conf}")
        print(f"  Medium confidence: {medium_conf}")
        print(f"  Low confidence: {low_conf}")

        return results


def create_classifier(config: EntityResolutionConfig) -> CompanyClassifier:
    """
    Create and initialize company classifier.

    Args:
        config: Entity resolution configuration

    Returns:
        CompanyClassifier instance
    """
    return CompanyClassifier(config)
