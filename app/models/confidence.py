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
