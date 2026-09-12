import uuid

from fastapi import APIRouter, Depends, HTTPException
from lifelines.utils import concordance_index
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import get_db
from app.database.models import Customer
from app.features.pipeline import compute_features
from app.models.survival import get_cached_scaled_design_matrix, get_or_train_model, predict_for_features

router = APIRouter(prefix="/api/v1/customers", tags=["distress-risk"])


@router.get("/{customer_id}/distress-risk")
def distress_risk(customer_id: uuid.UUID, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail={"error": "customer_not_found"})

    cph, scaler, training_df = get_or_train_model(db)
    features = compute_features(db, customer_id, persist=False)
    prediction = predict_for_features(cph, scaler, features)

    x_scaled = get_cached_scaled_design_matrix()
    partial_hazards = cph.predict_partial_hazard(x_scaled)
    c_index = concordance_index(training_df["duration"], -partial_hazards, training_df["event"])

    return {
        "customer_id": str(customer_id),
        "distress_probability_12m": prediction["distress_probability_12m"],
        "survival_function": prediction["survival_function"],
        "hazard_ratios": prediction["hazard_ratios"],
        "median_survival_time_months": None,
        "concordance_index": round(float(c_index), 4),
        "model_version": settings.model_version,
    }
