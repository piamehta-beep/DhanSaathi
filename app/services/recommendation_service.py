"""End-to-end recommendation pipeline.

Wires the modules in the order the architecture prescribes:
features -> simulation -> survival -> anomaly -> optimizer -> safety gate,
then persists the result and writes an audit record. Each stage stays a pure
module; this service is the only place that knows the order.
"""

from __future__ import annotations

import numpy as np
from sqlalchemy.orm import Session

from app.database.models import Customer, Recommendation
from app.features.context import build_context
from app.features.pipeline import compute_features
from app.models.anomaly import max_anomaly_score, score_transactions
from app.models.cashflow_sim import run_simulation
from app.models.confidence import bootstrap_shortfall_ci, cbs_confidence
from app.models.explainer import explain_distress, explain_need_match, narrate
from app.models.recommender import (
    Evaluation,
    match_bank_products,
    no_action_evaluation,
    optimize,
)
from app.models.survival import predict_distress
from app.services.audit import record

N_PATHS = 500
ANOMALY_WINDOW_DAYS = 30


def build_simulation_inputs(db: Session, customer_id, features: dict) -> tuple[dict, dict]:
    """Returns (sim_inputs, baseline_scenario)."""
    ctx = build_context(db, customer_id)

    if ctx.monthly.empty:
        income_series = np.array([])
        fixed_non_emi = 0.0
        start_calendar_month = 1
    else:
        income_series = ctx.monthly["income"].to_numpy()
        fixed_non_emi = float(
            (ctx.monthly["expenses"] - ctx.monthly["discretionary"] - ctx.monthly["emi"]).mean()
        )
        start_calendar_month = (ctx.snapshot_date.month % 12) + 1

    sim_inputs = {
        "income_series": income_series,
        "fixed_expenses": fixed_non_emi + features["total_emi"],
        "monthly_discretionary_mean": features["monthly_discretionary_mean"],
        "expense_volatility": features["expense_volatility"],
        "liquid_savings": features["liquid_savings"],
        "min_buffer": features["min_buffer"],
        "monthly": ctx.monthly,
        "start_calendar_month": start_calendar_month,
        "n_paths": N_PATHS,
    }

    baseline_sim = run_simulation(
        income_series=sim_inputs["income_series"],
        fixed_expenses=sim_inputs["fixed_expenses"],
        monthly_discretionary_mean=sim_inputs["monthly_discretionary_mean"],
        expense_volatility=sim_inputs["expense_volatility"],
        liquid_savings=sim_inputs["liquid_savings"],
        min_buffer=sim_inputs["min_buffer"],
        monthly=sim_inputs["monthly"],
        start_calendar_month=sim_inputs["start_calendar_month"],
        n_paths=N_PATHS,
        months_projected=12,
        seed=42,
    )
    baseline = {
        "p_shortfall_12m": baseline_sim["p_shortfall_12m"],
        "expected_runway": baseline_sim["expected_runway"],
        "dbr": features["dbr"],
        "liquidity_percentiles": baseline_sim["liquidity_percentiles"],
    }
    return sim_inputs, baseline


def assess_customer(db: Session, customer_id) -> dict:
    """Run every analytical stage for one customer, without deciding anything."""
    customer = db.query(Customer).filter(Customer.id == customer_id).one()
    features = compute_features(db, customer_id, persist=False)
    ctx = build_context(db, customer_id)

    scored = score_transactions(ctx.txns, features["monthly_income_mean"])

    # Constraint C6 asks whether anomalous activity is *unresolved*, so the
    # score is taken over a recent window rather than the whole history. The
    # spec fixes the 0.80 threshold but not the window; measured on the seeded
    # data, "any anomaly ever" puts 98% of customers over the line and turns
    # C6 into a blanket ban on credit rather than a safety check. A 30-day
    # window (matching the anomaly_count_30d feature) blocks 18%.
    max_anomaly = max_anomaly_score(scored, ANOMALY_WINDOW_DAYS, ctx.snapshot_date)

    distress = predict_distress(db, customer_id)
    sim_inputs, baseline = build_simulation_inputs(db, customer_id, features)

    # distress_state is a derived judgement, not a stored flag: a customer is
    # treated as in distress when the survival model puts them above a
    # materially elevated 12-month probability, or their runway is already
    # under the minimum buffer the gate would demand of a new product.
    distress_state = bool(
        distress["distress_probability_12m"] >= 0.30
        or (features["liquidity_runway"] is not None and features["liquidity_runway"] < 1.0)
    )

    return {
        "customer": customer,
        "features": features,
        "scored_transactions": scored,
        "max_anomaly": max_anomaly,
        "distress": distress,
        "distress_state": distress_state,
        "sim_inputs": sim_inputs,
        "baseline": baseline,
    }


