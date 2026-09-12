import datetime as dt
import uuid

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Customer, Transaction
from app.features.pipeline import compute_features

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.get("")
def list_customers(
    persona: str | None = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(Customer)
    if persona:
        q = q.filter(Customer.persona == persona)
    total = q.count()
    customers = q.order_by(Customer.external_id).offset(offset).limit(limit).all()

    out = []
    for c in customers:
        try:
            features = compute_features(db, c.id, persist=False)
            dbr = features.get("dbr")
            runway = features.get("liquidity_runway")
        except Exception:
            dbr = None
            runway = None
        out.append({
            "id": str(c.id),
            "persona": c.persona,
            "name": c.name,
            "age": c.age,
            "city": c.city,
            "monthly_income_mean": float(c.monthly_income_mean),
            "dbr": dbr,
            "liquidity_runway": runway,
            "distress_state": c.distress_state,
            "life_stage": c.life_stage,
        })

    return {"customers": out, "total": total, "limit": limit, "offset": offset}


@router.get("/{customer_id}")
def get_customer(customer_id: uuid.UUID, db: Session = Depends(get_db)):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail={"error": "customer_not_found"})
    return {
        "id": str(c.id),
        "external_id": c.external_id,
        "persona": c.persona,
        "name": c.name,
        "age": c.age,
        "city": c.city,
        "state": c.state,
        "preferred_language": c.preferred_language,
        "monthly_income_mean": float(c.monthly_income_mean),
        "monthly_income_std": float(c.monthly_income_std),
        "liquid_savings": float(c.liquid_savings),
        "credit_limit": float(c.credit_limit) if c.credit_limit is not None else None,
        "credit_outstanding": float(c.credit_outstanding) if c.credit_outstanding is not None else None,
        "life_stage": c.life_stage,
        "distress_state": c.distress_state,
        "distress_event_month": c.distress_event_month,
        "distress_event_type": c.distress_event_type,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.get("/{customer_id}/transactions")
def get_transactions(
    customer_id: uuid.UUID,
    start_date: dt.date | None = None,
    end_date: dt.date | None = None,
    category: str | None = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail={"error": "customer_not_found"})

    q = db.query(Transaction).filter(Transaction.customer_id == customer_id)
    if start_date:
        q = q.filter(Transaction.txn_date >= start_date)
    if end_date:
        q = q.filter(Transaction.txn_date <= end_date)
    if category:
        q = q.filter(Transaction.category == category)

    total = q.count()
    txns = q.order_by(Transaction.txn_date.desc()).offset(offset).limit(limit).all()

    return {
        "transactions": [
            {
                "id": str(t.id),
                "txn_date": t.txn_date.isoformat(),
                "txn_time": t.txn_time.isoformat() if t.txn_time else None,
                "amount": float(t.amount),
                "type": t.type,
                "category": t.category,
                "merchant": t.merchant,
                "is_recurring": t.is_recurring,
                "is_anomaly": t.is_anomaly,
            }
            for t in txns
        ],
        "total": total,
    }


class NewTransaction(BaseModel):
    txn_date: dt.date
    txn_time: dt.time | None = None
    amount: float = Field(gt=0, description="Always positive; direction is carried by `type`")
    type: Literal["credit", "debit"]
    category: str
    merchant: str
    description: str | None = None
    is_recurring: bool = False


@router.post("/{customer_id}/transactions", status_code=201)
def create_transaction(
    customer_id: uuid.UUID, txn: NewTransaction, db: Session = Depends(get_db)
):
    """Append a transaction.

    Features are recomputed on read rather than cached here, so a new
    transaction is reflected in the next features/simulate/recommend call
    without an explicit invalidation step.
    """
    if not db.query(Customer).filter(Customer.id == customer_id).first():
        raise HTTPException(status_code=404, detail={"error": "customer_not_found"})

    row = Transaction(
        customer_id=customer_id,
        txn_date=txn.txn_date,
        txn_time=txn.txn_time,
        amount=txn.amount,
        type=txn.type,
        category=txn.category,
        merchant=txn.merchant,
        description=txn.description,
        is_recurring=txn.is_recurring,
        is_anomaly=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "id": str(row.id),
        "customer_id": str(customer_id),
        "txn_date": row.txn_date.isoformat(),
        "txn_time": row.txn_time.isoformat() if row.txn_time else None,
        "amount": float(row.amount),
        "type": row.type,
        "category": row.category,
        "merchant": row.merchant,
        "description": row.description,
        "is_recurring": row.is_recurring,
    }
