import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import AuditLog, Recommendation, SupportRequest, User
from app.security import get_current_user, require_customer_owner

router = APIRouter(prefix="/api/v1/customers", tags=["support"])
VALID_REASONS = {"low_confidence", "vetoed_recommendation", "general_question", "dispute"}


class SupportRequestIn(BaseModel):
    reason: str
    recommendation_id: uuid.UUID | None = None
    message: str = Field(min_length=1, max_length=4000)


@router.post("/{customer_id}/support-request", status_code=201)
def create_support_request(customer_id: uuid.UUID, req: SupportRequestIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_customer_owner(customer_id, current_user)
    if req.reason not in VALID_REASONS:
        raise HTTPException(status_code=422, detail="invalid support reason")
    if req.recommendation_id and not db.query(Recommendation).filter(Recommendation.id == req.recommendation_id, Recommendation.customer_id == customer_id).first():
        raise HTTPException(status_code=404, detail="recommendation not found")
    audit = None
    if req.recommendation_id:
        audit = db.query(AuditLog).filter(AuditLog.customer_id == customer_id, AuditLog.action.in_(["recommendation_generated", "safety_veto"])).order_by(AuditLog.timestamp.desc()).first()
    row = SupportRequest(customer_id=customer_id, reason=req.reason, recommendation_id=req.recommendation_id,
                         message=req.message, linked_audit_log_id=audit.id if audit else None)
    db.add(row)
    db.commit()
    return {"id": str(row.id), "customer_id": str(customer_id), "status": row.status, "linked_audit_log_id": str(row.linked_audit_log_id) if row.linked_audit_log_id else None}


@router.get("/{customer_id}/support-requests")
def list_support_requests(customer_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_customer_owner(customer_id, current_user)
    rows = db.query(SupportRequest).filter(SupportRequest.customer_id == customer_id).order_by(SupportRequest.created_at.desc()).all()
    return {"customer_id": str(customer_id), "support_requests": [{"id": str(r.id), "reason": r.reason, "recommendation_id": str(r.recommendation_id) if r.recommendation_id else None, "message": r.message, "linked_audit_log_id": str(r.linked_audit_log_id) if r.linked_audit_log_id else None, "status": r.status, "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]}
