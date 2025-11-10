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
    """LLM-driven parser to extract technology relationships from scholarly papers."""

    def __init__(
        self,
        openai_api_key: str,
        config_path: str = "configs/eVTOL_graph_relations.json",
        industry_name: str = None,
        industry_keywords: List[str] = None,
        industry_description: str = None,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.0
    ):
        """
        Initialize parser with industry-specific context.

        Args:
            openai_api_key: OpenAI API key
            config_path: Path to graph relations config file
            industry_name: Target industry (optional, loaded from config if not provided)
            industry_keywords: Core industry keywords (optional)
            industry_description: Brief description of the industry (optional)
            model_name: OpenAI model to use (default: gpt-4o-mini)
            temperature: Model temperature (0.0 = deterministic)
        """
        # Load allowed relations from config
        with open(config_path, 'r', encoding='utf-8') as f:
            self.graph_config = json.load(f)

        self.allowed_company_tech_relations = self.graph_config["allowed_company_tech_relations"]
        self.allowed_tech_tech_relations = self.graph_config["allowed_tech_tech_relations"]
        self.allowed_company_company_relations = self.graph_config["allowed_company_company_relations"]

        # Store industry context (can be passed or loaded from config)
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
        self.chain = self._create_chain()

    def parse_paper(self, paper_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a single paper into entity mentions and relationships.

        Args:
            paper_data: Paper record from Lens.org API

        Returns:
            Dictionary containing:
            - document: All paper metadata
            - document_metadata: Extra paper fields not in document
            - tech_mentions: Technologies with roles, strength, confidence
            - company_mentions: Companies with roles, strength, confidence
            - company_tech_relations: Relations with doc_ref added
            - tech_tech_relations: Relations with doc_ref added
            - company_company_relations: Relations with doc_ref added
        """
        # Check if abstract is empty - skip LLM call if no content to analyze
        abstract = self._clean_abstract(paper_data.get("abstract", ""))

        if not abstract or len(abstract.strip()) == 0:
            print("\n[SKIPPED] Paper has no abstract - skipping LLM call")
            llm_result = {
                "quality_score": 0.0,
                "tech_mentions": [],
                "company_mentions": [],
                "company_tech_relations": [],
                "tech_tech_relations": [],
                "company_company_relations": []
            }
        else:
            # Paper has abstract - proceed with LLM analysis
            input_text = self._format_paper_for_llm(paper_data)

            try:
                with get_openai_callback() as cb:
                    # LLM generates quality_score, mentions + relations only
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

        # Python extracts all document metadata
        doc_id = paper_data.get("lens_id", "")

        final_result = {
            "document": {
                # Core identification fields
                "doc_id": doc_id,
                "doc_type": "technical_paper",
                "title": paper_data.get("title", ""),
                "url": paper_data.get("url", ""),
                "source": "Lens.org Scholarly API",

                # Publication metadata
                "published_at": paper_data.get("date_published"),
                "summary": "",  # Empty as specified
                "content": abstract,  # Reuse already-cleaned abstract

                # Scoring
                "quality_score": llm_result.get("quality_score", 0.0),
                "relevance_score": 0.0,

                # Paper-specific fields
                "doi": self._extract_doi(paper_data),
                "venue_type": self._extract_venue_type(paper_data),
                "peer_reviewed": self._infer_peer_reviewed(paper_data),
                "source_title": paper_data.get("source", {}).get("title"),
                "year_published": paper_data.get("year_published"),
                "date_published": paper_data.get("date_published"),
                "citation_count": paper_data.get("scholarly_citations_count", 0),
                "patent_citations_count": paper_data.get("patent_citations_count", 0),

                # Embedding placeholder
                "embedding": []
            },
            "document_metadata": self._populate_document_metadata(paper_data),
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

TASK: Extract core technologies, innovations, and their relationships for knowledge graph construction.
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

    def _extract_venue_type(self, paper: Dict[str, Any]) -> str:
        """Extract first word from publication_type as venue_type."""
        publication_type = paper.get("publication_type", "")
        if publication_type:
            # Extract first word (e.g., "journal article" -> "journal")
            return publication_type.split()[0] if publication_type.split() else ""
        return ""

    def _infer_peer_reviewed(self, paper: Dict[str, Any]) -> Optional[bool]:
        """Infer peer-reviewed status from publication_type."""
        publication_type = paper.get("publication_type", "").lower()

        # Likely peer-reviewed types
        peer_reviewed_types = ["journal", "article", "conference", "proceedings"]
        non_peer_reviewed_types = ["preprint", "book", "thesis", "dissertation", "report"]

        for pr_type in peer_reviewed_types:
            if pr_type in publication_type:
                return True

        for npr_type in non_peer_reviewed_types:
            if npr_type in publication_type:
                return False

        # Unknown
        return None

    def _populate_document_metadata(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """Extract all extra fields that are not in the document dict."""
        return {
            "publication_type": paper.get("publication_type", ""),
            "publication_supplementary_type": paper.get("publication_supplementary_type", []),
            "external_ids": paper.get("external_ids", []),
            "open_access": paper.get("open_access", {}),
            "source_urls": paper.get("source_urls", []),
            "funding": paper.get("funding", []),
            "authors": paper.get("authors", []),
            "author_count": paper.get("author_count", 0),
            "scholarly_citations": paper.get("scholarly_citations", []),
            "patent_citations": paper.get("patent_citations", []),
            "references_count": paper.get("references_count", 0),
            "references": paper.get("references", []),
            "fields_of_study": paper.get("fields_of_study", []),
            "keywords": paper.get("keywords", []),
            "mesh_terms": paper.get("mesh_terms", []),
            "clinical_trials": paper.get("clinical_trials", []),
            "chemicals": paper.get("chemicals", []),
            "source": paper.get("source", {}),
            "matched_keyword": paper.get("matched_keyword", ""),
            "harvested_at": paper.get("harvested_at", "")
        }

    def _validate_relations(self, llm_result: Dict[str, Any]) -> None:
        """Validate that relation types match allowed enums from config."""
        # Validate company-tech relations
        for rel in llm_result.get("company_tech_relations", []):
            rel_type = rel.get("relation_type")
            if rel_type and rel_type not in self.allowed_company_tech_relations:
                print(f"  Warning: Invalid company-tech relation '{rel_type}' (allowed: {self.allowed_company_tech_relations})")

        # Validate tech-tech relations
        for rel in llm_result.get("tech_tech_relations", []):
            rel_type = rel.get("relation_type")
            if rel_type and rel_type not in self.allowed_tech_tech_relations:
                print(f"  Warning: Invalid tech-tech relation '{rel_type}' (allowed: {self.allowed_tech_tech_relations})")

        # Validate company-company relations
        for rel in llm_result.get("company_company_relations", []):
            rel_type = rel.get("relation_type")
            if rel_type and rel_type not in self.allowed_company_company_relations:
                print(f"  Warning: Invalid company-company relation '{rel_type}' (allowed: {self.allowed_company_company_relations})")

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure on parsing failure (LLM format)."""
        return {
            "quality_score": 0.0,
            "tech_mentions": [],
            "company_mentions": [],
            "company_tech_relations": [],
            "tech_tech_relations": [],
            "company_company_relations": []
        }

    def _create_chain(self):
        """Build the few-shot chain for paper technology extraction."""

        # Few-shot example 1: Highly relevant eVTOL paper
        ex_input_1 = """
    RESEARCH PAPER ANALYSIS REQUEST

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

    TASK: Extract core technologies, innovations, and their relationships for knowledge graph construction.
    """

        ex_output_1 = json.dumps({
            "quality_score": 0.95,
            "tech_mentions": [
                {
                    "name": "eVTOL Tilt-Rotor Aerodynamic Optimization",
                    "role": "subject",
                    "strength": 0.95,
                    "evidence_confidence": 0.98,
                    "evidence_text": "Primary topic: Optimization framework for tilt-rotor eVTOL configurations"
                },
                {
                    "name": "eVTOL Tilt-Rotor Aerodynamic Optimization",
                    "role": "studied",
                    "strength": 0.90,
                    "evidence_confidence": 0.96,
                    "evidence_text": "Research investigated hover-cruise efficiency trade-offs through CFD simulations"
                },
                {
                    "name": "Novel Rotor Blade Design",
                    "role": "proposed",
                    "strength": 0.85,
                    "evidence_confidence": 0.95,
                    "evidence_text": "Study introduces novel blade design achieving 12% hover efficiency improvement"
                },
                {
                    "name": "CFD Wind Tunnel Validation",
                    "role": "applied",
                    "strength": 0.75,
                    "evidence_confidence": 0.92,
                    "evidence_text": "CFD simulations validated against wind tunnel experiments for credibility"
                },
                {
                    "name": "Transition Phase Flight Control",
                    "role": "evaluated",
                    "strength": 0.70,
                    "evidence_confidence": 0.90,
                    "evidence_text": "Flight control strategies analyzed using dynamic flight simulations"
                }
            ],
            "company_mentions": [],
            "company_tech_relations": [],
            "tech_tech_relations": [
                {
                    "from_tech_name": "eVTOL Tilt-Rotor Aerodynamic Optimization",
                    "to_tech_name": "Novel Rotor Blade Design",
                    "relation_type": "enables",
                    "evidence_confidence": 0.95,
                    "evidence_text": "Optimization framework enabled development of novel blade design with quantified performance gains"
                },
                {
                    "from_tech_name": "CFD Wind Tunnel Validation",
                    "to_tech_name": "eVTOL Tilt-Rotor Aerodynamic Optimization",
                    "relation_type": "validates",
                    "evidence_confidence": 0.93,
                    "evidence_text": "Experimental validation provides credibility to optimization results"
                }
            ],
            "company_company_relations": []
        }, indent=2)

        # Few-shot example 2: Enabling technology paper
        ex_input_2 = """
    RESEARCH PAPER ANALYSIS REQUEST

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

    TASK: Extract core technologies, innovations, and their relationships for knowledge graph construction.
    """

        ex_output_2 = json.dumps({
            "quality_score": 0.88,
            "tech_mentions": [
                {
                    "name": "High-Power Density SiC Motor Inverter",
                    "role": "subject",
                    "strength": 0.95,
                    "evidence_confidence": 0.98,
                    "evidence_text": "Primary topic: SiC inverters for electric propulsion with 25 kW/kg density"
                },
                {
                    "name": "High-Power Density SiC Motor Inverter",
                    "role": "validated",
                    "strength": 0.88,
                    "evidence_confidence": 0.95,
                    "evidence_text": "Experimental validation demonstrates 99.2% efficiency and 5000-hour reliability"
                },
                {
                    "name": "Advanced Thermal Management for Inverters",
                    "role": "studied",
                    "strength": 0.80,
                    "evidence_confidence": 0.92,
                    "evidence_text": "Research investigates thermal management enabling high power density"
                },
                {
                    "name": "Optimized SiC Switching Topology",
                    "role": "proposed",
                    "strength": 0.75,
                    "evidence_confidence": 0.90,
                    "evidence_text": "Paper presents optimized topology achieving 99.2% peak efficiency"
                }
            ],
            "company_mentions": [],
            "company_tech_relations": [],
            "tech_tech_relations": [
                {
                    "from_tech_name": "Advanced Thermal Management for Inverters",
                    "to_tech_name": "High-Power Density SiC Motor Inverter",
                    "relation_type": "enables",
                    "evidence_confidence": 0.95,
                    "evidence_text": "Thermal management is key enabler for achieving 25 kW/kg power density"
                },
                {
                    "from_tech_name": "Optimized SiC Switching Topology",
                    "to_tech_name": "High-Power Density SiC Motor Inverter",
                    "relation_type": "improves_efficiency_of",
                    "evidence_confidence": 0.92,
                    "evidence_text": "Optimized topology delivers 99.2% efficiency, reducing thermal losses"
                }
            ],
            "company_company_relations": []
        }, indent=2)

        # Few-shot example 3: Low quality (not relevant)
        ex_input_3 = """
    RESEARCH PAPER ANALYSIS REQUEST

    Title: Machine Learning Approaches for Sentiment Analysis of Social Media Marketing Campaigns

    Year: 2024
    Publication Type: journal article
    Journal/Conference: Journal of Digital Marketing Research
    Publisher: Elsevier

    Abstract:
    This study investigates the effectiveness of machine learning algorithms for analyzing sentiment in social media marketing campaigns. We compare performance of BERT, GPT-based transformers, and traditional NLP methods across Twitter, Facebook, and Instagram datasets. Results show that fine-tuned transformer models achieve 92% accuracy in sentiment classification, outperforming traditional methods by 15%. The framework is applied to case studies in consumer electronics, fashion retail, and automotive industries.

    Citation Metrics:
    - Scholarly Citations: 12
    - Patent Citations: 0
    - References: 35

    Fields of Study: Machine learning, Sentiment analysis, Social media, Digital marketing

    TASK: Extract core technologies, innovations, and their relationships for knowledge graph construction.
    """

        ex_output_3 = json.dumps({
            "quality_score": 0.20,
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
                {"input": ex_input_2, "output": ex_output_2},
                {"input": ex_input_3, "output": ex_output_3}
            ],
        )

        # System prompt with universal role taxonomy and config-driven relations
        # Escape curly braces in JSON for LangChain template
        relation_defs_json = json.dumps(self.graph_config['relation_definitions'], indent=2)
        relation_defs_escaped = relation_defs_json.replace('{', '{{').replace('}', '}}')

        system_prompt = f"""
    You are a research paper analyst extracting entities and relationships for strategic intelligence.

    ALLOWED RELATION TYPES (use ONLY these from config):

    Company → Technology ({len(self.allowed_company_tech_relations)} types):
    {', '.join(self.allowed_company_tech_relations)}

    Technology → Technology ({len(self.allowed_tech_tech_relations)} types):
    {', '.join(self.allowed_tech_tech_relations)}

    Company → Company ({len(self.allowed_company_company_relations)} types):
    {', '.join(self.allowed_company_company_relations)}

    RELATION DEFINITIONS:
    {relation_defs_escaped}

    TECHNOLOGY ROLES FOR RESEARCH PAPERS (ONE role per mention - create separate mentions for same entity with different roles):
    - "subject": Primary topic of the paper
    - "studied": Researched/investigated/analyzed in the paper
    - "validated": Experimentally validated/tested/proven
    - "proposed": New method/approach proposed by authors
    - "evaluated": Performance evaluated/compared/benchmarked
    - "applied": Technology applied to solve a problem
    - "surveyed": Reviewed/surveyed in literature review

    COMPANY ROLES FOR RESEARCH PAPERS (ONE role per mention - create separate mentions for same entity with different roles):
    - "author": Author affiliation (university/research institution)
    - "sponsor": Funded the research
    - "partner": Research collaboration partner
    - "developer": Developed technology mentioned in paper

    STRENGTH SCORING (0.0-1.0) - Importance of THIS ROLE to Paper:
    - 1.0: Core focus (explicitly central to paper for this role)
    - 0.7-0.9: Key supporting element (critical but not primary for this role)
    - 0.4-0.6: Supporting element (mentioned 2-3 times for this role)
    - 0.1-0.3: Background/peripheral (mentioned once for this role)

    CONFIDENCE SCORING (0.0-1.0) - Certainty of THIS ROLE Assignment:
    - 0.95-1.0: Explicit statement, exact terminology for this role
    - 0.8-0.94: Strong inference from technical description for this role
    - 0.6-0.79: Moderate inference from context for this role
    - 0.5-0.59: Weak inference for this role

    QUALITY SCORE (0.0-1.0) - Industry Relevance Assessment:
    PURPOSE: Determine if this paper is actually relevant to the target industry.
    Some papers may mention keywords but not be truly related to the industry.
    Documents with quality_score < 0.85 will be FILTERED OUT in post-processing.

    Scoring Guidelines:
    - 0.95-1.0: Core industry research (direct application to target industry)
    - 0.85-0.94: Supporting technology (enables or complements industry)
    - 0.70-0.84: Tangentially related (shares components or methods)
    - 0.50-0.69: Keyword match only (not actually related to industry)
    - 0.0-0.49: Not related to industry (false positive from search)

    Example for eVTOL industry:
    - 0.98: "eVTOL aerodynamic optimization" (core eVTOL research)
    - 0.90: "Electric aircraft battery systems" (supporting technology)
    - 0.75: "Urban air mobility infrastructure" (tangential)
    - 0.60: "General electric motor control" (keyword match only)
    - 0.30: "Automotive sentiment analysis" (not eVTOL related)

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
    - Example: "eVTOL" as subject (strength=0.95) AND as studied (strength=0.90) = 2 separate entries
    - Use ONLY allowed relation types from config lists above
    - Evidence text must be < 200 chars and specific to THAT role
    - Extract 3-8 technology mentions total (including multiple roles for same tech)
    - Extract 0-3 company mentions total (research papers often have no company mentions)
    - All relation_type values must match config enums exactly
    - If paper has quality_score < 0.85, you can return empty tech_mentions and relations arrays

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
