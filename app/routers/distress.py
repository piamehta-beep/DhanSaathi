import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import get_db
from app.database.models import Customer
from app.models.survival import predict_distress

router = APIRouter(prefix="/api/v1/customers", tags=["distress-risk"])


@router.get("/{customer_id}/distress-risk")
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
