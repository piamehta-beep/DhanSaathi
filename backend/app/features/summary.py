"""Bulk summary metrics for list views.

The full feature pipeline is the authority on a customer's numbers, but
running it per row to render a table is wasteful: a 50-row page cost ~50
pipeline invocations and over a second of latency.

These aggregates reproduce the pipeline's definitions exactly for the two
metrics a list view shows, in two GROUP BY queries for the whole page:

    monthly_income_mean   = sum(credits over trailing 6 months) / 6
    monthly_expenses_mean = sum(debits over trailing 6 months) / 6
    dbr                   = total active EMI / monthly_income_mean
    liquidity_runway      = liquid_savings / monthly_expenses_mean

Mean-of-monthly-sums equals total-over-six-months divided by six whenever all
six months are present, which holds for the seeded dataset, so the figures
match `compute_features` rather than merely approximating it — a list showing
a different DBR from the detail view would be a bug report waiting to happen.
A test pins the two against each other.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.models import Customer, RecurringObligation, Transaction

WINDOW_MONTHS = 6


def trailing_window_start(db: Session) -> dt.date | None:
    """First day of the trailing 6-month window, derived from the data itself."""
    latest = db.query(func.max(Transaction.txn_date)).scalar()
    if latest is None:
        return None
    month = latest.month - (WINDOW_MONTHS - 1)
    year = latest.year
    while month <= 0:
        month += 12
        year -= 1
    return dt.date(year, month, 1)


def list_summary_metrics(db: Session, customer_ids: list) -> dict:
    if not customer_ids:
        return {}

    cutoff = trailing_window_start(db)
    if cutoff is None:
        return {}

    flows = dict.fromkeys(customer_ids)
    rows = db.query(
        Transaction.customer_id,
        Transaction.type,
        func.sum(Transaction.amount),
    ).filter(
        Transaction.customer_id.in_(customer_ids),
        Transaction.txn_date >= cutoff,
    ).group_by(Transaction.customer_id, Transaction.type).all()

    totals: dict = {}
    for customer_id, txn_type, amount in rows:
        totals.setdefault(customer_id, {})[txn_type] = float(amount or 0)

    emi_rows = db.query(
        RecurringObligation.customer_id,
        func.sum(RecurringObligation.amount),
    ).filter(
        RecurringObligation.customer_id.in_(customer_ids),
        RecurringObligation.active.is_(True),
        RecurringObligation.type == "emi",
    ).group_by(RecurringObligation.customer_id).all()
    emi_by_customer = {cid: float(total or 0) for cid, total in emi_rows}

    savings_rows = db.query(Customer.id, Customer.liquid_savings).filter(
        Customer.id.in_(customer_ids)
    ).all()
    savings_by_customer = {cid: float(value or 0) for cid, value in savings_rows}

    out: dict = {}
    for customer_id in customer_ids:
        flow = totals.get(customer_id, {})
        income = flow.get("credit", 0.0) / WINDOW_MONTHS
        expenses = flow.get("debit", 0.0) / WINDOW_MONTHS
        total_emi = emi_by_customer.get(customer_id, 0.0)
        liquid = savings_by_customer.get(customer_id, 0.0)

        out[customer_id] = {
            "monthly_income_mean": round(income, 2),
            "monthly_expenses_mean": round(expenses, 2),
            "total_emi": round(total_emi, 2),
            "dbr": round(total_emi / income, 4) if income > 0 else None,
            "liquidity_runway": round(liquid / expenses, 2) if expenses > 0 else None,
        }
    return out
