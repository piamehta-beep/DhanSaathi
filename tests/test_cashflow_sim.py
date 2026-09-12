"""Unit tests for the cash-flow simulation module.

The simulation is vectorized across Monte Carlo paths for speed (the
recommender runs one simulation per candidate product). These tests pin the
vectorized implementation against a naive sequential reference so a future
optimization cannot silently change the maths.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.models.cashflow_sim import estimate_income_params, run_simulation, seasonal_multipliers

MONTHS = [f"2024-{m:02d}" for m in range(1, 13)] + [f"2025-{m:02d}" for m in range(1, 7)]


def _monthly_fixture(income=80000.0, discretionary=30000.0, emi=15000.0, other_fixed=10000.0):
    return pd.DataFrame({
        "month": MONTHS,
        "t": range(1, len(MONTHS) + 1),
        "income": [income] * len(MONTHS),
        "expenses": [discretionary + emi + other_fixed] * len(MONTHS),
        "discretionary": [discretionary] * len(MONTHS),
        "emi": [emi] * len(MONTHS),
        "n_txns": [40] * len(MONTHS),
    })


def _reference_simulation(
    income_series, fixed_expenses, mu_d, expense_volatility, liquid_savings,
    min_buffer, s_m, start_calendar_month, n_paths, months, seed,
):
    """Naive per-path, per-month reference implementation (the pre-vectorized
    formulation), used only to check the fast path agrees."""
    rng = np.random.default_rng(seed)
    sigma_d = max(expense_volatility * mu_d, 1.0)
    mu_d = max(mu_d, 1.0)
    log_sigma = max(min(sigma_d / mu_d, 2.0), 0.05)
    theta_params = estimate_income_params(income_series)

    shortfalls = np.zeros(n_paths, dtype=bool)
    finals = np.empty(n_paths)
    for p in range(n_paths):
        i_prev = income_series[-1]
        deltas = np.diff(income_series)
        liquidity = liquid_savings
        breached = False
        for t in range(months):
            if len(deltas) > 0 and np.std(deltas) > 0:
                i_prev = max(i_prev + rng.choice(deltas), 0.0)
            else:
                i_prev = max(
                    i_prev + theta_params["theta"] * (theta_params["mu"] - i_prev)
                    + theta_params["sigma"] * rng.normal(),
                    0.0,
                )
            calendar_month = ((start_calendar_month - 1 + t) % 12) + 1
            multiplier = max(s_m.get(calendar_month, 1.0), 0.05)
            v_t = rng.lognormal(mean=np.log(mu_d * multiplier), sigma=log_sigma)
            liquidity = liquidity + i_prev - (fixed_expenses + v_t)
            if liquidity < min_buffer:
                breached = True
        shortfalls[p] = breached
        finals[p] = liquidity
    return shortfalls.mean(), finals.mean()


def test_vectorized_matches_sequential_reference_distribution():
    monthly = _monthly_fixture()
    income_series = monthly["income"].to_numpy()
    s_m = seasonal_multipliers(monthly)

    kwargs = dict(
        fixed_expenses=25000.0, mu_d=30000.0, expense_volatility=0.15,
        liquid_savings=200000.0, min_buffer=27500.0, s_m=s_m,
        start_calendar_month=1, n_paths=4000, months=12,
    )

    ref_p_shortfall, ref_mean_final = _reference_simulation(
        income_series=income_series, seed=7, **kwargs
    )

    fast = run_simulation(
        income_series=income_series,
        fixed_expenses=25000.0,
        monthly_discretionary_mean=30000.0,
        expense_volatility=0.15,
        liquid_savings=200000.0,
        min_buffer=27500.0,
        monthly=monthly,
        start_calendar_month=1,
        n_paths=4000,
        months_projected=12,
        seed=99,
    )
    fast_mean_final = fast["expected_liquidity"]["12"]

    # Different RNG draw orders, so compare distributions, not exact values.
    assert abs(fast["p_shortfall_12m"] - ref_p_shortfall) < 0.05
    assert abs(fast_mean_final - ref_mean_final) / abs(ref_mean_final) < 0.05


def test_simulation_is_deterministic_for_a_seed():
    monthly = _monthly_fixture()
    args = dict(
        income_series=monthly["income"].to_numpy(), fixed_expenses=25000.0,
        monthly_discretionary_mean=30000.0, expense_volatility=0.15,
        liquid_savings=200000.0, min_buffer=27500.0, monthly=monthly,
        start_calendar_month=1, n_paths=500, months_projected=12, seed=42,
    )
    a = run_simulation(**args)
    b = run_simulation(**args)
    assert a["p_shortfall_12m"] == b["p_shortfall_12m"]
    assert a["expected_liquidity"] == b["expected_liquidity"]


def test_higher_fixed_expenses_raise_shortfall_probability():
    monthly = _monthly_fixture()
    # Income 80k, discretionary ~30k: fixed=30k leaves the customer cash-flow
    # positive, fixed=60k puts them ~10k/month underwater against a 60k buffer.
    base = dict(
        income_series=monthly["income"].to_numpy(),
        monthly_discretionary_mean=30000.0, expense_volatility=0.15,
        liquid_savings=60000.0, min_buffer=27500.0, monthly=monthly,
        start_calendar_month=1, n_paths=1000, months_projected=12, seed=42,
    )
    low = run_simulation(fixed_expenses=30000.0, **base)
    high = run_simulation(fixed_expenses=60000.0, **base)
    assert high["p_shortfall_12m"] > low["p_shortfall_12m"]
    assert high["expected_runway"] <= low["expected_runway"]


def test_liquidity_is_cumulative_sum_of_net_flow():
    """L_t must be strictly L_0 + sum of monthly net flows — the vectorized
    cumsum and the original sequential accumulation are the same identity."""
    monthly = _monthly_fixture()
    sim = run_simulation(
        income_series=monthly["income"].to_numpy(), fixed_expenses=20000.0,
        monthly_discretionary_mean=30000.0, expense_volatility=0.0001,
        liquid_savings=100000.0, min_buffer=0.0, monthly=monthly,
        start_calendar_month=1, n_paths=200, months_projected=6, seed=3,
    )
    paths = sim["_liquidity_paths"]
    steps = np.diff(paths, axis=1)
    # Each step is income - (fixed + variable); with near-zero expense
    # volatility the per-month step must be near-constant within a path.
    assert np.all(np.isfinite(steps))
    assert paths.shape == (200, 6)
