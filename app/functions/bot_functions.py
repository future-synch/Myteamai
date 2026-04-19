"""
All 6 bot function implementations.
- fn_generate_welcome, fn_valuation_brief, fn_draft_outreach → Claude API (M2)
- fn_register_applicant, fn_match_applicants, fn_kyc_status → HubSpot API (M2/M3)
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from app.models.schemas import (
    DraftOutreachRequest, DraftOutreachResponse,
    KYCStatusRequest,    KYCStatusResponse,
    MatchApplicantsRequest, MatchApplicantsResponse,
    RegisterApplicantRequest, RegisterApplicantResponse,
    ValuationBriefRequest, ValuationBriefResponse,
    WelcomeFromTextResponse,
    WelcomeRequest, WelcomeResponse,
)
from app.services import hubspot_service

log = logging.getLogger(__name__)

# Model selection — Sonnet 4.6 for generation, Haiku 4.5 for fast extraction
MODEL_GENERATE = "claude-sonnet-4-6"
MODEL_EXTRACT  = "claude-haiku-4-5-20251001"


def _anthropic_client():
    """Return an anthropic.Anthropic client, or None if no API key."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    import anthropic
    return anthropic.Anthropic(api_key=api_key)


# ---------------------------------------------------------------------------
# fn_generate_welcome  (M2 — Claude API, form-based entry)
# ---------------------------------------------------------------------------

async def fn_generate_welcome(req: WelcomeRequest) -> WelcomeResponse:
    client = _anthropic_client()
    if client is None:
        return WelcomeResponse(status="blocked", message_draft=None)

    try:
        budget_line = f" Their budget is £{req.budget_gbp:,}." if req.budget_gbp else ""
        prompt = (
            f"You are {req.agent_name}, an estate agent at Curtis Sloane, a London "
            f"property firm specialising in W11 (Notting Hill, Holland Park).\n\n"
            f"Write a short, professional welcome message for a new client named "
            f"{req.client_name} who found you through {req.source}.{budget_line}\n\n"
            f"Requirements:\n"
            f"- Warm, professional tone\n"
            f"- Include the client's name ({req.client_name})\n"
            f"- Sign off with your name ({req.agent_name})\n"
            f"- No placeholder text in square brackets — real, finished prose only\n"
            f"- Under 120 words\n"
            f"- No subject line; just the message body"
        )

        message = client.messages.create(
            model=MODEL_GENERATE,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        draft = message.content[0].text.strip()
        return WelcomeResponse(status="ok", message_draft=draft)

    except Exception as exc:
        log.warning("Claude call failed (welcome): %s", exc)
        return WelcomeResponse(status="error", message_draft=f"Claude error: {exc}")


# ---------------------------------------------------------------------------
# fn_generate_welcome_from_text  (M2 — free-text entry per John's Gherkin)
# Test 1: "Welcome new client — James Hyde, came through Rightmove"
# ---------------------------------------------------------------------------

_EXTRACT_WELCOME_PROMPT = """You are extracting structured data from an estate agent's free-text request.

Text: "{text}"

Extract these fields and return ONLY a JSON object (no markdown, no explanation):
- client_name: the full name of the new client (required string)
- source: must be EXACTLY one of: Rightmove, Zoopla, Referral, Direct, Other (required string)
- budget_gbp: the client's budget in GBP as an integer, or null if not mentioned
- timeline: free-text timeline if mentioned (e.g. "August", "6 weeks"), else null

Rules:
- If the text mentions a platform like "Rightmove" or "Zoopla", that's the source.
- If the text says "came through a friend" or similar, source is "Referral".
- If the text says "came in directly" or similar, source is "Direct".
- If unclear, source is "Other".
- Budget like "3M", "2.5M", "1m" = millions. "500k" = 500000.

Return the JSON object only.

Example input: "Welcome Sarah Chen, Zoopla, budget 3M, wants to move August"
Example output: {{"client_name": "Sarah Chen", "source": "Zoopla", "budget_gbp": 3000000, "timeline": "August"}}

Example input: "Welcome new client — James Hyde, came through Rightmove"
Example output: {{"client_name": "James Hyde", "source": "Rightmove", "budget_gbp": null, "timeline": null}}
"""


def _parse_extracted_json(raw: str) -> Optional[Dict[str, Any]]:
    """Strip markdown fences and parse JSON."""
    raw = raw.strip()
    if raw.startswith("```"):
        # e.g. ```json\n{...}\n```
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if m:
            raw = m.group(1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        log.warning("Failed to parse extracted JSON: %s — raw: %s", exc, raw[:200])
        return None


async def fn_generate_welcome_from_text(
    text: str, agent_name: str = "James"
) -> WelcomeFromTextResponse:
    client = _anthropic_client()
    if client is None:
        return WelcomeFromTextResponse(status="blocked")

    # Step 1 — extract fields with Haiku (fast)
    try:
        extract_msg = client.messages.create(
            model=MODEL_EXTRACT,
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": _EXTRACT_WELCOME_PROMPT.format(text=text),
            }],
        )
        raw = extract_msg.content[0].text
    except Exception as exc:
        log.warning("Claude extract call failed: %s", exc)
        return WelcomeFromTextResponse(status="error", extracted=None, message_draft=f"Extraction error: {exc}")

    extracted = _parse_extracted_json(raw)
    if extracted is None or not extracted.get("client_name"):
        return WelcomeFromTextResponse(
            status="error",
            extracted=extracted,
            message_draft="Could not extract client details. Please use the Welcome Client form.",
        )

    # Normalise source to valid enum
    source = extracted.get("source") or "Other"
    if source not in {"Rightmove", "Zoopla", "Referral", "Direct", "Other"}:
        source = "Other"

    # Step 2 — build WelcomeRequest and generate
    try:
        welcome_req = WelcomeRequest(
            client_name=extracted["client_name"],
            source=source,
            agent_name=agent_name,
            dispatch=False,
            budget_gbp=extracted.get("budget_gbp"),
        )
    except Exception as exc:
        log.warning("WelcomeRequest validation failed: %s", exc)
        return WelcomeFromTextResponse(
            status="error",
            extracted=extracted,
            message_draft=f"Validation failed: {exc}",
        )

    welcome_resp = await fn_generate_welcome(welcome_req)
    return WelcomeFromTextResponse(
        status=welcome_resp.status,
        extracted=extracted,
        message_draft=welcome_resp.message_draft,
    )


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
# ---------------------------------------------------------------------------

