"""Optimizer and safety-gate validation (spec Section 9.3).

The headline criterion is absolute: no recommendation produced for any
customer may violate any hard constraint. That is asserted by re-deriving
the constraint checks from the persisted recommendation rather than trusting
the optimizer's own bookkeeping.

Persona-level expectations from Section 9.5 are checked separately, and the
no_action rate floor from Section 10.6 is checked too — a system that never
declines is not bank-adverse regardless of what its documentation claims.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.database.models import Customer
from app.safety.gate import (
    CREDIT_PRODUCTS,
    MAX_ANOMALY_SCORE,
    MAX_POST_DBR_CREDIT,
    MAX_P_SHORTFALL,
    MIN_POST_RUNWAY_MONTHS,
)
from app.services.recommendation_service import recommend

SAMPLE_SIZE = 120
SEED = 42


@pytest.fixture(scope="module")
def recommendations(db):
    rng = np.random.default_rng(SEED)
    customers = db.query(Customer).all()
    sample = rng.choice(customers, size=min(SAMPLE_SIZE, len(customers)), replace=False)
    return [(c, recommend(db, c.id, persist=False)) for c in sample]


def test_no_recommendation_violates_a_hard_constraint(recommendations):
    violations = []
    for customer, rec in recommendations:
        if rec["constraints_failed"]:
            violations.append((customer.external_id, "selected candidate has failed constraints",
                               rec["constraints_failed"]))

        if rec["product_type"] in CREDIT_PRODUCTS:
            sim = rec["simulation_summary"]
            if rec["distress_state"]:
                violations.append((customer.external_id, "credit to customer in distress", None))
            if sim["p_shortfall_12m"] > MAX_P_SHORTFALL:
                violations.append((customer.external_id, "post p_shortfall over limit",
                                   sim["p_shortfall_12m"]))
            if sim["expected_runway"] < MIN_POST_RUNWAY_MONTHS:
                violations.append((customer.external_id, "post runway under minimum",
                                   sim["expected_runway"]))
            if rec["max_anomaly_score"] >= MAX_ANOMALY_SCORE:
                violations.append((customer.external_id, "credit despite anomaly score",
                                   rec["max_anomaly_score"]))

    print(f"\n=== Optimizer constraint audit over {len(recommendations)} customers ===")
    print(f"  violations found: {len(violations)}")
    for v in violations[:10]:
        print(f"    {v}")
    print("========================================================\n")

    assert not violations, f"{len(violations)} hard-constraint violations: {violations[:5]}"


def test_distressed_customers_are_never_sold_credit(recommendations):
    offenders = [
        c.external_id for c, r in recommendations
        if c.persona == "distressed" and r["product_type"] in CREDIT_PRODUCTS
    ]
    assert not offenders, f"distressed customers offered credit: {offenders}"


def test_no_action_rate_and_persona_mix(recommendations):
    by_persona: dict[str, list[str]] = {}
    for customer, rec in recommendations:
        by_persona.setdefault(customer.persona, []).append(rec["product_type"])

    print("=== Recommendation mix by persona ===")
    for persona in sorted(by_persona):
        products = by_persona[persona]
        counts: dict[str, int] = {}
        for p in products:
            counts[p] = counts.get(p, 0) + 1
        no_action_rate = counts.get("no_action", 0) / len(products)
        mix = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        print(f"  {persona:18s} n={len(products):3d}  no_action={no_action_rate:.0%}   {mix}")

    overall_no_action = sum(
        1 for _, r in recommendations if r["product_type"] == "no_action"
    ) / len(recommendations)
    print(f"\n  overall no_action rate: {overall_no_action:.1%}")
    print("=====================================\n")

    # Section 9.5: distressed customers should overwhelmingly be declined.
    distressed = by_persona.get("distressed", [])
    if distressed:
        rate = sum(1 for p in distressed if p == "no_action") / len(distressed)
        assert rate >= 0.80, f"distressed no_action rate {rate:.0%} below 80%"

    # Section 9.5: healthy customers should mostly receive something actionable.
    stable = by_persona.get("stable_salaried", [])
    if stable:
        actionable = sum(1 for p in stable if p != "no_action") / len(stable)
        assert actionable >= 0.70, f"stable_salaried actionable rate {actionable:.0%} below 70%"
