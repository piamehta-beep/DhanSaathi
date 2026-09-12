"""Append-only audit logging (spec Section 10.3).

Every model invocation, recommendation, and safety veto is recorded with a
SHA-256 hash of its input, so that a past decision can be shown to be
reproducible from the same inputs without storing the raw customer data in
the log itself.
"""

from __future__ import annotations

import hashlib
import json

from sqlalchemy.orm import Session

from app.database.models import AuditLog


def hash_input(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def record(
    db: Session,
    customer_id,
    action: str,
    module: str,
    input_payload: dict,
    output_summary: dict,
) -> None:
    db.add(AuditLog(
        customer_id=customer_id,
        action=action,
        module=module,
        input_hash=hash_input(input_payload),
        output_summary=output_summary,
    ))
