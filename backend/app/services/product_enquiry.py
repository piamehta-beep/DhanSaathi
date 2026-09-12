"""Customer-initiated product enquiry: "can I afford X?"

The recommender cannot infer a borrowing need, and deliberately does not try:
a funding requirement comes from an expressed intention (a purchase, a
consolidation, an emergency), and no such signal exists in transaction
history. See app/models/need_match.py.

This module covers the other direction, which is where borrowing need
actually originates — the customer asks. The request supplies the intent, and
the system supplies the arithmetic: affordability, the full safety-gate
verdict, the simulated effect on their cash flow, and the real bank products
that match.

Two properties make this anti-predatory rather than a sales funnel:

- the same safety gate applies. A customer asking for a loan does not get a
  weaker check than one the optimizer proposed; the answer can simply be no,
  with the constraint that failed named.
- when the answer is no, the system computes the largest amount that *would*
  pass and offers that instead. Declining without saying what is affordable
  leaves the customer to guess, and guessing usually means asking a lender
  with less scruple.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.recommender import (
    PRODUCT_GRID,
    match_bank_products,
    monthly_cost,
)
from app.models.recommender import Evaluation
from app.safety.affordability import compute_post_dbr
from app.safety.gate import Candidate, GateResult, safety_gate
from app.scoring.benefit_score import CBSComponents
from app.services.recommendation_service import assess_customer

# Search resolution when computing the largest affordable amount.
AFFORDABILITY_SEARCH_STEPS = 24
# Smallest commitment used to probe which constraints are size-independent.
MIN_PROBE_AMOUNT = 5000.0


def _evaluate_amount(
    assessment: dict,
    product_type: str,
    amount: float,
    tenure_months: int | None,
) -> dict:
    features = assessment["features"]
    age = assessment["customer"].age

    cost = monthly_cost(product_type, amount, tenure_months, age)
    dbr_relevant = 0.0 if product_type == "mutual_fund_sip" else cost
    post_dbr = compute_post_dbr(
        features["total_emi"], dbr_relevant, features["monthly_income_mean"]
    )

    from app.models.recommender import _simulate_scenario

    sim = _simulate_scenario(assessment["sim_inputs"], cost)
    gate = safety_gate(
        candidate=Candidate(product_type, amount, tenure_months, cost),
        post_dbr=post_dbr,
        post_p_shortfall=sim["p_shortfall_12m"],
        post_runway=sim["expected_runway"],
        distress_state=assessment["distress_state"],
        max_anomaly_score=assessment["max_anomaly"],
        data_months=features["data_months"],
        savings_rate=features["savings_rate"],
    )

    return {
        "amount": amount,
        "tenure_months": tenure_months,
        "monthly_cost": round(cost, 2),
        "post_dbr": round(post_dbr, 4),
        "post_p_shortfall_12m": sim["p_shortfall_12m"],
        "post_runway_months": sim["expected_runway"],
        "passes": gate.is_safe,
        "veto_reason": gate.veto_reason,
        "constraints_passed": gate.constraints_passed,
        "constraints_failed": gate.constraints_failed,
        "_sim": sim,
    }


def largest_affordable(
    assessment: dict,
    product_type: str,
    requested_amount: float,
    tenure_months: int | None,
) -> dict | None:
    """Binary search for the largest amount that clears every constraint.

    Monotonicity assumption: a smaller commitment is never less safe than a
    larger one for the same product and tenure, which holds because every
    constraint the gate applies is monotone in monthly cost.
    """
    low, high = 0.0, float(requested_amount)
    best: dict | None = None

    for _ in range(AFFORDABILITY_SEARCH_STEPS):
        if high - low < 1000:
            break
        mid = (low + high) / 2
        result = _evaluate_amount(assessment, product_type, mid, tenure_months)
        if result["passes"]:
            best = result
            low = mid
        else:
            high = mid

    if best is None:
        return None

    # Round down to a figure a person would actually be quoted.
    rounded = int(best["amount"] // 5000 * 5000)
    if rounded < 5000:
        return None
    confirmed = _evaluate_amount(assessment, product_type, float(rounded), tenure_months)
    return confirmed if confirmed["passes"] else best


def evaluate_enquiry(
    db: Session,
    customer_id,
    product_type: str,
    amount: float,
    tenure_months: int | None = None,
) -> dict:
    if product_type not in PRODUCT_GRID:
        raise ValueError(f"unknown product_type: {product_type}")

    assessment = assess_customer(db, customer_id)
    features = assessment["features"]
    baseline = assessment["baseline"]

    requested = _evaluate_amount(assessment, product_type, amount, tenure_months)
    requested.pop("_sim", None)

    response = {
        "customer_id": str(customer_id),
        "requested": {
            "product_type": product_type,
            "amount": amount,
            "tenure_months": tenure_months,
        },
        "verdict": "affordable" if requested["passes"] else "declined",
        "assessment": requested,
        "baseline": {
            "dbr": features["dbr"],
            "p_shortfall_12m": baseline["p_shortfall_12m"],
            "expected_runway": baseline["expected_runway"],
            "liquidity_runway_months": features["liquidity_runway"],
        },
        "distress_probability_12m": assessment["distress"]["distress_probability_12m"],
        "counter_offer": None,
        "matching_products": [],
    }

    if not requested["passes"]:
        alternative = largest_affordable(assessment, product_type, amount, tenure_months)
        if alternative:
            alternative.pop("_sim", None)
            response["counter_offer"] = {
                **alternative,
                "note": (
                    "The requested amount does not clear the affordability checks. "
                    "This is the largest amount that does."
                ),
            }
        else:
            # When no amount works, the binding constraint is one that does
            # not depend on size — an existing debt burden already over the
            # ceiling, unresolved anomalous activity, a distress flag. Saying
            # "no" without naming it leaves the customer unable to act, so it
            # is identified by evaluating the smallest possible commitment.
            floor = _evaluate_amount(assessment, product_type, MIN_PROBE_AMOUNT, tenure_months)
            response["counter_offer"] = {
                "amount": None,
                "blocking_constraints": floor["constraints_failed"],
                "blocking_reason": floor["veto_reason"],
                "note": (
                    "No amount of this product clears the checks right now, because "
                    "the blocking condition does not depend on the amount requested."
                ),
            }

    # Ground whichever amount is actually viable against real bank products.
    viable_amount = requested["amount"] if requested["passes"] else (
        response["counter_offer"].get("amount") if response["counter_offer"] else None
    )
    if viable_amount:
        selected = Evaluation(
            product_type=product_type,
            amount=float(viable_amount),
            tenure_months=tenure_months,
            emi=0.0,
            cbs=0.0,
            components=CBSComponents(0, 0, 0, 0, 0),
            # The matcher re-runs the gate per bank product, so this placeholder
            # is never read as an authority on safety.
            gate=GateResult(True, None, [], []),
            post_dbr=0.0,
            post_p_shortfall=0.0,
            post_runway=0.0,
        )
        response["matching_products"] = match_bank_products(
            db=db,
            selected=selected,
            features=features,
            sim_inputs=assessment["sim_inputs"],
            distress_state=assessment["distress_state"],
            max_anomaly=assessment["max_anomaly"],
            age=assessment["customer"].age,
        )

        # An affordable amount can still fall below every listed lender's
        # minimum ticket size. That is a real outcome and worth stating rather
        # than returning an empty list that reads like a lookup failure.
        if not response["matching_products"]:
            response["matching_products_note"] = (
                f"No listed provider offers {product_type.replace('_', ' ')} at "
                f"Rs {int(viable_amount):,}; the affordable amount is below their "
                "minimum ticket size."
            )

    return response
