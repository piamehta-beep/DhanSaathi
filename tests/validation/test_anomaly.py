"""Anomaly detection validation against injected ground truth (spec Section 9.4).

Targets: precision > 0.70, recall > 0.60, F1 > 0.65, FPR < 0.05, measured at
the 0.7 score threshold against the `is_anomaly` tags the synthetic generator
recorded.

Per-type recall is reported as well as the aggregate, because the injected
types have very different detectability and an aggregate alone hides that.
`missed_emi` is deliberately absent from the per-transaction evaluation: it
is the *absence* of a transaction, so there is no row to score — detecting it
belongs to a recurring-payment check, not a per-transaction classifier.
"""

from __future__ import annotations

from collections import Counter

from app.database.models import Customer
from app.features.context import build_context
from app.features.pipeline import compute_features
from app.models.anomaly import score_transactions

SAMPLE_CUSTOMERS = 80
SCORE_THRESHOLD = 0.7


def test_anomaly_detection_precision_recall(db):
    tp = fp = fn = tn = 0
    by_type: Counter = Counter()
    hit_by_type: Counter = Counter()
    fp_by_method: Counter = Counter()

    for customer in db.query(Customer).limit(SAMPLE_CUSTOMERS).all():
        ctx = build_context(db, customer.id)
        features = compute_features(db, customer.id, persist=False)
        scored = score_transactions(ctx.txns, features["monthly_income_mean"])
        if scored.empty:
            continue

        predicted = scored["anomaly_score"] > SCORE_THRESHOLD
        truth = scored["is_anomaly"].astype(bool)

        tp += int((predicted & truth).sum())
        fp += int((predicted & ~truth).sum())
        fn += int((~predicted & truth).sum())
        tn += int((~predicted & ~truth).sum())

        for anomaly_type, was_caught in zip(scored.loc[truth, "anomaly_type"], predicted[truth]):
            by_type[anomaly_type] += 1
            hit_by_type[anomaly_type] += int(was_caught)
        for method in scored.loc[predicted & ~truth, "detection_method"]:
            fp_by_method[method] += 1

    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)
    fpr = fp / max(fp + tn, 1)

    print(f"\n=== Anomaly Detection Validation (n={SAMPLE_CUSTOMERS} customers) ===")
    print(f"  TP={tp}  FP={fp}  FN={fn}  TN={tn}")
    print(f"  precision = {precision:.4f}  (target > 0.70)")
    print(f"  recall    = {recall:.4f}  (target > 0.60)")
    print(f"  F1        = {f1:.4f}  (target > 0.65)")
    print(f"  FPR       = {fpr:.4f}  (target < 0.05)")
    print("\n  recall by injected anomaly type:")
    for anomaly_type, n in by_type.most_common():
        print(f"    {str(anomaly_type):18s} {hit_by_type[anomaly_type]:4d}/{n:4d} = {hit_by_type[anomaly_type] / n:.3f}")
    print(f"\n  false positives by detector: {dict(fp_by_method)}")
    print("=================================================================\n")

    assert precision > 0.70, f"precision {precision:.4f} below target"
    assert recall > 0.60, f"recall {recall:.4f} below target"
    assert f1 > 0.65, f"F1 {f1:.4f} below target"
    assert fpr < 0.05, f"FPR {fpr:.4f} above target"
