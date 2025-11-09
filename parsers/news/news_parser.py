"""
News Article Parser
Author: Pura Vida Sloth Intelligence System

Parses news articles with Tavily content extraction and LLM-based entity extraction.
Generates summaries, quality scores, and extracts entities for knowledge graph ingestion.
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate

from parsers.news.news_extractors import (
    extract_article_metadata,
    parse_seendate,
    classify_outlet_tier,
    extract_article_with_tavily,
    build_document_id,
    extract_domain,
    extract_publisher_name
)


def load_industry_config(config_path: str) -> Dict[str, Any]:
    """Load industry configuration from JSON file."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


class NewsParser:
    """
    Parser for news articles with Tavily content extraction and LLM-based entity extraction.
    """

    def __init__(
        self,
        openai_api_key: str,
        tavily_api_key: str,
        config_path: str,
        industry_name: str,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.0
    ):
        """
        Initialize NewsParser.

        Args:
            openai_api_key: OpenAI API key
            tavily_api_key: Tavily API key
            config_path: Path to graph relations config
            industry_name: Industry name (e.g., "eVTOL")
            model_name: OpenAI model name
            temperature: LLM temperature
        """
        self.openai_api_key = openai_api_key
        self.tavily_api_key = tavily_api_key
        self.industry_name = industry_name
        self.model_name = model_name
        self.temperature = temperature

        # Load graph relations config
        with open(config_path, 'r', encoding='utf-8') as f:
            self.graph_config = json.load(f)

        # Extract allowed relation types from config (industry-agnostic)
        self.allowed_company_tech_relations = self.graph_config["allowed_company_tech_relations"]
        self.allowed_tech_tech_relations = self.graph_config["allowed_tech_tech_relations"]
        self.allowed_company_company_relations = self.graph_config["allowed_company_company_relations"]

        # Initialize LLM
        self.llm = ChatOpenAI(
            api_key=openai_api_key,
            model=model_name,
            temperature=temperature
        )

        # Setup few-shot prompting
        self.prompt = self._setup_few_shot_prompt()

    def _setup_few_shot_prompt(self) -> ChatPromptTemplate:
        """
        Setup few-shot prompt template for news article extraction.

        Returns:
            ChatPromptTemplate with few-shot examples
        """
        # Few-shot examples for news articles (matching patents parser structure)
        examples = [
            {
                "input": {
                    "title": "Joby Aviation Receives FAA Type Certification for eVTOL Aircraft",
                    "domain": "aviationweek.com",
                    "content": "Joby Aviation announced today that it has received Type Certification from the Federal Aviation Administration (FAA) for its electric vertical takeoff and landing (eVTOL) aircraft. This milestone marks a significant step toward commercial operations of air taxis in urban air mobility markets. The certification validates Joby's proprietary electric propulsion system and advanced flight control software. Industry experts note this is the first eVTOL certification in the United States, positioning Joby ahead of competitors like Archer Aviation and Lilium. The company plans to begin commercial operations in 2025.",
                    "outlet_tier": "Industry Authority"
                },
                "output": {
                    "summary": "Joby Aviation received FAA Type Certification for its eVTOL aircraft, marking the first such certification in the US and positioning the company for 2025 commercial operations.",
                    "quality_score": 0.95,
                    "tech_mentions": [
                        {
                            "name": "eVTOL",
                            "role": "subject",
                            "strength": 0.95,
                            "evidence_confidence": 0.98,
                            "evidence_text": "Primary topic: FAA Type Certification for eVTOL aircraft"
                        },
                        {
                            "name": "electric propulsion",
                            "role": "implemented",
                            "strength": 0.80,
                            "evidence_confidence": 0.95,
                            "evidence_text": "Joby's proprietary electric propulsion system validated by FAA"
                        },
                        {
                            "name": "flight control software",
                            "role": "implemented",
                            "strength": 0.75,
                            "evidence_confidence": 0.95,
                            "evidence_text": "Advanced flight control software certified by FAA"
                        }
                    ],
                    "company_mentions": [
                        {
                            "name": "Joby Aviation",
                            "role": "developer",
                            "strength": 1.0,
                            "evidence_confidence": 1.0,
                            "evidence_text": "Joby Aviation announced FAA certification for its eVTOL"
                        },
                        {
                            "name": "Archer Aviation",
                            "role": "competitor",
                            "strength": 0.40,
                            "evidence_confidence": 0.90,
                            "evidence_text": "Joby positioned ahead of competitor Archer Aviation"
                        },
                        {
                            "name": "Lilium",
                            "role": "competitor",
                            "strength": 0.40,
                            "evidence_confidence": 0.90,
                            "evidence_text": "Joby positioned ahead of competitor Lilium"
                        },
                        {
                            "name": "Aviation Week",
                            "role": "publisher",
                            "strength": 0.10,
                            "evidence_confidence": 1.0,
                            "evidence_text": "Article published by Aviation Week"
                        }
                    ],
                    "company_company_relations": [
                        {
                            "from_company_name": "Joby Aviation",
                            "to_company_name": "Archer Aviation",
                            "relation_type": "competes_with",
                            "evidence_confidence": 0.90,
                            "evidence_text": "Joby ahead of Archer in eVTOL certification race"
                        },
                        {
                            "from_company_name": "Joby Aviation",
                            "to_company_name": "Lilium",
                            "relation_type": "competes_with",
                            "evidence_confidence": 0.90,
                            "evidence_text": "Joby ahead of Lilium in eVTOL certification race"
                        }
                    ],
                    "company_tech_relations": [
                        {
                            "company_name": "Joby Aviation",
                            "technology_name": "eVTOL",
                            "relation_type": "develops",
                            "evidence_confidence": 1.0,
                            "evidence_text": "Joby developed eVTOL aircraft that received FAA certification"
                        },
                        {
                            "company_name": "Joby Aviation",
                            "technology_name": "electric propulsion",
                            "relation_type": "develops",
                            "evidence_confidence": 0.98,
                            "evidence_text": "Joby's proprietary electric propulsion system"
                        }
                    ],
                    "tech_tech_relations": []
                }
            },
            {
                "input": {
                    "title": "Flying Cars: The Future of Transportation?",
                    "domain": "tech-blog-daily.com",
                    "content": "Flying cars have been a dream for decades, and now they might finally become a reality. Some companies are working on electric flying vehicles that could change how we travel. These vehicles use batteries and electric motors. They might be used in cities one day. However, there are many challenges like regulations and infrastructure.",
                    "outlet_tier": "Niche/Aggregator"
                },
                "output": {
                    "summary": "Generic overview of flying car concepts with no specific company mentions, technological details, or industry insights.",
                    "quality_score": 0.25,
                    "tech_mentions": [],
                    "company_mentions": [
                        {
                            "name": "Tech Blog Daily",
                            "role": "publisher",
                            "strength": 0.10,
                            "evidence_confidence": 1.0,
                            "evidence_text": "Article published by Tech Blog Daily"
                        }
                    ],
                    "company_company_relations": [],
                    "company_tech_relations": [],
                    "tech_tech_relations": []
                }
            }
        ]

        # Build examples string for system message
        # Need to escape curly braces in JSON for LangChain template
        examples_str = ""
        for idx, ex in enumerate(examples, 1):
            # Escape curly braces in JSON output (double them for template)
            json_output = json.dumps(ex['output'], indent=2)
            escaped_json = json_output.replace("{", "{{").replace("}", "}}")

            examples_str += f"\n\n--- EXAMPLE {idx} ---\n"
            examples_str += f"INPUT:\n"
            examples_str += f"Article Title: {ex['input']['title']}\n"
            examples_str += f"Outlet: {ex['input']['domain']}\n"
            examples_str += f"Tier: {ex['input']['outlet_tier']}\n"
            examples_str += f"\nArticle Content:\n{ex['input']['content']}\n"
            examples_str += f"\nOUTPUT:\n{escaped_json}"

        # Prepare relation definitions (escape curly braces for LangChain template)
        relation_defs_json = json.dumps(self.graph_config['relation_definitions'], indent=2)
        relation_defs_escaped = relation_defs_json.replace('{', '{{').replace('}', '}}')

        # Final prompt (matching gov_contracts parser structure)
        final_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are a news article analyzer for strategic intelligence in the {self.industry_name} industry.

