#!/usr/bin/env python3
"""
Analyze harvested data for Phase 1 documentation.

This script scans the data/{industry}/ directory and generates statistics
about collected documents from all 14+ data sources.

Usage:
    python src/downloaders/analyze_harvest_data.py --industry evtol
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple
import argparse


# Intelligence Layer mapping
LAYER_MAPPING = {
    # Layer 1: Innovation Signals (18-24 months ahead)
    "lens_patents": 1,
    "patents": 1,
    "lens_scholarly": 1,
    "research_papers": 1,
    "github_activity": 1,
    "academic_citations": 1,
    "citation_tracker": 1,

    # Layer 2: Market Formation (12-18 months ahead)
    "government_contracts": 2,
    "regulatory_docs": 2,
    "regulatory": 2,
    "job_postings": 2,
    "job_market": 2,

    # Layer 3: Financial Reality (0-6 months, real-time)
    "sec_filings": 3,
    "earnings_calls": 3,
    "earnings": 3,
    "insider_transactions": 3,
    "insider_trading": 3,
    "form13f_institutional_holdings": 3,
    "institutional_holdings": 3,
    "company_fundamentals": 3,
    "stock_market": 3,
    "stock_data": 3,

    # Layer 4: Narrative (Lagging indicator)
    "news_sentiment": 4,
    "press_releases": 4,
}

# Directories to exclude (not data sources)
EXCLUDE_DIRS = {
    "companies",
    "technologies",
    "PROCESSED_DOCUMENTS",
    "_consolidated",
    "__pycache__",
}


def get_layer_name(layer_num: int) -> str:
    """Get human-readable layer name."""
    layer_names = {
        1: "Layer 1: Innovation",
        2: "Layer 2: Market Formation",
        3: "Layer 3: Financial Reality",
        4: "Layer 4: Narrative",
    }
    return layer_names.get(layer_num, "Unknown")


def count_json_records(json_path: Path) -> int:
    """Count records in a JSON file."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

            # Handle different JSON structures
            if isinstance(data, list):
                return len(data)
            elif isinstance(data, dict):
                # Check common keys for record lists
                for key in ['data', 'results', 'documents', 'records', 'items']:
                    if key in data and isinstance(data[key], list):
                        return len(data[key])
                # If it's a dict with metadata, try to extract count
                if 'total' in data:
                    return data['total']
                if 'count' in data:
                    return data['count']
                # Otherwise count as 1 record
                return 1
            else:
                return 0
    except Exception as e:
        print(f"  Warning: Could not parse {json_path.name}: {e}")
        return 0


def get_directory_size(directory: Path) -> str:
    """Calculate total size of files in directory."""
    total_size = 0
    for file in directory.rglob('*'):
        if file.is_file():
            total_size += file.stat().st_size

    # Convert to human-readable format
    if total_size < 1024:
        return f"{total_size} B"
    elif total_size < 1024 ** 2:
        return f"{total_size / 1024:.1f} KB"
    elif total_size < 1024 ** 3:
        return f"{total_size / (1024 ** 2):.1f} MB"
    else:
        return f"{total_size / (1024 ** 3):.2f} GB"


def analyze_source_directory(source_dir: Path) -> Dict:
    """Analyze a single source directory."""
    source_name = source_dir.name

    # Check for metadata.json first
    metadata_path = source_dir / "metadata.json"
    stats = {
        "name": source_name,
        "layer": LAYER_MAPPING.get(source_name, 0),
        "files": 0,
        "records": 0,
        "file_types": set(),
        "size": get_directory_size(source_dir),
        "has_metadata": False,
    }

    # Count all files (excluding hidden and log files for display)
    all_files = [f for f in source_dir.rglob('*') if f.is_file()]
    stats["files"] = len(all_files)

    # Get file types
    for file in all_files:
        if file.suffix:
            stats["file_types"].add(file.suffix[1:].upper())

    # Try to read metadata.json for record counts
    if metadata_path.exists():
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                stats["has_metadata"] = True

                # Extract record count from metadata
                # Different sources use different keys
                if 'total_documents' in metadata:
                    stats["records"] = metadata['total_documents']
                elif 'total' in metadata:
                    stats["records"] = metadata['total']
                elif 'count' in metadata:
                    stats["records"] = metadata['count']
                elif 'total_records' in metadata:
                    stats["records"] = metadata['total_records']
                elif 'stats' in metadata and isinstance(metadata['stats'], dict):
                    if 'total' in metadata['stats']:
                        stats["records"] = metadata['stats']['total']
                    elif 'count' in metadata['stats']:
                        stats["records"] = metadata['stats']['count']

                print(f"  [OK] Found metadata.json with {stats['records']} records")
        except Exception as e:
            print(f"  Warning: Could not parse metadata.json: {e}")

    # If no metadata or no record count, try to count JSON records
    if stats["records"] == 0:
        json_files = list(source_dir.glob("*.json"))
        # Exclude metadata.json and log files
        json_files = [f for f in json_files if f.name not in ['metadata.json', 'checkpoint.json'] and not f.name.startswith('.')]

        if json_files:
            print(f"  Counting records from {len(json_files)} JSON files...")
            for json_file in json_files:
                stats["records"] += count_json_records(json_file)

    return stats


