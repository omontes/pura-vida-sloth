"""
Test Patent Downloader
======================
Tests for PQAI API-based patent downloader.

Validates:
- Industry-agnostic design (no hardcoded companies)
- Assignee-based search works
- Metadata format correct
- Checkpoint functionality
"""

from pathlib import Path
import json
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.downloaders.patents import PatentDownloader


def test_patent_download_industry_agnostic(tmp_path):
    """
    Test patent downloader with eVTOL config (industry-agnostic design).

    This test uses eVTOL companies but the downloader MUST work for ANY industry.
    """
    print("\n" + "=" * 60)
    print("Testing Patent Downloader (PQAI API)")
    print("=" * 60)

    # Test with ONE assignee only (fast test)
    test_assignees = {
        "JOBY": "Joby Aviation"  # Known to have patents
    }

    downloader = PatentDownloader(
        output_dir=tmp_path,
        start_date="2023-01-01",
        end_date="2025-12-31",
        assignees=test_assignees,
        limit=5,  # Only 5 patents for speed
        download_pdfs=False  # Skip PDFs for test speed
    )

    print(f"\nTest Config:")
    print(f"  Assignee: Joby Aviation")
    print(f"  Date Range: 2023-01-01 to 2025-12-31")
    print(f"  Limit: 5 patents")
    print(f"  Output: {tmp_path}")

    # Run download
    print("\nRunning patent download...")
    stats = downloader.download()

    # Validate stats format (REQUIRED keys)
    print("\nValidating stats format...")
    assert 'success' in stats, "Missing 'success' key"
    assert 'failed' in stats, "Missing 'failed' key"
    assert 'skipped' in stats, "Missing 'skipped' key"
    assert 'by_assignee' in stats, "Missing 'by_assignee' key"

    print(f"  [PASS] Stats format valid")
    print(f"  Success: {stats['success']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Skipped: {stats['skipped']}")

    # Validate at least some patents found
    assert stats['success'] >= 1, f"Should download at least 1 patent, got {stats['success']}"
    print(f"  [PASS] Downloaded {stats['success']} patent(s)")

    # Validate outputs exist
    print("\nValidating output files...")

    # Check patents.json
    patents_file = tmp_path / 'patents.json'
    assert patents_file.exists(), "patents.json not created"
    patents = json.loads(patents_file.read_text())
    assert len(patents) >= 1, "No patents in patents.json"
    print(f"  [PASS] patents.json exists ({len(patents)} patents)")

    # Check patents_metadata.json (REQUIRED format)
    metadata_file = tmp_path / 'patents_metadata.json'
    assert metadata_file.exists(), "patents_metadata.json not created"
    metadata = json.loads(metadata_file.read_text())
    assert len(metadata) >= 1, "No metadata entries"
    print(f"  [PASS] patents_metadata.json exists ({len(metadata)} entries)")

    # Validate metadata format
    print("\nValidating metadata format...")
    first_entry = metadata[0]
    required_fields = ['title', 'date', 'source', 'url', 'patent_number', 'assignee']
    for field in required_fields:
        assert field in first_entry, f"Missing required field: {field}"
    print(f"  [PASS] Metadata has all required fields")

    # Check checkpoint
    checkpoint_files = list(tmp_path.glob('.checkpoint_*.json'))
    assert len(checkpoint_files) == 1, f"Expected 1 checkpoint file, found {len(checkpoint_files)}"
    print(f"  [PASS] Checkpoint file created")

    # Sample patent data
    print("\nSample Patent Data:")
    sample = patents[0]
    print(f"  Patent Number: {sample.get('patent_number')}")
    print(f"  Title: {sample.get('title', 'N/A')[:80]}...")
    print(f"  Assignee: {sample.get('assignee')}")
    print(f"  Grant Date: {sample.get('grant_date')}")
    print(f"  URL: {sample.get('url')}")

    print("\n" + "=" * 60)
    print("[PASS] ALL TESTS PASSED")
    print("=" * 60)


def test_no_hardcoded_industry_data():
    """
    Ensure downloader has NO hardcoded industry-specific strings.

    CRITICAL: Patent downloader must work for ANY industry (not just eVTOL).
    """
    print("\n" + "=" * 60)
    print("Testing for Hardcoded Industry Data")
    print("=" * 60)

    source_code = Path('src/downloaders/patents.py').read_text()

    # These should NOT appear in downloader code (industry-specific terms)
    forbidden = [
        'Joby', 'Archer', 'Lilium', 'eVTOL',
        'flying car', 'air taxi', 'urban air mobility'
    ]

    print("\nChecking for forbidden terms...")
    violations = []
    for term in forbidden:
        if term in source_code:
            violations.append(term)
            print(f"  [FAIL] Found hardcoded term: '{term}'")

    if violations:
        raise AssertionError(
            f"Hardcoded industry terms found: {violations}. "
            f"Patent downloader must be industry-agnostic!"
        )

    print(f"  [PASS] No hardcoded industry terms found")
    print(f"  [PASS] Downloader is industry-agnostic")

    print("\n" + "=" * 60)
    print("[PASS] INDUSTRY-AGNOSTIC TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    import tempfile
    import shutil

    # Run test 1: Patent download
    print("\n\n" + "=" * 70)
    print(" PATENT DOWNLOADER TEST SUITE")
    print("=" * 70)

    # Create temp directory
    temp_dir = Path(tempfile.mkdtemp())
    print(f"\nTemp directory: {temp_dir}")

    try:
        # Test 1: Download patents
        test_patent_download_industry_agnostic(temp_dir)

        # Test 2: No hardcoded data
        test_no_hardcoded_industry_data()

        print("\n\n" + "=" * 70)
        print(" [SUCCESS] ALL TESTS PASSED SUCCESSFULLY!")
        print("=" * 70)
        print("\nPatent downloader is ready for production use.")
        print("Next step: Enable in config and run full harvest.")

    except Exception as e:
        print(f"\n\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            print(f"\nCleaned up temp directory: {temp_dir}")
