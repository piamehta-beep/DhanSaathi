"""18-month transaction generation per customer (spec Section 2.3).

Produces three parallel lists of plain dicts (transactions, recurring
obligations, loans) that `generator.py` bulk-inserts. Calendar starts at
2024-01-01 so real-world seasonality (festival months, summer, back-to-school)
lines up with actual month-of-year.
"""

from __future__ import annotations

import datetime as dt

import numpy as np

from app.safety.affordability import compute_emi

START_DATE = dt.date(2024, 1, 1)
N_MONTHS = 18

MERCHANT_POOLS = {
    "groceries": ["BIGBASKET", "DMART", "RELIANCE FRESH", "MORE SUPERMARKET", "SPENCERS", "NATURE BASKET"],
    "utilities": ["TATA POWER", "BSES", "AIRTEL BROADBAND", "JIO FIBER", "MUNICIPAL WATER BOARD"],
    "entertainment": ["BOOKMYSHOW", "NETFLIX", "PVR CINEMAS", "SPOTIFY", "INOX", "HOTSTAR"],
    "dining": ["SWIGGY", "ZOMATO", "DOMINOS", "MCDONALDS", "CAFE COFFEE DAY", "BARBEQUE NATION"],
    "transport": ["UBER", "OLA", "RAPIDO", "IRCTC", "METRO CARD RECHARGE", "INDIAN OIL PETROL PUMP"],
    "shopping": ["AMAZON", "FLIPKART", "MYNTRA", "AJIO", "CROMA", "LIFESTYLE"],
    "medical": ["APOLLO PHARMACY", "MEDPLUS", "FORTIS HOSPITAL", "PRACTO", "1MG"],
    "education": ["BYJUS", "UDEMY", "COURSERA", "SCHOOL FEE PORTAL", "UNACADEMY"],
}

DISCRETIONARY_CATEGORIES = {
    "groceries": {"freq": (4, 8), "amount": (500, 3000)},
    "utilities": {"freq": (2, 4), "amount": (500, 2000)},
    "entertainment": {"freq": (2, 6), "amount": (200, 2000)},
    "dining": {"freq": (3, 8), "amount": (200, 1000)},
    "transport": {"freq": (4, 10), "amount": (100, 500)},
    "shopping": {"freq": (1, 5), "amount": (500, 5000)},
    "medical": {"freq": (0, 2), "amount": (500, 5000)},
    "education": {"freq": (0, 2), "amount": (1000, 5000)},
}

LOAN_RATE_POOL = [10.5, 11.5, 12.5, 13.5, 14.5]
LOAN_TENURE_POOL = [24, 36, 48, 60]


def _month_date(month_idx: int, day: int) -> dt.date:
    year = START_DATE.year + (START_DATE.month - 1 + month_idx - 1) // 12
    month = (START_DATE.month - 1 + month_idx - 1) % 12 + 1
    day = min(day, 28)
    return dt.date(year, month, day)


def _seasonal_multiplier(category: str, calendar_month: int) -> float:
    mult = 1.0
    if category == "shopping" and calendar_month in (10, 11):
        mult *= 1.5
    if category == "shopping" and calendar_month == 12:
        mult *= 1.4
    if category == "entertainment" and calendar_month in (10, 11):
        mult *= 1.4
    if category == "dining" and calendar_month in (10, 11):
        mult *= 1.3
    if category == "utilities" and calendar_month in (4, 5, 6):
        mult *= 1.1
    if category == "education" and calendar_month in (6, 7):
        mult *= 1.3
    return mult


def _reverse_emi_to_principal(emi: float, annual_rate: float, tenure_months: int) -> float:
    monthly_rate = annual_rate / 12 / 100
    if monthly_rate == 0:
        return emi * tenure_months
    factor = (1 + monthly_rate) ** tenure_months
    return emi * (factor - 1) / (monthly_rate * factor)


