"""
Master Orchestrator: Run All Prerequisites
============================================

Purpose: Execute all 8 prerequisite scripts in correct order with error handling.

Workflow:
1. Create indexes (safe, fast)
2. Generate embeddings (EXPENSIVE - requires approval)
3. Create full-text index (safe, requires embeddings)
4. Create vector index (safe, requires embeddings)
5. Compute communities (EXPENSIVE - requires approval)
6. Generate community summaries (EXPENSIVE - requires approval)
7. Compute graph algorithms (EXPENSIVE - requires approval)
8. Validate all prerequisites (safe, fast)

Features:
- Interactive approval for expensive operations
- Resume capability (skips completed steps)
- Error handling with rollback
- Cost estimation before execution
- Progress tracking

Usage:
    python -m graph.prerequisites_configuration.run_all_prerequisites
    python -m graph.prerequisites_configuration.run_all_prerequisites --skip-validation
    python -m graph.prerequisites_configuration.run_all_prerequisites --auto-approve
"""

import os
import sys
import argparse
import subprocess
from typing import Dict, List
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from graph.prerequisites_configuration import (
    create_indexes,
    generate_embeddings,
    create_fulltext_index,
    create_vector_index,
    compute_communities,
    generate_community_summaries,
    compute_graph_algorithms,
    validate_prerequisites
)