def generate_markdown_table(results: List[Dict]) -> str:
    """Generate markdown table from analysis results."""

    # Sort by layer, then by name
    results.sort(key=lambda x: (x["layer"], x["name"]))

    # Group by layer
    layers = {}
    for result in results:
        layer = result["layer"]
        if layer not in layers:
            layers[layer] = []
        layers[layer].append(result)

    # Generate table
    table = []
    table.append("| Intelligence Layer | Data Source | Files | Records/Docs | File Types | Size | Status |")
    table.append("|-------------------|-------------|-------|--------------|------------|------|--------|")

    for layer_num in sorted(layers.keys()):
        layer_results = layers[layer_num]
        layer_name = get_layer_name(layer_num)

        for i, result in enumerate(layer_results):
            # Format file types
            file_types = ", ".join(sorted(result["file_types"])) if result["file_types"] else "—"

            # Determine status
            if result["files"] == 0:
                status = "Empty"
            elif result["files"] < 5:
                status = "Minimal"
            else:
                status = "Active"

            # First row of layer shows layer name
            if i == 0:
                table.append(f"| **{layer_name}** | {result['name']} | {result['files']} | {result['records']} | {file_types} | {result['size']} | {status} |")
            else:
                table.append(f"| | {result['name']} | {result['files']} | {result['records']} | {file_types} | {result['size']} | {status} |")

    return "\n".join(table)


def generate_summary_stats(results: List[Dict]) -> Dict:
    """Generate summary statistics."""
    total_files = sum(r["files"] for r in results)
    total_records = sum(r["records"] for r in results)
    active_sources = len([r for r in results if r["files"] >= 5])
    total_sources = len(results)

    # Layer breakdown
    layer_stats = {}
    for result in results:
        layer = result["layer"]
        if layer not in layer_stats:
            layer_stats[layer] = {"sources": 0, "files": 0, "records": 0}
        layer_stats[layer]["sources"] += 1
        layer_stats[layer]["files"] += result["files"]
        layer_stats[layer]["records"] += result["records"]

    return {
        "total_sources": total_sources,
        "active_sources": active_sources,
        "total_files": total_files,
        "total_records": total_records,
        "layer_stats": layer_stats,
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze harvested data for Phase 1 documentation")
    parser.add_argument("--industry", default="evtol", help="Industry name (default: evtol)")
    parser.add_argument("--output", help="Output markdown file (optional)")
    args = parser.parse_args()

    # Find data directory
    data_dir = Path("data") / args.industry
    if not data_dir.exists():
        print(f"Error: Data directory not found: {data_dir}")
        return

    print(f"Analyzing data collection for industry: {args.industry}")
    print(f"Data directory: {data_dir}")
    print("=" * 70)

    # Analyze each source directory
    results = []
    for source_dir in sorted(data_dir.iterdir()):
        if not source_dir.is_dir():
            continue
        if source_dir.name in EXCLUDE_DIRS:
            print(f"Skipping: {source_dir.name} (excluded)")
            continue

        print(f"\nAnalyzing: {source_dir.name}")
        stats = analyze_source_directory(source_dir)
        results.append(stats)
        print(f"  Files: {stats['files']}, Records: {stats['records']}, Size: {stats['size']}")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)

    # Generate summary
    summary = generate_summary_stats(results)
    print(f"\nTotal Sources: {summary['total_sources']}")
    print(f"Active Sources (>=5 files): {summary['active_sources']}")
    print(f"Total Files: {summary['total_files']}")
    print(f"Total Records: {summary['total_records']}")

    print("\nLayer Breakdown:")
    for layer_num in sorted(summary['layer_stats'].keys()):
        layer_name = get_layer_name(layer_num)
        stats = summary['layer_stats'][layer_num]
        print(f"  {layer_name}: {stats['sources']} sources, {stats['files']} files, {stats['records']} records")

    # Generate markdown table
    print("\n" + "=" * 70)
    print("MARKDOWN TABLE FOR DOCUMENTATION")
    print("=" * 70)
    print()
    table = generate_markdown_table(results)
    print(table)

    # Optionally save to file
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Phase 1 Data Collection Analysis\n\n")
            f.write(f"## Industry: {args.industry.upper()}\n\n")
            f.write("### Summary Statistics\n\n")
            f.write(f"- **Total Sources**: {summary['total_sources']}\n")
            f.write(f"- **Active Sources**: {summary['active_sources']}\n")
            f.write(f"- **Total Files**: {summary['total_files']}\n")
            f.write(f"- **Total Records**: {summary['total_records']}\n\n")
            f.write("### Detailed Breakdown\n\n")
            f.write(table)
        print(f"\n[OK] Markdown output saved to: {output_path}")


if __name__ == "__main__":
    main()
