"""The LLM layer must be a leaf (spec Section 6.5).

Its architectural guarantee is that it cannot influence any number. That is
worth enforcing mechanically rather than trusting: a future edit that imports
the optimizer "just to look something up" would quietly create the feedback
loop the design exists to prevent.
"""

from __future__ import annotations

import ast
from pathlib import Path

LLM_DIR = Path(__file__).resolve().parent.parent / "app" / "llm"

# Importing any of these would let language generation reach back into the
# decision path.
FORBIDDEN_PREFIXES = ("app.models", "app.safety", "app.services", "app.features")


def _imported_modules(source: str) -> set[str]:
    tree = ast.parse(source)
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_llm_layer_does_not_import_the_decision_path():
    violations = {}
    for py_file in LLM_DIR.rglob("*.py"):
        imported = _imported_modules(py_file.read_text())
        hits = {m for m in imported if m.startswith(FORBIDDEN_PREFIXES)}
        if hits:
            violations[py_file.name] = hits
    assert not violations, f"LLM layer reached into the decision path: {violations}"


def test_llm_is_disabled_under_strict_data_locality():
    """Section 10.4: with DATA_LOCALITY=strict the layer must not run at all,
    regardless of whether a key happens to be configured."""
    from app.config import settings
    from app.llm.explainer_llm import is_enabled

    assert settings.data_locality == "strict", "default config should be strict"
    enabled, reason = is_enabled()
    assert enabled is False
    assert reason == "disabled_by_data_locality_policy"


def test_disabled_layer_returns_no_text_and_never_raises():
    from app.llm.explainer_llm import generate_explanation

    result = generate_explanation({"product_type": "term_insurance"}, "hi")
    assert result["text"] is None
    assert result["enabled"] is False
    assert result["reason"]


def test_payload_is_minimised_and_frozen():
    """Only presentation fields reach the prompt — no raw transactions, no
    feature vector, no customer identity (Section 10.2)."""
    from app.llm.explainer_llm import payload_from_recommendation

    recommendation = {
        "product_type": "credit_card",
        "amount": 25000.0,
        "cbs_score": 0.41,
        "confidence_level": "high",
        "constraints_passed": ["C1", "C3"],
        "veto_reason": None,
        "monthly_cost": 776.13,
        "shap_values": [{"feature": "dbr", "value": 0.09, "shap": -0.3, "direction": "decreases_distress_risk"}],
        # None of the following may survive.
        "customer_id": "abc-123",
        "_assessment": {"features": {"liquid_savings": 83243.57}},
        "distress_probability": 0.02,
        "simulation_summary": {"p_shortfall_12m": 0.01},
    }
    payload = payload_from_recommendation(recommendation)

    assert "customer_id" not in payload
    assert "_assessment" not in payload
    assert "simulation_summary" not in payload
    assert payload["product_type"] == "credit_card"

    # A frozen copy, not a live reference into the decision objects.
    payload["shap_values"][0]["value"] = 999
    assert recommendation["shap_values"][0]["value"] == 0.09


def test_prompt_forbids_computation_and_carries_only_given_numbers():
    from app.llm.explainer_llm import build_prompt

    payload = {
        "product_type": "term_insurance", "amount": 2500000, "monthly_cost": 1666.67,
        "cbs_score": 0.45, "confidence_level": "high", "constraints_passed": ["C9"],
        "veto_reason": None,
        "shap_values": [{"feature": "dbr", "value": 0.25, "direction": "decreases_distress_risk"}],
    }
    prompt = build_prompt(payload, "hi")

    assert "Hindi" in prompt
    assert "Do not compute, estimate, or infer any values" in prompt
    assert "Do not make additional recommendations" in prompt
    assert "2500000" in prompt