def _income_multiplier_for_month(profile: dict, month_idx: int) -> tuple[float, str | None]:
    """Apply distress-driven income shocks (spec Section 2.5). Returns (multiplier, anomaly_type_or_None)."""
    persona = profile["persona"]
    dem = profile.get("distress_event_month")

    if persona == "distressed" and dem is not None:
        job_loss_window = profile.get("job_loss_window") or (8, 12)
        medical_window = profile.get("medical_emergency_window") or (10, 14)
        decline_start = 6
        if month_idx >= decline_start:
            base = 1 - 0.05 * (month_idx - decline_start + 1)
            base = max(base, 0.4)
        else:
            base = 1.0
        if job_loss_window[0] <= month_idx <= job_loss_window[0] + 1:
            return 0.3, "income_drop"
        return base, None

    if persona == "over_leveraged" and dem is not None:
        if 10 <= month_idx <= 14:
            return 0.9, None

    return 1.0, None


def generate_transactions(rng: np.random.Generator, profile: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Generate (transactions, recurring_obligations, loans) for one customer."""
    transactions: list[dict] = []
    obligations: list[dict] = []
    loans: list[dict] = []

    income_mean = profile["monthly_income_mean"]
    emi_ratio = profile["emi_ratio"]
    savings_rate = profile["savings_rate"]
    income_cv = profile["income_cv"]
    seasonality_lo, seasonality_hi = profile["seasonality_range"]
    credits_lo, credits_hi = profile["income_credits_per_month"]

    total_emi_target = income_mean * emi_ratio
    if total_emi_target > 100:
        annual_rate = float(rng.choice(LOAN_RATE_POOL))
        tenure = int(rng.choice(LOAN_TENURE_POOL))
        principal = round(_reverse_emi_to_principal(total_emi_target, annual_rate, tenure), 2)
        emi_amount = compute_emi(principal, annual_rate, tenure)
        loan_start = _month_date(1, 5)
        loans.append({
            "product_type": "personal_loan",
            "principal": principal,
            "interest_rate": annual_rate,
            "tenure_months": tenure,
            "emi_amount": emi_amount,
            "outstanding": principal,
            "start_date": loan_start,
            "end_date": None,
            "status": "active",
        })
        obligations.append({
            "type": "emi",
            "amount": emi_amount,
            "frequency": "monthly",
            "day_of_month": 5,
            "start_date": loan_start,
            "end_date": None,
            "active": True,
            "_loan_index": 0,
        })
    else:
        emi_amount = 0.0

    rent_amount = round(float(rng.uniform(8000, 25000)) * (income_mean / 60000), 2)
    obligations.append({
        "type": "rent", "amount": rent_amount, "frequency": "monthly",
        "day_of_month": 1, "start_date": START_DATE, "end_date": None, "active": True,
    })

    insurance_amount = round(float(rng.uniform(1000, 5000)), 2)
    obligations.append({
        "type": "insurance_premium", "amount": insurance_amount, "frequency": "monthly",
        "day_of_month": 10, "start_date": START_DATE, "end_date": None, "active": True,
    })

    sip_amount = 0.0
    if savings_rate > 0:
        sip_amount = round(savings_rate * income_mean * 0.3, 2)
        obligations.append({
            "type": "sip", "amount": sip_amount, "frequency": "monthly",
            "day_of_month": 10, "start_date": START_DATE, "end_date": None, "active": True,
        })

    base_discretionary_mid = sum(
        ((cfg["freq"][0] + cfg["freq"][1]) / 2) * ((cfg["amount"][0] + cfg["amount"][1]) / 2)
        for cfg in DISCRETIONARY_CATEGORIES.values()
    )
    target_discretionary = income_mean * (1 - savings_rate) - emi_amount - rent_amount - insurance_amount - sip_amount
    target_discretionary = max(target_discretionary, income_mean * 0.05)
    discretionary_scale = float(np.clip(target_discretionary / base_discretionary_mid, 0.1, 3.0))

    missed_emi_month = None
    if profile["persona"] in ("over_leveraged", "distressed") and profile.get("distress_event_month"):
        missed_emi_month = profile["distress_event_month"]

    for month_idx in range(1, N_MONTHS + 1):
        calendar_month = _month_date(month_idx, 1).month
        income_mult, income_anomaly = _income_multiplier_for_month(profile, month_idx)
        month_income_target = income_mean * income_mult

        n_credits = int(rng.integers(credits_lo, credits_hi + 1))
        if n_credits <= 1:
            amount = round(month_income_target * (1 + rng.normal(0, 0.03)), 2)
            day = int(rng.choice([1, 5, 10]))
            txn = {
                "txn_date": _month_date(month_idx, day), "txn_time": dt.time(9, 0),
                "amount": max(amount, 0), "type": "credit", "category": "salary",
                "merchant": "EMPLOYER CORP", "description": "SALARY CREDIT",
                "is_recurring": True, "is_anomaly": income_anomaly is not None,
                "anomaly_type": income_anomaly,
            }
            transactions.append(txn)
        else:
            per_credit_mean = month_income_target / n_credits
            days = sorted(rng.integers(1, 28, size=n_credits).tolist())
            for day in days:
                amount = round(float(rng.lognormal(np.log(max(per_credit_mean, 1)), 0.4)), 2)
                transactions.append({
                    "txn_date": _month_date(month_idx, int(day)), "txn_time": dt.time(int(rng.integers(8, 20)), 0),
                    "amount": amount, "type": "credit", "category": "gig_income",
                    "merchant": "PLATFORM PAYOUT", "description": "GIG PLATFORM PAYOUT",
                    "is_recurring": False, "is_anomaly": False, "anomaly_type": None,
                })

        if emi_amount > 0 and month_idx != missed_emi_month:
            transactions.append({
                "txn_date": _month_date(month_idx, 5), "txn_time": dt.time(10, 0),
                "amount": emi_amount, "type": "debit", "category": "emi",
                "merchant": "LOAN EMI - AUTO DEBIT", "description": "PERSONAL LOAN EMI",
                "is_recurring": True, "is_anomaly": False, "anomaly_type": None,
            })

        transactions.append({
            "txn_date": _month_date(month_idx, 1), "txn_time": dt.time(6, 0),
            "amount": rent_amount, "type": "debit", "category": "rent",
            "merchant": "HOUSE OWNER - RENT", "description": "MONTHLY RENT",
            "is_recurring": True, "is_anomaly": False, "anomaly_type": None,
        })
        transactions.append({
            "txn_date": _month_date(month_idx, 10), "txn_time": dt.time(11, 0),
            "amount": insurance_amount, "type": "debit", "category": "insurance_premium",
            "merchant": "LIC / INSURER", "description": "INSURANCE PREMIUM",
            "is_recurring": True, "is_anomaly": False, "anomaly_type": None,
        })
        if sip_amount > 0:
            transactions.append({
                "txn_date": _month_date(month_idx, 10), "txn_time": dt.time(11, 30),
                "amount": sip_amount, "type": "debit", "category": "sip",
                "merchant": "MUTUAL FUND SIP", "description": "SIP INVESTMENT",
                "is_recurring": True, "is_anomaly": False, "anomaly_type": None,
            })

        seasonality = float(rng.uniform(seasonality_lo, seasonality_hi))
        for category, cfg in DISCRETIONARY_CATEGORIES.items():
            freq = int(rng.integers(cfg["freq"][0], cfg["freq"][1] + 1))
            merchants = MERCHANT_POOLS[category]
            for _ in range(freq):
                base_amount = float(rng.uniform(*cfg["amount"]))
                mult = seasonality * _seasonal_multiplier(category, calendar_month) * discretionary_scale
                amount = round(base_amount * mult, 2)
                day = int(rng.integers(1, 29))
                merchant = merchants[rng.integers(0, len(merchants))]
                transactions.append({
                    "txn_date": _month_date(month_idx, day),
                    "txn_time": dt.time(int(rng.integers(7, 23)), int(rng.integers(0, 60))),
                    "amount": amount, "type": "debit", "category": category,
                    "merchant": merchant, "description": f"{merchant} - {category.upper()}",
                    "is_recurring": False, "is_anomaly": False, "anomaly_type": None,
                })

        medical_window = profile.get("medical_emergency_window")
        if profile["persona"] == "distressed" and medical_window and medical_window[0] <= month_idx <= medical_window[1]:
            if month_idx == medical_window[0]:
                emergency_amount = round(float(rng.uniform(3, 6)) * income_mean, 2)
                transactions.append({
                    "txn_date": _month_date(month_idx, 15), "txn_time": dt.time(2, 30),
                    "amount": emergency_amount, "type": "debit", "category": "medical",
                    "merchant": "FORTIS HOSPITAL", "description": "MEDICAL EMERGENCY",
                    "is_recurring": False, "is_anomaly": True, "anomaly_type": "large_amount",
                })

    for i, ob in enumerate(obligations):
        ob["_index"] = i

    return transactions, obligations, loans
