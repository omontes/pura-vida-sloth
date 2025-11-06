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

    def __init__(self, openai_api_key: str, model_name: str = "gpt-4o-mini", temperature: float = 0.0):
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
        Parse a single patent into technology nodes and relationships.

        Args:
            patent_data: Patent record from Lens.org API

        Returns:
            Dictionary containing:
            - patent_metadata: Basic patent information
            - technology_nodes: List of technologies/innovations identified
            - relationships: List of triplets (subject, predicate, object)
            - innovation_signals: Classification for lifecycle analysis
        """
        input_text = self._format_patent_for_llm(patent_data)

        try:
            with get_openai_callback() as cb:
                result = self.chain.invoke({"input": input_text})

                # Log token usage and cost
                print(f"\nToken Usage:")
                print(f"  Prompt tokens: {cb.prompt_tokens}")
                print(f"  Completion tokens: {cb.completion_tokens}")
                print(f"  Total tokens: {cb.total_tokens}")

                # Calculate cost (gpt-4o-mini pricing)
                cost_per_1m_input = 0.150
                cost_per_1m_output = 0.600

                cost_per_input_token = cost_per_1m_input / 1_000_000
                cost_per_output_token = cost_per_1m_output / 1_000_000

                input_cost = cb.prompt_tokens * cost_per_input_token
                output_cost = cb.completion_tokens * cost_per_output_token
                total_cost = input_cost + output_cost
                print(f"  Cost (USD): ${total_cost:.6f}")

        except Exception as e:
            print(f"Parsing error: {e}")
            result = self._empty_result()

        # Enrich with original patent data
        result["patent_metadata"]["lens_id"] = patent_data.get("lens_id", "")
        result["patent_metadata"]["patent_number"] = patent_data.get("patent_number", "")
        result["patent_metadata"]["url"] = patent_data.get("url", "")

        return result

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

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure on parsing failure."""
        return {
            "patent_metadata": {
                "lens_id": "",
                "patent_number": "",
                "title": "",
                "assignee": "",
                "filing_date": "",
                "url": ""
            },
            "technology_nodes": [],
            "relationships": [],
            "innovation_signals": {
                "maturity_level": "unknown",
                "innovation_type": "unknown",
                "competitive_positioning": "unknown"
            }
        }

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
            "patent_metadata": {
                "title": "SYSTEMS AND METHODS FOR VERTICAL TAKEOFF AND LANDING VEHICLE WITH OPERATION MODE-BASED ROTOR BLADE CONTROL",
                "assignee": "Joby Aero, Inc.",
                "filing_date": "2024-03-29"
            },
            "technology_nodes": [
                {
                    "node_id": "tech_magnetic_levitation_rotor",
                    "node_type": "technology",
                    "name": "Magnetic Levitation Rotor System",
                    "description": "Annular rotor magnetically levitated by stator for VTOL propulsion",
                    "maturity": "emerging",
                    "domain": "propulsion"
                },
                {
                    "node_id": "tech_independent_blade_control",
                    "node_type": "technology",
                    "name": "Independent Rotor Blade Pitch Control",
                    "description": "Individual blade pitch angle control for lift, pitch, roll, and yaw",
                    "maturity": "advanced",
                    "domain": "flight_control"
                },
                {
                    "node_id": "tech_redundant_control_systems",
                    "node_type": "technology",
                    "name": "Redundant Control Architecture",
                    "description": "Multiple independent controllers for platform component control",
                    "maturity": "mature",
                    "domain": "safety_systems"
                },
                {
                    "node_id": "company_joby",
                    "node_type": "organization",
                    "name": "Joby Aero, Inc.",
                    "description": "eVTOL aircraft manufacturer",
                    "role": "innovator"
                }
            ],
            "relationships": [
                {
                    "subject": "tech_magnetic_levitation_rotor",
                    "predicate": "enables",
                    "object": "tech_independent_blade_control",
                    "confidence": 0.95,
                    "evidence": "Magnetically levitated rotor allows independent blade pitch control without mechanical linkages"
                },
                {
                    "subject": "tech_independent_blade_control",
                    "predicate": "supports",
                    "object": "tech_redundant_control_systems",
                    "confidence": 0.90,
                    "evidence": "Independent blade control enables redundant flight control architecture"
                },
                {
                    "subject": "company_joby",
                    "predicate": "develops",
                    "object": "tech_magnetic_levitation_rotor",
                    "confidence": 1.0,
                    "evidence": "Joby Aero filed patent for magnetic levitation rotor system"
                },
                {
                    "subject": "tech_magnetic_levitation_rotor",
                    "predicate": "advances_beyond",
                    "object": "conventional_mechanical_rotor",
                    "confidence": 0.85,
                    "evidence": "Eliminates mechanical complexity of traditional rotor systems"
                }
            ],
            "innovation_signals": {
                "maturity_level": "early_commercial",
                "innovation_type": "breakthrough",
                "competitive_positioning": "differentiated",
                "technical_risk": "medium",
                "adoption_indicators": [
                    "Joby has multiple patents in magnetic levitation",
                    "Recent filing date suggests active development",
                    "5 citations indicate building on existing work"
                ]
            }
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
            "patent_metadata": {
                "title": "HIGH-ENERGY DENSITY LITHIUM-SULFUR BATTERY SYSTEM FOR ELECTRIC AIRCRAFT",
                "assignee": "Beta Technologies",
                "filing_date": "2023-08-15"
            },
            "technology_nodes": [
                {
                    "node_id": "tech_lithium_sulfur_400wh",
                    "node_type": "technology",
                    "name": "400+ Wh/kg Lithium-Sulfur Battery",
                    "description": "High energy density Li-S cells for aviation applications",
                    "maturity": "emerging",
                    "domain": "energy_storage"
                },
                {
                    "node_id": "tech_thermal_mgmt_aviation",
                    "node_type": "technology",
                    "name": "Aviation Battery Thermal Management",
                    "description": "Active cooling/heating system for high-discharge flight operations",
                    "maturity": "advanced",
                    "domain": "thermal_systems"
                },
                {
                    "node_id": "tech_active_cell_balancing",
                    "node_type": "technology",
                    "name": "Active Cell Balancing BMS",
                    "description": "Battery management with individual cell monitoring and balancing",
                    "maturity": "mature",
                    "domain": "power_electronics"
                },
                {
                    "node_id": "tech_modular_battery_swap",
                    "node_type": "technology",
                    "name": "Modular Battery Pack Architecture",
                    "description": "Quick-swap battery packs for rapid aircraft turnaround",
                    "maturity": "proven",
                    "domain": "operations"
                },
                {
                    "node_id": "company_beta",
                    "node_type": "organization",
                    "name": "Beta Technologies",
                    "description": "eVTOL developer focused on cargo and passenger transport",
                    "role": "innovator"
                }
            ],
            "relationships": [
                {
                    "subject": "tech_lithium_sulfur_400wh",
                    "predicate": "requires",
                    "object": "tech_thermal_mgmt_aviation",
                    "confidence": 0.95,
                    "evidence": "Li-S chemistry sensitive to temperature, requires active thermal management for aviation safety"
                },
                {
                    "subject": "tech_active_cell_balancing",
                    "predicate": "extends_life_of",
                    "object": "tech_lithium_sulfur_400wh",
                    "confidence": 0.90,
                    "evidence": "Active balancing extends cycle life of Li-S cells per patent abstract"
                },
                {
                    "subject": "tech_modular_battery_swap",
                    "predicate": "enables",
                    "object": "rapid_operations",
                    "confidence": 0.85,
                    "evidence": "Modular architecture supports quick turnaround for commercial operations"
                },
                {
                    "subject": "company_beta",
                    "predicate": "develops",
                    "object": "tech_lithium_sulfur_400wh",
                    "confidence": 1.0,
                    "evidence": "Beta Technologies filed patent for Li-S battery system"
                },
                {
                    "subject": "tech_lithium_sulfur_400wh",
                    "predicate": "competes_with",
                    "object": "lithium_ion_aviation_battery",
                    "confidence": 0.80,
                    "evidence": "Li-S offers higher energy density than conventional Li-ion (typically 250-300 Wh/kg)"
                }
            ],
            "innovation_signals": {
                "maturity_level": "development",
                "innovation_type": "incremental_breakthrough",
                "competitive_positioning": "critical_enabler",
                "technical_risk": "high",
                "adoption_indicators": [
                    "12 citations suggest building on established research",
                    "400+ Wh/kg exceeds current commercial aviation batteries",
                    "Thermal management indicates addressing known Li-S challenges",
                    "Modular design shows focus on commercial operations"
                ]
            }
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

        # System prompt with schema definition
        system_prompt = """
You are a patent technology analyst specializing in extracting innovation signals for strategic intelligence.

Your task is to analyze patent data and extract:

1. TECHNOLOGY NODES: Core technologies, innovations, and organizations
2. RELATIONSHIPS: How technologies relate to each other (triplets for knowledge graph)
3. INNOVATION SIGNALS: Maturity assessment for lifecycle analysis

OUTPUT SCHEMA:

{{
  "patent_metadata": {{
    "title": string,
    "assignee": string,
    "filing_date": "YYYY-MM-DD"
  }},
  "technology_nodes": [
    {{
      "node_id": string,              // Unique ID (use snake_case: tech_*, company_*, concept_*)
      "node_type": "technology" | "organization" | "concept",
      "name": string,                 // Human-readable name
      "description": string,          // Brief technical description
      "maturity": "emerging" | "advanced" | "mature" | "proven",
      "domain": string                // Technical domain (propulsion, energy_storage, flight_control, etc.)
    }}
  ],
  "relationships": [
    {{
      "subject": string,              // node_id of subject
      "predicate": string,            // Relationship type (see below)
      "object": string,               // node_id of object (can reference external concepts)
      "confidence": float,            // 0.0-1.0
      "evidence": string              // Why this relationship exists
    }}
  ],
  "innovation_signals": {{
    "maturity_level": "research" | "development" | "early_commercial" | "commercial" | "mature",
    "innovation_type": "breakthrough" | "incremental_breakthrough" | "incremental" | "sustaining",
    "competitive_positioning": "first_mover" | "differentiated" | "critical_enabler" | "me_too",
    "technical_risk": "low" | "medium" | "high" | "very_high",
    "adoption_indicators": [string]   // Evidence of technology readiness/adoption
  }}
}}

RELATIONSHIP PREDICATES (use these):
- "enables": Technology A makes technology B possible
- "requires": Technology A needs technology B to function
- "supports": Technology A helps technology B work better
- "advances_beyond": Technology A improves over technology B
- "competes_with": Technology A is alternative to technology B
- "contradicts": Technology A challenges assumptions of technology B
- "develops": Organization develops technology
- "extends_life_of": Technology A improves durability/lifetime of B
- "builds_on": Technology A is based on prior work in technology B

EXTRACTION GUIDELINES:

1. IDENTIFY CORE TECHNOLOGIES:
   - Extract 3-6 key technologies from title + abstract
   - Focus on novel contributions, not generic concepts
   - Include the assignee organization as a node
   - Use descriptive names that capture technical essence

2. NODE_ID NAMING:
   - Use snake_case prefixes: tech_*, company_*, concept_*
   - Be specific: "tech_magnetic_levitation_rotor" not "tech_rotor"
   - Keep concise but descriptive

3. MATURITY ASSESSMENT:
   - "emerging": Novel approach, early research stage
   - "advanced": Proven concept, needs engineering refinement
   - "mature": Well-understood, widely implemented in other domains
   - "proven": Commercial deployment in target industry

4. RELATIONSHIPS:
   - Create 4-8 triplets per patent
   - Include at least one "develops" relationship (company → technology)
   - Look for enabling relationships (what makes what possible?)
   - Identify competitive/contradictory relationships where clear
   - confidence = 1.0 for explicit facts, 0.7-0.95 for inferences
   - evidence must cite specific patent content

5. INNOVATION SIGNALS:
   - maturity_level: Where is this in commercialization pipeline?
   - innovation_type: How novel? (breakthrough = new paradigm, incremental = refinement)
   - competitive_positioning: Strategic value (first_mover, differentiated, critical_enabler, me_too)
   - technical_risk: How hard to implement? (consider physics, safety, certification)
   - adoption_indicators: List 3-5 concrete signals (citation count, filing dates, technical details)

6. DOMAIN CATEGORIES (use these):
   - propulsion, energy_storage, flight_control, avionics, materials, manufacturing,
   - thermal_systems, power_electronics, safety_systems, operations, software, sensors

CRITICAL RULES:
- Output ONLY valid JSON (no markdown, no commentary)
- All node_ids must be unique within the patent
- All relationship subject/object must reference valid node_ids OR external concepts
- Confidence scores must be realistic (0.7-1.0 range typical)
- Evidence must be specific, not generic
- Focus on INNOVATION, not generic engineering

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
    print(f"Technology Nodes Extracted: {len(result.get('technology_nodes', []))}")
    print(f"Relationships Identified: {len(result.get('relationships', []))}")
    print(f"Innovation Maturity: {result.get('innovation_signals', {}).get('maturity_level', 'unknown')}")
    print(f"Innovation Type: {result.get('innovation_signals', {}).get('innovation_type', 'unknown')}")

    # Show sample nodes
    if result.get('technology_nodes'):
        print("\nSample Technology Nodes:")
        for node in result['technology_nodes'][:3]:
            print(f"  - {node.get('name')} ({node.get('node_type')})")

    # Show sample relationships
    if result.get('relationships'):
        print("\nSample Relationships:")
        for rel in result['relationships'][:3]:
            print(f"  - {rel.get('subject')} --[{rel.get('predicate')}]--> {rel.get('object')}")

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