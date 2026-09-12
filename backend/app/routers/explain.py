import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Recommendation
from app.features.pipeline import compute_features
from app.models.explainer import explain_distress, explain_need_match, narrate
from app.schemas import ExplainResponse
from app.security import require_customer_access

router = APIRouter(prefix="/api/v1/customers", tags=["explainability"], dependencies=[Depends(require_customer_access)])


@router.get("/{customer_id}/explain/{recommendation_id}", response_model=ExplainResponse)
def explain(customer_id: uuid.UUID, recommendation_id: uuid.UUID, db: Session = Depends(get_db)):
    """Attributions for a recommendation, including a vetoed one.

    Spec Section 10.7 treats explanation as a right, so this endpoint answers
    for declined recommendations too — and for those it reports which
    constraint blocked the decision and the values that triggered it, which is
    the part a customer actually needs in order to act.
    """
    rec = db.query(Recommendation).filter(
        Recommendation.id == recommendation_id,
        Recommendation.customer_id == customer_id,
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail={"error": "recommendation_not_found"})

    features = compute_features(db, customer_id, persist=False)
    distress_attr = explain_distress(db, features)
    need_attr = explain_need_match(db, features, rec.product_type)

    return {
        "customer_id": str(customer_id),
        "recommendation_id": str(recommendation_id),
        "product_type": rec.product_type,
        "status": rec.status,
        "shap_values": distress_attr,
        "need_match_attribution": need_attr,
        "model_used": "xgboost_need_match + cox_survival",
        "explanation": narrate(distress_attr, need_attr, rec.product_type),
        "veto_reason": rec.veto_reason,
        "constraints_failed": rec.constraints_failed,
        "confidence_level": rec.confidence_level,
        "confidence_interval": rec.confidence_interval,
    }
