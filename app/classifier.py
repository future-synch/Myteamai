"""
M1 Intent Classifier — pure Python regex, zero AI calls, fully deterministic.
CLAUDE.md Section: CLASSIFIER PATTERNS (bugs fixed 16 April 2026)
"""

import re
from typing import List, Optional

CAPABILITIES: List[str] = [
    "Generate a welcome message for a new client",
    "Register a new applicant",
    "Find applicants matching a property",
    "Generate a valuation briefing pack",
    "Draft a personalised outreach message",
    "Check KYC/AML compliance status",
]

# Order is significant — more specific patterns before more general ones.
# Bug 1 fixed: removed bare \bvaluation\b (was matching "Book a valuation appointment")
# Bug 2 fixed: added \bcontact\b to DRAFT_OUTREACH (TS Section 4.3 keyword)
_PATTERNS = [
    ("KYC_STATUS", [
        r"\bkyc\b",
        r"\baml\b",
        r"\bcompliance\b",
        r"\bdocuments?\s+outstanding\b",
    ]),
    ("REGISTER_APPLICANT", [
        r"\bnew\s+applicant\b",
        r"\bregister\s+applicant\b",
        r"\bapplicant\s+intake\b",
    ]),
    ("MATCH_APPLICANTS", [
        r"\bmatch\s+applicants?\b",
        r"\bfind\s+applicants?\b",
        r"\bwho\s+fits\b",
        r"\bsuitable\s+applicants?\b",
        r"\bmatch\s+for\b",
    ]),
    ("VALUATION_BRIEF", [
        # valuat(?:i)?on handles both "valuation" and typo "valuaton"
        r"\bvaluat(?:i)?on\s+brief(?:ing)?\b",
        r"\bprepare\s+valuation\b",
        r"\bcomparables?\b",
        r"\bprice\s+valuation\b",
    ]),
    ("DRAFT_OUTREACH", [
        r"\bdraft\b",
        r"\boutreach\b",
        r"\bwrite\s+to\b",
        r"\bcontact\b",
        r"\bpersonalised?\s+(?:message|note|letter)\b",
    ]),
    ("WELCOME_CLIENT", [
        r"\bwelcome\b",
        r"\bnew\s+client\b",
        r"\bregister\s+client\b",
        r"\bonboard\b",
    ]),
]

_GREETING_TOKENS = {"hello", "hi", "hey", "good morning", "good afternoon", "good evening"}
_THANKS_TOKENS   = {"thanks", "thank you", "cheers"}


class ClassificationResult:
    def __init__(self, intent: str, message: str = ""):
        self.intent = intent
        self.is_unknown = intent == "UNKNOWN_INTENT"
        self.capabilities: Optional[List[str]] = CAPABILITIES if self.is_unknown else None
        self.message = message
        self.tokens_consumed = 0  # Always 0 — classifier never calls Claude


def classify(text: str) -> ClassificationResult:
    lowered = text.lower().strip()

    for intent, patterns in _PATTERNS:
        for pattern in patterns:
            if re.search(pattern, lowered, re.IGNORECASE):
                return ClassificationResult(intent)

    # Compose a context-appropriate message for unknown intent
    bare = lowered.rstrip(".,!?").strip()
    if bare in _GREETING_TOKENS:
        msg = "Hello! I'm here to help with your property management tasks."
    elif any(t in bare for t in _THANKS_TOKENS):
        msg = "You're welcome! Let me know if there's anything else I can help with."
    else:
        msg = "I can only assist with property management tasks."

    return ClassificationResult("UNKNOWN_INTENT", msg)
