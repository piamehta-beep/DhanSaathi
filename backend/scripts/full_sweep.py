"""Run the recommender across the entire customer base and audit every result.

Spec Section 9.3's pass criterion is zero hard-constraint violations across
all 1,000 customers, which is too slow for the normal test loop — the pytest
suite samples instead. This script is the full run.

Usage: python -m scripts.full_sweep
"""

from __future__ import annotations

import collections
import time

from app.database.connection import SessionLocal
from app.database.models import Customer
from app.safety.gate import (
    CREDIT_PRODUCTS,
    MAX_ANOMALY_SCORE,
    MAX_P_SHORTFALL,
    MIN_POST_RUNWAY_MONTHS,
)
from app.services.recommendation_service import recommend


def main() -> None:
    db = SessionLocal()
    started = time.time()
    violations = []
    by_persona = collections.defaultdict(collections.Counter)
    product_counts = collections.Counter()

    customers = db.query(Customer).all()
    for i, customer in enumerate(customers, start=1):
        rec = recommend(db, customer.id, persist=False)
        by_persona[customer.persona][rec["product_type"]] += 1
        product_counts[rec["product_type"]] += 1

        if rec["constraints_failed"]:
            violations.append((customer.external_id, "failed_constraints", rec["constraints_failed"]))

        if rec["product_type"] in CREDIT_PRODUCTS:
            sim = rec["simulation_summary"]
            if rec["distress_state"]:
                violations.append((customer.external_id, "credit_to_distressed", None))
            if sim["p_shortfall_12m"] > MAX_P_SHORTFALL:
                violations.append((customer.external_id, "p_shortfall", sim["p_shortfall_12m"]))
            if sim["expected_runway"] < MIN_POST_RUNWAY_MONTHS:
                violations.append((customer.external_id, "runway", sim["expected_runway"]))
            if rec["max_anomaly_score"] >= MAX_ANOMALY_SCORE:
                violations.append((customer.external_id, "anomaly", rec["max_anomaly_score"]))

        if i % 100 == 0:
            print(f"  ...{i}/{len(customers)} ({time.time() - started:.0f}s)", flush=True)

    print("\n=== Full sweep over all customers ===")
    print(f"customers evaluated : {len(customers)}")
    print(f"elapsed             : {time.time() - started:.0f}s")
    print(f"HARD VIOLATIONS     : {len(violations)}")
    for v in violations[:20]:
        print(f"   {v}")

    total = sum(product_counts.values())
    print("\nrecommendation mix overall:")
    for product, count in product_counts.most_common():
        print(f"  {product:18s} {count:5d}  ({count / total:.1%})")

    print("\nby persona:")
    for persona in sorted(by_persona):
        counts = by_persona[persona]
        n = sum(counts.values())
        no_action = counts.get("no_action", 0) / n
        mix = ", ".join(f"{k}={v}" for k, v in counts.most_common())
        print(f"  {persona:18s} n={n:4d}  no_action={no_action:5.1%}  {mix}")

    db.close()


if __name__ == "__main__":
    main()
