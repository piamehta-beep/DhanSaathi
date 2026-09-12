"""Obligation / debt-burden features (spec Section 4.2)."""

from __future__ import annotations

from app.features.context import FeatureContext


def compute_obligation_features(ctx: FeatureContext, monthly_income_mean: float) -> dict:
    obligations = ctx.obligations
    if obligations.empty:
        total_emi = 0.0
        obligation_count = 0
        max_single_emi_ratio = 0.0
    else:
        emi_rows = obligations[obligations["type"] == "emi"]
        total_emi = float(emi_rows["amount"].sum())
        obligation_count = int(len(obligations))
        max_single_emi_ratio = (
            float(emi_rows["amount"].max()) / monthly_income_mean if monthly_income_mean > 0 and not emi_rows.empty else 0.0
        )

    dbr = total_emi / monthly_income_mean if monthly_income_mean > 0 else 0.0
    obligation_coverage = (monthly_income_mean - total_emi) / monthly_income_mean if monthly_income_mean > 0 else 0.0

    return {
        "total_emi": round(total_emi, 2),
        "dbr": round(dbr, 4),
        "obligation_count": obligation_count,
        "obligation_coverage": round(obligation_coverage, 4),
        "max_single_emi_ratio": round(max_single_emi_ratio, 4),
    }
