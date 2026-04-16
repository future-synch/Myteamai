"""
Pydantic v2 schemas for all 6 bot functions.
TS Section 5.1–5.6 — validation layer catches bad input before AI or CRM.
"""

from __future__ import annotations

import re
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

_MAX_NAME_LEN = 500   # reject absurdly long strings (test 12 §8)
_HTML_TAG_RE  = re.compile(r"<[^>]+>")


def _sanitise(value: str) -> str:
    """Strip HTML/script tags so injected content is never echoed verbatim."""
    return _HTML_TAG_RE.sub("", value).strip()


# ---------------------------------------------------------------------------
# Shared response models
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    error_code: str
    message: str
    capabilities: Optional[List[str]] = None


class ClassifyResponse(BaseModel):
    status: Literal["ok", "error"]
    intent: Optional[str] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
    capabilities: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# fn_generate_welcome  (TS Section 5.1)
# ---------------------------------------------------------------------------

class WelcomeRequest(BaseModel):
    client_name: str
    source: Literal["Rightmove", "Zoopla", "Referral", "Direct", "Other"]
    agent_name: str
    dispatch: bool
    budget_gbp: Optional[int] = None
    notes: Optional[str] = None

    @field_validator("client_name")
    @classmethod
    def validate_client_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Client name is required")
        v = _sanitise(v)
        if not v:
            raise ValueError("Client name is required")
        if len(v) > _MAX_NAME_LEN:
            raise ValueError(f"Client name must not exceed {_MAX_NAME_LEN} characters")
        if len(v) < 2:
            raise ValueError("Client name must be at least 2 characters")
        return v

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Agent name is required")
        return v.strip()

    @field_validator("dispatch", mode="before")
    @classmethod
    def validate_dispatch(cls, v: object) -> bool:
        if v is None or v == "":
            raise ValueError("dispatch field must be true or false")
        return v  # type: ignore[return-value]

    @field_validator("budget_gbp", mode="before")
    @classmethod
    def validate_budget_type(cls, v: object) -> object:
        if v is None:
            return v
        if isinstance(v, float) and not v.is_integer():
            raise ValueError("Budget must be a whole number")
        return v

    @field_validator("budget_gbp")
    @classmethod
    def validate_budget_value(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Budget must be a positive number")
        if v is not None and v < 100_000:
            raise ValueError("Budget must be at least £100,000")
        return v


class WelcomeResponse(BaseModel):
    status: str
    message_draft: Optional[str] = None
    hubspot_contact_id: Optional[str] = None


# ---------------------------------------------------------------------------
# fn_register_applicant  (TS Section 5.2)
# ---------------------------------------------------------------------------

class RegisterApplicantRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    budget: int = Field(ge=1)
    bedrooms_min: int = Field(ge=1)
    # TS Section 5.2: valid property types include "any"
    property_types: List[Literal["house", "flat", "maisonette", "any"]]
    # TS Section 5.2: financing enum (confirmed with John 16 April 2026)
    financing: Literal["cash", "mortgage_aip", "mortgage_no_aip", "unknown"]
    preferred_channel: Literal["email", "phone", "whatsapp"]
    source: str
    bedrooms_max: Optional[int] = None
    must_have: Optional[str] = None
    timeline_weeks: Optional[int] = None


class RegisterApplicantResponse(BaseModel):
    status: str
    applicant_id: Optional[str] = None
    hubspot_contact_id: Optional[str] = None


# ---------------------------------------------------------------------------
# fn_match_applicants  (TS Section 5.3)
# ---------------------------------------------------------------------------

class MatchApplicantsRequest(BaseModel):
    property_ref: str
    max_results: int = Field(default=5, ge=1, le=20)

    @field_validator("property_ref")
    @classmethod
    def validate_property_ref(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Property reference is required")
        return v.strip()


class MatchApplicantsResponse(BaseModel):
    status: str
    matches: Optional[List[dict]] = None
    count: int = 0


# ---------------------------------------------------------------------------
# fn_valuation_brief  (TS Section 5.4)
# ---------------------------------------------------------------------------

class ValuationBriefRequest(BaseModel):
    address: str
    postcode: str
    property_type: Literal["house", "flat", "maisonette"]
    bedrooms: int = Field(ge=0)
    condition: Optional[Literal["excellent", "good", "fair", "needs_work"]] = None
    sqft: Optional[int] = None


class ValuationBriefResponse(BaseModel):
    status: str
    briefing: Optional[str] = None


# ---------------------------------------------------------------------------
# fn_draft_outreach  (TS Section 5.5)
# recipient_type and channel confirmed with spec 16 April 2026
# ---------------------------------------------------------------------------

class DraftOutreachRequest(BaseModel):
    recipient_name: str
    # TS Section 5.5: who to send outreach to
    recipient_type: Literal[
        "long_term_resident", "recent_enquirer", "warm_lead", "lapsed"
    ]
    # TS Section 5.5: delivery channel
    channel: Literal["email", "handwritten_note", "letter"]
    agent_name: str
    context_notes: Optional[str] = None
    property_mention: Optional[str] = None


class DraftOutreachResponse(BaseModel):
    status: str
    draft: Optional[str] = None


# ---------------------------------------------------------------------------
# fn_kyc_status  (TS Section 5.6)
# ---------------------------------------------------------------------------

class KYCStatusRequest(BaseModel):
    name_or_id: str
    type: Literal["client", "applicant"]

    @field_validator("name_or_id")
    @classmethod
    def validate_name_or_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name_or_id is required")
        return v.strip()


class KYCStatusResponse(BaseModel):
    status: str
    kyc_complete: Optional[bool] = None
    outstanding_items: Optional[List[str]] = None
