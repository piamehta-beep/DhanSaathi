"""Persona definitions and per-customer parameter sampling (spec Section 2.2).

Each persona entry fully specifies the distributions used to sample one
customer's static profile and the generation parameters `transactions.py`
needs to build 18 months of realistic transaction history for them.
"""

from __future__ import annotations

import numpy as np

CITIES = [
    ("Mumbai", "Maharashtra"),
    ("Pune", "Maharashtra"),
    ("Delhi", "Delhi"),
    ("Bengaluru", "Karnataka"),
    ("Hyderabad", "Telangana"),
    ("Chennai", "Tamil Nadu"),
    ("Kolkata", "West Bengal"),
    ("Ahmedabad", "Gujarat"),
    ("Jaipur", "Rajasthan"),
    ("Lucknow", "Uttar Pradesh"),
]

FIRST_NAMES = [
    "Rajesh", "Priya", "Amit", "Sunita", "Vikram", "Anjali", "Suresh", "Kavita",
    "Arjun", "Neha", "Sanjay", "Pooja", "Ravi", "Deepa", "Manoj", "Shweta",
    "Karan", "Meera", "Rohit", "Divya",
]
LAST_NAMES = [
    "Kumar", "Sharma", "Patel", "Singh", "Gupta", "Rao", "Nair", "Reddy",
    "Mehta", "Iyer", "Joshi", "Desai", "Verma", "Chatterjee", "Pillai",
]

PERSONAS = {
    "stable_salaried": {
        "share": 0.25,
        "n": 250,
        "life_stage": "mid_career",
        "age": (35, 5),
        "income_mean": (80000, 5000),
        "emi_ratio": (0.20, 0.30),
        "savings_rate": (0.15, 0.25),
        "runway_months": (6, 12),
        "income_cv": 0.05,
        "seasonality": (1.0, 1.1),
        "n_anomalies": (1, 2),
        "income_credits_per_month": (1, 1),
        "savings_trend": "slightly_positive",
        "distress_event_rate": 0.0,
    },
    "gig_worker": {
        "share": 0.15,
        "n": 150,
        "life_stage": "early_career",
        "age": (28, 4),
        "income_mean": (45000, 12000),
        "emi_ratio": (0.10, 0.35),
        "savings_rate": (0.05, 0.15),
        "runway_months": (2, 5),
        "income_cv": 0.30,
        "seasonality": (0.7, 1.4),
        "n_anomalies": (3, 5),
        "income_credits_per_month": (3, 5),
        "savings_trend": "flat",
        "distress_event_rate": 0.0,
    },
    "over_leveraged": {
        "share": 0.15,
        "n": 150,
        "life_stage": "mid_career",
        "age": (38, 6),
        "income_mean": (60000, 7000),
        "emi_ratio": (0.50, 0.70),
        "savings_rate": (-0.05, 0.05),
        "runway_months": (0.5, 2),
        "income_cv": 0.12,
        "seasonality": (0.9, 1.2),
        "n_anomalies": (2, 4),
        "income_credits_per_month": (1, 1),
        "savings_trend": "negative",
        "distress_event_rate": 0.30,
        "distress_event_window": (12, 18),
        "distress_event_type": "missed_emi",
    },
    "young_earner": {
        "share": 0.20,
        "n": 200,
        "life_stage": "early_career",
        "age": (24, 2),
        "income_mean": (35000, 3000),
        "emi_ratio": (0.05, 0.15),
        "savings_rate": (0.10, 0.20),
        "runway_months": (3, 8),
        "income_cv": 0.08,
        "seasonality": (0.8, 1.5),
        "n_anomalies": (2, 3),
        "income_credits_per_month": (1, 1),
        "savings_trend": "positive",
        "distress_event_rate": 0.0,
    },
    "near_retirement": {
        "share": 0.10,
        "n": 100,
        "life_stage": "pre_retirement",
        "age": (55, 4),
        "income_mean": (70000, 6000),
        "emi_ratio": (0.30, 0.40),
        "savings_rate": (0.20, 0.30),
        "runway_months": (15, 30),
        "income_cv": 0.06,
        "seasonality": (0.95, 1.05),
        "n_anomalies": (1, 2),
        "income_credits_per_month": (1, 1),
        "savings_trend": "slightly_negative",
        "distress_event_rate": 0.0,
        "life_event_window": (15, 18),
    },
    "distressed": {
        "share": 0.15,
        "n": 150,
        "life_stage": "mid_career",
        "age": (32, 5),
        "income_mean": (40000, 10000),
        "emi_ratio": (0.60, 0.80),
        "savings_rate": (-0.10, 0.02),
        "runway_months": (0, 1.5),
        "income_cv": 0.25,
        "seasonality": (0.9, 1.2),
        "n_anomalies": (5, 8),
        "income_credits_per_month": (1, 1),
        "savings_trend": "negative",
        "distress_event_rate": 0.60,
        "distress_event_window": (6, 15),
        "distress_event_type": "job_loss_and_medical",
        "job_loss_window": (8, 12),
        "medical_emergency_window": (10, 14),
    },
}