def _simulation_summary(selected: Evaluation, baseline: dict) -> dict:
    if selected.product_type == "no_action" or not selected.simulation:
        percentiles = baseline.get("liquidity_percentiles", {})
        return {
            "p_shortfall_12m": baseline["p_shortfall_12m"],
            "expected_runway": baseline["expected_runway"],
            "p5_liquidity_12m": percentiles.get("12", {}).get("p5"),
            "p95_liquidity_12m": percentiles.get("12", {}).get("p95"),
        }
    percentiles = selected.simulation["liquidity_percentiles"]["12"]
    return {
        "p_shortfall_12m": selected.post_p_shortfall,
        "expected_runway": selected.post_runway,
        "p5_liquidity_12m": percentiles["p5"],
        "p95_liquidity_12m": percentiles["p95"],
    }


def recommend(db: Session, customer_id, language: str = "hi", persist: bool = True) -> dict:
    assessment = assess_customer(db, customer_id)
    customer = assessment["customer"]
    features = assessment["features"]

    selected, evaluations = optimize(
        db=db,
        features=features,
        sim_inputs=assessment["sim_inputs"],
        baseline=assessment["baseline"],
        distress_probability=assessment["distress"]["distress_probability_12m"],
        max_anomaly=assessment["max_anomaly"],
        life_stage=customer.life_stage,
        distress_state=assessment["distress_state"],
        age=customer.age,
    )

    # Propagate simulation uncertainty onto CBS and decide whether the
    # evidence is firm enough to act on at all.
    if selected.product_type != "no_action" and "_liquidity_paths" in selected.simulation:
        any_shortfall = (
            selected.simulation["_liquidity_paths"] < features["min_buffer"]
        ).any(axis=1)
        ci = bootstrap_shortfall_ci(any_shortfall, seed=42)
    else:
        baseline_p = assessment["baseline"]["p_shortfall_12m"]
        ci = {"p10": baseline_p, "p90": baseline_p}

    confidence = cbs_confidence(
        cbs_score=selected.cbs,
        p_shortfall_ci=ci,
        data_months=features["data_months"],
    )

    if not confidence["act"] and selected.product_type != "no_action":
        selected = no_action_evaluation(assessment["baseline"], {})

    status = "recommended" if selected.product_type != "no_action" else "no_action"

    distress_attribution = explain_distress(db, features)
    need_attribution = explain_need_match(db, features, selected.product_type)
    explanation = narrate(distress_attribution, need_attribution, selected.product_type)

    # When nothing was recommended, surface why the strongest blocked
    # alternative was blocked — "no_action" on its own tells the customer
    # nothing actionable.
    veto_reason = selected.gate.veto_reason
    if status == "no_action" and veto_reason is None:
        blocked = [e for e in evaluations if not e.gate.is_safe]
        if blocked:
            veto_reason = max(blocked, key=lambda e: e.cbs).gate.veto_reason

    result = {
        "customer_id": str(customer_id),
        "product_type": selected.product_type,
        "amount": float(selected.amount) if selected.amount is not None else None,
        "tenure_months": selected.tenure_months,
        "monthly_cost": round(selected.emi, 2) if selected.emi else None,
        "cbs_score": round(selected.cbs, 4),
        "cbs_components": selected.components.as_dict(),
        "constraints_passed": selected.gate.constraints_passed,
        "constraints_failed": selected.gate.constraints_failed,
        "simulation_summary": _simulation_summary(selected, assessment["baseline"]),
        "distress_probability": assessment["distress"]["distress_probability_12m"],
        "distress_state": assessment["distress_state"],
        "max_anomaly_score": round(assessment["max_anomaly"], 4),
        "status": status,
        "veto_reason": veto_reason,
        "language": language,
        "candidates_evaluated": len(evaluations),
        "candidates_feasible": sum(1 for e in evaluations if e.gate.is_safe),
        "confidence_level": confidence["confidence_level"],
        "confidence_interval": confidence["confidence_interval"],
        "shap_values": distress_attribution,
        "need_match_attribution": need_attribution,
        "explanation": explanation,
        "llm_explanation": None,
    }

    if persist:
        row = Recommendation(
            customer_id=customer_id,
            product_type=result["product_type"],
            amount=result["amount"],
            tenure_months=result["tenure_months"],
            cbs_score=result["cbs_score"],
            cbs_components=result["cbs_components"],
            constraints_passed=result["constraints_passed"],
            constraints_failed=result["constraints_failed"],
            shap_values=result["shap_values"],
            simulation_summary=result["simulation_summary"],
            distress_probability=result["distress_probability"],
            confidence_level=result["confidence_level"],
            confidence_interval=result["confidence_interval"],
            status=result["status"],
            veto_reason=result["veto_reason"],
            language=language,
        )
        db.add(row)
        db.flush()
        result["recommendation_id"] = str(row.id)

        record(
            db,
            customer_id=customer_id,
            action="recommendation_generated" if status == "recommended" else "safety_veto",
            module="recommender",
            input_payload={"features": features, "customer_id": str(customer_id)},
            output_summary={
                "product": result["product_type"],
                "cbs": result["cbs_score"],
                "status": status,
                "veto_reason": veto_reason,
            },
        )
        db.commit()

    result["_selected"] = selected
    result["_assessment"] = assessment
    return result
