"""Trend features (spec Section 4.4).

Slopes are OLS coefficients (scipy.stats.linregress) against month index t,
using the full available history rather than a fixed 6-month window, since a
trend needs more points than a level does. `runway_trend` reconstructs a
runway time series by working backward from the customer's current
liquid_savings using each month's net cash flow.
"""

from __future__ import annotations

import numpy as np
from scipy import stats

from app.features.context import FeatureContext


def _slope(t: np.ndarray, y: np.ndarray) -> float:
    if len(y) < 2 or np.all(y == y[0]):
        return 0.0
    slope, _, _, _, _ = stats.linregress(t, y)
    return float(slope)


def compute_trend_features(ctx: FeatureContext, monthly_expenses_mean: float) -> dict:
    monthly = ctx.monthly
    if monthly.empty or len(monthly) < 2:
        return {
            "savings_trend_slope": 0.0, "expense_trend_slope": 0.0,
            "expense_volatility": 0.0, "dbr_trend": 0.0, "runway_trend": 0.0,
        }

    t = monthly["t"].to_numpy()
    income = monthly["income"].to_numpy()
    expenses = monthly["expenses"].to_numpy()
    emi = monthly["emi"].to_numpy()
    net_savings = income - expenses

    savings_trend_slope = _slope(t, net_savings)
    expense_trend_slope = _slope(t, expenses)

    mu_e = float(np.mean(expenses))
    sigma_e = float(np.std(expenses, ddof=1)) if len(expenses) > 1 else 0.0
    expense_volatility = sigma_e / mu_e if mu_e > 0 else 0.0

    with np.errstate(divide="ignore", invalid="ignore"):
        dbr_series = np.where(income > 0, emi / income, 0.0)
    dbr_trend = _slope(t, dbr_series)

    liquid_savings_now = float(ctx.customer.liquid_savings)
    future_net_cumsum = np.cumsum(net_savings[::-1])[::-1]  # sum from month t+1..T at each t
    liquidity_series = liquid_savings_now - (future_net_cumsum - net_savings)
    runway_series = liquidity_series / monthly_expenses_mean if monthly_expenses_mean > 0 else np.zeros_like(t, dtype=float)
    runway_trend = _slope(t, runway_series)

    return {
        "savings_trend_slope": round(savings_trend_slope, 2),
        "expense_trend_slope": round(expense_trend_slope, 2),
        "expense_volatility": round(expense_volatility, 4),
        "dbr_trend": round(dbr_trend, 6),
        "runway_trend": round(runway_trend, 4),
    }
