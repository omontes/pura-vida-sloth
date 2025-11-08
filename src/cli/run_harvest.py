#!/usr/bin/env python
"""
Harvest Launcher - Convenience script to run the orchestrator
=============================================================

Usage:
    python run_harvest.py --config configs/evtol_config.json
    python run_harvest.py --config configs/evtol_config.json --dry-run
    python run_harvest.py --config configs/evtol_config.json --resume
"""

import sys
from src.core.orchestrator import main

if __name__ == "__main__":
    main()
