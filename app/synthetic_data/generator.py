"""Orchestrator: generates all 1,000 customers and bulk-inserts into Postgres.

Fully deterministic given `seed` — every RNG draw traces back to a single
seeded `numpy.random.Generator`, with one independent child generator per
customer (via `rng.spawn`) so customer N's data never depends on how many
transactions customer N-1 happened to generate.
"""

from __future__ import annotations

import time

import numpy as np
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.database.models import (
    Anomaly,
    AuditLog,
    Customer,
    FeatureSnapshot,
    Loan,
    Recommendation,
    RecurringObligation,
    SimulationResult,
    Transaction,
)
from app.synthetic_data.anomalies import inject_anomalies
from app.synthetic_data.personas import assign_personas, generate_customer
from app.synthetic_data.transactions import generate_transactions

BATCH_FLUSH_EVERY = 25


def clear_existing_data(db: Session) -> None:
    # Order matters: children before the parents they FK to.
    for model in [
        AuditLog,
        Anomaly,
        SimulationResult,
        Recommendation,
        FeatureSnapshot,
        RecurringObligation,
        Transaction,
        Loan,
        Customer,
    ]:
        db.query(model).delete()
    db.commit()


def generate_dataset(n: int = 1000, seed: int = 42, clear_existing: bool = True) -> dict:
    started = time.time()
    master_rng = np.random.default_rng(seed)
    persona_labels = assign_personas(master_rng)[:n]
    child_rngs = master_rng.spawn(n)

    db = SessionLocal()
    total_txns = 0
    total_obligations = 0
    total_loans = 0
    try:
        if clear_existing:
            clear_existing_data(db)

        for i, (persona_name, rng) in enumerate(zip(persona_labels, child_rngs)):
            external_id = f"CUST{i + 1:05d}"
            profile = generate_customer(rng, persona_name, external_id)

            transactions, obligations, loans = generate_transactions(rng, profile)
            transactions = inject_anomalies(rng, transactions, profile)

            customer = Customer(
                external_id=profile["external_id"],
                persona=profile["persona"],
                name=profile["name"],
                age=profile["age"],
                city=profile["city"],
                state=profile["state"],
                preferred_language=profile["preferred_language"],
                monthly_income_mean=round(profile["monthly_income_mean"], 2),
                monthly_income_std=round(profile["monthly_income_std"], 2),
                liquid_savings=round(profile["liquid_savings"], 2),
                life_stage=profile["life_stage"],
                distress_state=False,
                distress_event_month=profile["distress_event_month"],
                distress_event_type=profile["distress_event_type"],
            )
            db.add(customer)
            db.flush()

            loan_objs = []
            for loan in loans:
                loan_obj = Loan(customer_id=customer.id, **loan)
                db.add(loan_obj)
                loan_objs.append(loan_obj)
            if loan_objs:
                db.flush()

            for ob in obligations:
                loan_idx = ob.pop("_loan_index", None)
                ob.pop("_index", None)
                linked_loan_id = loan_objs[loan_idx].id if loan_idx is not None else None
                db.add(RecurringObligation(customer_id=customer.id, linked_loan_id=linked_loan_id, **ob))
            total_obligations += len(obligations)
            total_loans += len(loans)

            db.bulk_insert_mappings(
                Transaction,
                [{**t, "customer_id": customer.id} for t in transactions],
            )
            total_txns += len(transactions)

            if (i + 1) % BATCH_FLUSH_EVERY == 0:
                db.commit()

        db.commit()
    finally:
        db.close()

    elapsed = time.time() - started
    return {
        "customers": n,
        "transactions": total_txns,
        "obligations": total_obligations,
        "loans": total_loans,
        "elapsed_seconds": round(elapsed, 1),
        "seed": seed,
    }
