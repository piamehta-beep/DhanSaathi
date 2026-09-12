"""The safety gate — hard veto conditions (spec Section 6.3).

A pure deterministic function. No ML, no randomness, no network calls, no
database access. This is the architectural keystone: the constrained
optimizer may propose anything, but nothing reaches a customer without
passing every constraint here, and no model score can override a veto.
tests/test_safety_isolation.py fails the build if this package ever imports
an ML or LLM library.

Constraint IDs match the spec's table so that a veto reason can be traced
back to a numbered rule.
"""

from __future__ import annotations

from dataclasses import dataclass

CREDIT_PRODUCTS = ("personal_loan", "credit_card")

MAX_POST_DBR_CREDIT = 0.50          # C1
MAX_POST_DBR_NEW_LOAN = 0.40        # C2
MAX_P_SHORTFALL = 0.15              # C3
MIN_POST_RUNWAY_MONTHS = 3.0        # C4
MAX_ANOMALY_SCORE = 0.80            # C6
MIN_DATA_MONTHS = 3                 # C7
MAX_POST_DBR_INSURANCE = 0.60       # C9


@dataclass(frozen=True)
class Candidate:
    product_type: str
    amount: float | None = None
    tenure_months: int | None = None
    emi: float = 0.0


@dataclass(frozen=True)
class GateResult:
    is_safe: bool
    veto_reason: str | None
    constraints_passed: list[str]
    constraints_failed: list[str]


def safety_gate(
    candidate: Candidate,
    post_dbr: float,
    post_p_shortfall: float,
    post_runway: float,
    distress_state: bool,
    max_anomaly_score: float,
    data_months: int,
    savings_rate: float,
) -> GateResult:
    """Evaluate every hard constraint for one candidate.

    Returns which constraints applied and passed, which failed, and the first
    failure as the veto reason. All applicable constraints are evaluated
    rather than short-circuiting, so the audit log records the full picture.
    """
    passed: list[str] = []
    failed: list[str] = []

    def check(constraint_id: str, applies: bool, ok: bool) -> None:
        if not applies:
            return
        (passed if ok else failed).append(constraint_id)

    is_credit = candidate.product_type in CREDIT_PRODUCTS

    # C1: no new credit if post-DBR exceeds 0.50
    check("C1", is_credit, post_dbr <= MAX_POST_DBR_CREDIT)

    # C2: stricter DBR ceiling for a brand-new loan
    check("C2", candidate.product_type == "personal_loan", post_dbr <= MAX_POST_DBR_NEW_LOAN)

    # C3: no credit product if projected shortfall probability is too high
    check("C3", is_credit, post_p_shortfall <= MAX_P_SHORTFALL)

    # C4: no credit product if it leaves under 3 months of runway
    check("C4", is_credit, post_runway >= MIN_POST_RUNWAY_MONTHS)

    # C5: never extend credit to a customer already in distress
    check("C5", is_credit, not distress_state)

    # C6: no credit product while anomalous activity is unresolved
    check("C6", is_credit, max_anomaly_score < MAX_ANOMALY_SCORE)

    # C7: insufficient history to judge anything except protection products
    check("C7", candidate.product_type != "term_insurance", data_months >= MIN_DATA_MONTHS)

    # C8: cannot invest out of a negative savings rate
    check("C8", candidate.product_type == "mutual_fund_sip", savings_rate > 0)

    # C9: the insurance premium itself must remain affordable
    check("C9", candidate.product_type == "term_insurance", post_dbr <= MAX_POST_DBR_INSURANCE)

    veto_reason = _veto_reason(failed[0], candidate) if failed else None
    return GateResult(
        is_safe=not failed,
        veto_reason=veto_reason,
        constraints_passed=passed,
        constraints_failed=failed,
    )


def _veto_reason(constraint_id: str, candidate: Candidate) -> str:
    reasons = {
        "C1": "post_dbr_exceeds_0.50",
        "C2": "new_loan_dbr_exceeds_0.40",
        "C3": "shortfall_probability_exceeds_0.15",
        "C4": "runway_below_3_months",
        "C5": "customer_in_distress_state",
        "C6": "high_anomaly_score",
        "C7": "insufficient_data",
        "C8": "negative_savings_rate",
        "C9": "insurance_premium_unaffordable",
    }
    return reasons[constraint_id]
