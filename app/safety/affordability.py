"""Deterministic EMI and affordability arithmetic.

Zero ML/LLM dependencies by design (see tests/test_safety_isolation.py) — this
module is the ground truth for every EMI and DBR figure used elsewhere in the
system (synthetic data generation, the recommender, the safety gate).
"""


def compute_emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    """Standard reducing-balance EMI formula.

    EMI = P * r * (1+r)^n / ((1+r)^n - 1), where r = annual_rate/12/100 (monthly
    rate), n = tenure_months. annual_rate is a percentage (e.g. 12.5 for 12.5%).
    """
    monthly_rate = annual_rate / 12 / 100
    if monthly_rate == 0:
        return round(principal / tenure_months, 2)
    factor = (1 + monthly_rate) ** tenure_months
    emi = principal * monthly_rate * factor / (factor - 1)
    return round(emi, 2)


def compute_post_dbr(total_emi_existing: float, candidate_emi: float, monthly_income_mean: float) -> float:
    """Debt Burden Ratio after adding a candidate EMI to existing obligations."""
    if monthly_income_mean <= 0:
        return float("inf")
    return (total_emi_existing + candidate_emi) / monthly_income_mean
