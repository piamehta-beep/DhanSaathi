"""Conversational onboarding state machine (spec Section 7.12).

pan -> aadhaar -> address -> income -> review -> complete

The state machine is entirely deterministic: validation, transitions and
progress are computed here, in ordinary Python, with no model involved. An
LLM may translate the prompts into the customer's language, exactly as in the
recommendation flow, but it never decides whether an input is valid or what
step comes next. A language model that could advance a KYC flow would be a
compliance problem, not a feature.

Validation is format-level only. These are checksum and pattern checks
against publicly documented formats — the Verhoeff checksum for Aadhaar is
the published algorithm, not a lookup against any registry. Nothing here
contacts UIDAI or the Income Tax Department, and no identifier is verified
against a real record; this is a prototype flow, not real KYC.

Collected identifiers are stored masked. The full value is never persisted or
returned, because an onboarding prototype has no legitimate need to retain a
raw government identifier.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
AADHAAR_PATTERN = re.compile(r"^[2-9][0-9]{11}$")
PINCODE_PATTERN = re.compile(r"^[1-9][0-9]{5}$")

STEPS = ["pan", "aadhaar", "address", "income", "review", "complete"]

PROMPTS = {
    "pan": {
        "en": "Welcome! Please enter your PAN number (for example ABCDE1234F).",
        "hi": "नमस्ते! कृपया अपना PAN नंबर दर्ज करें (उदाहरण: ABCDE1234F)।",
    },
    "aadhaar": {
        "en": "Thank you. Now please enter your 12-digit Aadhaar number.",
        "hi": "धन्यवाद! अब कृपया अपना 12 अंकों का आधार नंबर दर्ज करें।",
    },
    "address": {
        "en": "Got it. What is your 6-digit PIN code?",
        "hi": "ठीक है। आपका 6 अंकों का पिन कोड क्या है?",
    },
    "income": {
        "en": "Almost done. What is your approximate monthly income in rupees?",
        "hi": "लगभग पूरा हो गया। आपकी अनुमानित मासिक आय कितनी है (रुपये में)?",
    },
    "review": {
        "en": "Please review your details and confirm (reply 'yes' to confirm).",
        "hi": "कृपया अपनी जानकारी की समीक्षा करें और पुष्टि करें ('हाँ' लिखें)।",
    },
    "complete": {
        "en": "Onboarding complete. Thank you!",
        "hi": "ऑनबोर्डिंग पूरी हुई। धन्यवाद!",
    },
}

ERRORS = {
    "pan": {
        "en": "That does not look like a valid PAN. The format is five letters, four digits, then one letter.",
        "hi": "यह मान्य PAN नहीं लगता। प्रारूप है: पाँच अक्षर, चार अंक, फिर एक अक्षर।",
    },
    "aadhaar": {
        "en": "That does not look like a valid Aadhaar number. It should be 12 digits.",
        "hi": "यह मान्य आधार नंबर नहीं लगता। इसमें 12 अंक होने चाहिए।",
    },
    "address": {
        "en": "That does not look like a valid PIN code. It should be 6 digits.",
        "hi": "यह मान्य पिन कोड नहीं लगता। इसमें 6 अंक होने चाहिए।",
    },
    "income": {
        "en": "Please enter your monthly income as a number, for example 35000.",
        "hi": "कृपया अपनी मासिक आय संख्या में दर्ज करें, जैसे 35000।",
    },
    "review": {
        "en": "Please reply 'yes' to confirm, or 'no' to start again.",
        "hi": "पुष्टि के लिए 'हाँ' लिखें, या फिर से शुरू करने के लिए 'नहीं'।",
    },
}

# Verhoeff tables — the published algorithm Aadhaar numbers use as a checksum.
_D_TABLE = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_P_TABLE = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


def verhoeff_valid(number: str) -> bool:
    """Verhoeff checksum, the algorithm Aadhaar uses. Format check only."""
    if not number.isdigit():
        return False
    c = 0
    for i, digit in enumerate(reversed(number)):
        c = _D_TABLE[c][_P_TABLE[i % 8][int(digit)]]
    return c == 0


def mask(value: str, keep_last: int = 4) -> str:
    if len(value) <= keep_last:
        return "*" * len(value)
    return "*" * (len(value) - keep_last) + value[-keep_last:]


@dataclass
class OnboardingSession:
    session_id: str
    language: str = "hi"
    customer_name: str | None = None
    step: str = "pan"
    collected: dict = field(default_factory=dict)
    attempts: dict = field(default_factory=dict)

    @property
    def progress(self) -> float:
        return round(STEPS.index(self.step) / (len(STEPS) - 1), 2)

    def prompt(self) -> str:
        return PROMPTS[self.step].get(self.language, PROMPTS[self.step]["en"])


def _validate(step: str, message: str) -> tuple[bool, object]:
    """Deterministic validation. Returns (ok, normalized_value)."""
    text = (message or "").strip()

    if step == "pan":
        value = text.upper().replace(" ", "")
        return bool(PAN_PATTERN.match(value)), value

    if step == "aadhaar":
        value = re.sub(r"[\s-]", "", text)
        return bool(AADHAAR_PATTERN.match(value)) and verhoeff_valid(value), value

    if step == "address":
        value = re.sub(r"\s", "", text)
        return bool(PINCODE_PATTERN.match(value)), value

    if step == "income":
        value = re.sub(r"[,\s₹]", "", text)
        try:
            amount = float(value)
        except ValueError:
            return False, None
        return amount > 0, amount

    if step == "review":
        affirmative = {"yes", "y", "haan", "हाँ", "हा", "ha", "confirm", "ok"}
        return text.lower() in affirmative, text.lower()

    return False, None


def advance(session: OnboardingSession, message: str) -> dict:
    """Process one message. Pure function of (session, message)."""
    if session.step == "complete":
        return {
            "step": "complete",
            "message": PROMPTS["complete"].get(session.language, PROMPTS["complete"]["en"]),
            "progress": 1.0,
            "accepted": True,
        }

    step = session.step
    ok, value = _validate(step, message)

    if not ok:
        session.attempts[step] = session.attempts.get(step, 0) + 1
        return {
            "step": step,
            "message": ERRORS[step].get(session.language, ERRORS[step]["en"]),
            "progress": session.progress,
            "accepted": False,
            "attempts": session.attempts[step],
        }

    # Identifiers are stored masked; the raw value is deliberately dropped.
    if step in ("pan", "aadhaar"):
        session.collected[step] = mask(str(value))
    elif step == "review":
        session.collected["confirmed"] = True
    else:
        session.collected[step] = value

    session.step = STEPS[STEPS.index(step) + 1]

    response = {
        "step": session.step,
        "message": session.prompt(),
        "progress": session.progress,
        "accepted": True,
    }
    if session.step == "review":
        response["review"] = dict(session.collected)
    return response
