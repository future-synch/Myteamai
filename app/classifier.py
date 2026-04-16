"""
M1 Intent Classifier — pure Python regex, zero AI calls, fully deterministic.
CLAUDE.md Section: CLASSIFIER PATTERNS (bugs fixed 16 April 2026)
"""

import re
from typing import Dict, List, Optional, Any

CAPABILITIES: List[str] = [
    "Generate a welcome message for a new client",
    "Register a new applicant",
    "Find applicants matching a property",
    "Generate a valuation briefing pack",
    "Draft a personalised outreach message",
    "Check KYC/AML compliance status",
]

# Maps each intent to its human-readable description (mirrors CAPABILITIES order)
INTENT_MAP: Dict[str, str] = {
    "WELCOME_CLIENT":     "Generate a welcome message for a new client",
    "REGISTER_APPLICANT": "Register a new applicant",
    "MATCH_APPLICANTS":   "Find applicants matching a property",
    "VALUATION_BRIEF":    "Generate a valuation briefing pack",
    "DRAFT_OUTREACH":     "Draft a personalised outreach message",
    "KYC_STATUS":         "Check KYC/AML compliance status",
}

# ---------------------------------------------------------------------------
# Classification patterns
# Order is significant — more specific before more general.
# Bug 1 fixed: removed bare \bvaluation\b (was matching "Book a valuation appointment")
# Bug 2 fixed: added \bcontact\b to DRAFT_OUTREACH (TS Section 4.3 keyword)
# ---------------------------------------------------------------------------
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

# Property address pattern: number + street name + road type
_ADDRESS_RE = re.compile(
    r"^\d+[a-z]?\s+[\w\s\-]+\b"
    r"(road|street|avenue|ave|lane|grove|close|place|way|drive|court"
    r"|gardens?|square|crescent|terrace|park|hill|walk|mews|row)\b",
    re.IGNORECASE,
)

_GREETING_TOKENS = {"hello", "hi", "hey", "good morning", "good afternoon", "good evening"}
_THANKS_TOKENS   = {"thanks", "thank you", "cheers"}


class ClassificationResult:
    def __init__(self, intent: str, message: str = ""):
        self.intent = intent
        self.is_unknown = intent == "UNKNOWN_INTENT"
        self.capabilities: Optional[List[str]] = CAPABILITIES if self.is_unknown else None
        self.message = message
        # Cost/rate accounting — pure Python classifier costs nothing
        self.tokens_consumed = 0
        self.rate_limit_counted = not self.is_unknown   # unknown skips per-hour rate limit
        self.daily_counter_counted = True               # all requests count toward daily counter
        # Admin session log entry (TS Section 8 — no PII stored)
        self.log_entry: Dict[str, Any] = {
            "intent": intent,
            "status": "error" if self.is_unknown else "ok",
            "ai_function": None,          # never set for unknown; set on known intents
            "token_usage": None,          # always None at classifier level
        }


def classify(text: str) -> ClassificationResult:
    lowered = text.lower().strip()

    # 1. Check domain-specific patterns
    for intent, patterns in _PATTERNS:
        for pattern in patterns:
            if re.search(pattern, lowered, re.IGNORECASE):
                result = ClassificationResult(intent)
                result.log_entry["ai_function"] = intent
                return result

    # 2. Determine context-appropriate message for unknown intent
    bare = lowered.rstrip(".,!?").strip()

    if bare in _GREETING_TOKENS:
        msg = "Hello! Here's what I can help you with:"
    elif any(t in bare for t in _THANKS_TOKENS):
        msg = "You're welcome! Let me know if you need anything else. Here's what I can help with:"
    elif _ADDRESS_RE.match(text.strip()):
        msg = ("I recognise that as a property address, but I'm not sure "
               "what you'd like me to do. Here's what I can help with:")
    else:
        msg = "I couldn't understand that request. Here's what I can do:"

    return ClassificationResult("UNKNOWN_INTENT", msg)
