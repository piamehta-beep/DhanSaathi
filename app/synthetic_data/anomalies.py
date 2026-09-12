"""Anomaly injection on top of a generated transaction stream (spec Section 2.4).

Distress-driven anomalies (missed_emi, income_drop, medical large_amount) are
already tagged by `transactions.py` since they require month-level context.
This module injects the remaining generic anomaly types up to each customer's
`n_anomalies` budget, and records the injected tag so the anomaly-detection
module (Section 5.4) can be validated against known ground truth.
"""

from __future__ import annotations

import datetime as dt

import numpy as np

ANOMALY_TYPES = ["large_amount", "unusual_time", "unusual_merchant", "frequency_spike"]


def inject_anomalies(rng: np.random.Generator, transactions: list[dict], profile: dict) -> list[dict]:
    n_target = profile["n_anomalies"]
    already_tagged = sum(1 for t in transactions if t["is_anomaly"])
    remaining = max(0, n_target - already_tagged)
    if remaining == 0:
        return transactions

    candidate_idxs = [
        i for i, t in enumerate(transactions)
        if t["type"] == "debit" and not t["is_recurring"] and not t["is_anomaly"]
    ]
    if not candidate_idxs:
        return transactions

    chosen = rng.choice(candidate_idxs, size=min(remaining, len(candidate_idxs)), replace=False)

    for i in chosen:
        anomaly_type = ANOMALY_TYPES[rng.integers(0, len(ANOMALY_TYPES))]
        txn = transactions[i]
        txn["is_anomaly"] = True
        txn["anomaly_type"] = anomaly_type

        if anomaly_type == "large_amount":
            txn["amount"] = round(txn["amount"] * float(rng.uniform(5, 10)), 2)
        elif anomaly_type == "unusual_time":
            txn["txn_time"] = dt.time(int(rng.integers(2, 5)), int(rng.integers(0, 60)))
        elif anomaly_type == "unusual_merchant":
            txn["merchant"] = "UNKNOWN_MERCHANT"
            txn["amount"] = round(txn["amount"] * float(rng.uniform(3, 6)), 2)
        elif anomaly_type == "frequency_spike":
            burst = []
            for _ in range(int(rng.integers(10, 15))):
                burst.append({**txn, "is_anomaly": True, "anomaly_type": "frequency_spike"})
            transactions.extend(burst)

    return transactions
