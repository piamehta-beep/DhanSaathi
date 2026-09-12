"""The list view's bulk metrics must agree with the feature pipeline.

The list endpoint computes DBR and runway with aggregate SQL instead of
running the pipeline per row. That is only a safe optimisation if it produces
the same numbers — a list showing a different DBR from the detail view would
be a bug report waiting to happen, and a subtle one, since both numbers look
plausible on their own.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.database.models import Customer
from app.features.pipeline import compute_features
from app.features.summary import list_summary_metrics

SAMPLE = 40
SEED = 11


def test_bulk_metrics_match_the_feature_pipeline(db):
    rng = np.random.default_rng(SEED)
    customers = db.query(Customer).all()
    sample = list(rng.choice(customers, size=min(SAMPLE, len(customers)), replace=False))

    metrics = list_summary_metrics(db, [c.id for c in sample])
    assert len(metrics) == len(sample)

    mismatches = []
    for customer in sample:
        features = compute_features(db, customer.id, persist=False)
        bulk = metrics[customer.id]

        for field in ["monthly_income_mean", "monthly_expenses_mean", "total_emi", "dbr"]:
            expected = features[field]
            actual = bulk[field]
            if expected is None or actual is None:
                if expected != actual:
                    mismatches.append((customer.external_id, field, expected, actual))
                continue
            if abs(float(expected) - float(actual)) > 0.02:
                mismatches.append((customer.external_id, field, expected, actual))

        expected_runway = features["liquidity_runway"]
        actual_runway = bulk["liquidity_runway"]
        if expected_runway is not None and actual_runway is not None:
            if abs(float(expected_runway) - float(actual_runway)) > 0.02:
                mismatches.append((customer.external_id, "liquidity_runway", expected_runway, actual_runway))

    assert not mismatches, f"bulk metrics diverged from the pipeline: {mismatches[:5]}"


def test_empty_input_is_handled(db):
    assert list_summary_metrics(db, []) == {}


def test_every_requested_customer_gets_an_entry(db):
    customers = db.query(Customer).limit(5).all()
    metrics = list_summary_metrics(db, [c.id for c in customers])
    for customer in customers:
        assert customer.id in metrics, "a customer with no data must still get an entry"
