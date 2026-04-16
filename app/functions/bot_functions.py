"""
All 6 bot function implementations.
M1: stubs that return structured responses (no external calls).
M2+: fn_generate_welcome calls Claude API.
"""

from __future__ import annotations

import os
from typing import Optional

from app.models.schemas import (
    DraftOutreachRequest, DraftOutreachResponse,
    KYCStatusRequest, KYCStatusResponse,
    MatchApplicantsRequest, MatchApplicantsResponse,
    RegisterApplicantRequest, RegisterApplicantResponse,
    ValuationBriefRequest, ValuationBriefResponse,
    WelcomeRequest, WelcomeResponse,
)


# ---------------------------------------------------------------------------
# fn_generate_welcome  (M2 — requires ANTHROPIC_API_KEY)
# ---------------------------------------------------------------------------

async def fn_generate_welcome(req: WelcomeRequest) -> WelcomeResponse:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return WelcomeResponse(
            status="blocked",
            message_draft=None,
        )

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        budget_line = (
            f" Their budget is £{req.budget_gbp:,}." if req.budget_gbp else ""
        )
        prompt = (
            f"You are {req.agent_name}, an estate agent at Curtis Sloane.\n"
            f"Write a short, professional welcome message for a new client named {req.client_name} "
            f"who found you through {req.source}.{budget_line}\n"
            f"The message should be warm, professional, include the client's name and your name. "
            f"Do NOT use any placeholder text in square brackets. Keep it under 120 words."
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
# fn_register_applicant  (M2 — requires HubSpot)
# ---------------------------------------------------------------------------

async def fn_register_applicant(req: RegisterApplicantRequest) -> RegisterApplicantResponse:
    return RegisterApplicantResponse(status="stub", applicant_id=None)


# ---------------------------------------------------------------------------
# fn_match_applicants  (M3 — requires seeded HubSpot data)
# ---------------------------------------------------------------------------

async def fn_match_applicants(req: MatchApplicantsRequest) -> MatchApplicantsResponse:
    return MatchApplicantsResponse(status="stub", matches=[], count=0)


# ---------------------------------------------------------------------------
# fn_valuation_brief  (M2 — requires Claude API)
# ---------------------------------------------------------------------------

async def fn_valuation_brief(req: ValuationBriefRequest) -> ValuationBriefResponse:
    return ValuationBriefResponse(status="stub", briefing=None)


# ---------------------------------------------------------------------------
# fn_draft_outreach  (M2 — requires Claude API)
# ---------------------------------------------------------------------------

async def fn_draft_outreach(req: DraftOutreachRequest) -> DraftOutreachResponse:
    return DraftOutreachResponse(status="stub", draft=None)


# ---------------------------------------------------------------------------
# fn_kyc_status  (M3 — requires HubSpot)
# ---------------------------------------------------------------------------

async def fn_kyc_status(req: KYCStatusRequest) -> KYCStatusResponse:
    return KYCStatusResponse(status="stub", kyc_complete=None, outstanding_items=None)
