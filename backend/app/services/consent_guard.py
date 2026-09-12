"""Consent enforcement (spec Section 10.1).

Purpose limitation is only real if it is enforced at the boundary, so every
endpoint that reads customer data declares the scope it needs and is refused
with HTTP 403 when that scope is not actively granted.

A scope counts as active only when a record exists with granted=True and
revoked_at IS NULL, so revocation takes effect immediately on the next
request rather than at some later batch job.

Enforcement can be disabled with ENFORCE_CONSENT=false for local debugging
against a dataset that has no consent records; it is on by default, because
a compliance control that ships off by default is not a compliance control.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import get_db
from app.database.models import ConsentRecord

SCOPE_TRANSACTION_ANALYSIS = "transaction_analysis"
SCOPE_PRODUCT_RECOMMENDATION = "product_recommendation"
SCOPE_CREDIT_ASSESSMENT = "credit_assessment"
SCOPE_ANOMALY_MONITORING = "anomaly_monitoring"


def has_active_consent(db: Session, customer_id, scope: str) -> bool:
    return db.query(ConsentRecord).filter(
        ConsentRecord.customer_id == customer_id,
        ConsentRecord.scope == scope,
        ConsentRecord.granted.is_(True),
        ConsentRecord.revoked_at.is_(None),
    ).first() is not None


def missing_scopes(db: Session, customer_id, scopes: list[str]) -> list[str]:
    return [s for s in scopes if not has_active_consent(db, customer_id, s)]


def require_consent(*scopes: str):
    """FastAPI dependency factory enforcing that every named scope is active."""
    required = list(scopes)

    def dependency(customer_id: uuid.UUID = Path(...), db: Session = Depends(get_db)) -> None:
        if not settings.enforce_consent:
            return
        missing = missing_scopes(db, customer_id, required)
        if missing:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "consent_required",
                    "missing_scopes": missing,
                    "message": (
                        "This customer has not granted consent for "
                        f"{', '.join(missing)}. Grant it via POST /api/v1/consent."
                    ),
                },
            )

    return dependency
