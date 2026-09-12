"""Feature pipeline orchestrator (spec Section 4.8).

`compute_features` is the single entrypoint every downstream module
(simulation, survival, recommender, anomaly, explainer) calls to get a
customer's current feature vector. It always recomputes fresh (features are
cheap relative to the ML models that consume them) and persists a snapshot
for audit/reproducibility, per the "no in-memory caching of state across
requests" principle in the architecture diagram.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import FeatureSnapshot
from app.features.behavioral import compute_behavioral_features
from app.features.context import build_context
from app.features.credit import compute_credit_features
from app.features.entropy import compute_entropy_features
from app.features.income import compute_income_features
from app.features.liquidity import compute_liquidity_features
from app.features.obligations import compute_obligation_features
from app.features.trends import compute_trend_features

FEATURE_VECTOR_ORDER = [
    "dbr", "savings_trend_slope", "expense_trend_slope", "income_cv", "liquidity_runway",
    "category_entropy", "anomaly_count_30d", "credit_util_trend", "income_stability",
    "expense_volatility", "savings_rate", "runway_trend", "txn_frequency_trend",
]


def compute_features(
    db: Session,
    customer_id,
    snapshot_date: dt.date | None = None,
    persist: bool = True,
    lookback_months: int | None = None,
) -> dict:
    features, _ = compute_features_with_snapshot_date(
        db, customer_id, snapshot_date, persist, lookback_months
    )
    return features


def compute_features_with_snapshot_date(
    db: Session,
    customer_id,
    snapshot_date: dt.date | None = None,
    persist: bool = True,
    lookback_months: int | None = None,
) -> tuple[dict, dt.date]:
    ctx = build_context(db, customer_id, snapshot_date, lookback_months)

    features: dict = {}
    features.update(compute_income_features(ctx))
    features.update(compute_obligation_features(ctx, features["monthly_income_mean"]))
    features.update(compute_liquidity_features(ctx, features["monthly_income_mean"]))
    features.update(compute_trend_features(ctx, features["monthly_expenses_mean"]))
    features.update(compute_entropy_features(ctx))
    features.update(compute_credit_features(ctx))
    features.update(compute_behavioral_features(ctx))
    features["data_months"] = ctx.data_months

    if persist:
        db.add(FeatureSnapshot(
            customer_id=customer_id,
            snapshot_date=ctx.snapshot_date,
            features=features,
            model_version=settings.model_version,
        ))
        db.commit()

    return features, ctx.snapshot_date


def feature_vector(features: dict) -> list[float]:
    """The standardized 13-element vector consumed by the survival model."""
    return [float(features.get(name) or 0.0) for name in FEATURE_VECTOR_ORDER]