ALLOWED RELATION TYPES (use ONLY these from config):

Company → Technology ({len(self.allowed_company_tech_relations)} types):
{', '.join(self.allowed_company_tech_relations)}

Technology → Technology ({len(self.allowed_tech_tech_relations)} types):
{', '.join(self.allowed_tech_tech_relations)}

Company → Company ({len(self.allowed_company_company_relations)} types):
{', '.join(self.allowed_company_company_relations)}

RELATION DEFINITIONS:
{relation_defs_escaped}

TECHNOLOGY ROLES (ONE role per mention - create separate mentions for same entity with different roles):
- "subject": Primary topic of article
- "invented": Created/designed/originated (mentioned as new innovation)
- "regulated": Subject to government oversight (certifications, regulations)
- "commercialized": Sold/promoted/monetized
- "studied": Researched/tested/validated
- "implemented": Built/coded/deployed in products
- "procured": Purchased/contracted

COMPANY ROLES (ONE role per mention - create separate mentions for same entity with different roles):
- "developer": Builds/invents technology
- "operator": Uses technology commercially
- "competitor": Market player competing with subject company
- "publisher": Media outlet publishing the article
- "issuer": Reports to SEC (public company)
- "sponsor": Funds R&D
- "investment_target": Held by investors (stock mentioned)
- "employer": Recruits talent (hiring news)

