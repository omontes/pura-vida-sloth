"""
Shared infrastructure for multi-agent system.

This module provides shared utilities, clients, and query modules
used across all 12 agents in the Hype Cycle analysis system.
"""

from src.agents.shared.openai_client import get_structured_llm, get_chat_llm
from src.agents.shared.constants import (
    TEMPORAL_WINDOWS,
    LAYER_WEIGHTS,
    THRESHOLDS,
    PHASE_NAMES,
    SCORING_RANGES,
)

__all__ = [
    "get_structured_llm",
    "get_chat_llm",
    "TEMPORAL_WINDOWS",
    "LAYER_WEIGHTS",
    "THRESHOLDS",
    "PHASE_NAMES",
    "SCORING_RANGES",
]
