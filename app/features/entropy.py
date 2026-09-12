"""Entropy / spending-diversity features (spec Section 4.5)."""

from __future__ import annotations

import numpy as np

from app.features.context import FeatureContext


def compute_entropy_features(ctx: FeatureContext) -> dict:
    txns = ctx.txns
    if txns.empty:
        return {"category_entropy": 0.0, "merchant_diversity": 0.0, "category_concentration": 0.0}

    debits = txns[txns["type"] == "debit"]
    if debits.empty:
        return {"category_entropy": 0.0, "merchant_diversity": 0.0, "category_concentration": 0.0}

    by_category = debits.groupby("category")["amount"].sum()
    total = by_category.sum()
    p = (by_category / total).to_numpy()
    p = p[p > 0]
    category_entropy = float(-np.sum(p * np.log(p))) if len(p) > 0 else 0.0
    category_concentration = float(p.max()) if len(p) > 0 else 0.0

    recent_cutoff = ctx.snapshot_date.toordinal() - 90
    recent = txns[txns["txn_date"].apply(lambda d: d.toordinal()) >= recent_cutoff]
    merchant_diversity = (
        recent["merchant"].nunique() / len(recent) if len(recent) > 0 else 0.0
    )

    return {
        "category_entropy": round(category_entropy, 4),
        "merchant_diversity": round(float(merchant_diversity), 4),
        "category_concentration": round(category_concentration, 4),
    }
