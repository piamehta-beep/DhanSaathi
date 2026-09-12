"""Credit-utilization features (spec Section 4.6). Only meaningful when the
customer has a credit_limit on file; returns None values otherwise so the
downstream pipeline can distinguish "no credit product" from "0% utilized"."""

from __future__ import annotations

from app.features.context import FeatureContext


def compute_credit_features(ctx: FeatureContext) -> dict:
    customer = ctx.customer
    if customer.credit_limit is None or float(customer.credit_limit) == 0:
        return {"credit_utilization": None, "credit_util_trend": None}

    credit_utilization = float(customer.credit_outstanding or 0) / float(customer.credit_limit)
    return {"credit_utilization": round(credit_utilization, 4), "credit_util_trend": 0.0}