STRENGTH SCORING (0.0-1.0) - Importance of THIS ROLE to Article:
- 1.0: Core focus (explicitly central to article for this role)
- 0.7-0.9: Key supporting element (critical but not primary for this role)
- 0.4-0.6: Supporting element (mentioned 2-3 times for this role)
- 0.1-0.3: Background/peripheral (mentioned once for this role)

CONFIDENCE SCORING (0.0-1.0) - Certainty of THIS ROLE Assignment:
- 0.95-1.0: Explicit statement, exact terminology for this role
- 0.8-0.94: Strong inference from article content for this role
- 0.6-0.79: Moderate inference from context for this role
- 0.5-0.59: Weak inference for this role

QUALITY SCORE (0.0-1.0) - Industry Relevance Assessment:
PURPOSE: Determine if this article is actually relevant to the {self.industry_name} industry.
Some articles may mention keywords but not be truly related to the industry.
Articles with quality_score < 0.85 will be FILTERED OUT in post-processing.

Scoring Guidelines:
- 0.95-1.0: Core industry news (direct application to {self.industry_name})
- 0.85-0.94: Supporting news (enables or complements industry)
- 0.70-0.84: Tangentially related (shares components or methods)
- 0.50-0.69: Keyword match only (not actually related to industry)
- 0.0-0.49: Not related to industry (false positive from search)

Example for {self.industry_name} industry:
- 1.0: "Joby receives FAA eVTOL certification" (core {self.industry_name} news)
- 0.90: "New battery tech for electric aircraft" (supporting technology)
- 0.75: "Urban mobility regulations announced" (tangential)
- 0.60: "General electric vehicle trends" (keyword match only)
- 0.30: "Tesla stock rises 10%" (not {self.industry_name} related)

CRITICAL: Be strict in scoring to maintain data quality for strategic intelligence.

OUTPUT SCHEMA:
{{{{
  "summary": string,  // 1-2 sentence concise summary of the article
  "quality_score": float,  // 0.0-1.0 industry relevance (0.85+ = relevant, <0.85 = discard)
  "tech_mentions": [
    {{{{
      "name": string,
      "role": string,  // SINGLE role (not array) - create multiple entries for same tech with different roles
      "strength": float,  // Strength of THIS specific role (0.0-1.0)
      "evidence_confidence": float,  // Confidence in THIS specific role (0.0-1.0)
      "evidence_text": string (max 200 chars, evidence for THIS role)
    }}}}
  ],
  "company_mentions": [
    {{{{
      "name": string,
      "role": string,  // SINGLE role (not array)
      "strength": float,  // Strength of THIS specific role (0.0-1.0)
      "evidence_confidence": float,  // Confidence in THIS specific role (0.0-1.0)
      "evidence_text": string (max 200 chars, evidence for THIS role)
    }}}}
  ],
  "company_tech_relations": [
    {{{{
      "company_name": string,
      "technology_name": string,
      "relation_type": string,  // MUST be one of: {', '.join(self.allowed_company_tech_relations)}
      "evidence_confidence": float,
      "evidence_text": string (max 200 chars)
    }}}}
  ],
  "company_company_relations": [
    {{{{
      "from_company_name": string,
      "to_company_name": string,
      "relation_type": string,  // MUST be one of: {', '.join(self.allowed_company_company_relations)}
      "evidence_confidence": float,
      "evidence_text": string (max 200 chars)
    }}}}
  ],
  "tech_tech_relations": [
    {{{{
      "from_tech_name": string,
      "to_tech_name": string,
      "relation_type": string,  // MUST be one of: {', '.join(self.allowed_tech_tech_relations)}
      "evidence_confidence": float,
      "evidence_text": string (max 200 chars)
    }}}}
  ]
}}}}

CRITICAL RULES:
- Output ONLY valid JSON (no markdown, no commentary)
- Each mention has ONE role only (not an array)
- If an entity has multiple roles, create SEPARATE mention entries with different strength/confidence for each role
- Example: "eVTOL" as subject (strength=0.95) AND as regulated (strength=0.80) = 2 separate entries
- Use ONLY allowed relation types from config (see ALLOWED RELATION TYPES above)
- Evidence text must be < 200 chars and specific to THAT role
- Extract 3-8 technology mentions total (including multiple roles for same tech)
- Extract 2-6 company mentions total (including multiple roles for same company)
- ALWAYS include the publisher as a company mention with role="publisher"

