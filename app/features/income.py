"""Income features (spec Section 4.1).

All formulas operate on the trailing N=6 month window (or fewer if the
customer has less history).
"""

from __future__ import annotations

import numpy as np
from scipy import stats

from app.features.context import FeatureContext

WINDOW = 6


def compute_income_features(ctx: FeatureContext) -> dict:
    monthly = ctx.monthly.tail(WINDOW)
    if monthly.empty:
        return {
            "monthly_income_mean": 0.0, "monthly_income_std": 0.0, "income_cv": 0.0,
            "income_stability": 0.0, "income_trend_slope": 0.0, "income_regularity": 0.0,
        }

    income = monthly["income"].to_numpy()
    mu_i = float(np.mean(income))
    sigma_i = float(np.std(income, ddof=1)) if len(income) > 1 else 0.0
    cv_i = sigma_i / mu_i if mu_i > 0 else 0.0
    income_stability = 1 - min(cv_i, 1.0)

    if len(income) >= 2:
        slope, _, _, _, _ = stats.linregress(monthly["t"].to_numpy(), income)
    else:
        slope = 0.0

    txns = ctx.txns
    regularity = 0.0
    if not txns.empty:
        salary_txns = txns[(txns["type"] == "credit") & (txns["category"] == "salary")]
        if not salary_txns.empty:
            expected_day = salary_txns["txn_date"].apply(lambda d: d.day).mode()
            expected_day = int(expected_day.iloc[0]) if not expected_day.empty else 1
            within = salary_txns["txn_date"].apply(lambda d: abs(d.day - expected_day) <= 3)
            regularity = float(within.mean())

    return {
        "monthly_income_mean": round(mu_i, 2),
        "monthly_income_std": round(sigma_i, 2),
        "income_cv": round(cv_i, 4),
        "income_stability": round(income_stability, 4),
        "income_trend_slope": round(float(slope), 2),
        "income_regularity": round(regularity, 4),
    }
