"""Behavioral features (spec Section 4.7).

anomaly_count_30d/90d use the ground-truth `is_anomaly` tag on transactions
until the Isolation Forest detector (Section 5.4, Milestone 3) is wired up to
write to the `anomalies` table instead.
"""

from __future__ import annotations

from scipy import stats

from app.features.context import FeatureContext


def compute_behavioral_features(ctx: FeatureContext) -> dict:
    txns = ctx.txns
    if txns.empty:
        return {
            "anomaly_count_30d": 0, "anomaly_count_90d": 0, "txn_frequency_trend": 0.0,
            "late_night_ratio": 0.0, "weekend_ratio": 0.0,
        }

    snapshot_ord = ctx.snapshot_date.toordinal()
    days_before = txns["txn_date"].apply(lambda d: snapshot_ord - d.toordinal())

    anomaly_count_30d = int(((days_before <= 30) & txns["is_anomaly"]).sum())
    anomaly_count_90d = int(((days_before <= 90) & txns["is_anomaly"]).sum())

    monthly = ctx.monthly
    if len(monthly) >= 2:
        slope, _, _, _, _ = stats.linregress(monthly["t"].to_numpy(), monthly["n_txns"].to_numpy())
    else:
        slope = 0.0

    recent = txns[days_before <= 90]
    if not recent.empty:
        has_time = recent["txn_time"].notna()
        late_night = recent[has_time]["txn_time"].apply(lambda t: t.hour >= 22 or t.hour < 4)
        late_night_ratio = float(late_night.mean()) if has_time.any() else 0.0
        weekend = recent["txn_date"].apply(lambda d: d.weekday() >= 5)
        weekend_ratio = float(weekend.mean())
    else:
        late_night_ratio = 0.0
        weekend_ratio = 0.0

    return {
        "anomaly_count_30d": anomaly_count_30d,
        "anomaly_count_90d": anomaly_count_90d,
        "txn_frequency_trend": round(float(slope), 4),
        "late_night_ratio": round(late_night_ratio, 4),
        "weekend_ratio": round(weekend_ratio, 4),
    }
