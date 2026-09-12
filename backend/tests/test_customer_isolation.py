"""Regression checks for per-customer query isolation.

The integration suite supplies the seeded PostgreSQL database; these focused
checks ensure the three affected handlers retain their customer filters and
fresh feature computation rather than reviving an in-memory response cache.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent / "app"


def test_recommendation_and_product_matching_are_customer_scoped():
    source = (ROOT / "routers" / "recommend.py").read_text()
    assert "Recommendation.customer_id == customer_id" in source
    assert "assessment = assess_customer(db, customer_id)" in source


def test_decision_trail_filters_by_requested_customer():
    source = (ROOT / "routers" / "consent.py").read_text()
    assert "AuditLog.customer_id == customer_id" in source


def test_feature_pipeline_has_no_module_level_response_cache():
    source = (ROOT / "features" / "pipeline.py").read_text()
    assert "build_context(db, customer_id" in source
    assert "_feature_cache" not in source
    assert "FEATURE_CACHE" not in source
