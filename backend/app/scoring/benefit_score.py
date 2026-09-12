"""Customer Benefit Score (spec Sections 5.3 and 6.1).

    CBS(x) = 0.30*need_match(x)
           + 0.25*affordability_delta(x)
           + 0.20*risk_reduction(x)
           + 0.15*life_stage_align(x)
           - 0.10*distress_delta(x)

clamped to [-1, 1]. `no_action` scores exactly 0 by definition: no change, no
benefit, no harm. That is what makes "do nothing" a real competitor rather
than a fallback — any product must earn a positive score against it.

The distress penalty weight is deliberately small (0.10): the hard safety
gate already blocks anything that materially raises distress risk, so this
term only needs to discriminate among the marginal cases that survive it.
"""

from __future__ import annotations

from dataclasses import dataclass

W_NEED_MATCH = 0.30
W_AFFORDABILITY = 0.25
W_RISK_REDUCTION = 0.20
W_LIFE_STAGE = 0.15
W_DISTRESS_PENALTY = 0.10

LIFE_STAGE_ALIGNMENT = {
    "early_career": {
        "personal_loan": 0.5, "credit_card": 0.7, "term_insurance": 0.3, "mutual_fund_sip": 0.9,
    },
    "mid_career": {
        "personal_loan": 0.6, "credit_card": 0.5, "term_insurance": 0.7, "mutual_fund_sip": 0.6,
    },
    "pre_retirement": {
        "personal_loan": 0.2, "credit_card": 0.1, "term_insurance": 0.9, "mutual_fund_sip": 0.3,
    },
    "retired": {
        "personal_loan": 0.1, "credit_card": 0.1, "term_insurance": 0.5, "mutual_fund_sip": 0.2,
    },
    "student": {
        "personal_loan": 0.3, "credit_card": 0.4, "term_insurance": 0.2, "mutual_fund_sip": 0.6,
    },
}

# Cover of roughly 10x annual income is the conventional adequacy benchmark
# used to judge how much protection gap a term policy actually closes.
RECOMMENDED_COVER_MULTIPLE = 10


@dataclass(frozen=True)
class CBSComponents:
    need_match: float
    affordability_delta: float
    risk_reduction: float
    life_stage_align: float
    distress_delta: float

    def as_dict(self) -> dict:
        return {
            "need_match": round(self.need_match, 4),
            "affordability_delta": round(self.affordability_delta, 4),
            "risk_reduction": round(self.risk_reduction, 4),
            "life_stage_align": round(self.life_stage_align, 4),
            "distress_delta": round(self.distress_delta, 4),
        }


def life_stage_align(life_stage: str, product_type: str) -> float:
    return LIFE_STAGE_ALIGNMENT.get(life_stage, {}).get(product_type, 0.0)


def affordability_delta(pre_runway: float, post_runway: float) -> float:
    """(post - pre) / max(pre, 1), clamped to [-1, 1]."""
    delta = (post_runway - pre_runway) / max(pre_runway, 1.0)
    return max(-1.0, min(1.0, delta))


def risk_reduction(
    product_type: str,
    amount: float | None,
    monthly_income_mean: float,
    existing_cover: float = 0.0,
    emi_reduction_ratio: float = 0.0,
) -> float:
    """Protection gap closed (insurance) or EMI burden removed (consolidation).

    Products that do neither score 0 — they may still be worth recommending
    on need and alignment, but they do not reduce risk and should not be
    credited as if they did.
    """
    if product_type == "term_insurance" and amount:
        recommended_cover = RECOMMENDED_COVER_MULTIPLE * 12 * monthly_income_mean
        if recommended_cover <= 0:
            return 0.0
        gap_closed = min(amount, max(recommended_cover - existing_cover, 0.0))
        return max(0.0, min(1.0, gap_closed / recommended_cover))

    if product_type == "personal_loan" and emi_reduction_ratio > 0:
        return max(0.0, min(1.0, emi_reduction_ratio))

    return 0.0


def compute_cbs(components: CBSComponents) -> float:
    raw = (
        W_NEED_MATCH * components.need_match
        + W_AFFORDABILITY * components.affordability_delta
        + W_RISK_REDUCTION * components.risk_reduction
        + W_LIFE_STAGE * components.life_stage_align
        - W_DISTRESS_PENALTY * components.distress_delta
    )
    return max(-1.0, min(1.0, raw))
