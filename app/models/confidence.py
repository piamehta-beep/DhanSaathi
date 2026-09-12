"""Confidence / uncertainty quantification (spec Section 5.6).

This module currently implements the simulation-output bootstrap band
(Section 5.6, "Simulation outputs"). CBS-level confidence (recommendation
bootstrap, system-level overrides) is added in Milestone 3/4 once the
recommender and survival model exist to produce a CBS distribution.
"""

from __future__ import annotations

import numpy as np

B_DEFAULT = 500


def bootstrap_shortfall_ci(shortfall_any: np.ndarray, b: int = B_DEFAULT, seed: int | None = None) -> dict:
    """80% CI on P(shortfall within 12 months) via resampling simulated paths."""
    rng = np.random.default_rng(seed)
    n = len(shortfall_any)
    stats = np.empty(b)
    for i in range(b):
        sample = rng.choice(shortfall_any, size=n, replace=True)
        stats[i] = sample.mean()

    p10 = float(np.percentile(stats, 10))
    p90 = float(np.percentile(stats, 90))
    return {"p10": round(p10, 4), "p90": round(p90, 4)}


MIN_DATA_MONTHS_FOR_CONFIDENCE = 3
CI_WIDTH_LOW = 0.50
CI_WIDTH_MEDIUM = 0.30


def cbs_confidence(
    cbs_score: float,
    p_shortfall_ci: dict,
    data_months: int,
    no_action_cbs: float = 0.0,
) -> dict:
    """Confidence in a CBS, and whether it is firm enough to act on.

    Uncertainty in CBS is dominated by uncertainty in the simulated shortfall
    probability, which feeds both the affordability and distress-penalty
    terms. The bootstrap band on that probability is therefore propagated onto
    CBS through the weights that carry it.

    The system-level overrides matter more than the band itself: too little
    history, or a CBS interval that overlaps doing nothing, means the honest
    answer is "I don't know yet" rather than a recommendation.
    """
    if data_months < MIN_DATA_MONTHS_FOR_CONFIDENCE:
        return {
            "confidence_level": "insufficient_data",
            "confidence_interval": {
                "cbs_low": None, "cbs_high": None,
                "method": "n/a", "ci_width_ratio": None,
            },
            "act": False,
        }

    # W_AFFORDABILITY (0.25) and W_DISTRESS_PENALTY (0.10) both move with the
    # shortfall probability, in the same direction, so their weights add.
    sensitivity = 0.25 + 0.10
    half_width = sensitivity * (p_shortfall_ci["p90"] - p_shortfall_ci["p10"]) / 2.0
    cbs_low = cbs_score - half_width
    cbs_high = cbs_score + half_width

    denominator = max(abs(cbs_score), 1e-6)
    ci_width_ratio = (cbs_high - cbs_low) / denominator

    if ci_width_ratio > CI_WIDTH_LOW:
        level = "low"
    elif ci_width_ratio > CI_WIDTH_MEDIUM:
        level = "medium"
    else:
        level = "high"

    # If the plausible range for this product reaches down to doing nothing,
    # the evidence does not distinguish them and the system should not act.
    if cbs_low <= no_action_cbs:
        level = "insufficient_confidence"

    return {
        "confidence_level": level,
        "confidence_interval": {
            "cbs_low": round(cbs_low, 4),
            "cbs_high": round(cbs_high, 4),
            "method": f"bootstrap_b{B_DEFAULT}_propagated",
            "ci_width_ratio": round(ci_width_ratio, 4),
        },
        "act": level != "insufficient_confidence",
    }
