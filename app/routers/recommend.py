import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Customer, Recommendation
from app.models.recommender import match_bank_products
from app.services.recommendation_service import assess_customer, recommend

router = APIRouter(prefix="/api/v1/customers", tags=["recommendation"])


class RecommendRequest(BaseModel):
    language: str = "hi"
    include_llm_explanation: bool = False


def _public(result: dict) -> dict:
    return {k: v for k, v in result.items() if not k.startswith("_")}


@router.post("/{customer_id}/recommend")
def create_recommendation(
    customer_id: uuid.UUID, req: RecommendRequest, db: Session = Depends(get_db)
):
    if not db.query(Customer).filter(Customer.id == customer_id).first():
        raise HTTPException(status_code=404, detail={"error": "customer_not_found"})

    result = recommend(db, customer_id, language=req.language)
    return _public(result)


@router.get("/{customer_id}/matching-products/{recommendation_id}")
def matching_products(
    customer_id: uuid.UUID, recommendation_id: uuid.UUID, db: Session = Depends(get_db)
):
    """Top 3 real bank products matching a recommendation (spec addendum).

    Every product is priced and re-checked through the safety gate
    individually, and carries its own provenance note so nothing here is
    presented as a verified live quote.
    """
    rec = db.query(Recommendation).filter(
        Recommendation.id == recommendation_id,
        Recommendation.customer_id == customer_id,
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail={"error": "recommendation_not_found"})

    if rec.product_type == "no_action" or rec.amount is None:
        return {
            "customer_id": str(customer_id),
            "recommendation_id": str(recommendation_id),
            "product_type": rec.product_type,
            "matching_products": [],
            "note": "No product was recommended, so there is nothing to match against.",
        }

    assessment = assess_customer(db, customer_id)

    from app.models.recommender import Evaluation
    from app.safety.gate import GateResult
    from app.scoring.benefit_score import CBSComponents

    selected = Evaluation(
        product_type=rec.product_type,
        amount=float(rec.amount),
        tenure_months=rec.tenure_months,
        emi=0.0,
        cbs=float(rec.cbs_score),
        components=CBSComponents(0, 0, 0, 0, 0),
        gate=GateResult(True, None, [], []),
        post_dbr=0.0,
        post_p_shortfall=0.0,
        post_runway=0.0,
    )

    matches = match_bank_products(
        db=db,
        selected=selected,
        features=assessment["features"],
        sim_inputs=assessment["sim_inputs"],
        distress_state=assessment["distress_state"],
        max_anomaly=assessment["max_anomaly"],
        age=assessment["customer"].age,
    )

    return {
        "customer_id": str(customer_id),
        "recommendation_id": str(recommendation_id),
        "product_type": rec.product_type,
        "amount": float(rec.amount),
        "tenure_months": rec.tenure_months,
        "matching_products": matches,
        "disclaimer": (
            "Rate bands shown are representative figures compiled for this "
            "prototype, not live quotes. Confirm current rates and eligibility "
            "on the provider's official website before acting."
        ),
    }
