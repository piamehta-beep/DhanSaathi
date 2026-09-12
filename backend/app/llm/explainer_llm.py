"""Vernacular explanation layer (spec Section 6.5).

Architecturally this module is a leaf. It sits after every number has been
computed and frozen, it converts a structured payload into natural language,
and nothing it returns is read by any model, optimizer or safety gate. The
constraint is enforced by construction rather than by intention:

- it receives an already-final payload and has no database session, so it
  cannot look anything up or influence what was decided;
- it imports nothing from app.models, app.safety or app.services, which
  tests/test_llm_isolation.py asserts, so no feedback loop can form;
- its output is stored in the separate `llm_explanation` column and is never
  parsed back into a number.

Two switches can disable it, and both fail closed:

- DATA_LOCALITY=strict (the default) disables it outright. Spec Section 10.4
  requires customer data to stay in-region, and a hosted model endpoint cannot
  be assumed to satisfy that. Set DATA_LOCALITY=regional only when the
  configured endpoint is genuinely in-region.
- no API key configured.

When disabled, the caller keeps the structured explanation, which is always
computed regardless. The vernacular text is an addition on top of the
explanation, never a replacement for it.
"""

from __future__ import annotations

import json
import os

from app.config import settings

PROMPT_TEMPLATE = """You are a banking assistant. Explain the following recommendation to the customer in {language}. Use the provided numbers exactly as given. Do not compute, estimate, or infer any values. Do not make additional recommendations. Do not add numbers that are not listed below.

Recommendation: {product_type}
Amount: {amount}
Monthly cost: {monthly_cost}
Customer Benefit Score: {cbs_score}
Top contributing factors: {shap_summary}
Confidence: {confidence_level}
Constraints passed: {constraints_passed}
Reason declined (if any): {veto_reason}

Write 2-4 short sentences a first-time banking customer can follow."""

LANGUAGE_NAMES = {
    "hi": "Hindi", "en": "English", "mr": "Marathi", "ta": "Tamil",
    "te": "Telugu", "bn": "Bengali", "gu": "Gujarati", "kn": "Kannada",
    "ml": "Malayalam", "pa": "Punjabi", "or": "Odia", "as": "Assamese",
}


def is_enabled() -> tuple[bool, str | None]:
    """Whether the layer can run, and if not, why."""
    if settings.data_locality == "strict":
        return False, "disabled_by_data_locality_policy"
    if not os.environ.get("OPENAI_API_KEY"):
        return False, "no_api_key_configured"
    return True, None


def build_prompt(payload: dict, language: str) -> str:
    """Render the prompt. Pure and testable — no network call."""
    shap_summary = ", ".join(
        f"{item['feature']}={item['value']} ({item['direction']})"
        for item in payload.get("shap_values", [])[:3]
    ) or "none available"

    return PROMPT_TEMPLATE.format(
        language=LANGUAGE_NAMES.get(language, language),
        product_type=payload.get("product_type"),
        amount=payload.get("amount"),
        monthly_cost=payload.get("monthly_cost"),
        cbs_score=payload.get("cbs_score"),
        shap_summary=shap_summary,
        confidence_level=payload.get("confidence_level"),
        constraints_passed=", ".join(payload.get("constraints_passed", [])) or "none",
        veto_reason=payload.get("veto_reason") or "not declined",
    )


def generate_explanation(payload: dict, language: str = "hi") -> dict:
    """Return {text, enabled, reason}. Never raises into the caller: a failed
    explanation must not fail a recommendation that is already decided."""
    enabled, reason = is_enabled()
    if not enabled:
        return {"text": None, "enabled": False, "reason": reason}

    prompt = build_prompt(payload, language)
    try:
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = client.chat.completions.create(
            model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=300,
        )
        return {
            "text": response.choices[0].message.content.strip(),
            "enabled": True,
            "reason": None,
        }
    except Exception as exc:  # pragma: no cover - depends on external service
        return {"text": None, "enabled": False, "reason": f"llm_call_failed: {type(exc).__name__}"}


def payload_from_recommendation(recommendation: dict) -> dict:
    """Extract exactly the fields the prompt is allowed to see.

    Deliberately narrow: raw transactions, the feature vector and the customer's
    identity are not included, satisfying the data-minimisation requirement in
    Section 10.2. Serialising through JSON also guarantees the payload is a
    frozen copy rather than a live reference to the decision objects.
    """
    allowed = {
        "product_type", "amount", "monthly_cost", "cbs_score",
        "confidence_level", "constraints_passed", "veto_reason", "shap_values",
    }
    return json.loads(json.dumps(
        {k: v for k, v in recommendation.items() if k in allowed}, default=str
    ))
