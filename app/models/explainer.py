"""SHAP-based explainability (spec Section 5.5).

Real feature attributions, not templated sentences. Two explainers are used
because the underlying models differ in kind:

- the need-match classifier is a gradient-boosted tree ensemble, so
  shap.TreeExplainer applies and is exact;
- the Cox model is not tree-based, so its attribution uses a linear
  decomposition of the partial hazard, beta_j * (x_j - mean_j), which is the
  exact Shapley value for a linear model and avoids the heavy sampling cost
  of KernelExplainer on every request.

Each returned feature carries a direction so the explanation can state which
way a factor pushed the decision, not merely how large it was.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import shap
from sqlalchemy.orm import Session

from app.models.need_match import get_or_train_need_model
from app.models.survival import get_or_train_model

TOP_N = 5


def explain_distress(db: Session, features: dict) -> list[dict]:
    """Attribution of the customer's distress risk to their features.

    For a Cox model log h(t|X) = log h_0(t) + sum_j beta_j * x_j, so the
    contribution of feature j to the log partial hazard, measured against the
    cohort mean, is exactly beta_j * (x_j - mean_j).
    """
    cph, scaler, _ = get_or_train_model(db)
    active_cols = list(cph.params_.index)

    raw = np.array([[float(features.get(c) or 0.0) for c in active_cols]])
    scaled = scaler.transform(raw)[0]
    betas = cph.params_.to_numpy()

    # Scaled inputs are already centred on the training mean, so the
    # contribution is simply beta_j * z_j.
    contributions = betas * scaled

    out = []
    for col, value, contribution in zip(active_cols, raw[0], contributions):
        out.append({
            "feature": col,
            "value": round(float(value), 4),
            "shap": round(float(contribution), 4),
            "direction": "increases_distress_risk" if contribution > 0 else "decreases_distress_risk",
        })
    out.sort(key=lambda d: abs(d["shap"]), reverse=True)
    return out[:TOP_N]


def explain_need_match(db: Session, features: dict, product_type: str) -> list[dict]:
    """TreeExplainer attribution for the predicted need of one product."""
    model = get_or_train_need_model(db)
    if product_type not in model.classes:
        return []

    from app.features.pipeline import FEATURE_VECTOR_ORDER, feature_vector

    vec = np.array([feature_vector(features)])
    scaled = model.scaler.transform(vec)

    explainer = shap.TreeExplainer(model.clf)
    shap_values = explainer.shap_values(scaled)

    class_index = model.classes.index(product_type)
    if isinstance(shap_values, list):
        values = np.array(shap_values[class_index])[0]
    else:
        arr = np.array(shap_values)
        values = arr[0, :, class_index] if arr.ndim == 3 else arr[0]

    out = []
    for col, value, contribution in zip(FEATURE_VECTOR_ORDER, vec[0], values):
        out.append({
            "feature": col,
            "value": round(float(value), 4),
            "shap": round(float(contribution), 4),
            "direction": "increases_need_match" if contribution > 0 else "decreases_need_match",
        })
    out.sort(key=lambda d: abs(d["shap"]), reverse=True)
    return out[:TOP_N]


def narrate(distress_attr: list[dict], need_attr: list[dict], product_type: str) -> str:
    """A plain-language summary built strictly from the computed attributions.

    No number here is invented: every value quoted comes from the attribution
    lists above. This is the structured ground truth the optional LLM layer
    rephrases; it never computes anything itself.
    """
    if not distress_attr:
        return "Not enough data to attribute this recommendation."

    risk_drivers = [d for d in distress_attr if d["direction"] == "increases_distress_risk"][:2]
    protective = [d for d in distress_attr if d["direction"] == "decreases_distress_risk"][:2]

    parts = []
    if risk_drivers:
        drivers = ", ".join(f"{d['feature']}={d['value']}" for d in risk_drivers)
        parts.append(f"Main risk factors: {drivers}.")
    if protective:
        strengths = ", ".join(f"{d['feature']}={d['value']}" for d in protective)
        parts.append(f"Offsetting strengths: {strengths}.")
    if need_attr and product_type != "no_action":
        top = need_attr[0]
        parts.append(
            f"{product_type} was matched most strongly on {top['feature']}={top['value']}."
        )
    if product_type == "no_action":
        parts.append("No product cleared the safety checks by enough margin to be worth acting on.")
    return " ".join(parts)
