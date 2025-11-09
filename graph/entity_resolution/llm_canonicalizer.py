"""
Phase 3: LLM Canonical Name Selection
Uses GPT-4o-mini with few-shot prompting to select canonical technology names for clusters
Supports both sequential and async concurrent processing
"""

import json
import os
import asyncio
from asyncio import Semaphore
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.callbacks import get_openai_callback

from .schemas import TechnologyCluster, LLMCanonicalResult
from .config import EntityResolutionConfig, get_pipeline_config

# Load environment variables
load_dotenv()


class LLMCanonicalizer:
    """Selects canonical technology names using LLM with few-shot prompting."""

    def __init__(self, config: EntityResolutionConfig):
        """
        Initialize LLM canonicalizer.

        Args:
            config: Entity resolution configuration
        """
        self.config = config
        self.pipeline_config = get_pipeline_config()

        # Load OpenAI API key
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        # Initialize LLM
        self.llm = ChatOpenAI(
            temperature=self.pipeline_config['llm_temperature'],
            model=self.pipeline_config['llm_model'],
            api_key=self.openai_api_key,
            timeout=120.0
        )

        self.output_parser = JsonOutputParser()
        self.chain = self._create_chain()

        # Track costs
        self.total_cost = 0.0
        self.total_tokens = 0

    def _create_chain(self):
        """Build few-shot chain for canonical name selection."""

        # Few-shot example 1: Tiltrotor variants
        ex_input_1 = """
CLUSTER CANONICALIZATION REQUEST

Industry: eVTOL (Electric Vertical Takeoff and Landing)

Technology Variants (3 mentions):
1. "Tiltrotor System" (occurrences: 5)
2. "Tilt-Rotor Propulsion" (occurrences: 3)
3. "Tilting Rotor Assembly" (occurrences: 2)

TASK: Select the best canonical name for this technology cluster.
"""

        ex_output_1 = json.dumps({
            "canonical_name": "Tiltrotor System",
            "domain": "Propulsion",
            "description": "Aircraft propulsion system with rotors that can tilt between vertical (hover) and horizontal (forward flight) orientations, enabling VTOL capability",
            "confidence": 0.95,
            "reasoning": "Tiltrotor System is the most widely recognized term in aerospace engineering. It's concise, technically accurate, and clearly describes the core mechanism. The other variants are valid but less standard."
        }, indent=2)

        # Few-shot example 2: Battery technology variants
        ex_input_2 = """
CLUSTER CANONICALIZATION REQUEST

Industry: eVTOL (Electric Vertical Takeoff and Landing)

Technology Variants (4 mentions):
1. "Lithium-Ion Battery Pack" (occurrences: 8)
2. "Li-ion Energy Storage System" (occurrences: 4)
3. "Rechargeable Lithium Battery" (occurrences: 3)
4. "Lithium Battery Module" (occurrences: 2)

TASK: Select the best canonical name for this technology cluster.
"""

        ex_output_2 = json.dumps({
            "canonical_name": "Lithium-Ion Battery System",
            "domain": "Energy Storage",
            "description": "Rechargeable battery system using lithium-ion chemistry for energy storage in electric aircraft, providing power for propulsion and avionics",
            "confidence": 0.92,
            "reasoning": "Lithium-Ion Battery System captures the essential technology while being more general than 'pack' or 'module'. It's the standard industry term that encompasses various form factors (packs, modules, cells) and is widely recognized in aviation."
        }, indent=2)

        # Few-shot example 3: Autonomous flight control variants
        ex_input_3 = """
CLUSTER CANONICALIZATION REQUEST

Industry: eVTOL (Electric Vertical Takeoff and Landing)

Technology Variants (5 mentions):
1. "Autonomous Flight Control System" (occurrences: 6)
2. "Self-Flying Aircraft Control" (occurrences: 3)
3. "Automated Pilot System" (occurrences: 4)
4. "AI-Based Flight Controller" (occurrences: 2)
5. "Autonomous Navigation System" (occurrences: 3)

TASK: Select the best canonical name for this technology cluster.
"""

        ex_output_3 = json.dumps({
            "canonical_name": "Autonomous Flight Control System",
            "domain": "Avionics",
            "description": "Automated system for controlling aircraft flight operations without human pilot intervention, using sensors, processors, and algorithms for navigation and control",
            "confidence": 0.94,
            "reasoning": "Autonomous Flight Control System is the established aerospace terminology. It's more precise than 'self-flying' or 'automated pilot', and more comprehensive than 'navigation system' (which is a subset). This term is widely used in aviation regulations and technical literature."
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

        # System prompt
        system_prompt = """
You are an expert aerospace engineer and technology taxonomist specializing in electric vertical takeoff and landing (eVTOL) aircraft.

Your task is to analyze clusters of technology mention variants and select the BEST canonical name that represents the technology.

SELECTION CRITERIA (in priority order):

1. **Industry Standard Terminology**: Prefer terms widely used in aerospace engineering, aviation regulations (FAA/EASA), and technical literature

2. **Technical Precision**: Select names that accurately describe the core technology without being overly specific or generic

3. **Generalizability**: Choose terms that encompass variants/subcategories rather than specific implementations

4. **Clarity**: Prefer clear, unambiguous names over jargon or marketing terms

5. **Occurrence Weight**: Consider mention frequency, but don't let it override technical correctness

DOMAIN CATEGORIES (choose one):
- Propulsion: Motors, rotors, engines, thrust systems
- Energy Storage: Batteries, fuel cells, power systems
- Avionics: Flight control, navigation, sensors, autonomy
- Airframe: Wings, fuselage, landing gear, structures
- Safety: Redundancy, fault tolerance, emergency systems
- Infrastructure: Charging, vertiports, ground systems
- Manufacturing: Production processes, materials, assembly

OUTPUT SCHEMA:
{{
  "canonical_name": string (concise, 2-6 words, title case),
  "domain": string (one of the categories above),
  "description": string (1-2 sentences, technical but accessible),
  "confidence": float (0.0-1.0, how certain you are this is the best choice),
  "reasoning": string (2-3 sentences explaining your choice)
}}

CRITICAL RULES:
- Output ONLY valid JSON (no markdown, no commentary)
- canonical_name must be in Title Case (e.g., "Tiltrotor System", not "tiltrotor system")
- If all variants are equally good, choose the most common one
- confidence should be >0.90 for clear cases, 0.80-0.89 for good choices with minor ambiguity, <0.80 for difficult cases
- description should be technical but understandable by aerospace professionals
- reasoning must justify why you chose this name over the alternatives

REMEMBER: You are creating a canonical technology catalog that will be used for strategic intelligence analysis. Precision and consistency matter.
"""

        final_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            few_shot,
            ("human", "{input}")
        ])

        return final_prompt | self.llm | self.output_parser

    def _format_cluster_for_llm(self, cluster: TechnologyCluster) -> str:
        """
        Format cluster into readable text for LLM processing.

        Args:
            cluster: TechnologyCluster object

        Returns:
            Formatted input text
        """
        # Get industry from config
        industry = f"{self.config.config.get('industry_name', self.config.industry)} ({self.config.industry})"

        # Format variants with rich metadata for LLM expert analysis
        variants_text = ""
        for i, name in enumerate(cluster.mention_names, 1):
            meta = cluster.mention_metadata.get(name, {})

            # Count document types
            doc_types = meta.get("doc_types", [])
            patent_count = sum(1 for d in doc_types if d == "patent")
            paper_count = sum(1 for d in doc_types if d == "technical_paper")

            # Format variant with metadata
            variants_text += f'{i}. "{name}" '
            variants_text += f'({meta.get("occurrence_count", 0)} occurrences, '
            variants_text += f'strength: {meta.get("avg_strength", 0):.2f}, '
            variants_text += f'confidence: {meta.get("avg_confidence", 0):.2f}, '
            variants_text += f'roles: {"/".join(meta.get("roles", []))}, '
            variants_text += f'{patent_count} patents + {paper_count} papers)\n'

        formatted = f"""
CLUSTER CANONICALIZATION REQUEST

Industry: {industry}

Technology Variants ({len(cluster.mention_names)} mentions):
{variants_text}
TASK: Select the best canonical name for this technology cluster.
""".strip()

        return formatted

    def canonicalize_cluster(self, cluster: TechnologyCluster) -> Optional[LLMCanonicalResult]:
        """
        Canonicalize a single cluster using LLM.

        Args:
            cluster: TechnologyCluster object

        Returns:
            LLMCanonicalResult object or None on error
        """
        input_text = self._format_cluster_for_llm(cluster)

        try:
            with get_openai_callback() as cb:
                # LLM generates canonical name + metadata
                llm_result = self.chain.invoke({"input": input_text})

                # Track costs
                self.total_cost += cb.total_cost
                self.total_tokens += cb.total_tokens

                print(f"  Cluster {cluster.cluster_id}: {llm_result.get('canonical_name', 'ERROR')}")
                print(f"    Tokens: {cb.total_tokens}, Cost: ${cb.total_cost:.6f}")

        except Exception as e:
            print(f"  Error canonicalizing cluster {cluster.cluster_id}: {e}")
            return None

        # Create result object
        result = LLMCanonicalResult(
            cluster_id=cluster.cluster_id,
            input_variants=cluster.mention_names,
            canonical_name=llm_result.get('canonical_name', ''),
            domain=llm_result.get('domain'),
            description=llm_result.get('description'),
            confidence=llm_result.get('confidence', 0.0),
            reasoning=llm_result.get('reasoning', '')
        )

        return result

    async def canonicalize_cluster_async(self, cluster: TechnologyCluster,
                                        semaphore: Semaphore) -> Optional[LLMCanonicalResult]:
        """
        Canonicalize a single cluster asynchronously with concurrency control.

        Args:
            cluster: TechnologyCluster object
            semaphore: Asyncio semaphore to limit concurrent requests

        Returns:
            LLMCanonicalResult object or None on error
        """
        async with semaphore:  # Limit concurrent requests
            input_text = self._format_cluster_for_llm(cluster)

            try:
                with get_openai_callback() as cb:
                    # Use ainvoke for async processing
                    llm_result = await self.chain.ainvoke({"input": input_text})

                    # Track costs
                    self.total_cost += cb.total_cost
                    self.total_tokens += cb.total_tokens

                    print(f"  Cluster {cluster.cluster_id}: {llm_result.get('canonical_name', 'ERROR')}")
                    print(f"    Tokens: {cb.total_tokens}, Cost: ${cb.total_cost:.6f}")

            except Exception as e:
                print(f"  Error canonicalizing cluster {cluster.cluster_id}: {e}")
                return None

            # Create result object
            result = LLMCanonicalResult(
                cluster_id=cluster.cluster_id,
                input_variants=cluster.mention_names,
                canonical_name=llm_result.get('canonical_name', ''),
                domain=llm_result.get('domain'),
                description=llm_result.get('description'),
                confidence=llm_result.get('confidence', 0.0),
                reasoning=llm_result.get('reasoning', '')
            )

            return result

    async def canonicalize_batch_async(self, clusters: List[TechnologyCluster],
                                       max_concurrent: int = 20) -> List[LLMCanonicalResult]:
        """
        Canonicalize clusters concurrently using async processing.

        Args:
            clusters: List of TechnologyCluster objects
            max_concurrent: Maximum concurrent requests (default: 20)

        Returns:
            List of LLMCanonicalResult objects
        """
        print(f"\nProcessing {len(clusters)} clusters with {max_concurrent} concurrent requests...")

        semaphore = Semaphore(max_concurrent)

        # Create tasks for all clusters
        tasks = [
            self.canonicalize_cluster_async(cluster, semaphore)
            for cluster in clusters
        ]

        # Process all concurrently with progress tracking
        results = []
        completed = 0

        for coro in asyncio.as_completed(tasks):
            result = await coro
            if result:
                results.append(result)
            completed += 1

            # Progress indicator every 50 clusters
            if completed % 50 == 0:
                print(f"\n  Progress: {completed}/{len(clusters)} clusters completed\n")

        print(f"\n  [SUCCESS] Completed {len(results)}/{len(clusters)} clusters")

        return results

    def canonicalize_batch(self, clusters: List[TechnologyCluster],
                          start_idx: int = 0,
                          limit: Optional[int] = None) -> List[LLMCanonicalResult]:
        """
        Canonicalize a batch of clusters.

        Args:
            clusters: List of TechnologyCluster objects
            start_idx: Starting index for batch processing
            limit: Maximum number of clusters to process (None = all)

        Returns:
            List of LLMCanonicalResult objects
        """
        # Determine end index
        end_idx = len(clusters) if limit is None else min(start_idx + limit, len(clusters))

        print(f"\nCanonicalizing clusters {start_idx} to {end_idx-1}...")

        results = []

        for i in range(start_idx, end_idx):
            cluster = clusters[i]
            result = self.canonicalize_cluster(cluster)

            if result:
                results.append(result)

        return results

    def run(self, clusters: List[TechnologyCluster],
           limit: Optional[int] = None,
           use_async: bool = True) -> List[LLMCanonicalResult]:
        """
        Run Phase 3: Canonicalize clusters using LLM.

        Args:
            clusters: List of TechnologyCluster objects from Phase 2B
            limit: Maximum number of clusters to process (for testing)
            use_async: Use async concurrent processing (default: True)

        Returns:
            List of LLMCanonicalResult objects
        """
        print(f"\n{'='*80}")
        print("PHASE 3: LLM CANONICAL NAME SELECTION")
        print(f"{'='*80}")

        total_clusters = len(clusters)
        process_count = limit if limit else total_clusters
        clusters_to_process = clusters[:process_count]

        print(f"Processing {process_count} of {total_clusters} clusters...")
        print(f"Mode: {'Async Concurrent (20 parallel)' if use_async else 'Sequential'}")

        # Choose processing mode
        if use_async:
            max_concurrent = self.pipeline_config.get('max_concurrent_requests', 20)
            results = asyncio.run(self.canonicalize_batch_async(
                clusters_to_process,
                max_concurrent=max_concurrent
            ))
        else:
            results = self.canonicalize_batch(clusters_to_process, start_idx=0, limit=limit)

        # Save results
        self.save_results(results)

        # Print summary
        self._print_summary(results)

        return results

    def save_results(self, results: List[LLMCanonicalResult]):
        """
        Save LLM canonicalization results to JSON file.

        Args:
            results: List of LLMCanonicalResult objects
        """
        output_dir = self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / self.pipeline_config['output_files']['llm_canonical_names']

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([r.model_dump() for r in results], f, indent=2, ensure_ascii=False)

        print(f"\nSaved canonical names to: {output_file}")

    def _print_summary(self, results: List[LLMCanonicalResult]):
        """Print summary statistics."""
        print(f"\n{'='*80}")
        print("PHASE 3 SUMMARY")
        print(f"{'='*80}")

        print(f"Total clusters canonicalized: {len(results)}")
        print(f"Total cost: ${self.total_cost:.4f}")
        print(f"Total tokens: {self.total_tokens}")

        if results:
            avg_confidence = sum(r.confidence for r in results) / len(results)
            print(f"Average confidence: {avg_confidence:.2f}")

            # Domain distribution
            domain_counts = {}
            for r in results:
                domain = r.domain or "Unknown"
                domain_counts[domain] = domain_counts.get(domain, 0) + 1

            print(f"\nDomain distribution:")
            for domain, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {domain}: {count}")

            # Sample results
            print(f"\nSample canonical names:")
            for i, result in enumerate(results[:10], 1):
                variants_preview = result.input_variants[0] if result.input_variants else "N/A"
                if len(result.input_variants) > 1:
                    variants_preview += f" (+{len(result.input_variants)-1} more)"

                print(f"  {i}. {result.canonical_name} (confidence: {result.confidence:.2f})")
                print(f"     Domain: {result.domain}")
                print(f"     Variants: {variants_preview}")
                print()

        print(f"{'='*80}")


def load_clusters(config: EntityResolutionConfig, filename: str) -> List[TechnologyCluster]:
    """
    Load clusters from JSON file.

    Args:
        config: Entity resolution configuration
        filename: Filename in output directory

    Returns:
        List of TechnologyCluster objects
    """
    file_path = config.output_dir / filename

    if not file_path.exists():
        raise FileNotFoundError(f"Clusters file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return [TechnologyCluster(**item) for item in data]
