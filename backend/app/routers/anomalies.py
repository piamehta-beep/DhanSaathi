import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Anomaly, Customer
from app.features.context import build_context
from app.features.pipeline import compute_features
from app.models.anomaly import score_transactions
from app.schemas import AnomalyListResponse
from app.services.consent_guard import SCOPE_ANOMALY_MONITORING, require_consent
from app.security import require_customer_access

router = APIRouter(prefix="/api/v1/customers", tags=["anomalies"], dependencies=[Depends(require_customer_access)])


@router.get(
    "/{customer_id}/anomalies",
    response_model=AnomalyListResponse,
    dependencies=[Depends(require_consent(SCOPE_ANOMALY_MONITORING))],
)
def get_anomalies(
    customer_id: uuid.UUID,
    start_date: dt.date | None = None,
    end_date: dt.date | None = None,
    min_score: float = Query(0.5, ge=0.0, le=1.0),
    limit: int = Query(50, le=500),
    persist: bool = False,
    db: Session = Depends(get_db),
):
    if not db.query(Customer).filter(Customer.id == customer_id).first():
        raise HTTPException(status_code=404, detail={"error": "customer_not_found"})

    ctx = build_context(db, customer_id)
    features = compute_features(db, customer_id, persist=False)
    scored = score_transactions(ctx.txns, features["monthly_income_mean"])

    if scored.empty:
        return {"anomalies": [], "total": 0}

    flagged = scored[scored["anomaly_score"] >= min_score].copy()
    if start_date is not None:
        flagged = flagged[flagged["txn_date"] >= start_date]
    if end_date is not None:
        flagged = flagged[flagged["txn_date"] <= end_date]

    flagged = flagged.sort_values("anomaly_score", ascending=False).head(limit)

    results = []
    for _, row in flagged.iterrows():
        results.append({
            "transaction_id": str(row["transaction_id"]),
            "txn_date": row["txn_date"].isoformat(),
            "amount": float(row["amount"]),
            "type": row["type"],
            "category": row["category"],
            "merchant": row["merchant"],
            "detection_method": row["detection_method"],
            "anomaly_score": round(float(row["anomaly_score"]), 4),
            "confidence": round(float(row["confidence"]), 4),
            "features": {
                "robust_z_amount": round(float(row["robust_z_amount"]), 4),
                "time_deviation": round(float(row["time_deviation"]), 4),
                "merchant_novelty": int(row["merchant_novelty"]),
                "amount_vs_income": round(float(row["amount_vs_income"]), 4),
                "daily_category_count": int(row["daily_category_count"]),
            },
            "injected_tag": row["anomaly_type"],
        })

    if persist:
        for item in results:
            db.add(Anomaly(
                customer_id=customer_id,
                transaction_id=uuid.UUID(item["transaction_id"]),
                detection_method=item["detection_method"],
                anomaly_score=item["anomaly_score"],
                confidence=item["confidence"],
                features=item["features"],
                is_true_positive=item["injected_tag"] is not None,
            ))
        db.commit()

    return {"anomalies": results, "total": len(results)}
