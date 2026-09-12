"""Cash-flow Monte Carlo simulation (spec Section 5.1).

Income follows a discrete-time Ornstein-Uhlenbeck process:
    I_{t+1} = I_t + theta*(mu - I_t) + sigma*eps_t,   eps_t ~ N(0,1)
estimated from the customer's own income history, with a bootstrapped-residual
alternative preferred when >=12 months of data are available (it preserves the
customer's own distributional shape rather than assuming Gaussian shocks).

Expenses = fixed (EMI + rent + insurance + SIP, deterministic) + variable
V_t ~ LogNormal(ln(mu_D * s_m), sigma_D), where s_m is a month-of-year
seasonal multiplier estimated from history.

A "shortfall" at month t is L_t < min_buffer, where min_buffer =
0.5 * monthly_expenses_mean (the same threshold used by the survival model's
event definition, Section 5.2).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

N_PATHS_DEFAULT = 1000
MONTHS_DEFAULT = 12
OU_THETA_FALLBACK = 0.3


def estimate_income_params(income_series: np.ndarray) -> dict:
    """MLE-style OU parameter estimation (spec Section 5.1)."""
    mu = float(np.mean(income_series))
    sigma = float(np.std(income_series, ddof=1)) if len(income_series) > 1 else max(mu * 0.1, 1.0)

    if len(income_series) < 6:
        theta = OU_THETA_FALLBACK
    else:
        i_t = income_series[1:]
        i_tm1 = income_series[:-1]
        if np.std(i_tm1) == 0 or np.std(i_t) == 0:
            rho = 0.0
        else:
            rho = float(np.corrcoef(i_t, i_tm1)[0, 1])
        rho = float(np.clip(rho, 1e-6, 0.999))
        theta = -np.log(rho) if rho > 0 else OU_THETA_FALLBACK

    return {"mu": mu, "sigma": sigma, "theta": max(theta, 1e-3)}


def select_income_method(data_months: int) -> str:
    return "bootstrap" if data_months >= 12 else "ou"


def seasonal_multipliers(monthly: pd.DataFrame) -> dict[int, float]:
    """s_m = mean(discretionary spend in calendar month m) / overall mean."""
    if monthly.empty or "discretionary" not in monthly:
        return {m: 1.0 for m in range(1, 13)}

    df = monthly.copy()
    df["calendar_month"] = df["month"].apply(lambda s: int(s.split("-")[1]))
    overall_mean = df["discretionary"].mean()
    if overall_mean <= 0:
        return {m: 1.0 for m in range(1, 13)}

    by_month = df.groupby("calendar_month")["discretionary"].mean()
    return {m: float(by_month.get(m, overall_mean) / overall_mean) for m in range(1, 13)}


def _sample_income_paths(
    method: str,
    income_series: np.ndarray,
    ou_params: dict,
    n_paths: int,
    months_projected: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """All Monte Carlo income paths at once as an (n_paths, months) array.

    Vectorized across paths: the recursion is inherently sequential in t (each
    month depends on the previous one, and the non-negativity clamp is
    path-dependent so it cannot be replaced by a cumulative sum), but every
    path advances simultaneously. That makes this O(months) numpy operations
    rather than O(n_paths * months) Python iterations, which matters because
    the recommender runs one simulation per candidate product in its grid.
    """
    paths = np.empty((n_paths, months_projected))
    start = income_series[-1] if len(income_series) > 0 else ou_params["mu"]
    i_prev = np.full(n_paths, float(start))

    if method == "bootstrap" and len(income_series) >= 2:
        deltas = np.diff(income_series)
        draws = rng.choice(deltas, size=(n_paths, months_projected), replace=True)
        for t in range(months_projected):
            i_prev = np.maximum(i_prev + draws[:, t], 0.0)
            paths[:, t] = i_prev
    else:
        mu, sigma, theta = ou_params["mu"], ou_params["sigma"], ou_params["theta"]
        eps = rng.normal(size=(n_paths, months_projected))
        for t in range(months_projected):
            i_prev = np.maximum(i_prev + theta * (mu - i_prev) + sigma * eps[:, t], 0.0)
            paths[:, t] = i_prev

    return paths


def run_simulation(
    income_series: np.ndarray,
    fixed_expenses: float,
    monthly_discretionary_mean: float,
    expense_volatility: float,
    liquid_savings: float,
    min_buffer: float,
    monthly: pd.DataFrame,
    start_calendar_month: int,
    n_paths: int = N_PATHS_DEFAULT,
    months_projected: int = MONTHS_DEFAULT,
    seed: int | None = None,
) -> dict:
    """Run the full Monte Carlo simulation for one scenario.

    `fixed_expenses` already includes the scenario's EMI delta (baseline vs.
    take_loan/smaller_loan differ only in this input from the caller).
    """
    rng = np.random.default_rng(seed)
    data_months = len(income_series)
    method = select_income_method(data_months)
    ou_params = estimate_income_params(income_series) if len(income_series) > 0 else {"mu": 0.0, "sigma": 0.0, "theta": OU_THETA_FALLBACK}
    s_m = seasonal_multipliers(monthly)
    sigma_d = max(expense_volatility * monthly_discretionary_mean, 1.0)
    mu_d = max(monthly_discretionary_mean, 1.0)

    income_paths = _sample_income_paths(method, income_series, ou_params, n_paths, months_projected, rng)

    calendar_months = ((start_calendar_month - 1 + np.arange(months_projected)) % 12) + 1
    multipliers = np.array([max(s_m.get(int(m), 1.0), 0.05) for m in calendar_months])
    log_means = np.log(mu_d * multipliers)
    log_sigma = max(min(sigma_d / mu_d, 2.0), 0.05)

    variable_expenses = rng.lognormal(
        mean=log_means, sigma=log_sigma, size=(n_paths, months_projected)
    )

    net_flow = income_paths - (fixed_expenses + variable_expenses)
    liquidity_paths = liquid_savings + np.cumsum(net_flow, axis=1)
    shortfall_paths = liquidity_paths < min_buffer

    any_shortfall = shortfall_paths.any(axis=1)
    p_shortfall_12m = float(any_shortfall.mean())

    expected_liquidity = {str(t + 1): round(float(liquidity_paths[:, t].mean()), 2) for t in range(months_projected)}
    liquidity_percentiles = {
        str(t + 1): {
            "p5": round(float(np.percentile(liquidity_paths[:, t], 5)), 2),
            "p50": round(float(np.percentile(liquidity_paths[:, t], 50)), 2),
            "p95": round(float(np.percentile(liquidity_paths[:, t], 95)), 2),
        }
        for t in range(months_projected)
    }

    first_shortfall_month = np.where(
        shortfall_paths.any(axis=1),
        shortfall_paths.argmax(axis=1) + 1,
        months_projected,
    )
    expected_runway = float(first_shortfall_month.mean())

    return {
        "p_shortfall_12m": round(p_shortfall_12m, 4),
        "expected_liquidity": expected_liquidity,
        "liquidity_percentiles": liquidity_percentiles,
        "expected_runway": round(expected_runway, 2),
        "parameters": {
            "theta": round(ou_params["theta"], 4),
            "mu": round(ou_params["mu"], 2),
            "sigma": round(ou_params["sigma"], 2),
            "method": method,
        },
        "_liquidity_paths": liquidity_paths,  # internal, stripped before API response
    }
