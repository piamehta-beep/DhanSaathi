import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import AuditLog, ConsentRecord, Customer
from app.services.audit import record

router = APIRouter(prefix="/api/v1", tags=["consent-and-audit"])

VALID_SCOPES = {
    "transaction_analysis", "credit_assessment", "product_recommendation",
    "marketing", "anomaly_monitoring",
}


class ConsentRequest(BaseModel):
    customer_id: uuid.UUID
    scope: str
    granted: bool
    purpose: str


@router.post("/consent", status_code=201)
def grant_consent(req: ConsentRequest, db: Session = Depends(get_db)):
    if req.scope not in VALID_SCOPES:
        raise HTTPException(status_code=422, detail={"error": "invalid_scope", "valid": sorted(VALID_SCOPES)})
    if not db.query(Customer).filter(Customer.id == req.customer_id).first():
        raise HTTPException(status_code=404, detail={"error": "customer_not_found"})

    row = ConsentRecord(
        customer_id=req.customer_id,
        scope=req.scope,
        granted=req.granted,
        granted_at=dt.datetime.now(dt.timezone.utc) if req.granted else None,
        purpose=req.purpose,
    )
    db.add(row)
    record(
        db, customer_id=req.customer_id, action="consent_granted" if req.granted else "consent_denied",
        module="consent", input_payload={"scope": req.scope}, output_summary={"granted": req.granted},
    )
    db.commit()

    return {
        "id": str(row.id),
        "customer_id": str(req.customer_id),
        "scope": row.scope,
        "granted": row.granted,
        "granted_at": row.granted_at.isoformat() if row.granted_at else None,
        "revoked_at": None,
        "purpose": row.purpose,
    }


@router.get("/customers/{customer_id}/consent")
def list_consent(customer_id: uuid.UUID, db: Session = Depends(get_db)):
    rows = db.query(ConsentRecord).filter(
        ConsentRecord.customer_id == customer_id
    ).order_by(ConsentRecord.created_at.desc()).all()

    return {
        "customer_id": str(customer_id),
        "consent_records": [{
            "id": str(r.id),
            "scope": r.scope,
            "granted": r.granted,
            "granted_at": r.granted_at.isoformat() if r.granted_at else None,
            "revoked_at": r.revoked_at.isoformat() if r.revoked_at else None,
            "purpose": r.purpose,
            "active": bool(r.granted and r.revoked_at is None),
        } for r in rows],
    }


@router.post("/consent/{consent_id}/revoke")
def revoke_consent(consent_id: uuid.UUID, db: Session = Depends(get_db)):
    row = db.query(ConsentRecord).filter(ConsentRecord.id == consent_id).first()
    if not row:
        raise HTTPException(status_code=404, detail={"error": "consent_not_found"})

    row.revoked_at = dt.datetime.now(dt.timezone.utc)
    record(
        db, customer_id=row.customer_id, action="consent_revoked", module="consent",
        input_payload={"consent_id": str(consent_id)}, output_summary={"scope": row.scope},
    )
    db.commit()

    return {
        "id": str(row.id),
        "scope": row.scope,
        "granted": row.granted,
        "revoked_at": row.revoked_at.isoformat(),
        "active": False,
    }


@router.get("/audit/{customer_id}")
def get_audit_log(
    customer_id: uuid.UUID,
    action: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog).filter(AuditLog.customer_id == customer_id)
    if action:
        q = q.filter(AuditLog.action == action)
    total = q.count()
    rows = q.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    return {
        "customer_id": str(customer_id),
        "logs": [{
            "id": str(r.id),
            "action": r.action,
            "module": r.module,
            "input_hash": r.input_hash,
            "output_summary": r.output_summary,
            "timestamp": r.timestamp.isoformat(),
        } for r in rows],
        "total": total,
    }
