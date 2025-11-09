"""
Government Contracts Parser for Knowledge Graph Extraction

Extracts technology and company entities/relations from USASpending.gov contract data.
Uses LLM to analyze contract metadata, description, and award details.

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

from parsers.gov_contracts.contract_extractors import (
    extract_contract_metadata,
    calculate_contract_duration,
    categorize_contract_size,
    derive_agency_type,
    build_document_id,
    build_contract_url
)


class GovContractsParser:
    """LLM-driven parser to extract entities and relationships from government contracts."""

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
        Initialize government contracts parser with industry-specific context.

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

    def parse_contract(
        self,
        contract_dict: Dict[str, Any],
        metadata_record: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Parse a single government contract.

        Args:
            contract_dict: Contract data dictionary from USASpending.gov API
            metadata_record: Optional metadata dict

        Returns:
            Dictionary containing:
            - document: All document metadata + LLM-generated quality score
            - document_metadata: Extra contract-specific fields
            - tech_mentions: Technologies with roles, strength, confidence
            - company_mentions: Companies with roles, strength, confidence
            - company_tech_relations: Relations with doc_ref added
            - tech_tech_relations: Relations with doc_ref added
            - company_company_relations: Relations with doc_ref added
        """
        # Extract and normalize metadata
        metadata = extract_contract_metadata(contract_dict)

        # Format contract for LLM analysis
        llm_input = self._format_contract_for_llm(metadata)

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
        doc_id = build_document_id(metadata['award_id'])

        # Build title
        title = f"{metadata['recipient_name']} - {metadata['awarding_sub_agency']} Contract"

        # Build URL (use existing if available, otherwise construct)
        url = metadata['url'] if metadata['url'] else build_contract_url(metadata['award_id'])

        # Calculate derived fields
        contract_duration_days = calculate_contract_duration(
            metadata['start_date'],
            metadata['end_date']
        )
        contract_size_category = categorize_contract_size(metadata['award_amount'])
        agency_type = derive_agency_type(metadata['awarding_agency'])

        # Build final result
        final_result = {
            "document": {
                # Core identification fields
                "doc_id": doc_id,
                "doc_type": "government_contract",
                "title": title,
                "url": url,
                "source": "USASpending.gov",

                # Publication metadata
                "published_at": metadata.get("start_date"),
                "summary": "",  # Empty per user requirement
                "content": metadata.get("description", ""),  # Description per user requirement

                # Scoring
                "quality_score": llm_result.get("quality_score", 0.0),
                "relevance_score": 0.0,  # Placeholder for agents

                # Contract-specific document fields (per user requirement)
                "award_id": metadata.get("award_id"),
                "recipient_name": metadata.get("recipient_name"),
                "award_amount": metadata.get("award_amount", 0.0),
                "start_date": metadata.get("start_date"),
                "end_date": metadata.get("end_date"),
                "awarding_agency": metadata.get("awarding_agency"),
                "awarding_sub_agency": metadata.get("awarding_sub_agency"),

                # Embedding placeholder
                "embedding": []
            },
            "document_metadata": {
                # Extra contract-specific fields
                "award_type": metadata.get("award_type"),
                "search_term": metadata.get("search_term"),
                "agency_type": agency_type,
                "contract_size_category": contract_size_category,
                "contract_duration_days": contract_duration_days
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
        contract_dict: Dict[str, Any],
        out_path: str = "gov_contract_parse_result.json",
        metadata_record: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Parse a government contract and save results to JSON file."""
        result = self.parse_contract(contract_dict, metadata_record)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to: {out_path}")
        return result

    def _format_contract_for_llm(self, metadata: Dict[str, Any]) -> str:
        """
        Format contract data as readable text for LLM analysis.

        Args:
            metadata: Normalized contract metadata

        Returns:
            Formatted string for LLM input
        """
        duration_days = calculate_contract_duration(
            metadata.get('start_date'),
            metadata.get('end_date')
        )

        duration_years = duration_days / 365 if duration_days > 0 else 0

        return f"""GOVERNMENT CONTRACT ANALYSIS REQUEST

Award ID: {metadata.get('award_id', 'Unknown')}
Recipient: {metadata.get('recipient_name', 'Unknown')}
Award Amount: ${metadata.get('award_amount', 0):,.2f}
Contract Duration: {duration_days} days ({duration_years:.1f} years)
Start Date: {metadata.get('start_date', 'Unknown')}
End Date: {metadata.get('end_date', 'Unknown')}

Awarding Agency: {metadata.get('awarding_agency', 'Unknown')}
Awarding Sub-Agency: {metadata.get('awarding_sub_agency', 'Unknown')}

Contract Description: {metadata.get('description', 'No description provided')}

TASK: Extract core technologies, companies, and their relationships for knowledge graph construction.
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
        """Build the few-shot chain for government contract entity extraction."""

        # Few-shot example 1: High-quality eVTOL contract (high relevance)
        ex_input_1 = f"""GOVERNMENT CONTRACT ANALYSIS REQUEST

Award ID: FA864922P0797
Recipient: ARCHER AVIATION INC.
Award Amount: $744,796.00
Contract Duration: 459 days (1.3 years)
Start Date: 2022-03-24
End Date: 2023-06-26

Awarding Agency: Department of Defense
Awarding Sub-Agency: Department of the Air Force

Contract Description: PRECISION LANDING LOCALIZATION TECHNOLOGY FOR AUTONOMOUS ELECTRIC VERTICAL TAKE-OFF AND LANDING AIRCRAFT IN GLOBAL POSITIONING SYSTEM-DENIED ENVIRONMENTS

TASK: Extract core technologies, companies, and their relationships for knowledge graph construction.
Also determine: quality_score (0.0-1.0, relevance to {self.industry_name} industry)."""

        ex_output_1 = json.dumps({
            "quality_score": 0.98,
            "tech_mentions": [
                {
                    "name": "Autonomous Flight Systems",
                    "role": "funded",
                    "strength": 0.95,
                    "evidence_confidence": 0.98,
                    "evidence_text": "Precision landing technology for autonomous electric VTOL aircraft"
                },
                {
                    "name": "GPS-Denied Navigation",
                    "role": "funded",
                    "strength": 0.90,
                    "evidence_confidence": 0.95,
                    "evidence_text": "Localization technology in GPS-denied environments"
                },
                {
                    "name": "eVTOL Aircraft",
                    "role": "deployed",
                    "strength": 0.92,
                    "evidence_confidence": 0.98,
                    "evidence_text": "Electric vertical take-off and landing aircraft deployment"
                },
                {
                    "name": "Precision Landing",
                    "role": "funded",
                    "strength": 0.88,
                    "evidence_confidence": 0.92,
                    "evidence_text": "Precision landing localization technology development"
                }
            ],
            "company_mentions": [
                {
                    "name": "Archer Aviation",
                    "role": "contractor",
                    "strength": 1.0,
                    "evidence_confidence": 1.0,
                    "evidence_text": "Recipient Name: ARCHER AVIATION INC."
                },
                {
                    "name": "US Air Force",
                    "role": "customer",
                    "strength": 1.0,
                    "evidence_confidence": 1.0,
                    "evidence_text": "Awarding Sub-Agency: Department of the Air Force"
                }
            ],
            "company_tech_relations": [
                {
                    "company_name": "Archer Aviation",
                    "technology_name": "Autonomous Flight Systems",
                    "relation_type": "develops",
                    "evidence_confidence": 0.98,
                    "evidence_text": "Archer develops precision landing for autonomous eVTOL aircraft"
                },
                {
                    "company_name": "Archer Aviation",
                    "technology_name": "GPS-Denied Navigation",
                    "relation_type": "develops",
                    "evidence_confidence": 0.95,
                    "evidence_text": "Archer develops localization technology for GPS-denied environments"
                },
                {
                    "company_name": "US Air Force",
                    "technology_name": "eVTOL Aircraft",
                    "relation_type": "funds",
                    "evidence_confidence": 0.98,
                    "evidence_text": "US Air Force funds eVTOL technology development through contract"
                }
            ],
            "tech_tech_relations": [
                {
                    "from_tech_name": "Precision Landing",
                    "to_tech_name": "Autonomous Flight Systems",
                    "relation_type": "enables",
                    "evidence_confidence": 0.92,
                    "evidence_text": "Precision landing enables autonomous flight operations"
                },
                {
                    "from_tech_name": "GPS-Denied Navigation",
                    "to_tech_name": "Precision Landing",
                    "relation_type": "enables",
                    "evidence_confidence": 0.90,
                    "evidence_text": "GPS-denied navigation enables precision landing in constrained environments"
                }
            ],
            "company_company_relations": [
                {
                    "from_company_name": "Archer Aviation",
                    "to_company_name": "US Air Force",
                    "relation_type": "partners_with",
                    "evidence_confidence": 1.0,
                    "evidence_text": "Contract awarded by US Air Force to Archer Aviation for eVTOL technology"
                }
            ]
        }, indent=2)

        # Few-shot example 2: Low-quality generic contract (low relevance)
        ex_input_2 = f"""GOVERNMENT CONTRACT ANALYSIS REQUEST

Award ID: ZB93
Recipient: THE BOEING COMPANY
Award Amount: $306,324.95
Contract Duration: 365 days (1.0 years)
Start Date: 2020-01-01
End Date: 2020-12-31

Awarding Agency: Department of Defense
Awarding Sub-Agency: Defense Logistics Agency

Contract Description: SPARES

TASK: Extract core technologies, companies, and their relationships for knowledge graph construction.
Also determine: quality_score (0.0-1.0, relevance to {self.industry_name} industry)."""

        ex_output_2 = json.dumps({
            "quality_score": 0.30,
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

        system_prompt = f"""You are a government contracts analyst extracting entities and relationships for strategic intelligence in the {self.industry_name} industry.

ALLOWED RELATION TYPES (use ONLY these from config):

Company → Technology ({len(self.allowed_company_tech_relations)} types):
{', '.join(self.allowed_company_tech_relations)}

Technology → Technology ({len(self.allowed_tech_tech_relations)} types):
{', '.join(self.allowed_tech_tech_relations)}

Company → Company ({len(self.allowed_company_company_relations)} types):
{', '.join(self.allowed_company_company_relations)}

RELATION DEFINITIONS:
{relation_defs_escaped}

ENTITY ROLES FOR GOVERNMENT CONTRACTS:

Technology Roles:
- "funded": Technology receiving government funding
- "deployed": Technology being deployed in contract
- "validated": Technology validated by government use
- "researched": Technology under government research contract

Company Roles:
- "contractor": Company receiving the contract award (ALWAYS EXTRACT)
- "customer": Government agency awarding the contract (ALWAYS EXTRACT)
- "partner": Strategic government-industry partner
- "subcontractor": Subcontractor mentioned in contract

CRITICAL: Government contracts create DUAL company entities:
1. Contractor (recipient company) - role: "contractor"
2. Customer (government agency) - role: "customer"
ALWAYS extract BOTH companies and create company-company relation: contractor → partners_with → agency

STRENGTH SCORING (0.0-1.0):
- 1.0: Core focus of contract (explicit in description)
- 0.7-0.9: Major component of contract
- 0.4-0.6: Supporting element
- 0.1-0.3: Mentioned/referenced

CONFIDENCE SCORING (0.0-1.0):
- 0.95-1.0: Explicit in description or award details
- 0.8-0.94: Strong inference from contract metadata
- 0.6-0.79: Moderate inference
- 0.5-0.59: Weak inference

QUALITY SCORE (0.0-1.0) - Industry Relevance Assessment:
PURPOSE: Determine if this contract is actually relevant to the {self.industry_name} industry.
Government contracts are pre-filtered, but some may still not be truly {self.industry_name}-related.
Contracts with quality_score < 0.85 will be FILTERED OUT in post-processing.

Scoring Guidelines for {self.industry_name} industry:
- 0.95-1.0: Core industry contract (eVTOL development, UAM infrastructure, flight systems)
- 0.85-0.94: Supporting technology (autonomy, batteries, sensors specifically for eVTOL)
- 0.70-0.84: Related aerospace (general aviation systems adaptable to eVTOL)
- 0.50-0.69: Generic technology (keyword match only, not industry-specific)
- 0.0-0.49: Not industry-related (spare parts, admin services, generic contracts)

Examples for {self.industry_name}:
- 1.0: "Autonomous eVTOL flight control system development" (core eVTOL tech)
- 0.90: "Electric propulsion battery management for VTOL" (supporting tech)
- 0.75: "Advanced aviation sensor integration" (general aerospace)
- 0.60: "Generic aircraft component manufacturing" (keyword match only)
- 0.30: "Spare parts for aircraft" (not eVTOL-specific)

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
- Extract 2-6 technology mentions for relevant contracts
- ALWAYS extract 2 company mentions: contractor + customer agency
- ALWAYS create company-company relation: contractor → partners_with → agency
- Quality score < 0.85 → can return minimal arrays (not highly relevant)
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
