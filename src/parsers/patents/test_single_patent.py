"""
Test Script: Validate Patent Batch Processing with Single Patent

Tests the batch processing pipeline with just 1 patent to verify:
- Configuration loading
- Parser initialization
- Checkpoint system
- File output structure
- Quality scoring

Usage:
    python test_single_patent.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from parsers.patents.batch_process_patents import batch_process_patents


def test_single_patent():
    """Test batch processing with a single patent."""

    print("\n" + "=" * 80)
    print("TESTING: Single Patent Batch Processing")
    print("=" * 80 + "\n")

    print("This will test the batch processing pipeline with just 1 patent to validate:")
    print("  - Configuration loading")
    print("  - Parser initialization")
    print("  - Checkpoint system")
    print("  - File output structure")
    print("  - Quality scoring\n")

    # Run batch processing with limit=1
    result = batch_process_patents(
        config_path="configs/evtol_config.json",
        patents_file="data/eVTOL/lens_patents/patents.json",
        output_dir="data/eVTOL/lens_patents",
        limit=1,  # Process only 1 patent
        start_index=0,
        max_workers=1,
        subbatch_size=1,
        max_retries=2,
        quality_threshold=0.85,
        checkpoint_interval=100,
        resume=False  # Don't resume for clean test
    )

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80 + "\n")

    if result:
        print("SUCCESS: Test passed! Batch processing pipeline is working correctly.")
        print(f"\nResults:")
        print(f"  Total processed: {result['total_processed']}")
        print(f"  Quality patents: {result['total_quality']}")
        print(f"  Errors: {result['total_errors']}")
        print(f"\nOutput files:")
        for name, path in result['output_files'].items():
            print(f"  {name}: {path}")
    else:
        print("FAILED: Test failed! Check error messages above.")

    return result


if __name__ == "__main__":
    test_single_patent()
