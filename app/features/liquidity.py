"""Liquidity features (spec Section 4.3)."""

from __future__ import annotations

from app.features.context import FeatureContext

WINDOW = 6


def compute_liquidity_features(ctx: FeatureContext, monthly_income_mean: float) -> dict:
    monthly = ctx.monthly.tail(WINDOW)
    liquid_savings = float(ctx.customer.liquid_savings)

    if monthly.empty:
        mu_e = 0.0
        mu_d = 0.0
    else:
        mu_e = float(monthly["expenses"].mean())
        mu_d = float(monthly["discretionary"].mean())

    liquidity_runway = liquid_savings / mu_e if mu_e > 0 else float("inf")
    savings_rate = (monthly_income_mean - mu_e) / monthly_income_mean if monthly_income_mean > 0 else 0.0
    min_buffer = 0.5 * mu_e

    return {
        "liquid_savings": round(liquid_savings, 2),
        "monthly_expenses_mean": round(mu_e, 2),
        "monthly_discretionary_mean": round(mu_d, 2),
        "liquidity_runway": round(liquidity_runway, 2) if liquidity_runway != float("inf") else None,
        "savings_rate": round(savings_rate, 4),
        "min_buffer": round(min_buffer, 2),
    }