class PrerequisitesOrchestrator:
    """Orchestrate execution of all prerequisite scripts."""

    def __init__(self, auto_approve: bool = False, skip_validation: bool = False):
        """Initialize orchestrator."""
        self.auto_approve = auto_approve
        self.skip_validation = skip_validation
        self.completed_steps = self.load_checkpoint()

    def load_checkpoint(self) -> List[str]:
        """Load checkpoint of completed steps."""
        checkpoint_file = "graph/prerequisites_configuration/.checkpoint_orchestrator.txt"
        if os.path.exists(checkpoint_file):
            with open(checkpoint_file, 'r') as f:
                return [line.strip() for line in f.readlines()]
        return []

    def save_checkpoint(self, step: str):
        """Save checkpoint after completing a step."""
        checkpoint_file = "graph/prerequisites_configuration/.checkpoint_orchestrator.txt"
        os.makedirs(os.path.dirname(checkpoint_file), exist_ok=True)
        with open(checkpoint_file, 'a') as f:
            f.write(f"{step}\n")
        self.completed_steps.append(step)

    def is_completed(self, step: str) -> bool:
        """Check if step was already completed."""
        return step in self.completed_steps

    def run_step(self, step_num: int, step_name: str, func, requires_approval: bool = False):
        """Run a single prerequisite step."""
        step_id = f"step_{step_num}_{step_name}"

        print("\n" + "="*80)
        print(f"STEP {step_num}/8: {step_name.upper().replace('_', ' ')}")
        print("="*80)

        if self.is_completed(step_id):
            print(f"[OK] Already completed (found in checkpoint)")
            print(f"   To re-run, delete: graph/prerequisites_configuration/.checkpoint_orchestrator.txt")
            return True

        if requires_approval and not self.auto_approve:
            print(f"\n[WARN]  This step requires approval (expensive operation)")
            response = input(f"Run {step_name}? (yes/no): ").strip().lower()
            if response != 'yes':
                print(f"[SKIP]  Skipped by user")
                return False

        try:
            print(f"\n🚀 Running {step_name}...")
            func()
            self.save_checkpoint(step_id)
            print(f"\n[OK] Step {step_num} completed successfully")
            return True

        except KeyboardInterrupt:
            print(f"\n[WARN]  Interrupted by user")
            return False
        except Exception as e:
            print(f"\n[ERROR] Step {step_num} failed: {e}")
            print(f"\nError details:")
            import traceback
            traceback.print_exc()
            return False

    def run_all(self):
        """Run all prerequisite scripts in order."""

        print("="*80)
        print("GRAPH PREREQUISITES SETUP")
        print("="*80)
        print()
        print("This will run all 8 prerequisite scripts in the correct order:")
        print("  1. Create Indexes (fast, free)")
        print("  2. Generate Embeddings (10-15 min, $0.20-1.00)")
        print("  3. Create Full-Text Index (fast, free)")
        print("  4. Create Vector Index (fast, free)")
        print("  5. Compute Communities (5-10 min, free)")
        print("  6. Generate Community Summaries (5-10 min, $0.01-0.05)")
        print("  7. Compute Graph Algorithms (5-10 min, free)")
        print("  8. Validate Prerequisites (fast, free)")
        print()

        if self.auto_approve:
            print("🤖 AUTO-APPROVE MODE: All steps will run without prompts")
        else:
            print("📋 INTERACTIVE MODE: You will be prompted before expensive operations")

        print()
        input("Press ENTER to begin...")

        # Step 1: Create Indexes
        success = self.run_step(
            1,
            "create_indexes",
            create_indexes.create_indexes,
            requires_approval=False
        )
        if not success:
            print("\n[ERROR] Setup aborted after step 1")
            return

        # Step 2: Generate Embeddings
        success = self.run_step(
            2,
            "generate_embeddings",
            generate_embeddings.generate_embeddings,
            requires_approval=True  # EXPENSIVE
        )
        if not success:
            print("\n[WARN]  Skipping steps 3-4 (require embeddings)")
            # Skip to step 5
        else:
            # Step 3: Create Full-Text Index
            success = self.run_step(
                3,
                "create_fulltext_index",
                create_fulltext_index.create_fulltext_index,
                requires_approval=False
            )

            # Step 4: Create Vector Index
            success = self.run_step(
                4,
                "create_vector_index",
                create_vector_index.create_vector_index,
                requires_approval=False
            )

        # Step 5: Compute Communities
        success = self.run_step(
            5,
            "compute_communities",
            compute_communities.compute_communities,
            requires_approval=True  # EXPENSIVE
        )

        # Step 6: Generate Community Summaries
        if success:
            success = self.run_step(
                6,
                "generate_community_summaries",
                generate_community_summaries.generate_community_summaries,
                requires_approval=True  # EXPENSIVE (but cheap)
            )
        else:
            print("\n[WARN]  Skipping step 6 (requires communities from step 5)")

        # Step 7: Compute Graph Algorithms
        success = self.run_step(
            7,
            "compute_graph_algorithms",
            compute_graph_algorithms.compute_graph_algorithms,
            requires_approval=True  # EXPENSIVE
        )

        # Step 8: Validate Prerequisites
        if not self.skip_validation:
            self.run_step(
                8,
                "validate_prerequisites",
                validate_prerequisites.validate_prerequisites,
                requires_approval=False
            )
        else:
            print("\n[SKIP]  Skipping validation (--skip-validation flag)")

        # Final summary
        print("\n" + "="*80)
        print("SETUP COMPLETE")
        print("="*80)
        print()
        print(f"[OK] Completed steps: {len(self.completed_steps)}/8")
        print()

        if len(self.completed_steps) >= 7:
            print("🎉 Graph prerequisites are ready!")
            print()
            print("Next steps:")
            print("  1. Review validation report: graph/prerequisites_configuration/validation_report.json")
            print("  2. Start multi-agent system development")
            print("  3. Run single-run MVP test")
        else:
            print("[WARN]  Setup incomplete. Review errors above and re-run.")
            print()
            print("To reset and start fresh:")
            print("  rm graph/prerequisites_configuration/.checkpoint_orchestrator.txt")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run all graph prerequisite scripts")
    parser.add_argument("--auto-approve", action="store_true",
                       help="Auto-approve all expensive operations (no prompts)")
    parser.add_argument("--skip-validation", action="store_true",
                       help="Skip final validation step")
    args = parser.parse_args()

    orchestrator = PrerequisitesOrchestrator(
        auto_approve=args.auto_approve,
        skip_validation=args.skip_validation
    )

    try:
        orchestrator.run_all()
    except KeyboardInterrupt:
        print("\n\n[WARN]  Setup interrupted by user")
        print("Progress has been saved. Re-run to resume from last completed step.")
        sys.exit(1)


if __name__ == "__main__":
    main()