{examples_str}"""),
            ("human", "Article Title: {title}\nOutlet: {domain}\nTier: {outlet_tier}\n\nArticle Content:\n{content}")
        ])

        return final_prompt

    def parse_article(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a news article with Tavily content extraction and LLM-based entity extraction.

        Args:
            article_data: Raw article dictionary from GDELT

        Returns:
            Parsed result with document, metadata, entities, and relations
        """
        # Extract metadata
        metadata = extract_article_metadata(article_data)

        # Extract article content with Tavily
        url = metadata['url']
        domain = metadata['domain'] or extract_domain(url)

        print(f"  [Tavily] Extracting content from: {domain}")
        article_content = extract_article_with_tavily(
            url=url,
            api_key=self.tavily_api_key,
            extract_depth="basic"
        )

        if not article_content:
            raise ValueError(f"Failed to extract article content from {url}")

        # Classify outlet tier
        outlet_tier = classify_outlet_tier(domain)

        # Build document ID
        doc_id = build_document_id(url)

        # Prepare LLM input
        llm_input = {
            "title": metadata['title'],
            "domain": domain,
            "content": article_content,
            "outlet_tier": outlet_tier
        }

        # Call LLM for extraction
        print(f"  [LLM] Extracting entities and scoring...")
        chain = self.prompt | self.llm | JsonOutputParser()

        try:
            llm_result = chain.invoke(llm_input)
        except Exception as e:
            raise ValueError(f"LLM extraction failed: {e}")

        # Parse seendate
        seendate = parse_seendate(metadata['seendate'])

        # Python constructs document and document_metadata (matching patents parser structure)
        final_result = {
            "document": {
                "doc_id": doc_id,
                "doc_type": "news_article",
                "title": metadata['title'],
                "summary": llm_result.get("summary", ""),
                "content": "",  # Empty string, not placeholder
                "url": url,
                "source": "GDELT/Tavily",
                "quality_score": llm_result.get("quality_score", 0.0),
                "relevance_score": 0.0,
                "embedding": []
            },
            "document_metadata": {
                "domain": domain,
                "outlet_tier": outlet_tier,
                "seendate": seendate.isoformat() if seendate else None,
                "lang": metadata['language'],
                "keyword": metadata['keyword']
            },
            "tech_mentions": llm_result.get("tech_mentions", []),
            "company_mentions": llm_result.get("company_mentions", []),
            "company_tech_relations": llm_result.get("company_tech_relations", []),
            "tech_tech_relations": llm_result.get("tech_tech_relations", []),
            "company_company_relations": llm_result.get("company_company_relations", [])
        }

        # Ensure publisher is in company mentions with all required fields
        publisher_name = extract_publisher_name(domain)
        publisher_exists = any(
            c.get('name') == publisher_name and c.get('role') == 'publisher'
            for c in final_result.get('company_mentions', [])
        )

        if not publisher_exists:
            final_result['company_mentions'].append({
                "name": publisher_name,
                "role": "publisher",
                "strength": 0.10,
                "evidence_confidence": 1.0,
                "evidence_text": f"Article published by {publisher_name}"
            })

        # Add doc_ref to all relations (matching patents parser)
        for rel in final_result.get('company_tech_relations', []):
            rel['doc_ref'] = doc_id
        for rel in final_result.get('tech_tech_relations', []):
            rel['doc_ref'] = doc_id
        for rel in final_result.get('company_company_relations', []):
            rel['doc_ref'] = doc_id

        # Validate relations match config
        warnings = self._validate_relations(final_result)
        if warnings:
            print(f"⚠️  Validation warnings: {warnings}")

        return final_result

    def _validate_relations(self, result: Dict[str, Any]) -> List[str]:
        """
        Validate that all relations use allowed types from config.

        Args:
            result: Parsed result dictionary

        Returns:
            List of validation warning messages
        """
        warnings = []

        # Load allowed relation types from graph config
        allowed_company_tech = self.graph_config.get("allowed_company_tech_relations", [])
        allowed_tech_tech = self.graph_config.get("allowed_tech_tech_relations", [])
        allowed_company_company = self.graph_config.get("allowed_company_company_relations", [])

        for rel in result.get("company_tech_relations", []):
            if rel.get("relation_type") not in allowed_company_tech:
                warnings.append(f"Invalid company_tech relation: {rel.get('relation_type')}")

        for rel in result.get("tech_tech_relations", []):
            if rel.get("relation_type") not in allowed_tech_tech:
                warnings.append(f"Invalid tech_tech relation: {rel.get('relation_type')}")

        for rel in result.get("company_company_relations", []):
            if rel.get("relation_type") not in allowed_company_company:
                warnings.append(f"Invalid company_company relation: {rel.get('relation_type')}")

        return warnings
