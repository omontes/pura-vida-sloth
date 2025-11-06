"""
Scholarly Papers Relevance & Knowledge Graph Parser
Author: Pura Vida Sloth Intelligence System

Analyzes research papers to:
- Assess relevance to target industry (0-10 scale, threshold: 8.0)
- Extract technology nodes and relationships for relevant papers
- Generate innovation signals for lifecycle assessment

Output: Industry-filtered papers with Neo4j-compatible knowledge graph triplets
"""

import os
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.callbacks import get_openai_callback


class ScholarlyRelevanceParser:
    """LLM-driven parser to assess paper relevance and extract knowledge graphs."""

    def __init__(
        self,
        openai_api_key: str,
        industry_name: str,
        industry_keywords: List[str],
        industry_description: str,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.0,
        relevance_threshold: float = 8.0
    ):
        """
        Initialize parser with industry-specific context.

        Args:
            openai_api_key: OpenAI API key
            industry_name: Target industry (e.g., "eVTOL", "Quantum Computing")
            industry_keywords: Core industry keywords for context
            industry_description: Brief description of the industry
            model_name: OpenAI model to use (default: gpt-4o-mini)
            temperature: Model temperature (0.0 = deterministic)
            relevance_threshold: Score threshold for relevance (default: 8.0/10)
        """
        self.industry_name = industry_name
        self.industry_keywords = industry_keywords
        self.industry_description = industry_description
        self.relevance_threshold = relevance_threshold

        self.llm = ChatOpenAI(
            temperature=temperature,
            model=model_name,
            api_key=openai_api_key,
            timeout=300.0
        )
        self.output_parser = JsonOutputParser()
        self.chain = self._create_chain()

    def parse_paper(self, paper_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a single paper: assess relevance + extract knowledge graph.

        Args:
            paper_data: Paper record from Lens.org API

        Returns:
            Dictionary containing:
            - paper_metadata: Basic paper information
            - relevance_assessment: Score, category, justification
            - technology_nodes: List of technologies (if relevant)
            - relationships: List of triplets (if relevant)
            - innovation_signals: Research impact classification (if relevant)
        """
        input_text = self._format_paper_for_llm(paper_data)

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

        # Enrich with original paper data
        result["paper_metadata"]["lens_id"] = paper_data.get("lens_id", "")
        result["paper_metadata"]["url"] = paper_data.get("url", "")
        result["paper_metadata"]["doi"] = self._extract_doi(paper_data)

        return result

    def parse_and_save(self, paper_data: Dict[str, Any], out_path: str = "paper_parse_result.json") -> Dict[str, Any]:
        """Parse a paper and save results to JSON file."""
        result = self.parse_paper(paper_data)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to: {out_path}")
        return result

    def _format_paper_for_llm(self, paper: Dict[str, Any]) -> str:
        """Format paper data into readable text for LLM processing."""

        # Extract key fields
        title = paper.get("title", "")
        abstract = self._clean_abstract(paper.get("abstract", ""))
        year = paper.get("year_published", "")
        publication_type = paper.get("publication_type", "")

        # Citation counts
        scholarly_citations = paper.get("scholarly_citations_count", 0)
        patent_citations = paper.get("patent_citations_count", 0)
        references_count = paper.get("references_count", 0)

        # Fields of study and keywords
        fields_of_study = paper.get("fields_of_study", [])
        keywords = paper.get("keywords", [])

        # Source info
        source = paper.get("source", {})
        journal = source.get("title", "Unknown")
        publisher = source.get("publisher", "Unknown")

        # Format fields of study
        fields_info = ""
        if fields_of_study:
            fields_info = f"\n\nFields of Study: {', '.join(fields_of_study[:10])}"

        # Format keywords
        keywords_info = ""
        if keywords:
            keywords_info = f"\n\nKeywords: {', '.join(keywords[:10])}"

        # Handle missing abstract
        abstract_section = f"\n\nAbstract:\n{abstract}" if abstract else "\n\n[No abstract available]"

        formatted = f"""
RESEARCH PAPER ANALYSIS REQUEST

Industry Context: {self.industry_name}
Industry Description: {self.industry_description}

Title: {title}

Year: {year}
Publication Type: {publication_type}
Journal/Conference: {journal}
Publisher: {publisher}

{abstract_section}

Citation Metrics:
- Scholarly Citations: {scholarly_citations}
- Patent Citations: {patent_citations}
- References: {references_count}{fields_info}{keywords_info}

TASK:
1. Assess relevance to {self.industry_name} industry (0-10 scale, threshold: {self.relevance_threshold})
2. If relevant (>= {self.relevance_threshold}): Extract core technologies, innovations, and relationships for knowledge graph
""".strip()

        return formatted

    def _clean_abstract(self, abstract: str) -> str:
        """Remove HTML/XML tags and clean abstract text."""
        if not abstract:
            return ""

        # Remove JATS XML tags
        cleaned = re.sub(r'<jats:[^>]+>', '', abstract)
        cleaned = re.sub(r'</jats:[^>]+>', '', cleaned)

        # Remove other HTML tags
        cleaned = re.sub(r'<[^>]+>', '', cleaned)

        # Clean up whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip()

        return cleaned

    def _extract_doi(self, paper: Dict[str, Any]) -> str:
        """Extract DOI from external_ids."""
        external_ids = paper.get("external_ids", [])
        for ext_id in external_ids:
            if ext_id.get("type") == "doi":
                return ext_id.get("value", "")
        return ""

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure on parsing failure."""
        return {
            "paper_metadata": {
                "lens_id": "",
                "title": "",
                "year_published": "",
                "publication_type": "",
                "doi": "",
                "url": ""
            },
            "relevance_assessment": {
                "relevance_score": 0.0,
                "is_relevant": False,
                "relevance_category": "unknown",
                "justification": "Parsing error",
                "confidence": 0.0
            },
            "technology_nodes": [],
            "relationships": [],
            "innovation_signals": {
                "research_stage": "unknown",
                "innovation_type": "unknown",
                "impact_potential": "unknown"
            }
        }

    def _create_chain(self):
        """Build the few-shot chain for paper relevance & technology extraction."""

        # Few-shot example 1: Highly relevant eVTOL paper (direct application)
        ex_input_1 = f"""
RESEARCH PAPER ANALYSIS REQUEST

Industry Context: eVTOL
Industry Description: Electric Vertical Takeoff and Landing aircraft for urban air mobility

Title: Aerodynamic Optimization of eVTOL Tilt-Rotor Configuration for Hover and Cruise Efficiency

Year: 2024
Publication Type: journal article
Journal/Conference: Journal of Aircraft
Publisher: American Institute of Aeronautics and Astronautics

Abstract:
This paper presents a comprehensive aerodynamic optimization framework for electric vertical takeoff and landing (eVTOL) aircraft with tilt-rotor configurations. We investigate the trade-offs between hover efficiency and cruise performance through computational fluid dynamics simulations validated against wind tunnel experiments. The study introduces a novel rotor blade design that achieves 12% improvement in hover efficiency while maintaining cruise lift-to-drag ratio. Flight control strategies for transition phase are analyzed using dynamic flight simulations. Results demonstrate that optimized tilt-rotor configurations can extend eVTOL range by 18% compared to conventional designs.

Citation Metrics:
- Scholarly Citations: 15
- Patent Citations: 3
- References: 42

Fields of Study: Aerodynamics, Aircraft design, Electric aircraft, Vertical flight, Computational fluid dynamics

Keywords: eVTOL, tilt-rotor, aerodynamic optimization, hover efficiency, urban air mobility

TASK:
1. Assess relevance to eVTOL industry (0-10 scale, threshold: 8.0)
2. If relevant (>= 8.0): Extract core technologies, innovations, and relationships for knowledge graph
"""

        ex_output_1 = json.dumps({
            "paper_metadata": {
                "title": "Aerodynamic Optimization of eVTOL Tilt-Rotor Configuration for Hover and Cruise Efficiency",
                "year_published": 2024,
                "publication_type": "journal article",
                "journal": "Journal of Aircraft"
            },
            "relevance_assessment": {
                "relevance_score": 9.5,
                "is_relevant": True,
                "relevance_category": "direct_application",
                "justification": "Paper directly addresses core eVTOL design challenges (aerodynamic optimization, tilt-rotor configuration, hover-cruise efficiency trade-offs) with quantified performance improvements (12% hover efficiency, 18% range extension). Highly relevant for eVTOL aircraft development.",
                "confidence": 0.98
            },
            "technology_nodes": [
                {
                    "node_id": "tech_tilt_rotor_optimization",
                    "node_type": "technology",
                    "name": "eVTOL Tilt-Rotor Aerodynamic Optimization",
                    "description": "Optimization framework balancing hover efficiency and cruise performance for tilt-rotor eVTOL",
                    "maturity": "advanced",
                    "domain": "aerodynamics"
                },
                {
                    "node_id": "tech_novel_rotor_blade",
                    "node_type": "technology",
                    "name": "Hybrid Hover-Cruise Rotor Blade Design",
                    "description": "Novel blade geometry achieving 12% hover efficiency improvement while maintaining cruise performance",
                    "maturity": "emerging",
                    "domain": "propulsion"
                },
                {
                    "node_id": "tech_transition_flight_control",
                    "node_type": "technology",
                    "name": "Tilt-Rotor Transition Flight Control",
                    "description": "Flight control strategies for hover-cruise transition phase optimization",
                    "maturity": "advanced",
                    "domain": "flight_control"
                },
                {
                    "node_id": "tech_cfd_validation",
                    "node_type": "technology",
                    "name": "CFD-Wind Tunnel Validation Framework",
                    "description": "Computational fluid dynamics simulations validated against experimental data",
                    "maturity": "mature",
                    "domain": "simulation"
                }
            ],
            "relationships": [
                {
                    "subject": "tech_tilt_rotor_optimization",
                    "predicate": "enables",
                    "object": "tech_novel_rotor_blade",
                    "confidence": 0.95,
                    "evidence": "Optimization framework enabled development of novel blade design with quantified performance gains"
                },
                {
                    "subject": "tech_novel_rotor_blade",
                    "predicate": "improves_performance_of",
                    "object": "evtol_aircraft",
                    "confidence": 0.95,
                    "evidence": "Blade design extends eVTOL range by 18% through improved aerodynamic efficiency"
                },
                {
                    "subject": "tech_transition_flight_control",
                    "predicate": "requires",
                    "object": "tech_tilt_rotor_optimization",
                    "confidence": 0.90,
                    "evidence": "Flight control strategies depend on optimized tilt-rotor aerodynamic characteristics"
                },
                {
                    "subject": "tech_cfd_validation",
                    "predicate": "validates",
                    "object": "tech_tilt_rotor_optimization",
                    "confidence": 0.95,
                    "evidence": "CFD simulations validated against wind tunnel experiments provide credibility to optimization results"
                }
            ],
            "innovation_signals": {
                "research_stage": "advanced_development",
                "innovation_type": "incremental_breakthrough",
                "impact_potential": "high",
                "technical_risk": "medium",
                "adoption_indicators": [
                    "15 citations indicate active research interest",
                    "3 patent citations suggest commercial applicability",
                    "Quantified performance improvements (12% hover, 18% range)",
                    "Wind tunnel validation demonstrates technical feasibility",
                    "Published in prestigious AIAA journal"
                ]
            }
        }, indent=2)

        # Few-shot example 2: Marginally relevant paper (enabling technology)
        ex_input_2 = f"""
RESEARCH PAPER ANALYSIS REQUEST

Industry Context: eVTOL
Industry Description: Electric Vertical Takeoff and Landing aircraft for urban air mobility

Title: High-Power Density Silicon Carbide Inverters for Electric Propulsion Systems

Year: 2023
Publication Type: conference proceedings article
Journal/Conference: IEEE Energy Conversion Congress
Publisher: IEEE

Abstract:
This paper presents design and experimental validation of high-power density silicon carbide (SiC) motor inverters for electric propulsion applications. The inverter achieves 99.2% peak efficiency at 150 kW output with power density of 25 kW/kg through advanced thermal management and optimized switching topology. While primarily targeting electric aircraft propulsion, the technology is applicable to various electric vehicle systems including ground transportation and marine propulsion. Reliability testing demonstrates 5000-hour operation under aviation-grade thermal cycling conditions.

Citation Metrics:
- Scholarly Citations: 8
- Patent Citations: 1
- References: 28

Fields of Study: Power electronics, Silicon carbide, Electric propulsion, Inverters, Thermal management

Keywords: SiC inverter, electric propulsion, power density, motor drive, aviation

TASK:
1. Assess relevance to eVTOL industry (0-10 scale, threshold: 8.0)
2. If relevant (>= 8.0): Extract core technologies, innovations, and relationships for knowledge graph
"""

        ex_output_2 = json.dumps({
            "paper_metadata": {
                "title": "High-Power Density Silicon Carbide Inverters for Electric Propulsion Systems",
                "year_published": 2023,
                "publication_type": "conference proceedings article",
                "journal": "IEEE Energy Conversion Congress"
            },
            "relevance_assessment": {
                "relevance_score": 8.5,
                "is_relevant": True,
                "relevance_category": "enabling_technology",
                "justification": "Paper addresses critical enabling technology for eVTOL (high-power density electric propulsion inverters). SiC inverters are essential for eVTOL power systems. Mentions aviation applications and aviation-grade reliability testing. High power density (25 kW/kg) and efficiency (99.2%) are critical metrics for eVTOL range and payload.",
                "confidence": 0.92
            },
            "technology_nodes": [
                {
                    "node_id": "tech_sic_inverter_evtol",
                    "node_type": "technology",
                    "name": "Aviation-Grade SiC Motor Inverter",
                    "description": "150 kW silicon carbide inverter with 25 kW/kg power density for electric propulsion",
                    "maturity": "advanced",
                    "domain": "power_electronics"
                },
                {
                    "node_id": "tech_advanced_thermal_mgmt",
                    "node_type": "technology",
                    "name": "High-Power Inverter Thermal Management",
                    "description": "Thermal management system enabling 25 kW/kg power density in aviation environment",
                    "maturity": "advanced",
                    "domain": "thermal_systems"
                },
                {
                    "node_id": "tech_optimized_switching",
                    "node_type": "technology",
                    "name": "Optimized SiC Switching Topology",
                    "description": "Switching topology achieving 99.2% efficiency at 150 kW output",
                    "maturity": "mature",
                    "domain": "power_electronics"
                }
            ],
            "relationships": [
                {
                    "subject": "tech_sic_inverter_evtol",
                    "predicate": "enables",
                    "object": "evtol_electric_propulsion",
                    "confidence": 0.95,
                    "evidence": "High power density and efficiency critical for eVTOL range and payload capacity"
                },
                {
                    "subject": "tech_advanced_thermal_mgmt",
                    "predicate": "enables",
                    "object": "tech_sic_inverter_evtol",
                    "confidence": 0.95,
                    "evidence": "Thermal management is key enabler for achieving 25 kW/kg power density"
                },
                {
                    "subject": "tech_optimized_switching",
                    "predicate": "improves_efficiency_of",
                    "object": "tech_sic_inverter_evtol",
                    "confidence": 0.90,
                    "evidence": "Optimized topology delivers 99.2% efficiency, reducing thermal losses"
                },
                {
                    "subject": "tech_sic_inverter_evtol",
                    "predicate": "supports",
                    "object": "evtol_range_extension",
                    "confidence": 0.85,
                    "evidence": "High efficiency reduces battery energy consumption, extending flight range"
                }
            ],
            "innovation_signals": {
                "research_stage": "advanced_development",
                "innovation_type": "incremental",
                "impact_potential": "high",
                "technical_risk": "medium",
                "adoption_indicators": [
                    "Aviation-grade reliability testing (5000 hours)",
                    "Exceeds typical eVTOL power density requirements (15-20 kW/kg)",
                    "8 citations show growing interest in SiC for aviation",
                    "Conference proceeding suggests active commercialization efforts",
                    "1 patent citation indicates IP development"
                ]
            }
        }, indent=2)

        # Few-shot example 3: Irrelevant paper (below threshold)
        ex_input_3 = f"""
RESEARCH PAPER ANALYSIS REQUEST

Industry Context: eVTOL
Industry Description: Electric Vertical Takeoff and Landing aircraft for urban air mobility

Title: Machine Learning Approaches for Sentiment Analysis of Social Media Marketing Campaigns

Year: 2024
Publication Type: journal article
Journal/Conference: Journal of Digital Marketing Research
Publisher: Elsevier

Abstract:
This study investigates the effectiveness of machine learning algorithms for analyzing sentiment in social media marketing campaigns. We compare performance of BERT, GPT-based transformers, and traditional NLP methods across Twitter, Facebook, and Instagram datasets. Results show that fine-tuned transformer models achieve 92% accuracy in sentiment classification, outperforming traditional methods by 15%. The framework is applied to case studies in consumer electronics, fashion retail, and automotive industries. Implications for marketing strategy optimization and customer engagement are discussed.

Citation Metrics:
- Scholarly Citations: 12
- Patent Citations: 0
- References: 35

Fields of Study: Machine learning, Sentiment analysis, Social media, Digital marketing, Natural language processing

Keywords: sentiment analysis, social media marketing, BERT, transformer models, customer engagement

TASK:
1. Assess relevance to eVTOL industry (0-10 scale, threshold: 8.0)
2. If relevant (>= 8.0): Extract core technologies, innovations, and relationships for knowledge graph
"""

        ex_output_3 = json.dumps({
            "paper_metadata": {
                "title": "Machine Learning Approaches for Sentiment Analysis of Social Media Marketing Campaigns",
                "year_published": 2024,
                "publication_type": "journal article",
                "journal": "Journal of Digital Marketing Research"
            },
            "relevance_assessment": {
                "relevance_score": 2.0,
                "is_relevant": False,
                "relevance_category": "not_relevant",
                "justification": "Paper focuses on social media sentiment analysis and digital marketing strategies with no connection to eVTOL technology, aircraft design, electric propulsion, urban air mobility, or related technical domains. Case studies cover consumer electronics, fashion, and automotive but not aviation or eVTOL. Not relevant to eVTOL industry.",
                "confidence": 0.99
            },
            "technology_nodes": [],
            "relationships": [],
            "innovation_signals": {
                "research_stage": "not_applicable",
                "innovation_type": "not_applicable",
                "impact_potential": "not_applicable"
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
                {"input": ex_input_2, "output": ex_output_2},
                {"input": ex_input_3, "output": ex_output_3}
            ],
        )

        # System prompt with schema definition
        # Escape braces for LangChain's ChatPromptTemplate
        output_schema = """
{{
  "paper_metadata": {{
    "title": string,
    "year_published": integer,
    "publication_type": string,
    "journal": string
  }},
  "relevance_assessment": {{
    "relevance_score": float,              // 0.0-10.0 scale
    "is_relevant": boolean,                // true if >= THRESHOLD
    "relevance_category": "direct_application" | "enabling_technology" | "adjacent_research" | "not_relevant",
    "justification": string,               // Explain why relevant/not relevant (2-3 sentences)
    "confidence": float                    // 0.0-1.0
  }},
  "technology_nodes": [                    // ONLY if is_relevant = true
    {{
      "node_id": string,                   // Unique ID (snake_case: tech_*, concept_*)
      "node_type": "technology" | "concept",
      "name": string,                      // Human-readable name
      "description": string,               // Brief technical description
      "maturity": "emerging" | "advanced" | "mature" | "proven",
      "domain": string                     // Technical domain
    }}
  ],
  "relationships": [                       // ONLY if is_relevant = true
    {{
      "subject": string,                   // node_id of subject
      "predicate": string,                 // Relationship type (see below)
      "object": string,                    // node_id of object (can reference external concepts)
      "confidence": float,                 // 0.0-1.0
      "evidence": string                   // Why this relationship exists
    }}
  ],
  "innovation_signals": {{                 // ONLY if is_relevant = true
    "research_stage": "fundamental_research" | "applied_research" | "advanced_development" | "commercialization",
    "innovation_type": "breakthrough" | "incremental_breakthrough" | "incremental" | "sustaining",
    "impact_potential": "very_high" | "high" | "medium" | "low",
    "technical_risk": "low" | "medium" | "high" | "very_high",
    "adoption_indicators": [string]        // Evidence of research maturity/impact
  }}
}}"""

        system_prompt = f"""
You are a research paper analyst specializing in assessing paper relevance to specific industries and extracting innovation signals for strategic intelligence.

INDUSTRY CONTEXT:
- Target Industry: {self.industry_name}
- Industry Description: {self.industry_description}
- Core Keywords: {', '.join(self.industry_keywords[:10])}

Your task is to analyze research papers and:

1. RELEVANCE ASSESSMENT: Score paper relevance to {self.industry_name} industry (0-10 scale)
2. KNOWLEDGE GRAPH EXTRACTION: For relevant papers (>= {self.relevance_threshold}), extract technologies and relationships
3. INNOVATION SIGNALS: Assess research stage and impact potential

OUTPUT SCHEMA:
{output_schema}

RELEVANCE SCORING GUIDELINES (0-10 scale):

9.0-10.0: HIGHLY RELEVANT - Direct application to {self.industry_name}
  - Paper explicitly addresses {self.industry_name} technology, design, operations, or applications
  - Core research findings directly applicable to {self.industry_name} development
  - Examples: "{self.industry_name} aerodynamics", "{self.industry_name} flight control", "{self.industry_name} certification"

8.0-8.9: RELEVANT - Enabling technology or critical component
  - Paper addresses technologies that enable/improve {self.industry_name} systems
  - Research on key subsystems (batteries, motors, avionics, materials)
  - Mentions aviation/aircraft applications or has clear {self.industry_name} applicability
  - Examples: "electric propulsion for aircraft", "aviation-grade power electronics"

6.0-7.9: MODERATELY RELEVANT - Adjacent research
  - Technologies applicable to {self.industry_name} but not primary focus
  - General aviation research with potential {self.industry_name} applicability
  - Related fields (drones, electric vehicles) with some technical overlap
  - Below threshold: DO NOT extract knowledge graph

4.0-5.9: TANGENTIALLY RELEVANT - Distant connection
  - Broad topics (machine learning, materials science) without specific {self.industry_name} application
  - Generic engineering research that could apply to many industries
  - Below threshold: DO NOT extract knowledge graph

0.0-3.9: NOT RELEVANT - No connection to {self.industry_name}
  - Research in unrelated domains (social sciences, biology, marketing, etc.)
  - No technical applicability to {self.industry_name}
  - Below threshold: DO NOT extract knowledge graph

RELEVANCE CATEGORIES:

- "direct_application": Paper explicitly studies {self.industry_name} technology/applications
- "enabling_technology": Paper addresses technologies that enable {self.industry_name} (batteries, motors, controls)
- "adjacent_research": Related aviation/electric vehicle research with some applicability
- "not_relevant": No connection to {self.industry_name}

RELATIONSHIP PREDICATES (use these):
- "enables": Technology A makes technology B possible
- "requires": Technology A needs technology B to function
- "supports": Technology A helps technology B work better
- "improves_performance_of": Technology A enhances efficiency/capability of B
- "improves_efficiency_of": Technology A reduces losses/waste in B
- "validates": Research/testing validates technology
- "builds_on": Technology A extends prior work in B
- "competes_with": Technology A is alternative to B

KNOWLEDGE GRAPH EXTRACTION (ONLY if relevance_score >= {self.relevance_threshold}):

1. IDENTIFY CORE TECHNOLOGIES:
   - Extract 3-5 key technologies from title + abstract
   - Focus on novel contributions relevant to {self.industry_name}
   - Use descriptive names that capture technical essence

2. NODE_ID NAMING:
   - Use snake_case prefixes: tech_*, concept_*
   - Be specific: "tech_sic_inverter_evtol" not "tech_inverter"
   - Keep concise but descriptive

3. MATURITY ASSESSMENT:
   - "emerging": Novel approach, early research stage
   - "advanced": Proven concept, needs engineering refinement
   - "mature": Well-understood, widely implemented in other domains
   - "proven": Commercial deployment in target industry

4. RELATIONSHIPS:
   - Create 3-6 triplets per paper (if relevant)
   - Look for enabling relationships (what makes what possible?)
   - confidence = 0.9-1.0 for explicit facts, 0.7-0.89 for inferences
   - evidence must cite specific paper content

5. INNOVATION SIGNALS (if relevant):
   - research_stage: Where is this in R&D pipeline?
   - innovation_type: How novel? (breakthrough = new paradigm, incremental = refinement)
   - impact_potential: How important for {self.industry_name}? (consider technical merit + citation metrics)
   - technical_risk: How hard to implement? (consider physics, safety, certification)
   - adoption_indicators: List 3-5 concrete signals (citations, validation, publication venue)

6. DOMAIN CATEGORIES (use these):
   - aerodynamics, propulsion, flight_control, avionics, energy_storage, power_electronics,
   - materials, manufacturing, thermal_systems, safety_systems, simulation, operations

CRITICAL RULES:
- Output ONLY valid JSON (no markdown, no commentary)
- Relevance score must be realistic (be strict: most papers should score < 8.0)
- If relevance_score < {self.relevance_threshold}: technology_nodes, relationships, and detailed innovation_signals should be EMPTY
- If relevant: extract knowledge graph with 3-5 nodes and 3-6 relationships
- All node_ids must be unique within the paper
- Confidence scores must be realistic (0.7-1.0 range typical)
- Evidence must be specific, not generic
- Focus on INNOVATION and {self.industry_name} APPLICABILITY

SPECIAL CASES:
- If abstract is missing: base assessment on title + fields of study + keywords only
- If paper is generic survey/review: likely not relevant unless explicitly focused on {self.industry_name}
- If paper has low citation count: not disqualifying if technically relevant
"""

        final_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            few_shot,
            ("human", "{input}")
        ])

        return final_prompt | self.llm | self.output_parser


def load_papers_from_file(file_path: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Load paper data from JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        papers = json.load(f)

    if limit:
        papers = papers[:limit]

    return papers


def load_industry_config(config_path: str) -> Dict[str, Any]:
    """Load industry configuration from JSON file."""
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config
