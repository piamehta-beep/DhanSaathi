"""Customer-initiated enquiry tests.

The property that matters is that asking for credit does not buy a weaker
check than being offered it. A sales funnel would relax the gate for a
motivated customer; this must not.
"""

from __future__ import annotations

import pytest

from app.database.models import Customer
from app.safety.gate import MAX_POST_DBR_CREDIT, MAX_P_SHORTFALL, MIN_POST_RUNWAY_MONTHS
from app.services.product_enquiry import evaluate_enquiry

LARGE_LOAN = 500000.0
TENURE = 36


@pytest.fixture(scope="module")
def enquiries(db):
    out = {}
    for persona in ["stable_salaried", "young_earner", "over_leveraged", "distressed"]:
        customer = db.query(Customer).filter(Customer.persona == persona).first()
        out[persona] = evaluate_enquiry(db, customer.id, "personal_loan", LARGE_LOAN, TENURE)
    return out


def test_distressed_and_overleveraged_are_declined_however_much_they_ask(enquiries):
    for persona in ["over_leveraged", "distressed"]:
        result = enquiries[persona]
        assert result["verdict"] == "declined", f"{persona} was approved for a large loan"
        assert result["assessment"]["constraints_failed"], "a decline must name a constraint"


def test_a_decline_always_explains_itself(enquiries):
    """Either a counter-offer amount, or the size-independent blocking reason."""
    for persona, result in enquiries.items():
        if result["verdict"] != "declined":
            continue
        offer = result["counter_offer"]
        assert offer is not None
        explained = offer.get("amount") is not None or offer.get("blocking_constraints")
        assert explained, f"{persona} was declined with no actionable explanation"


def test_counter_offer_is_itself_affordable_and_smaller(enquiries):
    """A counter-offer that failed the gate would be worse than no offer."""
    for persona, result in enquiries.items():
        offer = result["counter_offer"]
        if not offer or offer.get("amount") is None:
            continue

        assert offer["passes"] is True, f"{persona} counter-offer does not clear the gate"
        assert not offer["constraints_failed"]
        assert offer["amount"] < LARGE_LOAN, "counter-offer must be smaller than requested"
        assert offer["post_dbr"] <= MAX_POST_DBR_CREDIT
        assert offer["post_p_shortfall_12m"] <= MAX_P_SHORTFALL
        assert offer["post_runway_months"] >= MIN_POST_RUNWAY_MONTHS


def test_enquiry_gate_matches_the_recommender_gate(db):
    """Same customer, same product, same amount — the verdict cannot differ
    depending on who initiated it."""
    from app.models.recommender import monthly_cost
    from app.safety.affordability import compute_post_dbr
    from app.services.recommendation_service import assess_customer

    customer = db.query(Customer).filter(Customer.persona == "over_leveraged").first()
    result = evaluate_enquiry(db, customer.id, "personal_loan", LARGE_LOAN, TENURE)

    assessment = assess_customer(db, customer.id)
    cost = monthly_cost("personal_loan", LARGE_LOAN, TENURE, assessment["customer"].age)
    expected_dbr = compute_post_dbr(
        assessment["features"]["total_emi"], cost,
        assessment["features"]["monthly_income_mean"],
    )

    assert result["assessment"]["monthly_cost"] == pytest.approx(round(cost, 2))
    assert result["assessment"]["post_dbr"] == pytest.approx(round(expected_dbr, 4))


def test_matching_products_are_only_returned_for_a_viable_amount(enquiries):
    for persona, result in enquiries.items():
        offer = result["counter_offer"]
        no_viable_amount = (
            result["verdict"] == "declined"
            and (not offer or offer.get("amount") is None)
        )
        if no_viable_amount:
            assert result["matching_products"] == [], (
                f"{persona} has no affordable amount but was shown bank products"
            )


def test_every_listed_bank_product_carries_its_own_gate_verdict(enquiries):
    for result in enquiries.values():
        for product in result["matching_products"]:
            assert "passes_safety_gate" in product
            assert "source_note" in product, "provenance must travel with every product"


def test_unknown_product_type_is_rejected(db):
    customer = db.query(Customer).first()
    with pytest.raises(ValueError):
        evaluate_enquiry(db, customer.id, "crypto_moonshot", 100000.0, 12)
