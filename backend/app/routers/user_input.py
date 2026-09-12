"""Manual real-data entry endpoints.

TODO (intentionally deferred): CSV upload/parsing, encryption at rest, rate
limiting, and a data-deletion endpoint.
"""

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Customer, RecurringObligation, Transaction, User
from app.security import get_current_user

router = APIRouter(prefix="/api/v1/customers/me", tags=["manual-entry"])
ALLOWED_CATEGORIES = {"salary", "gig_income", "rent", "emi", "insurance_premium", "sip", "medical", "groceries", "utilities", "transport", "other"}


class SetupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=18, le=100)
    city: str = Field(min_length=1, max_length=50)
    monthly_income_mean: float = Field(gt=0)
    state: str = "Unknown"
    preferred_language: str = "en"


class IncomeRequest(BaseModel):
    amount: float = Field(gt=0)
    credit_day: int = Field(ge=1, le=31)


class ObligationRequest(BaseModel):
    amount: float = Field(gt=0)
    day_of_month: int = Field(ge=1, le=31)
    type: str

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value not in {"rent", "emi", "insurance_premium", "sip"}:
            raise ValueError("type must be rent, emi, insurance_premium, or sip")
        return value


class ManualTransactionRequest(BaseModel):
    date: dt.date
    amount: float = Field(gt=0)
    type: str
    category: str
    merchant: str = Field(min_length=1, max_length=100)

    @field_validator("date")
    @classmethod
    def date_not_future(cls, value: dt.date) -> dt.date:
        if value > dt.date.today():
            raise ValueError("date must not be in the future")
        return value

    @field_validator("type")
    @classmethod
    def validate_transaction_type(cls, value: str) -> str:
        if value not in {"credit", "debit"}:
            raise ValueError("type must be credit or debit")
        return value

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        if value not in ALLOWED_CATEGORIES:
            raise ValueError(f"category must be one of: {', '.join(sorted(ALLOWED_CATEGORIES))}")
        return value


def _customer(user: User, db: Session) -> Customer:
    if user.customer_id is None:
        raise HTTPException(status_code=409, detail="complete setup first")
    customer = db.query(Customer).filter(Customer.id == user.customer_id).first()
    if not customer:
        raise HTTPException(status_code=409, detail="linked customer no longer exists")
    return customer


@router.post("/setup", status_code=status.HTTP_201_CREATED)
def setup(req: SetupRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.customer_id:
        return {"customer_id": str(current_user.customer_id), "created": False}
    customer = Customer(
        external_id=None, persona="user_provided", name=req.name, age=req.age,
        city=req.city, state=req.state, preferred_language=req.preferred_language,
        monthly_income_mean=req.monthly_income_mean, monthly_income_std=0,
        liquid_savings=0, credit_limit=None, credit_outstanding=None,
        life_stage="working", distress_state=False, data_source="user_provided",
    )
    db.add(customer)
    db.flush()
    current_user.customer_id = customer.id
    db.commit()
    return {"customer_id": str(customer.id), "created": True}


@router.post("/income", status_code=status.HTTP_201_CREATED)
def add_income(req: IncomeRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    customer = _customer(current_user, db)
    customer.monthly_income_mean = req.amount
    today = dt.date.today()
    day = min(req.credit_day, 28)
    txn = Transaction(customer_id=customer.id, txn_date=today.replace(day=day), amount=req.amount,
                      type="credit", category="salary", merchant="Manual salary entry", data_source="user_provided")
    db.add(txn)
    db.commit()
    return {"customer_id": str(customer.id), "transaction_id": str(txn.id), "amount": req.amount, "credit_day": req.credit_day}


@router.post("/obligations", status_code=status.HTTP_201_CREATED)
def add_obligation(req: ObligationRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    customer = _customer(current_user, db)
    row = RecurringObligation(customer_id=customer.id, type=req.type, amount=req.amount,
                              frequency="monthly", day_of_month=req.day_of_month, start_date=dt.date.today(), active=True)
    db.add(row)
    db.commit()
    return {"id": str(row.id), "customer_id": str(customer.id), "type": row.type, "amount": float(row.amount)}


@router.post("/transactions", status_code=status.HTTP_201_CREATED)
def add_transaction(req: ManualTransactionRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    customer = _customer(current_user, db)
    row = Transaction(customer_id=customer.id, txn_date=req.date, amount=req.amount, type=req.type,
                      category=req.category, merchant=req.merchant, is_recurring=False, is_anomaly=False,
                      data_source="user_provided")
    db.add(row)
    db.commit()
    return {"id": str(row.id), "customer_id": str(customer.id), "data_source": row.data_source}
