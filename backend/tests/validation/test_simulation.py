"""Cash-flow simulation backtest (spec Section 9.2).

For a sample of customers per persona: estimate OU/bootstrap parameters from
months 1-12, simulate months 13-18, and check how often actual liquidity
falls within the simulated [p5, p95] band. Prints per-persona coverage and
P(shortfall) so results are visible before Milestone 3.
"""

from __future__ import annotations

import numpy as np

from app.database.models import Customer
from app.features.context import build_context
from app.models.cashflow_sim import run_simulation

SEED = 42
SAMPLE_PER_PERSONA = 15


def _reconstruct_liquidity_series(ctx):
    monthly = ctx.monthly
    net = (monthly["income"] - monthly["expenses"]).to_numpy()
    liquid_now = float(ctx.customer.liquid_savings)
    future_cumsum = np.cumsum(net[::-1])[::-1]
    return liquid_now - (future_cumsum - net)


def test_simulation_backtest(db):
    rng = np.random.default_rng(SEED)
    personas = [p for (p,) in db.query(Customer.persona).distinct().all()]

    print("\n=== Simulation Backtest Summary (months 13-18 held out) ===")
    overall_coverage = []

    for persona in personas:
        customers = db.query(Customer).filter(Customer.persona == persona).all()
        sample = rng.choice(customers, size=min(SAMPLE_PER_PERSONA, len(customers)), replace=False)

        coverages = []
        shortfall_flags = []

        for c in sample:
            ctx = build_context(db, c.id, snapshot_date=None)
            monthly = ctx.monthly
            if len(monthly) < 18:
                continue

            train = monthly.iloc[:12]
            actual_future = monthly.iloc[12:18]
            liquidity_series_full = _reconstruct_liquidity_series(ctx)
            liquid_at_month12 = liquidity_series_full[11]

            fixed_non_emi = float((train["expenses"] - train["discretionary"] - train["emi"]).mean())
            fixed_expenses = fixed_non_emi + float(train["emi"].mean())
            min_buffer = 0.5 * float(train["expenses"].mean())

            sim = run_simulation(
                income_series=train["income"].to_numpy(),
                fixed_expenses=fixed_expenses,
                monthly_discretionary_mean=float(train["discretionary"].mean()),
                expense_volatility=float(train["expenses"].std(ddof=1) / train["expenses"].mean()) if train["expenses"].mean() > 0 else 0.0,
                liquid_savings=liquid_at_month12,
                min_buffer=min_buffer,
                monthly=train,
                start_calendar_month=1,
                n_paths=500,
                months_projected=6,
                seed=SEED,
            )

            actual_liquidity_future = liquidity_series_full[12:18]
            in_band = 0
            for t in range(6):
                p5 = sim["liquidity_percentiles"][str(t + 1)]["p5"]
                p95 = sim["liquidity_percentiles"][str(t + 1)]["p95"]
                if p5 <= actual_liquidity_future[t] <= p95:
                    in_band += 1
            coverages.append(in_band / 6)
            shortfall_flags.append(sim["p_shortfall_12m"])

        if coverages:
            mean_coverage = float(np.mean(coverages))
            mean_p_shortfall = float(np.mean(shortfall_flags))
            overall_coverage.extend(coverages)
            print(f"  {persona:20s} n={len(coverages):3d}  coverage={mean_coverage:.2%}  mean_p_shortfall={mean_p_shortfall:.4f}")

    print(f"\nOverall coverage across all sampled customers: {np.mean(overall_coverage):.2%} (target > 80% avg)")
    print("=============================================================\n")

    assert np.mean(overall_coverage) > 0.80, "spec Section 9.2 target: >80% average coverage"
