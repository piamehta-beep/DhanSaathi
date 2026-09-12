"""Financial distress risk via Cox Proportional Hazards (spec Section 5.2).

h(t | X) = h_0(t) * exp(beta' X), fit with lifelines.CoxPHFitter (penalizer=0.1
for stability with correlated covariates). Ground-truth event/duration are
derived directly from each customer's own 18-month liquidity trajectory
(reconstructed from their final liquid_savings and monthly net cash flow),
not from the synthetic generator's injected distress-event metadata — the
event definition is "liquidity first falls below 0.5x monthly expenses"
(spec Section 5.2), independent of *why* that happened.

Baseline covariates are computed from only the customer's first 3 months of
transactions (data as of 2024-03-31), so the model predicts forward from an
early snapshot rather than leaking future behavior into its own predictors.
Any covariate with zero variance across the training set (e.g.
credit_util_trend, since no synthetic customer carries a credit card) is
dropped before fitting — Cox regression's Newton-Raphson step is singular
on a constant column, and a zero-variance feature carries no information
for the model anyway.
"""

from __future__ import annotations

import datetime as dt
import threading

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from app.database.models import Customer
from app.features.context import build_context
from app.features.pipeline import FEATURE_VECTOR_ORDER, compute_features, feature_vector

BASELINE_SNAPSHOT = dt.date(2024, 3, 31)
PENALIZER = 0.1

EXPECTED_SIGN = {
    "dbr": 1, "savings_trend_slope": -1, "income_cv": 1, "liquidity_runway": -1,
    "credit_util_trend": 1, "expense_volatility": 1, "category_entropy": -1,
    "anomaly_count_90d": 1, "income_stability": -1, "savings_rate": -1,
    "runway_trend": -1, "txn_frequency_trend": 0, "dbr_trend": 1,
}


def reconstruct_liquidity_series(db: Session, customer_id) -> tuple[np.ndarray, float]:
    ctx = build_context(db, customer_id, snapshot_date=None)
    monthly = ctx.monthly
    if monthly.empty:
        return np.array([]), 0.0
    net = (monthly["income"] - monthly["expenses"]).to_numpy()
    liquid_now = float(ctx.customer.liquid_savings)
    future_cumsum = np.cumsum(net[::-1])[::-1]
    liquidity_series = liquid_now - (future_cumsum - net)
    mean_expenses = float(monthly["expenses"].mean())
    min_buffer = 0.5 * mean_expenses if mean_expenses > 0 else 0.0
    return liquidity_series, min_buffer


def compute_duration_event(liquidity_series: np.ndarray, min_buffer: float) -> tuple[int, int]:
    if len(liquidity_series) == 0:
        return 1, 0
    below = liquidity_series < min_buffer
    if below.any():
        event_month = int(np.argmax(below)) + 1
        return max(event_month, 1), 1
    return len(liquidity_series), 0


def build_training_dataset(db: Session) -> pd.DataFrame:
    customers = db.query(Customer).all()
    rows = []
    for c in customers:
        liquidity_series, min_buffer = reconstruct_liquidity_series(db, c.id)
        duration, event = compute_duration_event(liquidity_series, min_buffer)
        features = compute_features(db, c.id, snapshot_date=BASELINE_SNAPSHOT, persist=False)
        vec = feature_vector(features)
        row = dict(zip(FEATURE_VECTOR_ORDER, vec))
        row["duration"] = duration
        row["event"] = event
        row["persona"] = c.persona
        row["customer_id"] = str(c.id)
        rows.append(row)
    return pd.DataFrame(rows)


def active_feature_columns(df: pd.DataFrame) -> list[str]:
    """Feature columns with non-zero variance in this training set."""
    return [c for c in FEATURE_VECTOR_ORDER if df[c].std(ddof=0) > 1e-9]


def fit_cox_model(df: pd.DataFrame) -> tuple[CoxPHFitter, StandardScaler, pd.DataFrame]:
    active_cols = active_feature_columns(df)
    x = df[active_cols]
    scaler = StandardScaler()
    x_scaled = pd.DataFrame(scaler.fit_transform(x), columns=active_cols, index=df.index)
    fit_df = x_scaled.copy()
    fit_df["duration"] = df["duration"].astype(float)
    fit_df["event"] = df["event"].astype(int)

    cph = CoxPHFitter(penalizer=PENALIZER)
    cph.fit(fit_df, duration_col="duration", event_col="event")
    return cph, scaler, x_scaled


def predict_for_features(cph: CoxPHFitter, scaler: StandardScaler, features: dict) -> dict:
    active_cols = list(cph.params_.index)
    vec = [float(features.get(name) or 0.0) for name in active_cols]
    x = pd.DataFrame([vec], columns=active_cols)
    x_scaled = pd.DataFrame(scaler.transform(x), columns=active_cols)

    survival_fn = cph.predict_survival_function(x_scaled)
    sf = survival_fn.iloc[:, 0]

    def sf_at(month: int) -> float:
        idx = sf.index[sf.index <= month]
        return float(sf.loc[idx[-1]]) if len(idx) else 1.0

    survival_points = {str(m): round(sf_at(m), 4) for m in [1, 3, 6, 12]}
    distress_probability_12m = round(1 - sf_at(12), 4)
    hazard_ratios = {k: round(float(v), 4) for k, v in cph.hazard_ratios_.to_dict().items()}

    return {
        "hazard_ratios": hazard_ratios,
        "survival_function": survival_points,
        "distress_probability_12m": distress_probability_12m,
    }


_model_lock = threading.Lock()
_model_cache: dict = {}


def get_or_train_model(db: Session) -> tuple[CoxPHFitter, StandardScaler, pd.DataFrame]:
    """Lazily train once per process and cache. Training data is a frozen
    property of the seeded dataset, not per-request business state.

    Returns (cph, scaler, training_df) where training_df carries the raw
    (unscaled) covariates plus duration/event/persona/customer_id — callers
    needing the scaled design matrix for concordance/diagnostics should
    re-scale via `scaler`.
    """
    with _model_lock:
        if "cph" not in _model_cache:
            df = build_training_dataset(db)
            cph, scaler, x_scaled = fit_cox_model(df)
            _model_cache["cph"] = cph
            _model_cache["scaler"] = scaler
            _model_cache["training_df"] = df
            _model_cache["x_scaled"] = x_scaled
        return _model_cache["cph"], _model_cache["scaler"], _model_cache["training_df"]


def get_cached_scaled_design_matrix() -> pd.DataFrame:
    return _model_cache["x_scaled"]


def reset_model_cache() -> None:
    _model_cache.clear()
