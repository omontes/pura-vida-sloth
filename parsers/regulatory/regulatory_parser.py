"""
Regulatory Document Parser for Knowledge Graph Extraction

Extracts technology and company entities/relations from Federal Register regulatory documents.
Supports: FAA, EPA, DoD, NASA, FCC regulatory filings.

Author: Pura Vida Sloth Intelligence System
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.callbacks import get_openai_callback

from parsers.regulatory.document_extractors import (
    extract_all_metadata,
    chunk_text
)


class RegulatoryDocumentParser:
    """LLM-driven parser to extract entities and relationships from regulatory documents."""

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
        Initialize regulatory document parser with industry-specific context.

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

        # Create chains for summarization and extraction
        self.summary_chain = self._create_summary_chain()
        self.extraction_chain = self._create_extraction_chain()

    def parse_document(
        self,
        file_path: str,
        metadata_record: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Parse a single regulatory document from markdown file.

        Args:
            file_path: Path to regulatory markdown file
            metadata_record: Optional metadata dict

        Returns:
            Dictionary containing:
            - document: All document metadata + LLM-generated summary
            - document_metadata: Extra regulatory-specific fields
            - tech_mentions: Technologies with roles, strength, confidence
            - company_mentions: Companies with roles, strength, confidence
            - company_tech_relations: Relations with doc_ref added
            - tech_tech_relations: Relations with doc_ref added
            - company_company_relations: Relations with doc_ref added
        """
        # Read file content
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Extract metadata using regex
        filename = os.path.basename(file_path)
        metadata = extract_all_metadata(content, filename)

        # Check if content is too small
        if not content or len(content.strip()) < 200:
            print(f"\n[SKIPPED] Document has insufficient content - skipping LLM call")
            llm_result = self._empty_result()
            summary = ""
        else:
            # Step 1: Summarize chunks (if content is large)
            if len(content) > 10000:
                print(f"\n[PROCESSING] Content is large ({len(content)} chars), chunking...")
                chunks = chunk_text(content, chunk_size=5000)
                print(f"[PROCESSING] Summarizing {len(chunks[:5])} chunks...")
                chunk_summaries = self._summarize_chunks(chunks[:5])  # Limit to 5 chunks
                combined_summary = " ".join(chunk_summaries)
            else:
                combined_summary = content

            # Step 2: Extract entities and relations
            print(f"[PROCESSING] Extracting entities and relations...")
            llm_result = self._extract_entities(
                summary=combined_summary,
                document_type=metadata.get("document_type", "notice"),
                regulatory_body=metadata.get("regulatory_body", "")
            )

            # Create document summary (200-500 chars)
            summary = self._create_document_summary(combined_summary)

        # Generate document ID
        fr_doc_id = metadata.get("federal_register_doc_id", "unknown")
        agency_slug = filename.split('_')[0] if '_' in filename else "unknown"
        doc_id = f"regulatory_{agency_slug}_{fr_doc_id}"

        # Build title
        title = self._create_title(
            metadata.get("regulatory_body"),
            metadata.get("document_type"),
            metadata.get("published_at")
        )

        # Build URL
        url = f"https://federalregister.gov/d/{fr_doc_id}" if fr_doc_id != "unknown" else ""

        # Build final result
        final_result = {
            "document": {
                # Core identification fields
                "doc_id": doc_id,
                "doc_type": "regulation",
                "title": title,
                "url": url,
                "source": "Federal Register",

                # Publication metadata
                "published_at": metadata.get("published_at"),
                "summary": summary,
                "content": "",  # Empty (too large to store)

                # Scoring
                "quality_score": llm_result.get("quality_score", 0.0),
                "relevance_score": 0.0,  # Placeholder for agents

                # Regulatory-specific document fields
                "regulatory_body": metadata.get("regulatory_body"),
                "sub_agency": metadata.get("sub_agency"),
                "document_type": metadata.get("document_type"),
                "decision_type": metadata.get("decision_type"),
                "effective_date": metadata.get("effective_date"),
                "docket_number": metadata.get("docket_number"),
                "federal_register_doc_id": fr_doc_id,

                # Embedding placeholder
                "embedding": []
            },
            "document_metadata": {
                "federal_register_volume": metadata.get("federal_register_volume"),
                "federal_register_issue": metadata.get("federal_register_issue"),
                "section": metadata.get("section"),
                "comment_deadline": metadata.get("comment_deadline"),
                "contact_email": metadata.get("contact_email"),
                "action_text": metadata.get("action_text")
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
        file_path: str,
        out_path: str = "regulatory_parse_result.json",
        metadata_record: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Parse a regulatory document and save results to JSON file."""
        result = self.parse_document(file_path, metadata_record)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to: {out_path}")
        return result

    def _summarize_chunks(self, chunks: List[str]) -> List[str]:
        """Summarize each content chunk using LLM."""
        summaries = []

        for i, chunk in enumerate(chunks):
            try:
                with get_openai_callback() as cb:
                    summary = self.summary_chain.invoke({"text": chunk})
                    summaries.append(summary)
                    print(f"  Chunk {i+1}/{len(chunks)}: {cb.total_tokens} tokens")
            except Exception as e:
                print(f"  Chunk {i+1} summarization error: {e}")
                # Use first 500 chars as fallback
                summaries.append(chunk[:500])

        return summaries

    def _extract_entities(
        self,
        summary: str,
        document_type: str,
        regulatory_body: str
    ) -> Dict[str, Any]:
        """Extract entities and relations from combined summary."""
        input_text = f"""
REGULATORY DOCUMENT ANALYSIS REQUEST

Document Type: {document_type}
Regulatory Body: {regulatory_body}

Content Summary:
{summary[:10000]}

TASK: Extract core technologies, companies, and their relationships for knowledge graph construction.
Also determine: quality_score (0.0-1.0, relevance to {self.industry_name} industry).
"""

        try:
            with get_openai_callback() as cb:
                result = self.extraction_chain.invoke({"input": input_text})
                print(f"  Extraction: {cb.total_tokens} tokens (${cb.total_cost:.6f})")
                return result
        except Exception as e:
            print(f"  Extraction error: {e}")
            return self._empty_result()

    def _create_document_summary(self, combined_summary: str) -> str:
        """Create final document summary (200-500 chars)."""
        # Clean markdown artifacts
        import re

        # Remove HTML-like tags
        cleaned = re.sub(r'<[^>]+>', '', combined_summary)
        # Remove markdown links
        cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', cleaned)
        # Remove multiple whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)

        # Skip attestation/metadata sections at the beginning
        # Look for first substantive content (usually starts after "**AGENCY:**" or similar)
        agency_match = re.search(r'\*\*AGENCY:\*\*(.+?)(?=\*\*|$)', cleaned, re.DOTALL)
        summary_match = re.search(r'\*\*SUMMARY:\*\*(.+?)(?=\*\*|$)', cleaned, re.DOTALL)

        if summary_match:
            # Use SUMMARY section if available
            summary = summary_match.group(1).strip()[:500]
        elif agency_match:
            # Start from AGENCY section
            start_pos = agency_match.start()
            summary = cleaned[start_pos:start_pos+500]
        else:
            # Fallback: skip first 200 chars (likely metadata)
            summary = cleaned[200:700]

        # Trim to sentence boundary
        last_period = summary.rfind('. ')
        if last_period > 100:
            summary = summary[:last_period + 1]

        return summary.strip()

    def _create_title(
        self,
        regulatory_body: Optional[str],
        document_type: Optional[str],
        published_at: Optional[str]
    ) -> str:
        """Create document title from metadata."""
        parts = []

        if regulatory_body:
            parts.append(regulatory_body)
        if document_type:
            parts.append(document_type.replace('_', ' ').title())
        if published_at:
            parts.append(published_at)

        return " - ".join(parts) if parts else "Regulatory Document"

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

    def _create_summary_chain(self):
        """Create LLM chain for chunk summarization."""
        from langchain_core.output_parsers import StrOutputParser

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a regulatory document analyst. Summarize the following Federal Register document excerpt into 2-3 concise sentences focusing on regulatory decisions, technology requirements, and affected companies. Ignore boilerplate legal text."),
            ("human", "{text}")
        ])

        return prompt | self.llm | StrOutputParser()

    def _create_extraction_chain(self):
        """Build the few-shot chain for regulatory document entity extraction."""

        # Few-shot example 1: FAA eVTOL safety reporting (high relevance)
        ex_input_1 = """
REGULATORY DOCUMENT ANALYSIS REQUEST

Document Type: notice
Regulatory Body: FAA

Content Summary:
The Federal Aviation Administration (FAA) announces a new voluntary safety event reporting system for small unmanned aircraft systems (sUAS) operations. The system will collect data on near-miss incidents, operational anomalies, and safety events involving electric vertical takeoff and landing (eVTOL) aircraft operations. Operators of electric VTOL platforms are encouraged to submit safety reports to improve operational safety standards. The FAA will use this data to inform future certification requirements for urban air mobility operations. The system includes provisions for autonomous flight operations and advanced air mobility systems. Partnership with NASA and industry stakeholders including Joby Aviation and Archer Aviation to establish baseline safety metrics.

TASK: Extract core technologies, companies, and their relationships for knowledge graph construction.
Also determine: quality_score (0.0-1.0, relevance to eVTOL industry).
"""

        ex_output_1 = json.dumps({
            "quality_score": 0.98,
            "tech_mentions": [
                {
                    "name": "eVTOL Aircraft",
                    "role": "regulated",
                    "strength": 0.95,
                    "evidence_confidence": 0.98,
                    "evidence_text": "FAA establishes safety reporting requirements for electric VTOL aircraft operations"
                },
                {
                    "name": "Autonomous Flight Systems",
                    "role": "regulated",
                    "strength": 0.80,
                    "evidence_confidence": 0.90,
                    "evidence_text": "System includes provisions for autonomous flight operations"
                },
                {
                    "name": "Urban Air Mobility",
                    "role": "regulated",
                    "strength": 0.85,
                    "evidence_confidence": 0.95,
                    "evidence_text": "Data will inform future certification requirements for urban air mobility operations"
                }
            ],
            "company_mentions": [
                {
                    "name": "FAA",
                    "role": "issuer",
                    "strength": 1.0,
                    "evidence_confidence": 1.0,
                    "evidence_text": "Federal Aviation Administration announces reporting system"
                },
                {
                    "name": "NASA",
                    "role": "partner",
                    "strength": 0.70,
                    "evidence_confidence": 0.90,
                    "evidence_text": "Partnership with NASA to establish baseline safety metrics"
                },
                {
                    "name": "Joby Aviation",
                    "role": "operator",
                    "strength": 0.65,
                    "evidence_confidence": 0.85,
                    "evidence_text": "Industry stakeholder including Joby Aviation"
                },
                {
                    "name": "Archer Aviation",
                    "role": "operator",
                    "strength": 0.65,
                    "evidence_confidence": 0.85,
                    "evidence_text": "Industry stakeholder including Archer Aviation"
                }
            ],
            "company_tech_relations": [
                {
                    "company_name": "FAA",
                    "technology_name": "eVTOL Aircraft",
                    "relation_type": "researches",
                    "evidence_confidence": 0.95,
                    "evidence_text": "FAA researches eVTOL safety through data collection and reporting requirements"
                }
            ],
            "tech_tech_relations": [
                {
                    "from_tech_name": "Autonomous Flight Systems",
                    "to_tech_name": "Urban Air Mobility",
                    "relation_type": "enables",
                    "evidence_confidence": 0.90,
                    "evidence_text": "Autonomous flight provisions support urban air mobility certification"
                }
            ],
            "company_company_relations": [
                {
                    "from_company_name": "FAA",
                    "to_company_name": "NASA",
                    "relation_type": "partners_with",
                    "evidence_confidence": 0.90,
                    "evidence_text": "Partnership to establish baseline safety metrics"
                }
            ]
        }, indent=2)

        # Few-shot example 2: Low relevance environmental notice
        ex_input_2 = """
REGULATORY DOCUMENT ANALYSIS REQUEST

Document Type: notice
Regulatory Body: EPA

Content Summary:
The Environmental Protection Agency announces availability of the final Environmental Impact Statement for the proposed construction of a wastewater treatment facility in rural Michigan. The facility will process agricultural runoff and municipal sewage using advanced biological treatment methods. Public comment period closed on June 15, 2024. The project includes installation of anaerobic digesters and membrane filtration systems. No significant environmental impacts were identified. Construction is expected to begin in 2025.

TASK: Extract core technologies, companies, and their relationships for knowledge graph construction.
Also determine: quality_score (0.0-1.0, relevance to eVTOL industry).
"""

        ex_output_2 = json.dumps({
            "quality_score": 0.15,
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

        system_prompt = f"""
You are a regulatory analyst extracting entities and relationships from Federal Register documents for strategic intelligence.

ALLOWED RELATION TYPES (use ONLY these from config):

Company → Technology ({len(self.allowed_company_tech_relations)} types):
{', '.join(self.allowed_company_tech_relations)}

Technology → Technology ({len(self.allowed_tech_tech_relations)} types):
{', '.join(self.allowed_tech_tech_relations)}

Company → Company ({len(self.allowed_company_company_relations)} types):
{', '.join(self.allowed_company_company_relations)}

RELATION DEFINITIONS:
{relation_defs_escaped}

ENTITY ROLES FOR REGULATORY DOCUMENTS:

Technology Roles:
- "subject": Primary technology topic of regulation
- "regulated": Technology subject to regulatory oversight
- "approved": Technology approved by agency
- "studied": Technology under research/evaluation
- "proposed": Technology in proposed regulations
- "required": Technology mandated by regulation

Company Roles:
- "issuer": Regulatory agency issuing the document
- "operator": Company operating regulated technology
- "developer": Company developing regulated technology
- "partner": Strategic partner with regulatory agency
- "contractor": Company receiving government contract

STRENGTH SCORING (0.0-1.0):
- 1.0: Core focus of regulation
- 0.7-0.9: Key regulatory requirement
- 0.4-0.6: Supporting element
- 0.1-0.3: Mentioned in passing

CONFIDENCE SCORING (0.0-1.0):
- 0.95-1.0: Explicit statement in regulation
- 0.8-0.94: Strong regulatory inference
- 0.6-0.79: Moderate inference
- 0.5-0.59: Weak inference

QUALITY SCORE (0.0-1.0):
- 0.95-1.0: Core industry regulation (direct {self.industry_name} regulation)
- 0.85-0.94: Supporting regulation (enables industry)
- 0.70-0.84: Tangentially related
- 0.50-0.69: Keyword match only
- 0.0-0.49: Not industry-related

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
- Extract 2-6 technology mentions
- Extract 1-4 company mentions
- Quality score < 0.85 → can return empty arrays
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
