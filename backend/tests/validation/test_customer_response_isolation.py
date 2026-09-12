"""Run against the seeded PostgreSQL database to catch cross-customer leakage."""
import pytest
import uuid

from app.database.models import Customer
from app.routers.consent import get_audit_log
from app.routers.recommend import matching_products
from app.services.recommendation_service import assess_customer, recommend


def test_safety_and_recommendation_inputs_are_not_reused_between_customers(db):
    customer_ids = [row[0] for row in db.query(Customer.id).order_by(Customer.id).limit(2).all()]
    if len(customer_ids) < 2:
        pytest.skip("requires two seeded customers")

    first = assess_customer(db, customer_ids[0])
    second = assess_customer(db, customer_ids[1])

    # The important regression assertion is input isolation: the gate is fed
    # a separately loaded feature vector for each requested customer.
    assert first["features"] is not second["features"]
    assert first["customer"].id != second["customer"].id

    one = recommend(db, customer_ids[0], persist=True)
    two = recommend(db, customer_ids[1], persist=True)
    assert one["customer_id"] != two["customer_id"]
    assert one["_assessment"]["features"] is not two["_assessment"]["features"]

    products_one = matching_products(customer_ids[0], uuid.UUID(one["recommendation_id"]), db)
    products_two = matching_products(customer_ids[1], uuid.UUID(two["recommendation_id"]), db)
    assert products_one != products_two
    assert products_one["customer_id"] != products_two["customer_id"]

    audit_one = get_audit_log(customer_ids[0], db=db)
    audit_two = get_audit_log(customer_ids[1], db=db)
    assert audit_one != audit_two
    assert audit_one["customer_id"] != audit_two["customer_id"]
