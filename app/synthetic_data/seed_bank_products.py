"""Load bank product reference data from data/bank_products_seed.csv.

The reference data lives in CSV rather than inline in code so the rate bands
can be refreshed without a code change. Every row carries a source_note
stating that its figures are representative bands rather than live quotes;
source_url is deliberately left blank where a page was not actually
verified, since a fabricated citation is worse than an honest "illustrative"
label.

Run with: python -m app.synthetic_data.seed_bank_products
"""

from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path

from app.database.connection import SessionLocal
from app.database.models import BankProduct

SEED_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "bank_products_seed.csv"


def _optional_decimal(value: str) -> float | None:
    value = (value or "").strip()
    return float(value) if value else None


def load_bank_products(clear_existing: bool = True) -> dict:
    db = SessionLocal()
    try:
        if clear_existing:
            db.query(BankProduct).delete()
            db.commit()

        with SEED_PATH.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))

        for row in rows:
            db.add(BankProduct(
                bank_name=row["bank_name"],
                product_type=row["product_type"],
                product_name=row["product_name"],
                min_amount=float(row["min_amount"]),
                max_amount=float(row["max_amount"]),
                interest_rate_min=float(row["interest_rate_min"]),
                interest_rate_max=float(row["interest_rate_max"]),
                tenure_options=json.loads(row["tenure_options"] or "[]"),
                processing_fee_pct=_optional_decimal(row["processing_fee_pct"]),
                annual_fee=_optional_decimal(row["annual_fee"]),
                eligibility_notes=row["eligibility_notes"],
                source_url=(row["source_url"] or "").strip() or None,
                source_note=row["source_note"],
                last_verified_date=dt.date.fromisoformat(row["last_verified_date"]),
            ))
        db.commit()
        return {"bank_products_loaded": len(rows), "source": str(SEED_PATH)}
    finally:
        db.close()


if __name__ == "__main__":
    print(load_bank_products())
