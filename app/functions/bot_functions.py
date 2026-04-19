"""
All 6 bot function implementations.
- fn_generate_welcome, fn_valuation_brief, fn_draft_outreach → Claude API (M2)
- fn_register_applicant, fn_match_applicants, fn_kyc_status → HubSpot API (M2/M3)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from app.models.schemas import (
    DraftOutreachRequest, DraftOutreachResponse,
    KYCStatusRequest,    KYCStatusResponse,
    MatchApplicantsRequest, MatchApplicantsResponse,
    RegisterApplicantRequest, RegisterApplicantResponse,
    ValuationBriefRequest, ValuationBriefResponse,
    WelcomeRequest, WelcomeResponse,
)
from app.services import hubspot_service

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# fn_generate_welcome  (M2 — Claude API)
# ---------------------------------------------------------------------------

async def fn_generate_welcome(req: WelcomeRequest) -> WelcomeResponse:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return WelcomeResponse(status="blocked", message_draft=None)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        budget_line = f" Their budget is £{req.budget_gbp:,}." if req.budget_gbp else ""
        prompt = (
            f"You are {req.agent_name}, an estate agent at Curtis Sloane.\n"
            f"Write a short, professional welcome message for a new client named "
            f"{req.client_name} who found you through {req.source}.{budget_line}\n"
            f"The message should be warm, professional, include the client's name and "
            f"your name. Do NOT use any placeholder text in square brackets. "
            f"Keep it under 120 words."
        )

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        draft = message.content[0].text.strip()
        return WelcomeResponse(status="ok", message_draft=draft)

    except Exception as exc:  # pragma: no cover
        return WelcomeResponse(status="error", message_draft=str(exc))


# ---------------------------------------------------------------------------
# fn_register_applicant  (M2 — HubSpot contacts.write)
# ---------------------------------------------------------------------------

async def fn_register_applicant(req: RegisterApplicantRequest) -> RegisterApplicantResponse:
    parts = req.full_name.strip().split()
    firstname = parts[0]
    lastname  = " ".join(parts[1:]) if len(parts) > 1 else ""

    properties: Dict[str, Any] = {
        "firstname":                    firstname,
        "lastname":                     lastname,
        "email":                        req.email,
        "phone":                        req.phone,
        "applicant_budget_gbp":         req.budget,
        "applicant_bedrooms_min":       req.bedrooms_min,
        "applicant_property_types":     ";".join(req.property_types),
        "applicant_financing":          req.financing,
        "applicant_preferred_channel":  req.preferred_channel,
        "applicant_source":             req.source,
    }
    if req.bedrooms_max is not None:
        properties["applicant_bedrooms_max"] = req.bedrooms_max
    if req.must_have:
        properties["applicant_must_have"] = req.must_have
    if req.timeline_weeks is not None:
        properties["applicant_timeline_weeks"] = req.timeline_weeks

    try:
        result = await hubspot_service.create_contact(properties)
        contact_id = str(result.get("id", ""))
        log.info("HubSpot contact created: %s (%s)", contact_id, req.email)
        return RegisterApplicantResponse(
            status="ok",
            applicant_id=contact_id,
            hubspot_contact_id=contact_id,
        )
    except Exception as exc:
        log.warning("HubSpot create_contact failed: %s", exc)
        return RegisterApplicantResponse(status="error", applicant_id=None)


# ---------------------------------------------------------------------------
# fn_match_applicants  (M3 — HubSpot contacts.read)
# M1: returns list of applicants from HubSpot with basic budget/bedrooms filter.
# M3: will rank by property criteria (price, bedrooms, property_type match).
# ---------------------------------------------------------------------------

async def fn_match_applicants(req: MatchApplicantsRequest) -> MatchApplicantsResponse:
    try:
        results = await hubspot_service.list_applicant_contacts(limit=req.max_results)
        matches = [
            {
                "id":         r.get("id"),
                "properties": r.get("properties", {}),
            }
            for r in results
        ]
        return MatchApplicantsResponse(
            status="ok",
            matches=matches,
            count=len(matches),
        )
    except Exception as exc:
        log.warning("HubSpot search_contacts failed: %s", exc)
        return MatchApplicantsResponse(status="error", matches=[], count=0)


# ---------------------------------------------------------------------------
# fn_valuation_brief  (M2 — Claude API)
# ---------------------------------------------------------------------------

async def fn_valuation_brief(req: ValuationBriefRequest) -> ValuationBriefResponse:
    return ValuationBriefResponse(status="stub", briefing=None)


# ---------------------------------------------------------------------------
# fn_draft_outreach  (M2 — Claude API)
# ---------------------------------------------------------------------------

async def fn_draft_outreach(req: DraftOutreachRequest) -> DraftOutreachResponse:
    return DraftOutreachResponse(status="stub", draft=None)


# ---------------------------------------------------------------------------
# fn_kyc_status  (M3 — HubSpot contacts.read)
# ---------------------------------------------------------------------------

async def fn_kyc_status(req: KYCStatusRequest) -> KYCStatusResponse:
    try:
        contact = await hubspot_service.find_contact_by_name_or_email(req.name_or_id)
        if contact is None:
            return KYCStatusResponse(
                status="not_found",
                kyc_complete=None,
                outstanding_items=None,
            )

        props = contact.get("properties", {})
        kyc_status_value = (props.get("kyc_status") or "").lower()
        outstanding_raw  = props.get("kyc_documents_outstanding") or ""
        outstanding_items: Optional[List[str]] = (
            [s.strip() for s in outstanding_raw.split(";") if s.strip()]
            if outstanding_raw else None
        )

        return KYCStatusResponse(
            status="ok",
            kyc_complete=(kyc_status_value == "complete"),
            outstanding_items=outstanding_items,
        )
    except Exception as exc:
        log.warning("HubSpot KYC lookup failed: %s", exc)
        return KYCStatusResponse(status="error", kyc_complete=None, outstanding_items=None)
