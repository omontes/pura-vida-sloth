"""
Gold Dataset Creation Utilities for Patent Parser Validation

This module provides helper functions for creating and managing the gold standard
dataset where Claude manually parses patents with expert analysis.
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime


def load_patents_slice(
    patents_file: str,
    start_index: int,
    end_index: int
) -> List[Dict[str, Any]]:
    """
    Load a slice of patents from patents.json.

    Args:
        patents_file: Path to patents.json
        start_index: Starting index (inclusive)
        end_index: Ending index (exclusive)

    Returns:
        List of patent dictionaries
    """
    with open(patents_file, "r", encoding="utf-8") as f:
        patents = json.load(f)

    return patents[start_index:end_index]


def validate_gold_entry(entry: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate a gold dataset entry meets quality thresholds.

    Quality criteria:
    - Minimum 3 technology nodes (unless abstract is empty)
    - Minimum 3 relationships
    - All relationships have confidence >= 0.7
    - All relationships cite evidence
    - Innovation signals are classified (not "unknown")

    Args:
        entry: Parsed patent entry

    Returns:
        (is_valid, list of validation errors)
    """
    errors = []

    # Check for empty abstract (valid skip case)
    abstract = entry.get("patent_metadata", {}).get("abstract", "")
    if not abstract or len(abstract.strip()) == 0:
        return True, ["Skipped: Empty abstract"]

    # Check minimum nodes
    nodes = entry.get("technology_nodes", [])
    if len(nodes) < 3:
        errors.append(f"Insufficient nodes: {len(nodes)} (minimum 3 required)")

    # Check minimum relationships
    relationships = entry.get("relationships", [])
    if len(relationships) < 3:
        errors.append(f"Insufficient relationships: {len(relationships)} (minimum 3 required)")

    # Validate relationship quality
    for idx, rel in enumerate(relationships):
        confidence = rel.get("confidence", 0.0)
        if confidence < 0.7:
            errors.append(f"Relationship {idx+1} confidence too low: {confidence} < 0.7")

        evidence = rel.get("evidence", "")
        if not evidence or len(evidence.strip()) < 10:
            errors.append(f"Relationship {idx+1} missing evidence")

    # Check innovation signals
    signals = entry.get("innovation_signals", {})
    maturity = signals.get("maturity_level", "unknown")
    innovation_type = signals.get("innovation_type", "unknown")

    if maturity == "unknown":
        errors.append("Innovation maturity_level is 'unknown'")
    if innovation_type == "unknown":
        errors.append("Innovation type is 'unknown'")

    # Validate node references
    node_ids = {node.get("node_id") for node in nodes}
    for idx, rel in enumerate(relationships):
        subject = rel.get("subject")
        obj = rel.get("object")

        # Allow external references (concepts not in patent)
        # Only validate that subject exists (must be from this patent)
        if subject not in node_ids:
            errors.append(f"Relationship {idx+1} subject '{subject}' not found in nodes")

    is_valid = len(errors) == 0
    return is_valid, errors


def save_gold_entry(
    entry: Dict[str, Any],
    output_folder: str
) -> str:
    """
    Save a validated gold dataset entry.

    Args:
        entry: Parsed patent entry
        output_folder: Path to gold_dataset folder

    Returns:
        Path to saved file
    """
    lens_id = entry.get("patent_metadata", {}).get("lens_id", "unknown")

    # Create parsed subfolder
    parsed_folder = os.path.join(output_folder, "parsed")
    os.makedirs(parsed_folder, exist_ok=True)

    # Save individual file
    filename = f"{lens_id}.json"
    filepath = os.path.join(parsed_folder, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)

    return filepath


