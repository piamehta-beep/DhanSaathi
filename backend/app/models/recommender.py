"""Recommendation as constrained optimization (spec Section 5.3).

    x* = argmax CBS(x)  subject to every hard constraint in the safety gate,
    over x = (product_type, amount, tenure) enumerated on a discrete grid,
    with `no_action` always present in the decision space at CBS = 0.

Brute-force enumeration is used rather than a continuous relaxation: the grid
is small (~40 candidates), enumeration is exact, and every candidate's full
constraint evaluation is retained for the audit trail — which a solver's
interior path would not give.

The design is deliberately bank-adverse. `no_action` wins ties, wins whenever
no candidate clears the gate, and wins whenever the best candidate fails to
beat it by a margin — so a recommendation has to be affirmatively better than
leaving the customer alone, not merely non-harmful.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.database.models import BankProduct
from app.models.cashflow_sim import run_simulation
from app.models.need_match import get_or_train_need_model
from app.safety.affordability import compute_emi, compute_post_dbr
from app.safety.gate import Candidate, GateResult, safety_gate
from app.scoring.benefit_score import (
    CBSComponents,
    affordability_delta,
    compute_cbs,
    life_stage_align,
    risk_reduction,
)

PRODUCT_GRID: dict[str, dict] = {
    "personal_loan": {
        "amounts": [50000, 100000, 200000, 500000],
        "tenures": [12, 24, 36, 48, 60],
    },
    "credit_card": {
        "amounts": [25000, 50000, 100000, 200000],
        "tenures": [None],
    },
    "term_insurance": {
        "amounts": [500000, 1000000, 2500000, 5000000],
        "tenures": [10, 20, 30],
    },
    "mutual_fund_sip": {
        "amounts": [1000, 2500, 5000, 10000],
        "tenures": [None],
    },
}

# Representative pricing used when scoring the abstract grid, before matching
# against real bank products. Kept separate from bank_products so the
# optimizer's decision does not depend on which banks happen to be seeded.
DEFAULT_LOAN_RATE = 13.0
CREDIT_CARD_APR = 42.0
# Assumed monthly utilisation of a new card limit, for affordability purposes.
CREDIT_CARD_UTILISATION = 0.30
# Term-insurance premium per lakh of cover per year. Mortality risk compounds
# with age, so a flat rate is badly wrong at both ends — it roughly triples
# the true cost for a 25-year-old and understates it for someone near 60.
# Anchored at ~Rs 400/lakh/year at age 25 and growing ~7.5% per year of age,
# which tracks the published bands for this product category.
INSURANCE_PREMIUM_PER_LAKH_AT_25 = 400.0
INSURANCE_PREMIUM_AGE_GROWTH = 1.075
INSURANCE_REFERENCE_AGE = 25


def insurance_premium_per_lakh_annual(age: int) -> float:
    return INSURANCE_PREMIUM_PER_LAKH_AT_25 * (
        INSURANCE_PREMIUM_AGE_GROWTH ** max(age - INSURANCE_REFERENCE_AGE, 0)
    )

CBS_MARGIN_OVER_NO_ACTION = 0.05
TIE_BREAK_EPSILON = 0.02


@dataclass
class Evaluation:
    product_type: str
    amount: float | None
    tenure_months: int | None
    emi: float
    cbs: float
    components: CBSComponents
    gate: GateResult
    post_dbr: float
    post_p_shortfall: float
    post_runway: float
    simulation: dict = field(default_factory=dict)


def monthly_cost(
    product_type: str, amount: float | None, tenure_months: int | None, age: int = 35
) -> float:
    """The recurring monthly outflow a product commits the customer to.

    Every product type is converted to a monthly figure so that affordability
    is judged on one consistent basis: an EMI for a loan, assumed servicing on
    a card limit, the levelised premium for insurance, the instalment for a
    SIP.
    """
    if amount is None:
        return 0.0
    if product_type == "personal_loan":
        return compute_emi(amount, DEFAULT_LOAN_RATE, tenure_months or 36)
    if product_type == "credit_card":
        # A limit is not debt, but treating it as free would let the optimizer
        # hand out unlimited credit. Charge assumed utilisation serviced at the
        # card's APR over a year.
        return compute_emi(amount * CREDIT_CARD_UTILISATION, CREDIT_CARD_APR, 12)
    if product_type == "term_insurance":
        return (amount / 100000.0) * insurance_premium_per_lakh_annual(age) / 12.0
    if product_type == "mutual_fund_sip":
        return amount
    return 0.0


def _simulate_scenario(sim_inputs: dict, extra_monthly_cost: float) -> dict:
    return run_simulation(
        income_series=sim_inputs["income_series"],
        fixed_expenses=sim_inputs["fixed_expenses"] + extra_monthly_cost,
        monthly_discretionary_mean=sim_inputs["monthly_discretionary_mean"],
        expense_volatility=sim_inputs["expense_volatility"],
        liquid_savings=sim_inputs["liquid_savings"],
        min_buffer=sim_inputs["min_buffer"],
        monthly=sim_inputs["monthly"],
        start_calendar_month=sim_inputs["start_calendar_month"],
        n_paths=sim_inputs.get("n_paths", 500),
        months_projected=12,
        seed=42,
    )


def evaluate_candidate(
    product_type: str,
    amount: float | None,
    tenure_months: int | None,
    features: dict,
    sim_inputs: dict,
    baseline: dict,
    need_probs: dict[str, float],
    distress_probability: float,
    max_anomaly: float,
    life_stage: str,
    distress_state: bool,
    age: int = 35,
) -> Evaluation:
    cost = monthly_cost(product_type, amount, tenure_months, age)

    # A SIP is redirected savings, not an expense — it reduces liquid buffer
    # but is not a debt obligation, so it must not inflate DBR.
    dbr_relevant_cost = 0.0 if product_type == "mutual_fund_sip" else cost
    post_dbr = compute_post_dbr(
        features["total_emi"], dbr_relevant_cost, features["monthly_income_mean"]
    )

    sim = _simulate_scenario(sim_inputs, cost)
    post_p_shortfall = sim["p_shortfall_12m"]
    post_runway = sim["expected_runway"]

    gate = safety_gate(
        candidate=Candidate(product_type, amount, tenure_months, cost),
        post_dbr=post_dbr,
        post_p_shortfall=post_p_shortfall,
        post_runway=post_runway,
        distress_state=distress_state,
        max_anomaly_score=max_anomaly,
        data_months=features["data_months"],
        savings_rate=features["savings_rate"],
    )

    # Rising shortfall probability is the observable proxy for added distress
    # risk from this specific decision; the survival model supplies the
    # customer's standing level, the simulation supplies the increment.
    distress_delta = max(0.0, post_p_shortfall - baseline["p_shortfall_12m"])

    components = CBSComponents(
        need_match=need_probs.get(product_type, 0.0),
        affordability_delta=affordability_delta(baseline["expected_runway"], post_runway),
        risk_reduction=risk_reduction(
            product_type, amount, features["monthly_income_mean"]
        ),
        life_stage_align=life_stage_align(life_stage, product_type),
        distress_delta=distress_delta,
    )

    return Evaluation(
        product_type=product_type,
        amount=amount,
        tenure_months=tenure_months,
        emi=cost,
        cbs=compute_cbs(components),
        components=components,
        gate=gate,
        post_dbr=post_dbr,
        post_p_shortfall=post_p_shortfall,
        post_runway=post_runway,
        simulation=sim,
    )


def no_action_evaluation(baseline: dict, need_probs: dict[str, float]) -> Evaluation:
    components = CBSComponents(
        need_match=need_probs.get("no_action", 0.0),
        affordability_delta=0.0,
        risk_reduction=0.0,
        life_stage_align=0.0,
        distress_delta=0.0,
    )
    return Evaluation(
        product_type="no_action",
        amount=None,
        tenure_months=None,
        emi=0.0,
        cbs=0.0,  # zero by definition, regardless of components
        components=components,
        gate=GateResult(True, None, [], []),
        post_dbr=baseline["dbr"],
        post_p_shortfall=baseline["p_shortfall_12m"],
        post_runway=baseline["expected_runway"],
        simulation={},
    )


def optimize(
    db: Session,
    features: dict,
    sim_inputs: dict,
    baseline: dict,
    distress_probability: float,
    max_anomaly: float,
    life_stage: str,
    distress_state: bool,
    age: int = 35,
) -> tuple[Evaluation, list[Evaluation]]:
    """Enumerate the grid, keep every evaluation, return the winner.

    Returns (selected, all_evaluations) so the API can report why rejected
    candidates were rejected, not only what was chosen.
    """
    need_model = get_or_train_need_model(db)
    need_probs = need_model.predict_proba(features)

    evaluations: list[Evaluation] = []
    for product_type, grid in PRODUCT_GRID.items():
        for amount in grid["amounts"]:
            for tenure in grid["tenures"]:
                evaluations.append(evaluate_candidate(
                    product_type=product_type,
                    amount=amount,
                    tenure_months=tenure,
                    features=features,
                    sim_inputs=sim_inputs,
                    baseline=baseline,
                    need_probs=need_probs,
                    distress_probability=distress_probability,
                    max_anomaly=max_anomaly,
                    life_stage=life_stage,
                    distress_state=distress_state,
                    age=age,
                ))

    do_nothing = no_action_evaluation(baseline, need_probs)
    evaluations.append(do_nothing)

    feasible = [e for e in evaluations if e.gate.is_safe and e.product_type != "no_action"]
    if not feasible:
        return do_nothing, evaluations

    best = max(feasible, key=lambda e: e.cbs)

    # Tie-break toward the lower added distress risk, then toward no_action.
    near_best = [e for e in feasible if abs(e.cbs - best.cbs) <= TIE_BREAK_EPSILON]
    if len(near_best) > 1:
        best = min(near_best, key=lambda e: (e.components.distress_delta, -e.cbs))

    if best.cbs - do_nothing.cbs < CBS_MARGIN_OVER_NO_ACTION:
        return do_nothing, evaluations

    return best, evaluations


def match_bank_products(
    db: Session,
    selected: Evaluation,
    features: dict,
    sim_inputs: dict,
    distress_state: bool,
    max_anomaly: float,
    age: int = 35,
    top_n: int = 3,
) -> list[dict]:
    """Ground the abstract decision in real bank products (spec addendum).

    Each matching product is priced with the deterministic EMI formula at its
    own advertised rate band, then re-checked through the safety gate
    individually — a bank with a lower headline rate but a longer minimum
    tenure can fail a constraint that another bank passes, so the gate result
    is per-product rather than inherited from the abstract decision.
    """
    if selected.product_type == "no_action" or selected.amount is None:
        return []

    products = db.query(BankProduct).filter(
        BankProduct.product_type == selected.product_type,
        BankProduct.min_amount <= selected.amount,
        BankProduct.max_amount >= selected.amount,
    ).all()

    matches = []
    for product in products:
        tenure = selected.tenure_months
        tenure_options = product.tenure_options or []
        if tenure_options:
            tenure = min(tenure_options, key=lambda t: abs(t - (selected.tenure_months or 36)))

        rate_low = float(product.interest_rate_min)
        rate_high = float(product.interest_rate_max)

        if selected.product_type == "personal_loan":
            emi = compute_emi(float(selected.amount), rate_low, tenure or 36)
            total_payable = emi * (tenure or 36)
            total_interest = total_payable - float(selected.amount)
        elif selected.product_type == "credit_card":
            emi = compute_emi(float(selected.amount) * CREDIT_CARD_UTILISATION, rate_low, 12)
            total_interest = emi * 12 - float(selected.amount) * CREDIT_CARD_UTILISATION
        else:
            emi = monthly_cost(selected.product_type, float(selected.amount), tenure, age)
            total_interest = 0.0

        dbr_relevant = 0.0 if selected.product_type == "mutual_fund_sip" else emi
        post_dbr = compute_post_dbr(
            features["total_emi"], dbr_relevant, features["monthly_income_mean"]
        )
        sim = _simulate_scenario(sim_inputs, emi)

        gate = safety_gate(
            candidate=Candidate(selected.product_type, float(selected.amount), tenure, emi),
            post_dbr=post_dbr,
            post_p_shortfall=sim["p_shortfall_12m"],
            post_runway=sim["expected_runway"],
            distress_state=distress_state,
            max_anomaly_score=max_anomaly,
            data_months=features["data_months"],
            savings_rate=features["savings_rate"],
        )

        matches.append({
            "bank_name": product.bank_name,
            "product_name": product.product_name,
            "product_type": product.product_type,
            "amount": float(selected.amount),
            "tenure_months": tenure,
            "interest_rate_band": {"min": rate_low, "max": rate_high},
            "monthly_cost": round(emi, 2),
            "total_interest_at_min_rate": round(total_interest, 2),
            "processing_fee_pct": float(product.processing_fee_pct) if product.processing_fee_pct is not None else None,
            "annual_fee": float(product.annual_fee) if product.annual_fee is not None else None,
            "post_dbr": round(post_dbr, 4),
            "post_p_shortfall_12m": sim["p_shortfall_12m"],
            "post_runway_months": sim["expected_runway"],
            "passes_safety_gate": gate.is_safe,
            "veto_reason": gate.veto_reason,
            "constraints_failed": gate.constraints_failed,
            "eligibility_notes": product.eligibility_notes,
            "source_note": product.source_note,
            "source_url": product.source_url,
            "last_verified_date": product.last_verified_date.isoformat(),
        })

    # Cheapest first, but any product that fails its own gate sorts last
    # regardless of price — a cheap unsafe option is not a better option.
    matches.sort(key=lambda m: (not m["passes_safety_gate"], m["monthly_cost"]))
    return matches[:top_n]
