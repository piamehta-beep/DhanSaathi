import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import get_db
from app.database.models import Customer
from app.models.survival import predict_distress
from app.schemas import DistressRiskResponse
from app.services.consent_guard import (
    SCOPE_CREDIT_ASSESSMENT,
    SCOPE_TRANSACTION_ANALYSIS,
    require_consent,
)
from app.security import require_customer_access

router = APIRouter(prefix="/api/v1/customers", tags=["distress-risk"], dependencies=[Depends(require_customer_access)])


@router.get(
    "/{customer_id}/distress-risk",
    response_model=DistressRiskResponse,
    dependencies=[
        Depends(require_consent(SCOPE_TRANSACTION_ANALYSIS, SCOPE_CREDIT_ASSESSMENT))
    ],
)
def distress_risk(customer_id: uuid.UUID, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail={"error": "customer_not_found"})

    prediction = predict_distress(db, customer_id)

    return {
        "customer_id": str(customer_id),
        "median_survival_time_months": None,
        "model_version": settings.model_version,
        **prediction,
    }