async def fn_match_applicants(req: MatchApplicantsRequest) -> MatchApplicantsResponse:
    try:
        results = await hubspot_service.list_applicant_contacts(limit=req.max_results)
        matches = [
            {"id": r.get("id"), "properties": r.get("properties", {})}
            for r in results
        ]
        return MatchApplicantsResponse(status="ok", matches=matches, count=len(matches))
    except Exception as exc:
        log.warning("HubSpot search_contacts failed: %s", exc)
        return MatchApplicantsResponse(status="error", matches=[], count=0)


# ---------------------------------------------------------------------------
# fn_valuation_brief  (M2 — Claude API)
# ---------------------------------------------------------------------------

async def fn_valuation_brief(req: ValuationBriefRequest) -> ValuationBriefResponse:
    client = _anthropic_client()
    if client is None:
        return ValuationBriefResponse(status="blocked", briefing=None)

    try:
        sqft_line = f" Approximately {req.sqft} sqft." if req.sqft else ""
        condition_line = f" Condition: {req.condition}." if req.condition else ""
        prompt = (
            f"You are an estate agent at Curtis Sloane preparing a valuation briefing "
            f"pack for a London property. Write a concise, professional briefing.\n\n"
            f"Property:\n"
            f"- Address: {req.address}\n"
            f"- Postcode: {req.postcode}\n"
            f"- Type: {req.property_type}\n"
            f"- Bedrooms: {req.bedrooms}\n"
            f"{sqft_line}{condition_line}\n\n"
            f"Structure the briefing with short sections:\n"
            f"1. Executive summary (1–2 sentences)\n"
            f"2. Suggested asking price range (use your London market knowledge)\n"
            f"3. Comparables strategy (how to reference similar recent sales)\n"
            f"4. Positioning (what to emphasise in the marketing)\n"
            f"5. Realistic time-on-market expectation\n\n"
            f"Keep the entire briefing under 250 words. Use plain prose, no markdown headers, "
            f"just short paragraphs. Do not use square-bracketed placeholders."
        )

        message = client.messages.create(
            model=MODEL_GENERATE,
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
        briefing = message.content[0].text.strip()
        return ValuationBriefResponse(status="ok", briefing=briefing)

    except Exception as exc:
        log.warning("Claude call failed (valuation): %s", exc)
        return ValuationBriefResponse(status="error", briefing=f"Claude error: {exc}")


# ---------------------------------------------------------------------------
# fn_draft_outreach  (M2 — Claude API)
# ---------------------------------------------------------------------------

_CHANNEL_GUIDE = {
    "email":            "Format as an email. Friendly but professional. 80–120 words.",
    "handwritten_note": "Format as a short handwritten note. Warm and personal. 40–80 words, single paragraph.",
    "letter":           "Format as a formal letter. 100–160 words. No subject line.",
}

_RECIPIENT_GUIDE = {
    "long_term_resident": "a long-term resident of the area who may consider a move",
    "recent_enquirer":    "someone who recently enquired about properties",
    "warm_lead":          "a warm lead who has shown genuine interest",
    "lapsed":             "a lapsed contact we haven't spoken to recently",
}


async def fn_draft_outreach(req: DraftOutreachRequest) -> DraftOutreachResponse:
    client = _anthropic_client()
    if client is None:
        return DraftOutreachResponse(status="blocked", draft=None)

    try:
        channel_instr   = _CHANNEL_GUIDE.get(req.channel, "Professional tone.")
        recipient_desc  = _RECIPIENT_GUIDE.get(req.recipient_type, "a contact")
        context_line    = f"Context: {req.context_notes}\n" if req.context_notes else ""
        property_line   = f"Property of interest: {req.property_mention}\n" if req.property_mention else ""

        prompt = (
            f"You are {req.agent_name}, an estate agent at Curtis Sloane (London W11).\n\n"
            f"Draft an outreach message to {req.recipient_name}, who is {recipient_desc}.\n\n"
            f"{context_line}{property_line}"
            f"Channel: {req.channel}. {channel_instr}\n\n"
            f"Requirements:\n"
            f"- Address {req.recipient_name} by name\n"
            f"- Sign off with your name ({req.agent_name})\n"
            f"- Warm but professional\n"
            f"- No placeholder text in square brackets\n"
            f"- Ready to send as-is"
        )

        message = client.messages.create(
            model=MODEL_GENERATE,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        draft = message.content[0].text.strip()
        return DraftOutreachResponse(status="ok", draft=draft)

    except Exception as exc:
        log.warning("Claude call failed (outreach): %s", exc)
        return DraftOutreachResponse(status="error", draft=f"Claude error: {exc}")


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
