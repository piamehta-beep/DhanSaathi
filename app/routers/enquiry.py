import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Customer
from app.services.consent_guard import (
    SCOPE_CREDIT_ASSESSMENT,
    SCOPE_TRANSACTION_ANALYSIS,
    require_consent,
)
from app.schemas import EnquiryResponse
from app.services.product_enquiry import evaluate_enquiry

router = APIRouter(prefix="/api/v1/customers", tags=["enquiry"])


class EnquiryRequest(BaseModel):
    product_type: str
    amount: float = Field(gt=0)
    tenure_months: int | None = Field(default=None, gt=0)


@router.post(
    "/{customer_id}/enquire",
    response_model=EnquiryResponse,
    dependencies=[
        Depends(require_consent(SCOPE_TRANSACTION_ANALYSIS, SCOPE_CREDIT_ASSESSMENT))
    ],
)
def enquire(customer_id: uuid.UUID, req: EnquiryRequest, db: Session = Depends(get_db)):
    """Answer "can I afford this?" for a product the customer asked about.

    The same safety gate applies as to anything the optimizer proposes — a
    customer who asks for credit does not get a weaker check than one who was
    offered it. When the answer is no, the response carries the largest amount
    that would pass, so the customer is told what *is* affordable rather than
    left to guess.
    """
    if not db.query(Customer).filter(Customer.id == customer_id).first():
        raise HTTPException(status_code=404, detail={"error": "customer_not_found"})

    try:
        return evaluate_enquiry(
            db, customer_id, req.product_type, req.amount, req.tenure_months
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"error": str(exc)}) from exc
