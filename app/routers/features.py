import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import get_db
from app.database.models import Customer
from app.features.pipeline import compute_features_with_snapshot_date
from app.schemas import FeaturesResponse
from app.services.consent_guard import SCOPE_TRANSACTION_ANALYSIS, require_consent

router = APIRouter(prefix="/api/v1/customers", tags=["features"])


@router.get(
    "/{customer_id}/features",
    response_model=FeaturesResponse,
    dependencies=[Depends(require_consent(SCOPE_TRANSACTION_ANALYSIS))],
)
def get_features(
    customer_id: uuid.UUID,
    snapshot_date: dt.date | None = Query(None),
    db: Session = Depends(get_db),
):
    if not db.query(Customer).filter(Customer.id == customer_id).first():
        raise HTTPException(status_code=404, detail={"error": "customer_not_found"})

    features, resolved_date = compute_features_with_snapshot_date(db, customer_id, snapshot_date)
    return {
        "customer_id": str(customer_id),
        "snapshot_date": str(resolved_date),
        "features": features,
        "model_version": settings.model_version,
    }
