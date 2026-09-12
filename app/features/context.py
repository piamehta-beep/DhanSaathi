"""Shared data-loading for the feature pipeline (spec Section 4.8, step 1).

Builds one `FeatureContext` per (customer, snapshot_date) that every feature
module (income/obligations/liquidity/trends/entropy/credit/behavioral)
consumes, so each module stays a pure function of already-loaded data rather
than re-querying the database.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import pandas as pd
from sqlalchemy.orm import Session

from app.database.models import Customer, RecurringObligation, Transaction


@dataclass
class FeatureContext:
    customer: Customer
    snapshot_date: dt.date
    txns: pd.DataFrame  # one row per transaction, up to snapshot_date
    monthly: pd.DataFrame  # one row per calendar month, aggregated
    obligations: pd.DataFrame  # active recurring obligations as of snapshot_date
    data_months: int


def _month_key(d: dt.date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def build_context(db: Session, customer_id, snapshot_date: dt.date | None = None) -> FeatureContext:
    customer = db.query(Customer).filter(Customer.id == customer_id).one()

    txns_q = db.query(Transaction).filter(Transaction.customer_id == customer_id)
    if snapshot_date is not None:
        txns_q = txns_q.filter(Transaction.txn_date <= snapshot_date)
    txns = txns_q.order_by(Transaction.txn_date).all()

    rows = [{
        "txn_date": t.txn_date,
        "txn_time": t.txn_time,
        "amount": float(t.amount),
        "type": t.type,
        "category": t.category,
        "merchant": t.merchant,
        "is_recurring": t.is_recurring,
        "is_anomaly": t.is_anomaly,
    } for t in txns]
    txns_df = pd.DataFrame(rows)

    if txns_df.empty:
        resolved_snapshot = snapshot_date or dt.date.today()
        monthly = pd.DataFrame(columns=[
            "month", "income", "expenses", "emi", "discretionary", "n_txns",
        ])
    else:
        resolved_snapshot = snapshot_date or txns_df["txn_date"].max()
        txns_df["month"] = txns_df["txn_date"].apply(_month_key)

        credits = txns_df[txns_df["type"] == "credit"].groupby("month")["amount"].sum()
        debits_all = txns_df[txns_df["type"] == "debit"].groupby("month")["amount"].sum()
        emi = txns_df[(txns_df["type"] == "debit") & (txns_df["category"] == "emi")].groupby("month")["amount"].sum()
        discretionary = txns_df[
            (txns_df["type"] == "debit") & (~txns_df["is_recurring"])
        ].groupby("month")["amount"].sum()
        n_txns = txns_df.groupby("month").size()

        months_index = sorted(txns_df["month"].unique())
        monthly = pd.DataFrame(index=months_index)
        monthly["month"] = months_index
        monthly["income"] = credits.reindex(months_index).fillna(0.0)
        monthly["expenses"] = debits_all.reindex(months_index).fillna(0.0)
        monthly["emi"] = emi.reindex(months_index).fillna(0.0)
        monthly["discretionary"] = discretionary.reindex(months_index).fillna(0.0)
        monthly["n_txns"] = n_txns.reindex(months_index).fillna(0).astype(int)
        monthly = monthly.reset_index(drop=True)
        monthly["t"] = range(1, len(monthly) + 1)

    obligations = db.query(RecurringObligation).filter(
        RecurringObligation.customer_id == customer_id,
        RecurringObligation.active.is_(True),
    ).all()
    obligations_df = pd.DataFrame([{
        "type": o.type, "amount": float(o.amount), "frequency": o.frequency,
    } for o in obligations])

    return FeatureContext(
        customer=customer,
        snapshot_date=resolved_snapshot,
        txns=txns_df,
        monthly=monthly,
        obligations=obligations_df,
        data_months=len(monthly),
    )
