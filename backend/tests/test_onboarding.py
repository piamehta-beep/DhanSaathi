"""Onboarding state machine tests (spec Section 7.12).

The point being defended is that transitions are deterministic and that
identifiers are never retained in the clear. A language model may translate
the prompts, but must never be able to advance the flow or decide validity.
"""

from __future__ import annotations

import pytest

from app.services.onboarding import (
    STEPS,
    OnboardingSession,
    advance,
    mask,
    verhoeff_valid,
)

# Valid-by-checksum Aadhaar-format numbers (synthetic, not real allocations).
VALID_AADHAAR = "234567890124"


def _session(language: str = "en") -> OnboardingSession:
    return OnboardingSession(session_id="test", language=language)


def test_verhoeff_checksum_accepts_valid_and_rejects_tampered():
    assert verhoeff_valid(VALID_AADHAAR)
    # Changing any single digit must break the checksum.
    tampered = VALID_AADHAAR[:-1] + str((int(VALID_AADHAAR[-1]) + 1) % 10)
    assert not verhoeff_valid(tampered)


def test_happy_path_walks_every_step_in_order():
    s = _session()
    assert s.step == "pan"

    steps_seen = [s.step]
    for message in ["ABCDE1234F", VALID_AADHAAR, "560001", "35000", "yes"]:
        result = advance(s, message)
        assert result["accepted"] is True, f"rejected at {s.step}: {message}"
        steps_seen.append(result["step"])

    assert steps_seen == STEPS
    assert s.step == "complete"
    assert s.progress == 1.0


@pytest.mark.parametrize(
    "step_inputs,bad_value",
    [
        ([], "ABCD1234F"),                      # PAN too short
        ([], "12345ABCDE"),                     # PAN wrong shape
        (["ABCDE1234F"], "1234"),               # Aadhaar too short
        (["ABCDE1234F"], "234567890123"),       # Aadhaar fails checksum
        (["ABCDE1234F", VALID_AADHAAR], "12"),  # PIN too short
        (["ABCDE1234F", VALID_AADHAAR], "012345"),  # PIN cannot start with 0
        (["ABCDE1234F", VALID_AADHAAR, "560001"], "not a number"),
        (["ABCDE1234F", VALID_AADHAAR, "560001"], "-500"),
    ],
)
def test_invalid_input_is_rejected_and_does_not_advance(step_inputs, bad_value):
    s = _session()
    for value in step_inputs:
        assert advance(s, value)["accepted"] is True
    step_before = s.step

    result = advance(s, bad_value)

    assert result["accepted"] is False
    assert s.step == step_before, "a rejected input must not advance the flow"
    assert result["attempts"] >= 1


def test_identifiers_are_stored_masked_never_in_the_clear():
    s = _session()
    advance(s, "ABCDE1234F")
    advance(s, VALID_AADHAAR)

    assert s.collected["pan"] == "******234F"
    assert s.collected["aadhaar"] == "********0124"

    serialized = repr(s.collected)
    assert "ABCDE1234F" not in serialized
    assert VALID_AADHAAR not in serialized


def test_mask_keeps_only_the_trailing_digits():
    assert mask("123456789012") == "********9012"
    assert mask("abc") == "***"


def test_input_is_normalised_before_validation():
    """Spacing, hyphens, rupee signs and case are formatting, not errors."""
    s = _session()
    assert advance(s, "  abcde1234f ")["accepted"] is True
    assert advance(s, "2345 6789 0124")["accepted"] is True
    assert advance(s, " 560001 ")["accepted"] is True
    assert advance(s, "₹35,000")["accepted"] is True
    assert s.collected["income"] == 35000.0


def test_hindi_prompts_are_served_for_hindi_sessions():
    s = _session(language="hi")
    assert "PAN" in s.prompt()
    assert any(ord(ch) > 2300 for ch in s.prompt()), "expected Devanagari text"

    result = advance(s, "bad-pan")
    assert result["accepted"] is False
    assert any(ord(ch) > 2300 for ch in result["message"])


def test_review_step_requires_explicit_confirmation():
    s = _session()
    for message in ["ABCDE1234F", VALID_AADHAAR, "560001", "35000"]:
        advance(s, message)
    assert s.step == "review"

    rejected = advance(s, "maybe")
    assert rejected["accepted"] is False
    assert s.step == "review"

    accepted = advance(s, "yes")
    assert accepted["accepted"] is True
    assert s.step == "complete"


def test_state_machine_has_no_ml_or_llm_imports():
    """The flow must not be advanceable by a model (see module docstring)."""
    import ast
    from pathlib import Path

    source = (Path(__file__).resolve().parent.parent / "app" / "services" / "onboarding.py").read_text()
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    forbidden = {"sklearn", "xgboost", "lifelines", "shap", "openai", "anthropic"}
    assert not (imported & forbidden)
