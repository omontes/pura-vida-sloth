"""
Patent Technology Parser for Knowledge Graph Construction
Author: Pura Vida Sloth Intelligence System

Analyzes patent data to extract:
- Core technologies and innovations
- Technical relationships (builds-on, contradicts, supports)
- Innovation signals for lifecycle assessment

Output: Neo4j-compatible triplets (node, edge, node) for multi-layer intelligence analysis
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.callbacks import get_openai_callback


class PatentTechnologyParser:
    """LLM-driven parser to extract technology relationships from patent data."""

    def __init__(self,
                 openai_api_key: str,
                 config_path: str = "configs/eVTOL_graph_relations.json",
                 model_name: str = "gpt-4o-mini",
                 temperature: float = 0.0):

        # Load allowed relations from config
        with open(config_path, 'r', encoding='utf-8') as f:
            self.graph_config = json.load(f)

        self.allowed_company_tech_relations = self.graph_config["allowed_company_tech_relations"]
        self.allowed_tech_tech_relations = self.graph_config["allowed_tech_tech_relations"]
        self.allowed_company_company_relations = self.graph_config["allowed_company_company_relations"]

        # Initialize LLM
        self.llm = ChatOpenAI(
            temperature=temperature,
            model=model_name,
            api_key=openai_api_key,
            timeout=300.0
        )
        self.output_parser = JsonOutputParser()
        self.chain = self._create_chain()

    def parse_patent(self, patent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a single patent into entity mentions and relationships.

        Args:
            patent_data: Patent record from Lens.org API

        Returns:
            Dictionary containing:
            - document: All original patent metadata
            - tech_mentions: Technologies with roles, strength, confidence
            - company_mentions: Companies with roles, strength, confidence
            - company_tech_relations: Relations with doc_ref added
            - tech_tech_relations: Relations with doc_ref added
            - company_company_relations: Relations with doc_ref added
        """
        input_text = self._format_patent_for_llm(patent_data)

        try:
            with get_openai_callback() as cb:
                # LLM generates mentions + relations only
                llm_result = self.chain.invoke({"input": input_text})

                # Log token usage and cost
                print(f"\nToken Usage: {cb.total_tokens} tokens (${cb.total_cost:.6f})")

        except Exception as e:
            print(f"Parsing error: {e}")
            llm_result = {
                "quality_score": 0.0,
                "tech_mentions": [],
                "company_mentions": [],
                "company_tech_relations": [],
                "tech_tech_relations": [],
                "company_company_relations": []
            }

        # Python adds document metadata
        doc_id = patent_data.get("lens_id", "")

        # Extract patent fields from API data
        patent_type = patent_data.get("type", "")
        grant_date = patent_data.get("grant_date", "")
        discontinuation_date = patent_data.get("discontinuation_date", "")
        anticipated_term_date = patent_data.get("anticipated_term_date", "")

        # Compute legal status
        legal_status = self._compute_legal_status(
            patent_type=patent_type,
            discontinuation_date=discontinuation_date,
            anticipated_term_date=anticipated_term_date
        )

        final_result = {
            "document": {
                # Core identification fields
                "doc_id": doc_id,
                "doc_type": "patent",
                "title": patent_data.get("title", ""),
                "assignee_name": patent_data.get("assignee", ""),

                # Patent-specific fields
                "patent_number": patent_data.get("patent_number", ""),
                "jurisdiction": patent_data.get("jurisdiction", ""),
                "type": patent_type,
                "legal_status": legal_status,
                "filing_date": patent_data.get("filing_date", ""),
                "grant_date": grant_date if grant_date else None,
                "published_at": patent_data.get("publication_date", ""),
                "citation_count": patent_data.get("citation_count", 0),
                "simple_family_size": patent_data.get("simple_family_size", 0),

                # Generalized document fields
                "url": patent_data.get("url", ""),
                "source": "Lens.org Patent API",
                "summary": "",
                "content": patent_data.get("abstract", ""),
                "quality_score": llm_result.get("quality_score", 0.0),
                "relevance_score": 0.0,
                "embedding": []
            },
            "document_metadata": {
                "kind": patent_data.get("kind", ""),
                "cpc_codes": patent_data.get("cpc_codes", []),
                "doc_key": patent_data.get("doc_key", ""),
                "publication_type": patent_data.get("publication_type", ""),
                "lang": patent_data.get("lang", ""),
                "extended_family_size": patent_data.get("extended_family_size", 0),
                "earliest_priority_date": patent_data.get("earliest_priority_date", ""),
                "anticipated_term_date": anticipated_term_date,
                "discontinuation_date": discontinuation_date,
                "has_terminal_disclaimer": patent_data.get("has_terminal_disclaimer", False),
                "ipcr_codes": patent_data.get("ipcr_codes", [])
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
        warnings = self._validate_relations(final_result)
        if warnings:
            print(f"⚠️  Validation warnings: {warnings}")

        return final_result

    def parse_and_save(self, patent_data: Dict[str, Any], out_path: str = "patent_parse_result.json") -> Dict[str, Any]:
        """Parse a patent and save results to JSON file."""
        result = self.parse_patent(patent_data)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to: {out_path}")
        return result

    def _format_patent_for_llm(self, patent: Dict[str, Any]) -> str:
        """Format patent data into readable text for LLM processing."""

        # Extract key fields
        title = patent.get("title", "")
        abstract = patent.get("abstract", "")
        assignee = patent.get("assignee", "Unknown")
        filing_date = patent.get("filing_date", "")
        publication_date = patent.get("publication_date", "")
        cpc_codes = patent.get("cpc_codes", [])
        citation_count = patent.get("citation_count", 0)

        # Format citations if available
        citations_info = ""
        if patent.get("detailed_citations"):
            citations_info = f"\n\nCited Patents: {len(patent['detailed_citations'])} references"

        # Format CPC codes
        cpc_info = ""
        if cpc_codes:
            cpc_info = f"\n\nCPC Classifications: {', '.join(cpc_codes[:5])}"  # First 5 codes

        formatted = f"""
PATENT ANALYSIS REQUEST

Title: {title}

Assignee/Company: {assignee}

Filing Date: {filing_date}
Publication Date: {publication_date}

Abstract:
{abstract}

Citation Count: {citation_count}{citations_info}{cpc_info}

TASK: Extract core technologies, innovations, and their relationships for knowledge graph construction.
""".strip()

        return formatted

    def _validate_relations(self, result: Dict[str, Any]) -> List[str]:
        """Validate that all relations use allowed types from config."""
        warnings = []

        for rel in result.get("company_tech_relations", []):
            if rel.get("relation_type") not in self.allowed_company_tech_relations:
                warnings.append(f"Invalid company_tech relation: {rel.get('relation_type')}")

        for rel in result.get("tech_tech_relations", []):
            if rel.get("relation_type") not in self.allowed_tech_tech_relations:
                warnings.append(f"Invalid tech_tech relation: {rel.get('relation_type')}")

        for rel in result.get("company_company_relations", []):
            if rel.get("relation_type") not in self.allowed_company_company_relations:
                warnings.append(f"Invalid company_company relation: {rel.get('relation_type')}")

        return warnings

    def _compute_legal_status(self, patent_type: str,
                              discontinuation_date: str = "",
                              anticipated_term_date: str = "") -> str:
        """
        Compute legal status from patent metadata.

        Args:
            patent_type: "application" or "granted"
            discontinuation_date: Discontinuation date if patent was abandoned
            anticipated_term_date: Expected expiry date

        Returns:
            Legal status: "pending" | "granted" | "expired" | "abandoned"
        """
        if patent_type == "granted":
            if discontinuation_date:
                return "abandoned"
            elif anticipated_term_date:
                try:
                    from datetime import datetime
                    term_date = datetime.fromisoformat(anticipated_term_date.replace('Z', '+00:00'))
                    if datetime.now() > term_date:
                        return "expired"
                except:
                    pass
            return "granted"
        return "pending"

    def _create_chain(self):
        """Build the few-shot chain for patent technology extraction."""

        # Few-shot example 1: eVTOL magnetic levitation system
        ex_input_1 = """
PATENT ANALYSIS REQUEST

Title: SYSTEMS AND METHODS FOR VERTICAL TAKEOFF AND LANDING VEHICLE WITH OPERATION MODE-BASED ROTOR BLADE CONTROL

Assignee/Company: Joby Aero, Inc.

Filing Date: 2024-03-29
Publication Date: 2025-05-30

Abstract:
Systems and methods relate to a vehicle, such as a vertical takeoff and landing (VTOL) platform, which can include a stator and a rotor magnetically levitated by the stator. The rotor and stator can be annular, such that the rotor rotates about a rotational axis. The stator can include magnets that provide guidance, levitation, and drive forces to drive the rotor, as well as to control operation of rotor blades of the rotor that can be independently rotated to specific pitch angles to control at least one of lift, pitch, roll, or yaw of the VTOL platform. Various controllers can be used to enable independent and redundant control of components of the VTOL platform. One or more processors can determine an adjusted target pitch angle for a rotor blade and cause the rotor blade to rotate to the adjusted target pitch angle.

Citation Count: 5

TASK: Extract core technologies, innovations, and their relationships for knowledge graph construction.
"""

        ex_output_1 = json.dumps({
            "quality_score": 0.98,
            "tech_mentions": [
                {
                    "name": "Magnetic Levitation Rotor System",
                    "role": "subject",
                    "strength": 0.95,
                    "evidence_confidence": 0.98,
                    "evidence_text": "Primary invention: Annular rotor magnetically levitated by stator for VTOL"
                },
                {
                    "name": "Magnetic Levitation Rotor System",
                    "role": "invented",
                    "strength": 0.90,
                    "evidence_confidence": 0.95,
                    "evidence_text": "Novel magnetic levitation system created by Joby for rotor propulsion"
                },
                {
                    "name": "Independent Rotor Blade Pitch Control",
                    "role": "invented",
                    "strength": 0.85,
                    "evidence_confidence": 0.95,
                    "evidence_text": "New control method for individual blade pitch angles"
                },
                {
                    "name": "Independent Rotor Blade Pitch Control",
                    "role": "implemented",
                    "strength": 0.80,
                    "evidence_confidence": 0.90,
                    "evidence_text": "Deployed pitch control for lift, pitch, roll, and yaw"
                },
                {
                    "name": "Redundant Control Architecture",
                    "role": "implemented",
                    "strength": 0.70,
                    "evidence_confidence": 0.90,
                    "evidence_text": "Multiple independent controllers for platform component control"
                }
            ],
            "company_mentions": [
                {
                    "name": "Joby Aero Inc",
                    "role": "owner",
                    "strength": 1.0,
                    "evidence_confidence": 1.0,
                    "evidence_text": "Assignee: Joby Aero, Inc."
                },
                {
                    "name": "Joby Aero Inc",
                    "role": "developer",
                    "strength": 0.98,
                    "evidence_confidence": 0.98,
                    "evidence_text": "Joby developed the magnetic levitation rotor system"
                }
            ],
            "company_tech_relations": [
                {
                    "company_name": "Joby Aero Inc",
                    "technology_name": "Magnetic Levitation Rotor System",
                    "relation_type": "owns_ip",
                    "evidence_confidence": 1.0,
                    "evidence_text": "Joby Aero filed patent for magnetic levitation rotor system"
                }
            ],
            "tech_tech_relations": [
                {
                    "from_tech_name": "Magnetic Levitation Rotor System",
                    "to_tech_name": "Independent Rotor Blade Pitch Control",
                    "relation_type": "enables",
                    "evidence_confidence": 0.95,
                    "evidence_text": "Magnetically levitated rotor allows independent blade pitch control without mechanical linkages"
                },
                {
                    "from_tech_name": "Independent Rotor Blade Pitch Control",
                    "to_tech_name": "Redundant Control Architecture",
                    "relation_type": "supports",
                    "evidence_confidence": 0.90,
                    "evidence_text": "Independent blade control enables redundant flight control architecture"
                }
            ],
            "company_company_relations": []
        }, indent=2)

        # Few-shot example 2: Battery technology
        ex_input_2 = """
PATENT ANALYSIS REQUEST

Title: HIGH-ENERGY DENSITY LITHIUM-SULFUR BATTERY SYSTEM FOR ELECTRIC AIRCRAFT

Assignee/Company: Beta Technologies

Filing Date: 2023-08-15
Publication Date: 2024-02-20

Abstract:
A battery system for electric vertical takeoff and landing aircraft comprises lithium-sulfur cells with enhanced energy density exceeding 400 Wh/kg. The system includes a thermal management subsystem that maintains cell temperature within optimal operating range during high-discharge flight operations. A battery management system monitors individual cell voltages and implements active balancing to extend cycle life. The architecture supports modular replacement of battery packs for rapid turnaround operations.

Citation Count: 12

CPC Classifications: H01M10/052, B64D27/24, H01M10/613

TASK: Extract core technologies, innovations, and their relationships for knowledge graph construction.
"""

        ex_output_2 = json.dumps({
            "quality_score": 0.92,
            "tech_mentions": [
                {
                    "name": "400+ Wh/kg Lithium-Sulfur Battery",
                    "role": "subject",
                    "strength": 0.95,
                    "evidence_confidence": 0.98,
                    "evidence_text": "Primary invention: High energy density Li-S cells for aviation"
                },
                {
                    "name": "400+ Wh/kg Lithium-Sulfur Battery",
                    "role": "invented",
                    "strength": 0.92,
                    "evidence_confidence": 0.96,
                    "evidence_text": "Novel Li-S chemistry exceeding 400 Wh/kg created by Beta"
                },
                {
                    "name": "Aviation Battery Thermal Management",
                    "role": "invented",
                    "strength": 0.80,
                    "evidence_confidence": 0.95,
                    "evidence_text": "New thermal management system designed for high-discharge operations"
                },
                {
                    "name": "Aviation Battery Thermal Management",
                    "role": "implemented",
                    "strength": 0.75,
                    "evidence_confidence": 0.90,
                    "evidence_text": "Active cooling/heating system deployed for flight operations"
                },
                {
                    "name": "Active Cell Balancing BMS",
                    "role": "implemented",
                    "strength": 0.70,
                    "evidence_confidence": 0.90,
                    "evidence_text": "Battery management with individual cell monitoring and balancing"
                },
                {
                    "name": "Modular Battery Pack Architecture",
                    "role": "invented",
                    "strength": 0.65,
                    "evidence_confidence": 0.85,
                    "evidence_text": "Quick-swap battery packs for rapid aircraft turnaround"
                }
            ],
            "company_mentions": [
                {
                    "name": "Beta Technologies",
                    "role": "owner",
                    "strength": 1.0,
                    "evidence_confidence": 1.0,
                    "evidence_text": "Assignee: Beta Technologies"
                },
                {
                    "name": "Beta Technologies",
                    "role": "developer",
                    "strength": 0.98,
                    "evidence_confidence": 0.98,
                    "evidence_text": "Beta developed the high-energy Li-S battery system"
                }
            ],
            "company_tech_relations": [
                {
                    "company_name": "Beta Technologies",
                    "technology_name": "400+ Wh/kg Lithium-Sulfur Battery",
                    "relation_type": "owns_ip",
                    "evidence_confidence": 1.0,
                    "evidence_text": "Beta Technologies filed patent for Li-S battery system"
                }
            ],
            "tech_tech_relations": [
                {
                    "from_tech_name": "400+ Wh/kg Lithium-Sulfur Battery",
                    "to_tech_name": "Aviation Battery Thermal Management",
                    "relation_type": "requires",
                    "evidence_confidence": 0.95,
                    "evidence_text": "Li-S chemistry sensitive to temperature, requires active thermal management for aviation safety"
                },
                {
                    "from_tech_name": "Active Cell Balancing BMS",
                    "to_tech_name": "400+ Wh/kg Lithium-Sulfur Battery",
                    "relation_type": "extends_life_of",
                    "evidence_confidence": 0.90,
                    "evidence_text": "Active balancing extends cycle life of Li-S cells"
                }
            ],
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

        # System prompt with universal role taxonomy and config-driven relations
        # Escape curly braces in JSON for LangChain template
        relation_defs_json = json.dumps(self.graph_config['relation_definitions'], indent=2)
        relation_defs_escaped = relation_defs_json.replace('{', '{{').replace('}', '}}')

        system_prompt = f"""
You are a patent technology analyst extracting entities and relationships for strategic intelligence.

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
- "subject": Primary topic of document
- "invented": Created/designed/originated
- "regulated": Subject to government oversight
- "commercialized": Sold/promoted/monetized
- "studied": Researched/tested/validated
- "implemented": Built/coded/deployed
- "procured": Purchased/contracted

COMPANY ROLES (ONE role per mention - create separate mentions for same entity with different roles):
- "owner": Holds IP rights (assignee in patents)
- "developer": Builds/invents technology
- "operator": Uses technology commercially
- "contractor": Receives government funding
- "issuer": Reports to SEC
- "competitor": Market player
- "sponsor": Funds R&D
- "investment_target": Held by investors
- "employer": Recruits talent

STRENGTH SCORING (0.0-1.0) - Importance of THIS ROLE to Document:
- 1.0: Core focus (explicitly central to document for this role)
- 0.7-0.9: Key supporting element (critical but not primary for this role)
- 0.4-0.6: Supporting element (mentioned 2-3 times for this role)
- 0.1-0.3: Background/peripheral (mentioned once for this role)

CONFIDENCE SCORING (0.0-1.0) - Certainty of THIS ROLE Assignment:
- 0.95-1.0: Explicit statement, exact terminology for this role
- 0.8-0.94: Strong inference from technical description for this role
- 0.6-0.79: Moderate inference from context for this role
- 0.5-0.59: Weak inference for this role

QUALITY SCORE (0.0-1.0) - Industry Relevance Assessment:
PURPOSE: Determine if this patent is actually relevant to the target industry.
Some patents may mention keywords but not be truly related to the industry.
Documents with quality_score < 0.85 will be FILTERED OUT in post-processing.

Scoring Guidelines:
- 0.95-1.0: Core industry technology (direct application to target industry)
- 0.85-0.94: Supporting technology (enables or complements industry)
- 0.70-0.84: Tangentially related (shares components or methods)
- 0.50-0.69: Keyword match only (not actually related to industry)
- 0.0-0.49: Not related to industry (false positive from search)

Example for eVTOL industry:
- 1.0: "Electric VTOL propulsion system" (core eVTOL technology)
- 0.90: "Lithium-sulfur battery for aviation" (supporting technology)
- 0.75: "Carbon fiber rotor blade manufacturing" (tangential)
- 0.60: "General electric motor control" (keyword match only)
- 0.30: "Automotive battery management" (not eVTOL related)

CRITICAL: Be strict in scoring to maintain data quality for strategic intelligence.

OUTPUT SCHEMA:
{{{{
  "quality_score": float,  // 0.0-1.0 industry relevance (0.85+ = relevant, <0.85 = discard)
  "tech_mentions": [
    {{{{
      "name": string,
      "role": string,  // SINGLE role (not array) - create multiple entries for same tech with different roles
      "strength": float,  // Strength of THIS specific role
      "evidence_confidence": float,  // Confidence in THIS specific role
      "evidence_text": string (max 200 chars, evidence for THIS role)
    }}}}
  ],
  "company_mentions": [
    {{{{
      "name": string,
      "role": string,  // SINGLE role (not array)
      "strength": float,  // Strength of THIS specific role
      "evidence_confidence": float,  // Confidence in THIS specific role
      "evidence_text": string (max 200 chars, evidence for THIS role)
    }}}}
  ],
  "company_tech_relations": [
    {{{{
      "company_name": string,
      "technology_name": string,
      "relation_type": string,  // Must be from allowed_company_tech_relations
      "evidence_confidence": float,
      "evidence_text": string (max 200 chars)
    }}}}
  ],
  "tech_tech_relations": [
    {{{{
      "from_tech_name": string,
      "to_tech_name": string,
      "relation_type": string,  // Must be from allowed_tech_tech_relations
      "evidence_confidence": float,
      "evidence_text": string (max 200 chars)
    }}}}
  ],
  "company_company_relations": [
    {{{{
      "from_company_name": string,
      "to_company_name": string,
      "relation_type": string,  // Must be from allowed_company_company_relations
      "evidence_confidence": float,
      "evidence_text": string (max 200 chars)
    }}}}
  ]
}}}}

CRITICAL RULES:
- Output ONLY valid JSON (no markdown, no commentary)
- Each mention has ONE role only (not an array)
- If an entity has multiple roles, create SEPARATE mention entries with different strength/confidence for each role
- Example: "eVTOL" as subject (strength=0.95) AND as invented (strength=0.90) = 2 separate entries
- Use ONLY allowed relation types from config lists above
- Evidence text must be < 200 chars and specific to THAT role
- Extract 5-10 technology mentions total (including multiple roles for same tech)
- Extract 2-5 company mentions total (including multiple roles for same company)
- All relation_type values must match config enums exactly

"""

        final_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            few_shot,
            ("human", "{input}")
        ])

        return final_prompt | self.llm | self.output_parser


def load_patents_from_file(file_path: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Load patent data from JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        patents = json.load(f)

    if limit:
        patents = patents[:limit]

    return patents


def parse_single_patent_test():
    """Test function: Parse a single patent for validation."""

    # Load API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    # Initialize parser
    parser = PatentTechnologyParser(
        openai_api_key=api_key,
        model_name="gpt-4o-mini",
        temperature=0.0
    )

    # Load patents
    patents_file = "data/eVTOL/lens_patents/patents.json"
    patents = load_patents_from_file(patents_file, limit=1)

    if not patents:
        print("No patents found in file")
        return

    # Parse first patent
    print(f"\n{'='*80}")
    print("TESTING PATENT PARSER - SINGLE PATENT")
    print(f"{'='*80}\n")

    patent = patents[0]
    print(f"Patent: {patent.get('title', 'No title')}")
    print(f"Assignee: {patent.get('assignee', 'Unknown')}")
    print(f"Filing Date: {patent.get('filing_date', 'Unknown')}\n")

    # Parse and save
    result = parser.parse_and_save(
        patent_data=patent,
        out_path="parsers/test_patent_output.json"
    )

    # Display summary
    print(f"\n{'='*80}")
    print("PARSING RESULTS SUMMARY")
    print(f"{'='*80}\n")

    # Document quality
    doc = result.get('document', {})
    print(f"Quality Score: {doc.get('quality_score', 0.0):.2f}")
    print(f"Legal Status: {doc.get('legal_status', 'N/A')}")
    print(f"Jurisdiction: {doc.get('jurisdiction', 'N/A')}")
    print(f"Simple Family Size: {doc.get('simple_family_size', 0)}")
    print()

    # Entity and relation counts
    print(f"Technology Mentions: {len(result.get('tech_mentions', []))}")
    print(f"Company Mentions: {len(result.get('company_mentions', []))}")
    print(f"Company-Tech Relations: {len(result.get('company_tech_relations', []))}")
    print(f"Tech-Tech Relations: {len(result.get('tech_tech_relations', []))}")
    print(f"Company-Company Relations: {len(result.get('company_company_relations', []))}")

    # Show sample tech mentions
    if result.get('tech_mentions'):
        print("\nSample Technology Mentions:")
        for mention in result['tech_mentions'][:3]:
            role = mention.get('role', 'N/A')
            print(f"  - {mention.get('name')} (role: {role}, strength: {mention.get('strength', 0):.2f})")

    # Show sample company mentions
    if result.get('company_mentions'):
        print("\nSample Company Mentions:")
        for mention in result['company_mentions'][:2]:
            role = mention.get('role', 'N/A')
            print(f"  - {mention.get('name')} (role: {role})")

    # Show sample relations
    if result.get('tech_tech_relations'):
        print("\nSample Tech-Tech Relations:")
        for rel in result['tech_tech_relations'][:3]:
            print(f"  - {rel.get('from_tech_name')} --[{rel.get('relation_type')}]--> {rel.get('to_tech_name')}")

    print(f"\n{'='*80}\n")

    return result


def parse_all_patents(industry: str = "eVTOL", limit: Optional[int] = None):
    """
    Parse all patents for an industry.

    Args:
        industry: Industry name (matches config folder structure)
        limit: Maximum number of patents to parse (None = all)

    NOTE: This function should only be run when explicitly requested by user.
    Use parse_single_patent_test() first to validate the parser.
    """

    # Load API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    # Initialize parser
    parser = PatentTechnologyParser(
        openai_api_key=api_key,
        model_name="gpt-4o-mini",
        temperature=0.0
    )

    # Load patents
    patents_file = f"data/{industry}/lens_patents/patents.json"
    patents = load_patents_from_file(patents_file, limit=limit)

    print(f"\n{'='*80}")
    print(f"PARSING ALL PATENTS - {industry.upper()}")
    print(f"{'='*80}")
    print(f"Total patents to parse: {len(patents)}\n")

    # Create output directory
    output_dir = f"parsers/output/{industry}_patents"
    os.makedirs(output_dir, exist_ok=True)

    results = []
    failed = []

    for idx, patent in enumerate(patents, 1):
        patent_id = patent.get("lens_id", f"unknown_{idx}")
        print(f"\n[{idx}/{len(patents)}] Processing: {patent_id}")
        print(f"  Title: {patent.get('title', 'No title')[:80]}...")

        try:
            result = parser.parse_patent(patent)

            # Save individual result
            output_file = f"{output_dir}/patent_{patent_id}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            results.append(result)
            print(f"  ✓ Parsed successfully")

        except Exception as e:
            print(f"  ✗ Failed: {e}")
            failed.append({"lens_id": patent_id, "error": str(e)})

    # Save consolidated results
    consolidated_file = f"{output_dir}/_all_patents_parsed.json"
    with open(consolidated_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Save failure log
    if failed:
        failure_file = f"{output_dir}/_parsing_failures.json"
        with open(failure_file, "w", encoding="utf-8") as f:
            json.dump(failed, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*80}")
    print("PARSING COMPLETE")
    print(f"{'='*80}")
    print(f"Successfully parsed: {len(results)}/{len(patents)}")
    print(f"Failed: {len(failed)}/{len(patents)}")
    print(f"\nOutput directory: {output_dir}/")
    print(f"Consolidated results: {consolidated_file}")

    return results


if __name__ == "__main__":
    # Only run single patent test when executed directly
    parse_single_patent_test()