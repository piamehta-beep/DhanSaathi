import uuid

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Customer, SimulationResult
from app.features.context import build_context
from app.features.pipeline import compute_features
from app.models.cashflow_sim import run_simulation
from app.models.confidence import bootstrap_shortfall_ci
from app.safety.affordability import compute_emi
from app.schemas import SimulateResponse

router = APIRouter(prefix="/api/v1/customers", tags=["simulation"])


class SimulateRequest(BaseModel):
    scenarios: list[str] = ["baseline"]
    loan_amount: float | None = None
    loan_tenure_months: int | None = None
    loan_interest_rate: float | None = None
    n_paths: int = 1000
    months_projected: int = 12
    method: str = "auto"


SCENARIO_EMI = {"baseline": 0.0, "wait": 0.0}


@router.post("/{customer_id}/simulate", response_model=SimulateResponse)
def simulate(customer_id: uuid.UUID, req: SimulateRequest, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail={"error": "customer_not_found"})

    ctx = build_context(db, customer_id)
    features = compute_features(db, customer_id, persist=False)

    income_series = ctx.monthly["income"].to_numpy() if not ctx.monthly.empty else np.array([])
    fixed_non_emi = float(
        (ctx.monthly["expenses"] - ctx.monthly["discretionary"] - ctx.monthly["emi"]).mean()
    ) if not ctx.monthly.empty else 0.0
    baseline_emi = features["total_emi"]
    start_calendar_month = int(ctx.snapshot_date.month) + 1
    if start_calendar_month > 12:
        start_calendar_month = 1

    scenario_emis = dict(SCENARIO_EMI)
    new_loan_emi = 0.0
    if req.loan_amount and req.loan_tenure_months and req.loan_interest_rate:
        new_loan_emi = compute_emi(req.loan_amount, req.loan_interest_rate, req.loan_tenure_months)
    scenario_emis["take_loan"] = new_loan_emi
    scenario_emis["smaller_loan"] = new_loan_emi / 2 if new_loan_emi else 0.0

    results = {}
    confidence_bands = {}
    for scenario in req.scenarios:
        delta_emi = scenario_emis.get(scenario, 0.0)
        fixed_expenses = fixed_non_emi + baseline_emi + delta_emi

        sim = run_simulation(
            income_series=income_series,
            fixed_expenses=fixed_expenses,
            monthly_discretionary_mean=features["monthly_discretionary_mean"],
            expense_volatility=features["expense_volatility"],
            liquid_savings=features["liquid_savings"],
            min_buffer=features["min_buffer"],
            monthly=ctx.monthly,
            start_calendar_month=start_calendar_month,
            n_paths=req.n_paths,
            months_projected=req.months_projected,
            seed=42,
        )
        liquidity_paths = sim.pop("_liquidity_paths")
        if delta_emi:
            sim["parameters"]["loan_emi"] = delta_emi

        any_shortfall = (liquidity_paths < features["min_buffer"]).any(axis=1)
        confidence_bands[scenario] = {"p_shortfall_12m": bootstrap_shortfall_ci(any_shortfall, seed=42)}

        results[scenario] = sim

        db.add(SimulationResult(
            customer_id=customer_id,
            scenario=scenario,
            n_paths=req.n_paths,
            months_projected=req.months_projected,
            p_shortfall_12m=sim["p_shortfall_12m"],
            expected_liquidity=sim["expected_liquidity"],
            liquidity_percentiles=sim["liquidity_percentiles"],
            parameters=sim["parameters"],
        ))

    simulation_id = uuid.uuid4()
    db.commit()

    return {
        "customer_id": str(customer_id),
        "simulation_id": str(simulation_id),
        "scenarios": results,
        "confidence_bands": confidence_bands,
    }
