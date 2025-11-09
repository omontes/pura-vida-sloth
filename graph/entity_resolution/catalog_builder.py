"""
Phase 5: Catalog Validation & Output
Validates merged catalog and generates final output
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Set
from collections import defaultdict

from .schemas import CanonicalTechnology, TechnologyCatalog, ValidationReport
from .config import EntityResolutionConfig, get_pipeline_config


class CatalogBuilder:
    """Validates and builds final technology catalog."""

    def __init__(self, config: EntityResolutionConfig):
        """
        Initialize catalog builder.

        Args:
            config: Entity resolution configuration
        """
        self.config = config
        self.pipeline_config = get_pipeline_config()

    def validate_catalog(self, catalog: List[CanonicalTechnology],
                        original_mention_count: int) -> ValidationReport:
        """
        Validate catalog for data quality issues.

        Checks:
        1. No duplicate canonical names
        2. All variants mapped to exactly one canonical
        3. Coverage of original mentions
        4. Quality metrics

        Args:
            catalog: List of CanonicalTechnology objects
            original_mention_count: Number of original unique mentions

        Returns:
            ValidationReport object
        """
        print(f"\nValidating catalog...")

        warnings = []
        duplicate_canonical_names = []
        orphaned_variants = []

        # Check 1: Duplicate canonical names
        canonical_names = [tech.canonical_name for tech in catalog]
        name_counts = defaultdict(int)
        for name in canonical_names:
            name_counts[name] += 1

        duplicates = [name for name, count in name_counts.items() if count > 1]
        if duplicates:
            duplicate_canonical_names = duplicates
            warnings.append(f"Found {len(duplicates)} duplicate canonical names")

        # Check 2: All variants map to exactly one canonical
        variant_mapping = defaultdict(list)  # variant -> [canonical_names]
        for tech in catalog:
            for variant in tech.variants:
                variant_mapping[variant.name].append(tech.canonical_name)

        orphaned = [v for v, canonicals in variant_mapping.items() if len(canonicals) != 1]
        if orphaned:
            orphaned_variants = orphaned
            warnings.append(f"Found {len(orphaned)} variants with != 1 canonical mapping")

        # Check 3: Coverage
        total_variants = sum(len(tech.variants) for tech in catalog)
        coverage_percentage = (total_variants / original_mention_count * 100) if original_mention_count > 0 else 0.0

        if coverage_percentage < 95.0:
            warnings.append(f"Low coverage: {coverage_percentage:.1f}% < 95%")

        # Quality metrics
        quality_metrics = {
            "total_canonical_technologies": len(catalog),
            "total_variants": total_variants,
            "avg_variants_per_canonical": total_variants / len(catalog) if catalog else 0.0,
            "coverage_percentage": coverage_percentage,
            "duplicate_check": "PASS" if not duplicates else "FAIL",
            "variant_mapping_check": "PASS" if not orphaned else "FAIL",
            "coverage_check": "PASS" if coverage_percentage >= 95.0 else "FAIL"
        }

        # Determine if validation passed
        passed = (len(duplicate_canonical_names) == 0 and
                 len(orphaned_variants) == 0 and
                 coverage_percentage >= 95.0)

        report = ValidationReport(
            total_canonical_technologies=len(catalog),
            total_variants=total_variants,
            total_source_documents=0,  # Will be updated if we track source docs
            coverage_percentage=coverage_percentage,
            duplicate_canonical_names=duplicate_canonical_names,
            orphaned_variants=orphaned_variants,
            quality_metrics=quality_metrics,
            warnings=warnings,
            passed=passed
        )

        return report

    def build_final_catalog(self, catalog: List[CanonicalTechnology]) -> TechnologyCatalog:
        """
        Build final technology catalog output.

        Args:
            catalog: List of CanonicalTechnology objects

        Returns:
            TechnologyCatalog object
        """
        print(f"\nBuilding final catalog...")

        # Sort by canonical name
        sorted_catalog = sorted(catalog, key=lambda x: x.canonical_name)

        # Calculate totals
        total_variants = sum(len(tech.variants) for tech in catalog)

        final_catalog = TechnologyCatalog(
            version="2.0",
            generated_at=datetime.utcnow().isoformat() + "Z",
            industry=self.config.config.get('industry_name', self.config.industry),
            total_canonical_technologies=len(catalog),
            total_variants=total_variants,
            technologies=sorted_catalog
        )

        return final_catalog

    def run(self, catalog: List[CanonicalTechnology],
           original_mention_count: int) -> TechnologyCatalog:
        """
        Run Phase 5: Validate and build final catalog.

        Args:
            catalog: Merged catalog from Phase 4
            original_mention_count: Number of original unique mentions

        Returns:
            Final TechnologyCatalog object
        """
        print(f"\n{'='*80}")
        print("PHASE 5: CATALOG VALIDATION & OUTPUT")
        print(f"{'='*80}")

        # Validate catalog
        validation_report = self.validate_catalog(catalog, original_mention_count)

        # Save validation report
        self.save_validation_report(validation_report)

        # Print validation results
        self._print_validation(validation_report)

        if not validation_report.passed:
            print("\n(\!\!)  WARNING: Validation failed! Review issues before using catalog.")

        # Build final catalog
        final_catalog = self.build_final_catalog(catalog)

        # Save final catalog
        self.save_final_catalog(final_catalog)

        # Print summary
        self._print_summary(final_catalog)

        return final_catalog

    def save_validation_report(self, report: ValidationReport):
        """Save validation report to JSON file."""
        output_dir = self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / self.pipeline_config['output_files']['validation_report']

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)

        print(f"  Saved validation report to: {output_file}")

    def save_final_catalog(self, catalog: TechnologyCatalog):
        """Save final catalog to data directory."""
        # Save to data/eVTOL/technologies/
        output_dir = self.config.data_dir / "technologies"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / self.pipeline_config['output_files']['final_catalog']

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(catalog.model_dump(), f, indent=2, ensure_ascii=False)

        print(f"\n  Saved final catalog to: {output_file}")

    def _print_validation(self, report: ValidationReport):
        """Print validation results."""
        print(f"\nValidation Results:")
        print(f"  Status: {'v PASS' if report.passed else 'x FAIL'}")
        print(f"  Coverage: {report.coverage_percentage:.1f}%")

        if report.duplicate_canonical_names:
            print(f"\n  (\!\!)  Duplicate canonical names: {len(report.duplicate_canonical_names)}")
            for name in report.duplicate_canonical_names[:5]:
                print(f"    - {name}")
            if len(report.duplicate_canonical_names) > 5:
                print(f"    ... and {len(report.duplicate_canonical_names) - 5} more")

        if report.orphaned_variants:
            print(f"\n  (\!\!)  Orphaned variants: {len(report.orphaned_variants)}")
            for variant in report.orphaned_variants[:5]:
                print(f"    - {variant}")
            if len(report.orphaned_variants) > 5:
                print(f"    ... and {len(report.orphaned_variants) - 5} more")

        if report.warnings:
            print(f"\n  Warnings:")
            for warning in report.warnings:
                print(f"    - {warning}")

    def _print_summary(self, catalog: TechnologyCatalog):
        """Print summary statistics."""
        print(f"\n{'='*80}")
        print("PHASE 5 SUMMARY")
        print(f"{'='*80}")

        print(f"Final Catalog:")
        print(f"  Version: {catalog.version}")
        print(f"  Generated: {catalog.generated_at}")
        print(f"  Industry: {catalog.industry}")
        print(f"  Total canonical technologies: {catalog.total_canonical_technologies}")
        print(f"  Total variants: {catalog.total_variants}")
        print(f"  Avg variants per canonical: {catalog.total_variants / catalog.total_canonical_technologies:.1f}")

        # Domain distribution
        domain_counts = defaultdict(int)
        for tech in catalog.technologies:
            domain = tech.domain or "Unknown"
            domain_counts[domain] += 1

        print(f"\nDomain distribution:")
        for domain, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            percentage = (count / catalog.total_canonical_technologies * 100)
            print(f"  {domain}: {count} ({percentage:.1f}%)")

        print(f"\n{'='*80}")


def load_merged_catalog(config: EntityResolutionConfig, filename: str) -> List[CanonicalTechnology]:
    """Load merged catalog from JSON file."""
    file_path = config.output_dir / filename

    if not file_path.exists():
        raise FileNotFoundError(f"Merged catalog file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return [CanonicalTechnology(**item) for item in data]
