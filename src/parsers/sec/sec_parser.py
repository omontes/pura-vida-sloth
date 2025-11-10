"""
SEC Filing Parser for Knowledge Graph Extraction

Extracts technology and company entities/relations from SEC EDGAR filings.
Supports: 10-K, 10-Q, 8-K, S-1 filings with industry-agnostic configuration.

Author: Pura Vida Sloth Intelligence System
"""

import os
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.callbacks import get_openai_callback

from parsers.sec.section_extractors import (
    extract_sections,
    parse_sec_header,
    derive_fiscal_period,
    chunk_text
)


class SECFilingParser:
    """LLM-driven parser to extract entities and relationships from SEC filings."""

    # Placeholder/generic company names to filter out
    PLACEHOLDER_COMPANIES = {
        "Another Retail Company",
        "Another Customer",
        "Another Supplier",
        "Certain Customers",
        "Certain Suppliers",
        "Major Customers",
        "Major Suppliers",
        "Various Customers",
        "Other Companies",
        "Third Party",
        "Unnamed Entity"
    }

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
        Initialize SEC filing parser with industry-specific context.

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

    def parse_filing(
        self,
        file_path: str,
        metadata_record: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Parse a single SEC filing from TXT file.

        Args:
            file_path: Path to SEC filing TXT file
            metadata_record: Optional metadata dict from metadata.json

        Returns:
            Dictionary containing:
            - document: All filing metadata + LLM-generated summary
            - document_metadata: Extra SEC-specific fields
            - tech_mentions: Technologies with roles, strength, confidence
            - company_mentions: Companies with roles, strength, confidence
            - company_tech_relations: Relations with doc_ref added
            - tech_tech_relations: Relations with doc_ref added
            - company_company_relations: Relations with doc_ref added
        """
        # Read file content
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Extract sections and metadata
        sections = extract_sections(content, filing_type='10-K')  # Will auto-detect
        sec_metadata = sections['metadata']
        content_chunks = sections['content_chunks']

        # Determine filing type
        filing_type = sec_metadata.get('filing_type', 'UNKNOWN')

        # Parse filename for additional metadata
        filename = os.path.basename(file_path)
        filename_parts = self._parse_filename(filename)

        # Generate document ID
        accession = sec_metadata.get('accession_number', '').replace('-', '')
        doc_id = f"sec_{accession}" if accession else f"sec_{filename_parts.get('accession', 'unknown')}"

        # Check if content is too small
        full_content = sections.get('full_content', '')
        if not full_content or len(full_content.strip()) < 100:
            print(f"\n[SKIPPED] Filing has insufficient content - skipping LLM call")
            llm_result = self._empty_result()
            summary = ""
        else:
            # Step 1: Summarize chunks
            print(f"\n[PROCESSING] Summarizing {len(content_chunks)} chunks...")
            chunk_summaries = self._summarize_chunks(content_chunks)
            combined_summary = " ".join(chunk_summaries)

            # Step 2: Extract entities and relations
            print(f"[PROCESSING] Extracting entities and relations...")
            llm_result = self._extract_entities(
                summary=combined_summary,
                filing_type=filing_type,
                company_name=sec_metadata.get('company_name', '')
            )

            # Create document summary (200-500 chars)
            summary = self._create_document_summary(combined_summary)

        # Derive fiscal period
        fiscal_year, fiscal_quarter = derive_fiscal_period(
            sec_metadata.get('report_period'),
            sec_metadata.get('fiscal_year_end'),
            filing_type
        )

        # Build final result
        final_result = {
            "document": {
                # Core identification fields
                "doc_id": doc_id,
                "doc_type": "sec_filing",
                "title": self._create_title(
                    sec_metadata.get('company_name'),
                    filing_type,
                    sec_metadata.get('filing_date')
                ),
                "url": metadata_record.get('url') if metadata_record else "",
                "source": "SEC EDGAR",

                # Publication metadata
                "published_at": sec_metadata.get('filing_date'),
                "summary": summary,
                "content": "",  # Empty (too large to store)

                # Scoring
                "quality_score": llm_result.get("quality_score", 0.0),
                "relevance_score": 0.0,  # Placeholder for agents

                # SEC-specific document fields
                "filing_type": filing_type,
                "cik": sec_metadata.get('cik'),
                "accession_number": sec_metadata.get('accession_number'),
                "filing_date": sec_metadata.get('filing_date'),
                "fiscal_year": fiscal_year,
                "fiscal_quarter": fiscal_quarter,

                # Embedding placeholder
                "embedding": []
            },
            "document_metadata": {
                "company_name": sec_metadata.get('company_name'),
                "ticker": filename_parts.get('ticker') or (metadata_record.get('ticker') if metadata_record else None),
                "fiscal_year_end": sec_metadata.get('fiscal_year_end'),
                "sic_code": sec_metadata.get('sic_code'),
                "sic_description": sec_metadata.get('sic_description'),
                "state_of_incorporation": sec_metadata.get('state_of_incorporation'),
                "ein": sec_metadata.get('ein'),
                "report_period": sec_metadata.get('report_period'),

                # LLM-extracted fields
                "revenue_mentioned": llm_result.get("revenue_mentioned", False),
                "revenue_amount": llm_result.get("revenue_amount"),
                "risk_factor_mentioned": llm_result.get("risk_factor_mentioned", False),
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
        out_path: str = "sec_parse_result.json",
        metadata_record: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Parse a filing and save results to JSON file."""
        result = self.parse_filing(file_path, metadata_record)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to: {out_path}")
        return result

    def _summarize_chunks(self, chunks: List[str]) -> List[str]:
        """Summarize each content chunk using LLM."""
        summaries = []

        for i, chunk in enumerate(chunks[:10]):  # Limit to first 10 chunks for cost control
            try:
                with get_openai_callback() as cb:
                    summary = self.summary_chain.invoke({"text": chunk})
                    summaries.append(summary)
                    print(f"  Chunk {i+1}/{min(len(chunks), 10)}: {cb.total_tokens} tokens")
            except Exception as e:
                print(f"  Chunk {i+1} summarization error: {e}")
                # Use first 500 chars as fallback
                summaries.append(chunk[:500])

        return summaries

    def _extract_entities(
        self,
        summary: str,
        filing_type: str,
        company_name: str
    ) -> Dict[str, Any]:
        """Extract entities and relations from combined summary."""
        input_text = f"""
SEC FILING ANALYSIS REQUEST

Filing Type: {filing_type}
Company: {company_name}

Content Summary:
{summary[:10000]}

TASK: Extract core technologies, companies, and their relationships for knowledge graph construction.
Also determine: revenue_mentioned (bool), revenue_amount (float if disclosed), risk_factor_mentioned (bool).
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
        # Take first 500 chars and trim to sentence boundary
        summary = combined_summary[:500]

        # Find last sentence boundary
        last_period = summary.rfind('. ')
        if last_period > 200:
            summary = summary[:last_period + 1]

        return summary.strip()

    def _create_title(
        self,
        company_name: Optional[str],
        filing_type: Optional[str],
        filing_date: Optional[str]
    ) -> str:
        """Create document title from metadata."""
        parts = []

        if company_name:
            parts.append(company_name)
        if filing_type:
            parts.append(filing_type)
        if filing_date:
            parts.append(filing_date)

        return " - ".join(parts) if parts else "SEC Filing"

    def _parse_filename(self, filename: str) -> Dict[str, str]:
        """
        Parse filename to extract ticker, filing_type, filing_date, accession.

        Expected format: {TICKER}_{FILING_TYPE}_{DATE}_{ACCESSION}.txt
        Example: ACHR_10-K_2024-02-29T00-00-00_000162828024007963.txt
        """
        result = {}

        # Remove .txt extension
        name = filename.replace('.txt', '')

        # Split by underscore
        parts = name.split('_')

        if len(parts) >= 4:
            result['ticker'] = parts[0]
            result['filing_type'] = parts[1]
            result['filing_date'] = parts[2]
            result['accession'] = parts[3]

        return result

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

    def _filter_placeholder_companies(self, llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter out placeholder/generic company names from extraction results.

        Removes:
        - Placeholder company mentions
        - Relations involving placeholder companies

        Args:
            llm_result: LLM extraction result dict

        Returns:
            Filtered result dict
        """
        # Filter company mentions
        original_count = len(llm_result.get("company_mentions", []))
        filtered_company_mentions = [
            mention for mention in llm_result.get("company_mentions", [])
            if mention.get("name") not in self.PLACEHOLDER_COMPANIES
        ]
        filtered_count = len(filtered_company_mentions)

        if filtered_count < original_count:
            print(f"  [FILTER] Removed {original_count - filtered_count} placeholder company mention(s)")

        # Get set of valid company names for relation filtering
        valid_companies = {mention.get("name") for mention in filtered_company_mentions}

        # Filter company-tech relations
        original_ct = len(llm_result.get("company_tech_relations", []))
        filtered_ct_relations = [
            rel for rel in llm_result.get("company_tech_relations", [])
            if rel.get("company_name") not in self.PLACEHOLDER_COMPANIES
        ]
        if len(filtered_ct_relations) < original_ct:
            print(f"  [FILTER] Removed {original_ct - len(filtered_ct_relations)} company-tech relation(s) with placeholders")

        # Filter company-company relations (both from and to)
        original_cc = len(llm_result.get("company_company_relations", []))
        filtered_cc_relations = [
            rel for rel in llm_result.get("company_company_relations", [])
            if (rel.get("from_company_name") not in self.PLACEHOLDER_COMPANIES and
                rel.get("to_company_name") not in self.PLACEHOLDER_COMPANIES)
        ]
        if len(filtered_cc_relations) < original_cc:
            print(f"  [FILTER] Removed {original_cc - len(filtered_cc_relations)} company-company relation(s) with placeholders")

        # Return filtered result
        return {
            "quality_score": llm_result.get("quality_score", 0.0),
            "revenue_mentioned": llm_result.get("revenue_mentioned", False),
            "revenue_amount": llm_result.get("revenue_amount"),
            "risk_factor_mentioned": llm_result.get("risk_factor_mentioned", False),
            "tech_mentions": llm_result.get("tech_mentions", []),
            "company_mentions": filtered_company_mentions,
            "company_tech_relations": filtered_ct_relations,
            "tech_tech_relations": llm_result.get("tech_tech_relations", []),  # No filtering needed
            "company_company_relations": filtered_cc_relations
        }

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure on parsing failure."""
        return {
            "quality_score": 0.0,
            "tech_mentions": [],
            "company_mentions": [],
            "company_tech_relations": [],
            "tech_tech_relations": [],
            "company_company_relations": [],
            "revenue_mentioned": False,
            "revenue_amount": None,
            "risk_factor_mentioned": False
        }

    def _create_summary_chain(self):
        """Create LLM chain for chunk summarization."""
        from langchain_core.output_parsers import StrOutputParser

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a financial document analyst. Summarize the following SEC filing excerpt into 2-3 concise sentences focusing on business operations, technologies, partnerships, and financial performance. Ignore boilerplate legal text and financial tables."),
            ("human", "{text}")
        ])

        return prompt | self.llm | StrOutputParser()

    def _create_extraction_chain(self):
        """Build the few-shot chain for SEC filing entity extraction."""

        # Few-shot example 1: 10-K for eVTOL company
        ex_input_1 = """
SEC FILING ANALYSIS REQUEST

Filing Type: 10-K
Company: Archer Aviation Inc.

Content Summary:
Archer Aviation is developing electric vertical takeoff and landing (eVTOL) aircraft for urban air mobility. The company's Midnight aircraft is designed to transport passengers in urban environments with reduced noise and zero emissions. Archer has strategic partnerships with United Airlines and Stellantis for commercialization and manufacturing. The company is investing heavily in battery technology and autonomous flight systems. Risk factors include regulatory certification delays from the FAA, competition from Joby Aviation and Lilium, and capital requirements for scaling production. Revenue from aircraft sales is not expected until 2025 pending FAA certification.

TASK: Extract core technologies, companies, and their relationships for knowledge graph construction.
Also determine: revenue_mentioned (bool), revenue_amount (float if disclosed), risk_factor_mentioned (bool).
"""

        ex_output_1 = json.dumps({
            "quality_score": 0.95,
            "revenue_mentioned": True,
            "revenue_amount": None,  # Not disclosed specific amount
            "risk_factor_mentioned": True,
            "tech_mentions": [
                {
                    "name": "eVTOL Aircraft",
                    "role": "subject",
                    "strength": 0.95,
                    "evidence_confidence": 0.98,
                    "evidence_text": "Company's primary product: Midnight eVTOL aircraft for urban air mobility"
                },
                {
                    "name": "Autonomous Flight Systems",
                    "role": "studied",
                    "strength": 0.75,
                    "evidence_confidence": 0.90,
                    "evidence_text": "Investing in autonomous flight system development"
                },
                {
                    "name": "Advanced Battery Technology",
                    "role": "studied",
                    "strength": 0.70,
                    "evidence_confidence": 0.88,
                    "evidence_text": "Heavy investment in battery technology for aircraft"
                }
            ],
            "company_mentions": [
                {
                    "name": "United Airlines",
                    "role": "partner",
                    "strength": 0.85,
                    "evidence_confidence": 0.95,
                    "evidence_text": "Strategic partnership for commercialization"
                },
                {
                    "name": "Stellantis",
                    "role": "partner",
                    "strength": 0.85,
                    "evidence_confidence": 0.95,
                    "evidence_text": "Manufacturing partnership for production scaling"
                },
                {
                    "name": "Joby Aviation",
                    "role": "developer",
                    "strength": 0.60,
                    "evidence_confidence": 0.85,
                    "evidence_text": "Mentioned as competitor in risk factors"
                },
                {
                    "name": "Lilium",
                    "role": "developer",
                    "strength": 0.60,
                    "evidence_confidence": 0.85,
                    "evidence_text": "Mentioned as competitor in risk factors"
                }
            ],
            "company_tech_relations": [
                {
                    "company_name": "Archer Aviation Inc.",
                    "technology_name": "eVTOL Aircraft",
                    "relation_type": "develops",
                    "evidence_confidence": 0.98,
                    "evidence_text": "Archer developing Midnight eVTOL aircraft"
                }
            ],
            "tech_tech_relations": [
                {
                    "from_tech_name": "Advanced Battery Technology",
                    "to_tech_name": "eVTOL Aircraft",
                    "relation_type": "enables",
                    "evidence_confidence": 0.90,
                    "evidence_text": "Battery technology is critical enabler for eVTOL performance"
                }
            ],
            "company_company_relations": [
                {
                    "from_company_name": "Archer Aviation Inc.",
                    "to_company_name": "United Airlines",
                    "relation_type": "partners_with",
                    "evidence_confidence": 0.95,
                    "evidence_text": "Strategic partnership for commercialization"
                },
                {
                    "from_company_name": "Archer Aviation Inc.",
                    "to_company_name": "Stellantis",
                    "relation_type": "partners_with",
                    "evidence_confidence": 0.95,
                    "evidence_text": "Manufacturing partnership"
                },
                {
                    "from_company_name": "Archer Aviation Inc.",
                    "to_company_name": "Joby Aviation",
                    "relation_type": "competes_with",
                    "evidence_confidence": 0.85,
                    "evidence_text": "Competitor mentioned in risk factors"
                }
            ]
        }, indent=2)

        # Few-shot example 2: Low relevance filing
        ex_input_2 = """
SEC FILING ANALYSIS REQUEST

Filing Type: 8-K
Company: Generic Retail Corp.

Content Summary:
Generic Retail Corp. filed an 8-K to announce the appointment of a new Chief Financial Officer. Jane Smith will join the company effective March 1, 2024. Ms. Smith previously served as CFO at Another Retail Company. The company also announced standard executive compensation details and updated employment agreements. No operational or strategic changes were disclosed.

TASK: Extract core technologies, companies, and their relationships for knowledge graph construction.
Also determine: revenue_mentioned (bool), revenue_amount (float if disclosed), risk_factor_mentioned (bool).
"""

        ex_output_2 = json.dumps({
            "quality_score": 0.15,
            "revenue_mentioned": False,
            "revenue_amount": None,
            "risk_factor_mentioned": False,
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
You are a financial analyst extracting entities and relationships from SEC filings for strategic intelligence.

ALLOWED RELATION TYPES (use ONLY these from config):

Company → Technology ({len(self.allowed_company_tech_relations)} types):
{', '.join(self.allowed_company_tech_relations)}

Technology → Technology ({len(self.allowed_tech_tech_relations)} types):
{', '.join(self.allowed_tech_tech_relations)}

Company → Company ({len(self.allowed_company_company_relations)} types):
{', '.join(self.allowed_company_company_relations)}

RELATION DEFINITIONS:
{relation_defs_escaped}

ENTITY ROLES FOR SEC FILINGS:

Technology Roles:
- "subject": Primary technology/product the company develops
- "studied": Technologies under R&D/investigation
- "validated": Technologies proven in testing/deployment
- "proposed": New technologies announced in filing
- "evaluated": Technologies assessed for adoption
- "applied": Technologies currently in use

Company Roles:
- "author": The filing company itself
- "partner": Strategic/commercial partner
- "developer": Company that developed mentioned technology
- "sponsor": Investor/funding provider

STRENGTH SCORING (0.0-1.0):
- 1.0: Core business focus
- 0.7-0.9: Key strategic initiative
- 0.4-0.6: Supporting element
- 0.1-0.3: Mentioned in passing

CONFIDENCE SCORING (0.0-1.0):
- 0.95-1.0: Explicit statement
- 0.8-0.94: Strong inference
- 0.6-0.79: Moderate inference
- 0.5-0.59: Weak inference

QUALITY SCORE (0.0-1.0):
- 0.95-1.0: Core industry filing (direct relevance)
- 0.85-0.94: Supporting technology (enables industry)
- 0.70-0.84: Tangentially related
- 0.50-0.69: Keyword match only
- 0.0-0.49: Not industry-related

SEC-SPECIFIC FIELDS:
- revenue_mentioned: true if filing mentions technology generating revenue
- revenue_amount: dollar amount if disclosed (null otherwise)
- risk_factor_mentioned: true if technologies mentioned in Risk Factors section

OUTPUT SCHEMA:
{{{{
  "quality_score": float,
  "revenue_mentioned": bool,
  "revenue_amount": float | null,
  "risk_factor_mentioned": bool,
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
- Extract 0-4 company mentions
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
