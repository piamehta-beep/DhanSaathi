"""A deliberately small, stateless tool dispatcher for financial questions."""

import uuid
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Customer, Recommendation, User
from app.features.pipeline import compute_features
from app.models.anomaly import max_anomaly_score, score_transactions
from app.models.recommender import Evaluation, match_bank_products
from app.safety.gate import GateResult
from app.scoring.benefit_score import CBSComponents
from app.security import get_current_user, require_customer_owner
from app.services.audit import record
from app.services.recommendation_service import ANOMALY_WINDOW_DAYS, assess_customer, recommend

router = APIRouter(prefix="/api/v1", tags=["chat"])
DECLINE = "I can help with savings goals, loan decisions, and understanding your spending — I can't advise on that."


class ChatRequest(BaseModel):
    customer_id: uuid.UUID
    message: str = Field(min_length=1, max_length=2000)
    language: str = "en"


def _tool_name(message: str) -> str | None:
    m = message.lower()
    if any(word in m for word in ("spend", "expense", "dbr", "feature", "income")):
        return "get_features"
    if any(word in m for word in ("anomal", "unusual", "fraud")):
        return "get_anomalies"
    if any(word in m for word in ("bank", "product", "compare")):
        return "get_matching_products"
    if any(word in m for word in ("simulate", "scenario", "what if")):
        return "run_simulation"
    if any(word in m for word in ("loan", "recommend", "saving", "savings")):
        return "get_recommendation"
    return None


TOOL_DEFINITIONS = [{"type": "function", "function": {"name": name, "description": name.replace("_", " "), "parameters": {"type": "object", "properties": {}}}} for name in ("get_features", "run_simulation", "get_recommendation", "get_matching_products", "get_anomalies")]


def _select_tool(message: str) -> str | None:
    """Use configured OpenAI-compatible tool selection when available.

    The deterministic fallback keeps the endpoint usable locally and never
    invents a financial value; replies are still rendered from tool output.
    """
    if os.environ.get("OPENAI_API_KEY") and os.environ.get("DATA_LOCALITY") != "strict":
        try:  # network availability is intentionally non-critical
            from openai import OpenAI
            response = OpenAI(api_key=os.environ["OPENAI_API_KEY"]).chat.completions.create(
                model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "You may only answer using the provided tools. Never invent numbers. If no tool matches, reply exactly: 'I can help with savings goals, loan decisions, and understanding your spending — I can't advise on that.'"},
                    {"role": "user", "content": message},
                ], tools=TOOL_DEFINITIONS, tool_choice="auto", max_tokens=50,
            )
            calls = response.choices[0].message.tool_calls or []
            if calls and calls[0].function.name in {item["function"]["name"] for item in TOOL_DEFINITIONS}:
                return calls[0].function.name
            return None
        except Exception:
            pass
    return _tool_name(message)


@router.post("/chat")
def chat(req: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_customer_owner(req.customer_id, current_user)
    if not db.query(Customer).filter(Customer.id == req.customer_id).first():
        raise HTTPException(status_code=404, detail="customer not found")
    tool = _select_tool(req.message)
    if tool is None:
        return {"reply": DECLINE, "tool": None}
    if tool == "get_features":
        data = compute_features(db, req.customer_id, persist=False)
        reply = f"Your DBR is {data['dbr']:.2%} and your average monthly income is ₹{data['monthly_income_mean']:.2f}."
    elif tool == "get_anomalies":
        assessment = assess_customer(db, req.customer_id)
        score = assessment["max_anomaly"]
        data = {"max_anomaly_score": score}
        reply = f"Your highest recent anomaly score is {score:.2f}."
    else:
        result = recommend(db, req.customer_id, language=req.language, persist=False)
        if tool == "get_matching_products" and result["product_type"] != "no_action":
            assessment = result["_assessment"]
            selected = result["_selected"]
            data = match_bank_products(db, selected, assessment["features"], assessment["sim_inputs"], assessment["distress_state"], assessment["max_anomaly"], assessment["customer"].age)
            reply = f"I found {len(data)} matching products after applying the safety gate."
        elif tool == "run_simulation":
            data = result["simulation_summary"]
            reply = f"The baseline 12-month shortfall probability is {data['p_shortfall_12m']:.2%}, with expected runway {data['expected_runway']:.2f} months."
        else:
            data = {k: result[k] for k in ("product_type", "amount", "monthly_cost", "status", "veto_reason")}
            if result["product_type"] == "no_action":
                reply = f"No product passed the safety checks. Reason: {result['veto_reason'] or 'insufficient safety margin'}."
            else:
                reply = f"Your recommendation is {result['product_type']} for ₹{result['amount']:.2f}; monthly cost is ₹{result['monthly_cost']:.2f}."
    record(db, req.customer_id, "chat_tool_call", "chat", {"message": req.message, "tool": tool}, {"tool": tool, "result": data})
    db.commit()
    return {"reply": reply, "tool": tool, "data": data}
