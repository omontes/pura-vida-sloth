"""
GitHub Activity Parser for Knowledge Graph Extraction

Extracts technology and company entities/relations from GitHub repository data.
Uses LLM to analyze repository metadata, description, topics, and activity metrics.

Author: Pura Vida Sloth Intelligence System
"""

import os
import json
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.callbacks import get_openai_callback

from parsers.github_activity.repository_extractors import (
    extract_repository_metadata,
    build_document_id,
    format_github_url
)


class GitHubActivityParser:
    """LLM-driven parser to extract entities and relationships from GitHub repositories."""

    def __init__(
        self,
        openai_api_key: str,
        config_path: str = "configs/eVTOL_graph_relations.json",
        industry_name: str = None,
        industry_keywords: list = None,
        industry_description: str = None,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.0
    ):
        """
        Initialize GitHub activity parser with industry-specific context.

        Args:
            openai_api_key: OpenAI API key
            config_path: Path to graph relations config file
            industry_name: Target industry (e.g., "eVTOL")
            industry_keywords: Core industry keywords
            industry_description: Brief description of the industry
            model_name: OpenAI model to use (default: gpt-4o-mini)
            temperature: Model temperature (0.0 = deterministic)
        """
        # Load allowed relations from config
        with open(config_path, 'r', encoding='utf-8') as f:
            self.graph_config = json.load(f)

        self.allowed_company_tech_relations = self.graph_config["allowed_company_tech_relations"]
        self.allowed_tech_tech_relations = self.graph_config["allowed_tech_tech_relations"]
        self.allowed_company_company_relations = self.graph_config["allowed_company_company_relations"]

        # Store industry context
        self.industry_name = industry_name
        self.industry_keywords = industry_keywords if industry_keywords else []
        self.industry_description = industry_description

        self.llm = ChatOpenAI(
            temperature=temperature,
            model=model_name,
            api_key=openai_api_key,
            timeout=300.0
        )
        self.output_parser = JsonOutputParser()

        # Create chain for extraction
        self.chain = self._create_chain()

    def parse_repository(
        self,
        repo_dict: Dict[str, Any],
        metadata_record: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Parse a single GitHub repository.

        Args:
            repo_dict: Repository data dictionary from GitHub API
            metadata_record: Optional metadata dict

        Returns:
            Dictionary containing:
            - document: All document metadata + LLM-generated quality score
            - document_metadata: Extra GitHub-specific fields
            - tech_mentions: Technologies with roles, strength, confidence
            - company_mentions: Companies with roles, strength, confidence
            - company_tech_relations: Relations with doc_ref added
            - tech_tech_relations: Relations with doc_ref added
            - company_company_relations: Relations with doc_ref added
        """
        # Extract and normalize metadata
        metadata = extract_repository_metadata(repo_dict)

        # Format repository for LLM analysis
        llm_input = self._format_repository_for_llm(metadata)

        # Call LLM for entity extraction and quality scoring
        print(f"[PROCESSING] Extracting entities and quality score...")
        try:
            with get_openai_callback() as cb:
                llm_result = self.chain.invoke({"input": llm_input})
                print(f"  Extraction: {cb.total_tokens} tokens (${cb.total_cost:.6f})")
        except Exception as e:
            print(f"  [ERROR] LLM extraction failed: {e}")
            llm_result = self._empty_result()

        # Build document ID
        owner = metadata['owner']
        repo_name = metadata['repo_name'].split('/')[-1] if '/' in metadata['repo_name'] else metadata['repo_name']
        doc_id = build_document_id(owner, repo_name)

        # Build title
        title = metadata['repo_name']

        # Build URL (use existing if available, otherwise construct)
        url = metadata['url'] if metadata['url'] else format_github_url(owner, repo_name)

        # Build final result
        final_result = {
            "document": {
                # Core identification fields
                "doc_id": doc_id,
                "doc_type": "github_repository",
                "title": title,
                "url": url,
                "source": "GitHub",

                # Publication metadata
                "published_at": metadata.get("created_at"),
                "summary": "",  # Empty per user requirement
                "content": metadata.get("description", ""),  # Description per user requirement

                # Scoring
                "quality_score": llm_result.get("quality_score", 0.0),
                "relevance_score": 0.0,  # Placeholder for agents

                # GitHub-specific document fields (per user requirement)
                "github_id": metadata.get("github_id"),
                "repo_name": metadata.get("repo_name"),
                "owner": metadata.get("owner"),
                "created_at": metadata.get("created_at"),
                "last_pushed_at": metadata.get("last_pushed_at"),
                "stars": metadata.get("stars", 0),
                "forks": metadata.get("forks", 0),
                "contributor_count": metadata.get("contributor_count", 0),

                # Embedding placeholder
                "embedding": []
            },
            "document_metadata": {
                # Extra GitHub-specific fields (per user requirement)
                "language": metadata.get("language"),
                "topics": metadata.get("topics", []),
                "license": metadata.get("license"),
                "watchers": metadata.get("watchers", 0),
                "open_issues": metadata.get("open_issues", 0),
                "size": metadata.get("size", 0),
                "days_since_last_update": metadata.get("days_since_last_update", 0),
                "is_active": metadata.get("is_active", False),
                "popularity_score": metadata.get("popularity_score", 0.0)
            },
            "tech_mentions": llm_result.get("tech_mentions", []),
            "company_mentions": llm_result.get("company_mentions", []),
            "company_tech_relations": llm_result.get("company_tech_relations", []),
            "tech_tech_relations": llm_result.get("tech_tech_relations", []),
            "company_company_relations": llm_result.get("company_company_relations", [])
        }

        # Add doc_ref to all relations
        for rel in final_result["company_tech_relations"]:
            rel["doc_ref"] = doc_id
        for rel in final_result["tech_tech_relations"]:
            rel["doc_ref"] = doc_id
        for rel in final_result["company_company_relations"]:
            rel["doc_ref"] = doc_id

        # Validate relations match config
        self._validate_relations(llm_result)

        return final_result

    def parse_and_save(
        self,
        repo_dict: Dict[str, Any],
        out_path: str = "github_parse_result.json",
        metadata_record: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Parse a GitHub repository and save results to JSON file."""
        result = self.parse_repository(repo_dict, metadata_record)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to: {out_path}")
        return result

    def _format_repository_for_llm(self, metadata: Dict[str, Any]) -> str:
        """
        Format repository data as readable text for LLM analysis.

        Args:
            metadata: Normalized repository metadata

        Returns:
            Formatted string for LLM input
        """
        topics_str = ", ".join(metadata.get('topics', []))

        return f"""GITHUB REPOSITORY ANALYSIS REQUEST

Repository: {metadata.get('repo_name', 'Unknown')}
Owner: {metadata.get('owner', 'Unknown')}
Stars: {metadata.get('stars', 0)}
Forks: {metadata.get('forks', 0)}
Contributors: {metadata.get('contributor_count', 0)}
Primary Language: {metadata.get('language', 'Unknown')}
Topics: {topics_str if topics_str else 'None'}
License: {metadata.get('license', 'Unknown')}
Created: {metadata.get('created_at', 'Unknown')}
Last Push: {metadata.get('last_pushed_at', 'Unknown')}
Days Since Update: {metadata.get('days_since_last_update', 0)}
Is Active: {metadata.get('is_active', False)}
Popularity Score: {metadata.get('popularity_score', 0.0)}

Description: {metadata.get('description', 'No description provided')}

TASK: Extract core technologies, companies/developers, and their relationships for knowledge graph construction.
Also determine: quality_score (0.0-1.0, relevance to {self.industry_name} industry)."""

    def _validate_relations(self, llm_result: Dict[str, Any]) -> None:
        """Validate that relation types match allowed enums from config."""
        # Validate company-tech relations
        for rel in llm_result.get("company_tech_relations", []):
            rel_type = rel.get("relation_type")
            if rel_type and rel_type not in self.allowed_company_tech_relations:
                print(f"  Warning: Invalid company-tech relation '{rel_type}'")

        # Validate tech-tech relations
        for rel in llm_result.get("tech_tech_relations", []):
            rel_type = rel.get("relation_type")
            if rel_type and rel_type not in self.allowed_tech_tech_relations:
                print(f"  Warning: Invalid tech-tech relation '{rel_type}'")

        # Validate company-company relations
        for rel in llm_result.get("company_company_relations", []):
            rel_type = rel.get("relation_type")
            if rel_type and rel_type not in self.allowed_company_company_relations:
                print(f"  Warning: Invalid company-company relation '{rel_type}'")

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure on parsing failure."""
        return {
            "quality_score": 0.0,
            "tech_mentions": [],
            "company_mentions": [],
            "company_tech_relations": [],
            "tech_tech_relations": [],
            "company_company_relations": []
        }

    def _create_chain(self):
        """Build the few-shot chain for GitHub repository entity extraction."""

        # Few-shot example 1: High-quality eVTOL repository (high relevance)
        ex_input_1 = f"""GITHUB REPOSITORY ANALYSIS REQUEST

Repository: joby/evtol-flight-controller
Owner: joby
Stars: 342
Forks: 87
Contributors: 15
Primary Language: C++
Topics: evtol, flight-control, autonomous-flight, aviation, uam
License: Apache-2.0
Created: 2022-03-15T10:30:00Z
Last Push: 2024-11-05T14:20:00Z
Days Since Update: 3
Is Active: True
Popularity Score: 0.85

Description: Advanced flight control system for electric VTOL aircraft with autonomous navigation capabilities. Implements multi-rotor control algorithms, sensor fusion, and real-time trajectory planning for urban air mobility operations.

TASK: Extract core technologies, companies/developers, and their relationships for knowledge graph construction.
Also determine: quality_score (0.0-1.0, relevance to {self.industry_name} industry)."""

        ex_output_1 = json.dumps({
            "quality_score": 0.98,
            "tech_mentions": [
                {
                    "name": "Flight Control Systems",
                    "role": "implemented",
                    "strength": 0.95,
                    "evidence_confidence": 0.98,
                    "evidence_text": "Advanced flight control system for electric VTOL aircraft with autonomous navigation"
                },
                {
                    "name": "Autonomous Flight",
                    "role": "implemented",
                    "strength": 0.90,
                    "evidence_confidence": 0.95,
                    "evidence_text": "Autonomous navigation capabilities with real-time trajectory planning"
                },
                {
                    "name": "Sensor Fusion",
                    "role": "implemented",
                    "strength": 0.85,
                    "evidence_confidence": 0.90,
                    "evidence_text": "Implements sensor fusion for multi-rotor control algorithms"
                },
                {
                    "name": "Urban Air Mobility",
                    "role": "applied",
                    "strength": 0.88,
                    "evidence_confidence": 0.92,
                    "evidence_text": "Designed for urban air mobility operations"
                }
            ],
            "company_mentions": [
                {
                    "name": "Joby Aviation",
                    "role": "developer",
                    "strength": 0.90,
                    "evidence_confidence": 0.95,
                    "evidence_text": "Repository owner joby develops eVTOL flight control system"
                }
            ],
            "company_tech_relations": [
                {
                    "company_name": "Joby Aviation",
                    "technology_name": "Flight Control Systems",
                    "relation_type": "develops",
                    "evidence_confidence": 0.95,
                    "evidence_text": "Joby develops advanced flight control system for eVTOL aircraft"
                },
                {
                    "company_name": "Joby Aviation",
                    "technology_name": "Autonomous Flight",
                    "relation_type": "develops",
                    "evidence_confidence": 0.92,
                    "evidence_text": "Joby develops autonomous navigation capabilities for eVTOL"
                }
            ],
            "tech_tech_relations": [
                {
                    "from_tech_name": "Sensor Fusion",
                    "to_tech_name": "Flight Control Systems",
                    "relation_type": "enables",
                    "evidence_confidence": 0.90,
                    "evidence_text": "Sensor fusion enables advanced flight control for multi-rotor systems"
                },
                {
                    "from_tech_name": "Autonomous Flight",
                    "to_tech_name": "Urban Air Mobility",
                    "relation_type": "enables",
                    "evidence_confidence": 0.88,
                    "evidence_text": "Autonomous navigation enables urban air mobility operations"
                }
            ],
            "company_company_relations": []
        }, indent=2)

        # Few-shot example 2: Low-quality generic repository (low relevance)
        ex_input_2 = f"""GITHUB REPOSITORY ANALYSIS REQUEST

Repository: johndoe/react-todo-app
Owner: johndoe
Stars: 12
Forks: 3
Contributors: 1
Primary Language: JavaScript
Topics: react, todo, web-app, frontend
License: MIT
Created: 2023-08-20T09:15:00Z
Last Push: 2023-09-05T11:30:00Z
Days Since Update: 430
Is Active: False
Popularity Score: 0.15

Description: A simple todo list application built with React and Redux. Features include adding, editing, and deleting tasks with local storage persistence.

TASK: Extract core technologies, companies/developers, and their relationships for knowledge graph construction.
Also determine: quality_score (0.0-1.0, relevance to {self.industry_name} industry)."""

        ex_output_2 = json.dumps({
            "quality_score": 0.10,
            "tech_mentions": [],
            "company_mentions": [],
            "company_tech_relations": [],
            "tech_tech_relations": [],
            "company_company_relations": []
        }, indent=2)

        # Create few-shot prompt wrapper
        example_prompt = ChatPromptTemplate.from_messages([
            ("human", "{input}"),
            ("ai", "{output}")
        ])

        few_shot = FewShotChatMessagePromptTemplate(
            example_prompt=example_prompt,
            examples=[
                {"input": ex_input_1, "output": ex_output_1},
                {"input": ex_input_2, "output": ex_output_2}
            ],
        )

        # System prompt
        relation_defs_json = json.dumps(self.graph_config['relation_definitions'], indent=2)
        relation_defs_escaped = relation_defs_json.replace('{', '{{').replace('}', '}}')

        system_prompt = f"""You are a GitHub repository analyst extracting entities and relationships for strategic intelligence in the {self.industry_name} industry.

ALLOWED RELATION TYPES (use ONLY these from config):

Company → Technology ({len(self.allowed_company_tech_relations)} types):
{', '.join(self.allowed_company_tech_relations)}

Technology → Technology ({len(self.allowed_tech_tech_relations)} types):
{', '.join(self.allowed_tech_tech_relations)}

Company → Company ({len(self.allowed_company_company_relations)} types):
{', '.join(self.allowed_company_company_relations)}

RELATION DEFINITIONS:
{relation_defs_escaped}

ENTITY ROLES FOR GITHUB REPOSITORIES:

Technology Roles:
- "implemented": Technology implemented in the repository code
- "applied": Technology applied/used in the project
- "researched": Technology under research/experimentation
- "supported": Technology supported by the library/framework
- "integrated": Technology integrated with other systems

Company Roles:
- "developer": Company/organization developing the repository
- "contributor": Company with significant contributions
- "sponsor": Company sponsoring the project
- "user": Company using the technology
- "maintainer": Company maintaining the project

STRENGTH SCORING (0.0-1.0):
- 1.0: Core focus of repository
- 0.7-0.9: Major component/feature
- 0.4-0.6: Supporting element
- 0.1-0.3: Mentioned/referenced

CONFIDENCE SCORING (0.0-1.0):
- 0.95-1.0: Explicit in description/topics
- 0.8-0.94: Strong inference from metadata
- 0.6-0.79: Moderate inference
- 0.5-0.59: Weak inference

QUALITY SCORE (0.0-1.0) - Industry Relevance Assessment:
PURPOSE: Determine if this repository is actually relevant to the {self.industry_name} industry.
Some repositories may have keyword matches but not be truly related to the industry.
Repositories with quality_score < 0.85 will be FILTERED OUT in post-processing.

Scoring Guidelines for {self.industry_name} industry:
- 0.95-1.0: Core industry implementation (flight control, eVTOL simulation, UAM infrastructure)
- 0.85-0.94: Supporting technology (battery management, autopilot libraries, aerospace tools)
- 0.70-0.84: General aerospace tools (CFD, flight planning, aviation safety)
- 0.50-0.69: Generic libraries used in industry (React for dashboards, TensorFlow for vision)
- 0.0-0.49: Not industry-related (generic web apps, unrelated projects)

Examples for {self.industry_name}:
- 1.0: "eVTOL flight controller with autonomous navigation" (core implementation)
- 0.90: "Electric propulsion motor controller" (supporting tech)
- 0.75: "General aviation weather API" (general aerospace)
- 0.60: "React dashboard framework" (generic tool, keyword match only)
- 0.30: "Todo list app" (not eVTOL related)

CRITICAL: Be strict in scoring to maintain data quality for strategic intelligence.

OUTPUT SCHEMA:
{{{{
  "quality_score": float,
  "tech_mentions": [
    {{{{
      "name": string,
      "role": string,
      "strength": float,
      "evidence_confidence": float,
      "evidence_text": string (max 200 chars)
    }}}}
  ],
  "company_mentions": [
    {{{{
      "name": string,
      "role": string,
      "strength": float,
      "evidence_confidence": float,
      "evidence_text": string (max 200 chars)
    }}}}
  ],
  "company_tech_relations": [
    {{{{
      "company_name": string,
      "technology_name": string,
      "relation_type": string,
      "evidence_confidence": float,
      "evidence_text": string (max 200 chars)
    }}}}
  ],
  "tech_tech_relations": [
    {{{{
      "from_tech_name": string,
      "to_tech_name": string,
      "relation_type": string,
      "evidence_confidence": float,
      "evidence_text": string (max 200 chars)
    }}}}
  ],
  "company_company_relations": [
    {{{{
      "from_company_name": string,
      "to_company_name": string,
      "relation_type": string,
      "evidence_confidence": float,
      "evidence_text": string (max 200 chars)
    }}}}
  ]
}}}}

CRITICAL RULES:
- Output ONLY valid JSON
- Each mention has ONE role only
- Use ONLY allowed relation types
- Evidence text < 200 chars
- Extract 2-6 technology mentions for relevant repos
- Extract 1-4 company mentions for relevant repos
- Quality score < 0.85 → can return empty arrays (not relevant)
- Be STRICT with quality scoring - avoid false positives
"""

        final_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            few_shot,
            ("human", "{input}")
        ])

        return final_prompt | self.llm | self.output_parser


def load_industry_config(config_path: str) -> Dict[str, Any]:
    """Load industry configuration from JSON file."""
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config