assert abs(sum(p["share"] for p in PERSONAS.values()) - 1.0) < 1e-9
assert sum(p["n"] for p in PERSONAS.values()) == 1000


def generate_customer(rng: np.random.Generator, persona_name: str, external_id: str) -> dict:
    """Sample one customer's static profile plus generation parameters."""
    cfg = PERSONAS[persona_name]

    age = int(max(18, round(rng.normal(*cfg["age"]))))
    income_mean = float(max(10000, rng.normal(*cfg["income_mean"])))
    income_std = float(income_mean * cfg["income_cv"])
    emi_ratio = float(rng.uniform(*cfg["emi_ratio"]))
    savings_rate = float(rng.uniform(*cfg["savings_rate"]))
    runway_months = float(rng.uniform(*cfg["runway_months"]))

    monthly_expenses_approx = income_mean * (1 - savings_rate)
    liquid_savings = float(max(0.0, runway_months * monthly_expenses_approx))

    city, state = cfg_city = CITIES[rng.integers(0, len(CITIES))]
    name = f"{FIRST_NAMES[rng.integers(0, len(FIRST_NAMES))]} {LAST_NAMES[rng.integers(0, len(LAST_NAMES))]}"

    seasonality_lo, seasonality_hi = cfg["seasonality"]
    n_anomalies = int(rng.integers(cfg["n_anomalies"][0], cfg["n_anomalies"][1] + 1))

    has_distress_event = bool(rng.random() < cfg["distress_event_rate"])
    distress_event_month = None
    distress_event_type = None
    if has_distress_event:
        window = cfg.get("distress_event_window", (6, 15))
        distress_event_month = int(rng.integers(window[0], window[1] + 1))
        distress_event_type = cfg.get("distress_event_type", "distress")

    return {
        "external_id": external_id,
        "persona": persona_name,
        "name": name,
        "age": age,
        "city": city,
        "state": state,
        "preferred_language": "hi",
        "life_stage": cfg["life_stage"],
        "monthly_income_mean": income_mean,
        "monthly_income_std": income_std,
        "liquid_savings": liquid_savings,
        "emi_ratio": emi_ratio,
        "savings_rate": savings_rate,
        "income_cv": cfg["income_cv"],
        "seasonality_range": (seasonality_lo, seasonality_hi),
        "n_anomalies": n_anomalies,
        "income_credits_per_month": cfg["income_credits_per_month"],
        "savings_trend": cfg["savings_trend"],
        "distress_state": False,
        "distress_event_month": distress_event_month,
        "distress_event_type": distress_event_type,
        "job_loss_window": cfg.get("job_loss_window"),
        "medical_emergency_window": cfg.get("medical_emergency_window"),
    }


def assign_personas(rng: np.random.Generator) -> list[str]:
    """Return a shuffled list of 1000 persona labels matching the exact counts."""
    labels: list[str] = []
    for persona_name, cfg in PERSONAS.items():
        labels.extend([persona_name] * cfg["n"])
    rng.shuffle(labels)
    return labels
