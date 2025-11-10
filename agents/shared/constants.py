"""
Fixed constants for first-run multi-agent system (deterministic MVP).

All temporal windows, weights, thresholds, and configuration values are
hardcoded here for reproducibility. Future multi-run consensus system
will vary these parameters across runs.
"""

from datetime import datetime, timedelta
from typing import Dict, List


# =============================================================================
# TEMPORAL WINDOWS (Fixed for First Run)
# =============================================================================

# Current date for first run (can be overridden for testing)
# Use fixed date for reproducibility instead of datetime.now()
ANALYSIS_DATE = "2025-01-09"  # Date from the specification document

TEMPORAL_WINDOWS = {
    "innovation": {
        "days": 730,  # 2 years for patents, papers, GitHub
        "start_date": "2023-01-01",
        "end_date": "2025-01-01",
        "description": "Innovation signals leading 18-24 months",
    },
    "adoption": {
        "days": 540,  # 18 months for government contracts, regulations
        "start_date": "2023-07-01",
        "end_date": "2025-01-01",
        "description": "Market formation leading 12-18 months",
    },
    "narrative": {
        "days": 180,  # 6 months for news sentiment (changed from 3 months to match some agents)
        "start_date": "2024-07-01",
        "end_date": "2025-01-01",
        "description": "Media narrative (lagging indicator)",
    },
    "risk": {
        "days": 180,  # 6 months for SEC filings, insider trading
        "start_date": "2024-07-01",
        "end_date": "2025-01-01",
        "description": "Financial reality (coincident 0-6 months)",
    },
}


# =============================================================================
# LAYER WEIGHTS (Fixed for First Run)
# =============================================================================

LAYER_WEIGHTS = {
    "innovation": 0.30,  # 30% - Leading indicator
    "adoption": 0.35,    # 35% - Strongest signal (government validation)
    "narrative": 0.15,   # 15% - Lagging indicator (contrarian)
    "risk": 0.20,        # 20% - Current reality check
}

# Validate weights sum to 1.0
assert sum(LAYER_WEIGHTS.values()) == 1.0, "Layer weights must sum to 1.0"


# =============================================================================
# SCORING THRESHOLDS
# =============================================================================

THRESHOLDS = {
    # Patent scoring (Agent 2: Innovation)
    "patent_count_high": 50,          # 50+ patents in 2yr = 100 score
    "citation_count_high": 500,       # 500+ citations = 100 score
    "paper_count_high": 30,           # 30+ papers in 2yr = 100 score
    "github_repos_high": 10,          # 10+ active repos = 100 score

    # Adoption scoring (Agent 3)
    "contract_value_high": 100_000_000,  # $100M+ in contracts = 100 score
    "approval_count_high": 5,            # 5+ regulatory approvals = 100 score
    "revenue_companies_high": 3,         # 3+ companies with revenue = 100 score

    # Narrative scoring (Agent 4)
    "news_count_high": 100,              # 100+ articles in 6mo = 100 score
    "weighted_prominence_high": 50,      # Prominence score 50+ = 100 score

    # Risk scoring (Agent 5)
    "risk_mention_count_high": 30,       # 30+ risk mentions = 100 score
    "insider_value_high": 10_000_000,    # $10M insider trading = significant

    # Quality filters
    "min_quality_score": 0.85,           # Document quality threshold
    "min_evidence_confidence": 0.75,     # Evidence extraction confidence
    "min_relationship_strength": 0.6,    # Relationship strength threshold

    # Graph algorithm thresholds
    "high_pagerank_threshold": 0.01,     # Top 10% importance
    "high_degree_centrality": 50,        # Top 5% connectivity
    "high_betweenness_centrality": 100,  # Bridge node threshold

    # Hype detection (Agent 6)
    "hype_narrative_multiplier": 1.5,    # Narrative > 1.5x fundamentals = hype
    "high_hype_score": 70,               # 70+ = significant hype
    "high_risk_threshold": 60,           # 60+ risk score = concerning

    # Phase confidence (Agent 7)
    "min_phase_confidence": 0.50,        # Minimum acceptable confidence
    "high_phase_confidence": 0.80,       # High confidence threshold
}


# =============================================================================
# GARTNER HYPE CYCLE PHASES
# =============================================================================

PHASE_NAMES = {
    "TRIGGER": "Technology Trigger",
    "PEAK": "Peak of Inflated Expectations",
    "TROUGH": "Trough of Disillusionment",
    "SLOPE": "Slope of Enlightenment",
    "PLATEAU": "Plateau of Productivity",
}

PHASE_CODES = list(PHASE_NAMES.keys())


# =============================================================================
# SCORING RANGES
# =============================================================================

SCORING_RANGES = {
    "layer_scores": (0.0, 100.0),      # All layer scores: 0-100
    "hype_score": (0.0, 100.0),        # Hype score: 0-100
    "phase_confidence": (0.0, 1.0),    # Confidence: 0.0-1.0
    "chart_x": (0.0, 4.0),             # X coordinate (time to plateau)
    "chart_y": (0.0, 1.0),             # Y coordinate (expectations)
    "evidence_strength": (0.0, 1.0),   # Relationship strength
    "quality_score": (0.0, 1.0),       # Document quality
}


# =============================================================================
# HYBRID SEARCH CONFIGURATION
# =============================================================================