def update_metadata(
    output_folder: str,
    entries: List[Dict[str, Any]],
    start_index: int,
    end_index: int
):
    """
    Update gold dataset metadata file.

    Args:
        output_folder: Path to gold_dataset folder
        entries: List of successfully parsed entries
        start_index: Starting index processed
        end_index: Ending index processed
    """
    metadata_file = os.path.join(output_folder, "_metadata.json")

    # Load existing metadata
    if os.path.exists(metadata_file):
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        metadata = {
            "dataset_name": "eVTOL Patents Gold Standard",
            "created_date": datetime.now().isoformat(),
            "total_entries": 0,
            "entries": []
        }

    # Add new entries
    for entry in entries:
        metadata["entries"].append({
            "lens_id": entry.get("patent_metadata", {}).get("lens_id"),
            "patent_number": entry.get("patent_metadata", {}).get("patent_number"),
            "title": entry.get("patent_metadata", {}).get("title"),
            "assignee": entry.get("patent_metadata", {}).get("assignee"),
            "filing_date": entry.get("patent_metadata", {}).get("filing_date"),
            "nodes_count": len(entry.get("technology_nodes", [])),
            "relationships_count": len(entry.get("relationships", [])),
            "parsed_date": datetime.now().isoformat()
        })

    metadata["total_entries"] = len(metadata["entries"])
    metadata["last_updated"] = datetime.now().isoformat()
    metadata["index_ranges_processed"] = metadata.get("index_ranges_processed", [])
    metadata["index_ranges_processed"].append({
        "start": start_index,
        "end": end_index,
        "date": datetime.now().isoformat(),
        "count": len(entries)
    })

    # Save metadata
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def log_validation_errors(
    output_folder: str,
    patent_data: Dict[str, Any],
    errors: List[str],
    index: int
):
    """
    Log validation errors and skipped patents.

    Args:
        output_folder: Path to gold_dataset folder
        patent_data: Original patent data
        errors: List of validation errors
        index: Index in patents.json
    """
    log_file = os.path.join(output_folder, "_validation_log.json")

    # Load existing log
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            log = json.load(f)
    else:
        log = {
            "log_created": datetime.now().isoformat(),
            "skipped_patents": [],
            "error_summary": {}
        }

    # Add entry
    log["skipped_patents"].append({
        "index": index,
        "lens_id": patent_data.get("lens_id"),
        "patent_number": patent_data.get("patent_number"),
        "title": patent_data.get("title", "")[:100],
        "errors": errors,
        "timestamp": datetime.now().isoformat()
    })

    # Update error summary
    for error in errors:
        error_type = error.split(":")[0]  # Get error category
        log["error_summary"][error_type] = log["error_summary"].get(error_type, 0) + 1

    log["last_updated"] = datetime.now().isoformat()
    log["total_skipped"] = len(log["skipped_patents"])

    # Save log
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def generate_batch_summary(
    parsed_entries: List[Dict[str, Any]],
    skipped: List[tuple[int, Dict[str, Any], List[str]]],
    start_index: int,
    end_index: int
) -> str:
    """
    Generate human-readable summary of batch parsing.

    Args:
        parsed_entries: Successfully parsed patents
        skipped: List of (index, patent_data, errors) for skipped patents
        start_index: Starting index
        end_index: Ending index

    Returns:
        Formatted summary string
    """
    total = end_index - start_index
    success = len(parsed_entries)
    skip_count = len(skipped)

    summary = f"""
{'='*80}
GOLD DATASET BATCH PARSING SUMMARY
{'='*80}

Index Range: {start_index} to {end_index-1} (inclusive)
Total Patents: {total}

✅ Successfully Parsed: {success}/{total} ({success/total*100:.1f}%)
⏭️  Skipped: {skip_count}/{total} ({skip_count/total*100:.1f}%)

"""

    # Quality metrics
    if parsed_entries:
        avg_nodes = sum(len(e.get("technology_nodes", [])) for e in parsed_entries) / success
        avg_rels = sum(len(e.get("relationships", [])) for e in parsed_entries) / success

        summary += f"""
Quality Metrics (Successfully Parsed):
  Average Nodes per Patent: {avg_nodes:.1f}
  Average Relationships per Patent: {avg_rels:.1f}
"""

    # Successfully parsed patents
    if parsed_entries:
        summary += f"\n{'='*80}\n"
        summary += "SUCCESSFULLY PARSED PATENTS:\n"
        summary += f"{'='*80}\n\n"

        for entry in parsed_entries:
            meta = entry.get("patent_metadata", {})
            nodes = len(entry.get("technology_nodes", []))
            rels = len(entry.get("relationships", []))
            signals = entry.get("innovation_signals", {})

            summary += f"✅ {meta.get('lens_id')}\n"
            summary += f"   Title: {meta.get('title', '')[:70]}...\n"
            summary += f"   Assignee: {meta.get('assignee')}\n"
            summary += f"   Nodes: {nodes}, Relationships: {rels}\n"
            summary += f"   Innovation: {signals.get('innovation_type')} | Maturity: {signals.get('maturity_level')}\n\n"

    # Skipped patents
    if skipped:
        summary += f"\n{'='*80}\n"
        summary += "SKIPPED PATENTS:\n"
        summary += f"{'='*80}\n\n"

        for idx, patent, errors in skipped:
            summary += f"⏭️  Index {idx}: {patent.get('lens_id')}\n"
            summary += f"   Title: {patent.get('title', '')[:70]}...\n"
            summary += f"   Reason: {'; '.join(errors[:2])}\n\n"

    summary += f"{'='*80}\n"

    return summary


if __name__ == "__main__":
    # Test validation function
    test_entry = {
        "patent_metadata": {
            "lens_id": "test-123",
            "abstract": "Test abstract"
        },
        "technology_nodes": [
            {"node_id": "tech_1", "name": "Tech 1"},
            {"node_id": "tech_2", "name": "Tech 2"},
            {"node_id": "tech_3", "name": "Tech 3"}
        ],
        "relationships": [
            {"subject": "tech_1", "object": "tech_2", "confidence": 0.9, "evidence": "Test evidence"},
            {"subject": "tech_2", "object": "tech_3", "confidence": 0.85, "evidence": "Test evidence 2"},
            {"subject": "tech_3", "object": "external_concept", "confidence": 0.8, "evidence": "Test evidence 3"}
        ],
        "innovation_signals": {
            "maturity_level": "emerging",
            "innovation_type": "breakthrough"
        }
    }

    is_valid, errors = validate_gold_entry(test_entry)
    print(f"Valid: {is_valid}")
    if errors:
        print(f"Errors: {errors}")
    else:
        print("✅ Entry passes all validation checks")
