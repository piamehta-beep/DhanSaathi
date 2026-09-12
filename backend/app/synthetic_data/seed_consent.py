"""Grant baseline consent for seeded customers.

Synthetic customers are modelled as having completed onboarding, so they carry
the scopes onboarding would have collected. Marketing consent is deliberately
*not* granted: it is the one scope the product does not need in order to
function, and defaulting it on is exactly the dark pattern the consent design
exists to avoid.

Run with: python -m app.synthetic_data.seed_consent
"""

from __future__ import annotations

import datetime as dt

from app.database.connection import SessionLocal
from app.database.models import ConsentRecord, Customer

GRANTED_SCOPES = {
    "transaction_analysis": "Analyse transaction history to understand income, spending and obligations",
    "product_recommendation": "Assess which banking products are suitable, including recommending none",
    "credit_assessment": "Evaluate affordability and repayment capacity before suggesting any credit",
    "anomaly_monitoring": "Monitor for unusual activity and early signs of financial distress",
}


def seed_consent(clear_existing: bool = True) -> dict:
    db = SessionLocal()
    try:
        if clear_existing:
            db.query(ConsentRecord).delete()
            db.commit()

        now = dt.datetime.now(dt.timezone.utc)
        customers = db.query(Customer).all()
        created = 0
        for customer in customers:
            for scope, purpose in GRANTED_SCOPES.items():
                db.add(ConsentRecord(
                    customer_id=customer.id,
                    scope=scope,
                    granted=True,
                    granted_at=now,
                    purpose=purpose,
                ))
                created += 1
        db.commit()
        return {"customers": len(customers), "consent_records_created": created}
    finally:
        db.close()


if __name__ == "__main__":
    print(seed_consent())