HYBRID_SEARCH_CONFIG = {
    "k_vector": 20,          # Top K from vector search
    "k_bm25": 20,            # Top K from BM25 search
    "vector_weight": 0.3,    # 30% vector, 70% BM25 for first run
    "k_final": 10,           # Final merged results
    "rrf_k": 60,             # Reciprocal Rank Fusion constant
}


# =============================================================================
# COMMUNITY CONFIGURATION
# =============================================================================

COMMUNITY_CONFIG = {
    "version": 1,                    # Use community_v1 for first run
    "version_str": "v1",             # String representation
    "algorithm": "Louvain",          # Louvain algorithm
    "resolution": 1.0,               # Balanced resolution
    "min_members": 5,                # Minimum community size
    "similarity_threshold": 0.8,     # For semantic community search
}


# =============================================================================
# AGENT-SPECIFIC CONFIGURATIONS
# =============================================================================

AGENT_TEMPERATURES = {
    "agent_02_innovation": 0.2,      # Factual reasoning
    "agent_03_adoption": 0.2,        # Factual reasoning
    "agent_04_narrative": 0.3,       # Slight creativity for sentiment nuance
    "agent_05_risk": 0.2,            # Factual reasoning
    "agent_08_analyst": 0.4,         # Creative executive summaries
}

# Agents that don't use LLMs (pure Python logic)
NON_LLM_AGENTS = [
    "agent_01_tech_discovery",       # Basic aggregation
    "agent_06_hype_scorer",          # Rule-based contradiction detection
    "agent_07_phase_detector",       # Decision tree classification
    "agent_09_ensemble",             # Weighted averaging
    "agent_10_chart_generator",      # Coordinate calculation
    "agent_11_evidence_compiler",    # Citation aggregation
    "agent_12_output_validator",     # Schema validation
]


# =============================================================================
# CONTRADICTION DETECTION RULES (Agent 6)
# =============================================================================

CONTRADICTION_RULES = {
    "narrative_exceeds_innovation": {
        "threshold": 1.5,
        "severity": "high",
        "description": "Narrative score > 1.5x innovation score (classic hype)",
    },
    "high_risk_high_narrative": {
        "risk_threshold": 60,
        "narrative_threshold": 80,
        "severity": "high",
        "description": "High risk + high narrative = Peak signal",
    },
    "over_connected_news_dominated": {
        "degree_threshold": 50,
        "news_ratio": 0.5,
        "severity": "high",
        "description": "High connectivity but news-dominated",
    },
    "bridge_node_conflict": {
        "betweenness_threshold": 100,
        "divergence_threshold": 0.3,
        "severity": "medium",
        "description": "Bridge technology with conflicting layer signals",
    },
    "adoption_without_innovation": {
        "adoption_threshold": 60,
        "innovation_threshold": 40,
        "severity": "medium",
        "description": "High adoption but low innovation = mature tech",
    },
    "low_fundamentals_high_hype": {
        "fundamentals_threshold": 40,
        "hype_threshold": 70,
        "severity": "high",
        "description": "Weak fundamentals + high hype = bubble risk",
    },
    "declining_innovation_rising_narrative": {
        "severity": "medium",
        "description": "Innovation declining but narrative growing (late Peak)",
    },
}


# =============================================================================
# OUTPUT VALIDATION RULES (Agent 12)
# =============================================================================

VALIDATION_RULES = {
    "required_fields": [
        "technology_id",
        "technology_name",
        "phase",
        "phase_code",
        "phase_confidence",
        "chart_x",
        "chart_y",
        "innovation_score",
        "adoption_score",
        "narrative_score",
        "risk_score",
    ],
    "score_ranges": SCORING_RANGES,
    "valid_phase_codes": PHASE_CODES,
    "min_citations_per_layer": 1,
    "max_retries": 3,
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_date_range(layer: str) -> tuple[str, str]:
    """
    Get fixed date range for a specific intelligence layer.

    Args:
        layer: One of 'innovation', 'adoption', 'narrative', 'risk'

    Returns:
        Tuple of (start_date, end_date) as ISO strings

    Example:
        >>> get_date_range("innovation")
        ('2023-01-01', '2025-01-01')
    """
    if layer not in TEMPORAL_WINDOWS:
        raise ValueError(f"Invalid layer: {layer}. Must be one of {list(TEMPORAL_WINDOWS.keys())}")

    window = TEMPORAL_WINDOWS[layer]
    return (window["start_date"], window["end_date"])


def get_days_back(layer: str) -> int:
    """
    Get number of days to look back for a specific layer.

    Args:
        layer: One of 'innovation', 'adoption', 'narrative', 'risk'

    Returns:
        Number of days to look back

    Example:
        >>> get_days_back("innovation")
        730
    """
    if layer not in TEMPORAL_WINDOWS:
        raise ValueError(f"Invalid layer: {layer}. Must be one of {list(TEMPORAL_WINDOWS.keys())}")

    return TEMPORAL_WINDOWS[layer]["days"]


def validate_score_range(score: float, score_type: str = "layer_scores") -> bool:
    """
    Validate that a score falls within the expected range.

    Args:
        score: Score value to validate
        score_type: Type of score (key in SCORING_RANGES)

    Returns:
        True if valid, False otherwise

    Example:
        >>> validate_score_range(85.5, "layer_scores")
        True
        >>> validate_score_range(150.0, "layer_scores")
        False
    """
    if score_type not in SCORING_RANGES:
        raise ValueError(f"Invalid score_type: {score_type}")

    min_val, max_val = SCORING_RANGES[score_type]
    return min_val <= score <= max_val
