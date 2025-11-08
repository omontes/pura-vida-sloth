"""
Merge Form 13F data from multiple quarters into single database directory.
Uses well-organized source folders with clear naming.
"""
import pandas as pd
from pathlib import Path
import shutil


def merge_quarters(output_dir: Path = Path('data/form13f')):
    """
    Merge Q1 and Q2 2025 data into database directory.

    Source folders:
      - data/form13f_dataset/form13f_march_april_may_2025/ (Q1 2025)
      - data/form13f_dataset/form13f_june_july_august_2025/ (Q2 2025)

    Output:
      - data/form13f/ (merged data for DuckDB)
    """
    # Define quarters to merge
    quarters = [
        Path('data/form13f_dataset/form13f_march_april_may_2025'),    # Q1 2025
        Path('data/form13f_dataset/form13f_june_july_august_2025')    # Q2 2025
    ]

    # TSV files to merge
    files = [
        'INFOTABLE.tsv',
        'SUBMISSION.tsv',
        'COVERPAGE.tsv',
        'SUMMARYPAGE.tsv',
        'SIGNATURE.tsv',
        'OTHERMANAGER.tsv',
        'OTHERMANAGER2.tsv'
    ]

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}\n")

    # Process each file
    for file in files:
        print(f"Merging {file}...")
        dfs = []

        for i, quarter_dir in enumerate(quarters):
            source_file = quarter_dir / file

            if not source_file.exists():
                print(f"  [SKIP] {quarter_dir.name}: file not found, skipping")
                continue

            # Read quarter data
            df = pd.read_csv(source_file, sep='\t', encoding='utf-8-sig', low_memory=False)
            dfs.append(df)
            print(f"  [OK] {quarter_dir.name}: {len(df):,} records")

        if not dfs:
            print(f"  [ERROR] No data found for {file}\n")
            continue

        # Concatenate all quarters
        merged_df = pd.concat(dfs, ignore_index=True)

        # Save merged file
        output_file = output_dir / file
        merged_df.to_csv(output_file, sep='\t', index=False, encoding='utf-8-sig')

        print(f"  [SAVED] {len(merged_df):,} total records to {output_file}\n")

    # Copy metadata and readme from Q2 folder
    metadata_src = quarters[1] / 'FORM13F_metadata.json'
    readme_src = quarters[1] / 'FORM13F_readme.htm'

    if metadata_src.exists():
        shutil.copy(metadata_src, output_dir / 'FORM13F_metadata.json')
        print("[OK] Copied metadata file")

    if readme_src.exists():
        shutil.copy(readme_src, output_dir / 'FORM13F_readme.htm')
        print("[OK] Copied readme file")

    print("\n" + "="*60)
    print("MERGE COMPLETE!")
    print("="*60)
    print(f"\nMerged data saved to: {output_dir.absolute()}")
    print("\nNext steps:")
    print("1. Rebuild DuckDB database:")
    print("   python -c \"from src.utils.duckdb_manager import Form13FDatabase; db = Form13FDatabase(); db.initialize(force_reload=True); db.close()\"")
    print("\n2. Re-run Form 13F downloader:")
    print("   python -m src.core.orchestrator --config configs/evtol_config.json")


if __name__ == "__main__":
    merge_quarters()
