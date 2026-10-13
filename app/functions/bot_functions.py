"""
All 6 bot function implementations.
- fn_generate_welcome, fn_valuation_brief, fn_draft_outreach → Claude API (M2)
- fn_register_applicant, fn_match_applicants, fn_kyc_status → HubSpot API (M2/M3)
"""

from __future__ import annotations

import html
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
from app.constants.registration_constants import VALID_PROPERTY_TYPES, VALID_SOURCE
from app.services.hubspot_registration import (
    RegistrationError,
    register_applicant_in_hubspot,
)
from app.services.hubspot_client import build_hubspot_client
from app.services.matching import find_matching_listings
from app.services.transports.gmail import create_draft

log = logging.getLogger(__name__)

# Model selection — Sonnet 4.6 for generation, Haiku 4.5 for fast extraction
MODEL_GENERATE = "claude-sonnet-4-6"
MODEL_EXTRACT  = "claude-haiku-4-5-20251001"


def _anthropic_client():
    """
    Return a Claude client honouring ANTHROPIC_MODE (real / mock / record).
    Returns None only when mode='real' and ANTHROPIC_API_KEY is unset.
    """
    from app.clients.claude_client import get_client
    return get_client()


# ---------------------------------------------------------------------------
# fn_generate_welcome  (M2 — Claude API, form-based entry)
# ---------------------------------------------------------------------------

async def fn_generate_welcome(req: WelcomeRequest) -> WelcomeResponse:
    client = _anthropic_client()
    if client is None:
        return WelcomeResponse(status="blocked", message_draft=None)

    try:
        budget_line   = f" Their budget is £{req.budget_gbp:,}." if req.budget_gbp else ""
        timeline_line = f" Their timeline: {req.timeline}." if req.timeline else ""
        property_line = f" Property preference: {req.property_type}." if req.property_type else ""
        prompt = (
            f"You are {req.agent_name}, an estate agent at Curtis Sloane, a London "
            f"property firm specialising in W11 (Notting Hill, Holland Park).\n\n"
            f"Write a short, professional welcome message for a new client named "
            f"{req.client_name} who found you through {req.source}."
            f"{budget_line}{timeline_line}{property_line}\n\n"
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

        # Optional HubSpot dispatch — only when requested
        hubspot_id: Optional[str] = None
        dispatched = False
        if req.dispatch:
            try:
                hs_result = await hubspot_service.create_contact({
                    "firstname": req.client_name.split()[0],
                    "lastname":  " ".join(req.client_name.split()[1:]) or "",
                    # FS-57: this dispatch write still uses the old "applicant_source"
                    # name; FS-57 removes fn_generate_welcome's dispatch behaviour.
                    "applicant_source": req.source,
                })
                hubspot_id = str(hs_result.get("id", "")) or None
                dispatched = hubspot_id is not None
            except Exception as exc:
                log.warning("Welcome dispatch to HubSpot failed: %s", exc)

        return WelcomeResponse(
            status="ok",
            message_draft=draft,
            hubspot_contact_id=hubspot_id,
            dispatched=dispatched,
        )

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

# ---------------------------------------------------------------------------
# FS-55 adapters — map the RegisterApplicantRequest onto the FS-50 criteria
# vocabulary (A-2 rev 5). No pre-amendment field names appear here.
# ---------------------------------------------------------------------------

# Source enum (lowercase, FS-50 constants) <-> WelcomeRequest's title-case Literal.
_SOURCE_TITLE = {"rightmove": "Rightmove", "zoopla": "Zoopla", "referral": "Referral",
                 "direct": "Direct", "other": "Other"}


def _budget_to_band(gbp: int) -> str:
    # Round UP to the nearest £1M ceiling; anything above £10M -> ten_plus.
    # PENDING R8 — not confirmed by Olesya. See TS v1.2 page 50823188 section 3.3.
    import math
    millions = math.ceil(gbp / 1_000_000)
    return f"up_to_{millions}m" if millions <= 10 else "ten_plus"


def _beds_to_band(n: int) -> str:
    # Floor band N_plus, capped at the configured ceiling (6_plus).
    return f"{min(max(n, 1), 6)}_plus"


def _norm_source(s: str) -> str:
    v = (s or "").strip().lower()
    return v if v in VALID_SOURCE else "other"


# FS-67: legacy API inputs mapped to canonical live values before the write.
_PROPERTY_TYPE_ALIASES = {"flat": "apartment"}


def _norm_property_types(types: List[str]) -> List[str]:
    # "any" -> skip predicate (no property-type constraint written / matched).
    # PENDING owner confirmation (Olesya): treat "any" as skip vs expand to all types.
    if "any" in types:
        return []
    mapped = [_PROPERTY_TYPE_ALIASES.get(t, t) for t in types]
    return [t for t in mapped if t in VALID_PROPERTY_TYPES]


def _request_to_criteria(req: RegisterApplicantRequest) -> Dict[str, Any]:
    return {
        "full_name":         req.full_name,
        "email":             req.email,
        "phone":             req.phone,
        "budget":            _budget_to_band(req.budget_gbp),
        "beds_required":     _beds_to_band(req.bedrooms_min),
        "property_types":    _norm_property_types(req.property_types),
        "financing_status":  req.financing,
        "preferred_channel": req.preferred_channel,
        "source":            _norm_source(req.source),
    }


# ---------------------------------------------------------------------------
# FS-57 — deterministic welcome email (NO Claude call for the body).
# fn_generate_welcome and the standalone welcome path are untouched; this is a
# separate, templated composer used only by registration step c.
# ---------------------------------------------------------------------------

_COUNT_WORD_CAP = {1: "One", 2: "Two", 3: "Three"}
_COUNT_WORD_LC = {2: "two", 3: "three"}


def _welcome_first_name(full_name: str) -> Optional[str]:
    """First word of a multi-word name; None for a single word (-> 'Hello,')."""
    parts = str(full_name or "").strip().split()
    return parts[0] if len(parts) >= 2 else None


def _budget_display(gbp: Optional[int]) -> Optional[str]:
    """Submitted budget as 'around £750k' (< £1m, whole thousands) or
    'around £1m' / '£1.5m' / '£1.25m' (>= £1m, up to two decimals, zeros
    trimmed). Never the HubSpot band."""
    if not gbp:
        return None
    if gbp < 1_000_000:
        return f"around £{round(gbp / 1000)}k"
    millions = f"{gbp / 1_000_000:.2f}".rstrip("0").rstrip(".")
    return f"around £{millions}m"


def _welcome_search_parts(req: RegisterApplicantRequest) -> List[str]:
    """The supplied-only search summary parts, in display order. Uses the
    SUBMITTED property types / budget / timeline — never the HubSpot band."""
    parts: List[str] = []
    types = [t for t in (req.property_types or []) if t != "any"]
    if types:
        parts.append("/".join(t.capitalize() for t in types))
    budget = _budget_display(req.budget_gbp)
    if budget:
        parts.append(budget)
    if req.timeline_weeks:
        parts.append(f"within {req.timeline_weeks} weeks")
    return parts


def _listing_content(match: dict) -> str:
    """One listing, by an EXPLICIT allowlist: address, price, bedrooms only.
    Nothing else on the match object (score, id, reason, notes) is read."""
    address = match.get("address")
    price = match.get("price_gbp")
    bedrooms = match.get("bedrooms")
    line = f"{address}, £{price:,}"
    if bedrooms is not None:
        line += f", {bedrooms} bedroom{'' if bedrooms == 1 else 's'}"
    return line


def _render_welcome_email(
    *,
    first_name: Optional[str],
    search_parts: List[str],
    matches: List[dict],
    agent_name: Optional[str],
) -> Dict[str, str]:
    """Pure, deterministic template -> {subject, html_body, text_body}."""
    count = len(matches)
    agent = agent_name or "The Curtis Sloane team"
    greeting = f"Hi {first_name}," if first_name else "Hello,"
    contents = [_listing_content(m) for m in matches]

    # Subject
    if count == 0:
        subject = "Thank you for registering with Curtis Sloane"
    else:
        noun = "property" if count == 1 else "properties"
        subject = f"{_COUNT_WORD_CAP.get(count, count)} {noun} to start your search"

    # Lead-in (non-zero only)
    lead = None
    if count == 1:
        lead = "To start, this one stands out:"
    elif count > 1:
        lead = f"To start, these are the {_COUNT_WORD_LC.get(count, count)} that fit best:"

    holding = ("We don't have a close match yet, but we will be in touch as soon "
               "as something suitable comes in.")
    closing = ("If any of these catch your eye, reply to this email and I will "
               "arrange a viewing and send you the full details.")
    search_sentence = ("Thank you for registering with Curtis Sloane. Here is "
                       "what we have noted for your search:")
    signoff = f"Best wishes,\n{agent}\nCurtis Sloane"

    # --- plain text ---
    text_blocks: List[str] = [greeting]
    if search_parts:
        text_blocks.append(f"{search_sentence}\n\n" + " · ".join(search_parts))
    if count == 0:
        text_blocks.append(holding)
    else:
        text_blocks.append(lead)
        text_blocks.append("\n".join(f"{i}. {c}" for i, c in enumerate(contents, 1)))
        text_blocks.append(closing)
    text_blocks.append(signoff)
    text_body = "\n\n".join(text_blocks)

    # --- html (escape every inserted value) ---
    html_blocks: List[str] = [f"<p>{html.escape(greeting)}</p>"]
    if search_parts:
        html_blocks.append(
            f"<p>{html.escape(search_sentence)}<br>"
            f"{html.escape(' · '.join(search_parts))}</p>"
        )
    if count == 0:
        html_blocks.append(f"<p>{html.escape(holding)}</p>")
    else:
        html_blocks.append(f"<p>{html.escape(lead)}</p>")
        html_blocks.append(
            "<ol>" + "".join(f"<li>{html.escape(c)}</li>" for c in contents) + "</ol>"
        )
        html_blocks.append(f"<p>{html.escape(closing)}</p>")
    html_blocks.append(f"<p>Best wishes,<br>{html.escape(agent)}<br>Curtis Sloane</p>")
    html_body = "".join(html_blocks)

    return {"subject": subject, "html_body": html_body, "text_body": text_body}


def _compose_welcome_draft(
    req: RegisterApplicantRequest,
    matches: List[dict],
    agent_name: Optional[str] = None,
) -> Dict[str, str]:
    """Step-c composer: assemble the template inputs from the SUBMITTED request
    and the matches, then render deterministically. No Claude call."""
    return _render_welcome_email(
        first_name=_welcome_first_name(req.full_name),
        search_parts=_welcome_search_parts(req),
        matches=matches,
        agent_name=agent_name,
    )


async def fn_register_applicant(
    req: RegisterApplicantRequest,
    agent_name: Optional[str] = None,
) -> RegisterApplicantResponse:
    """
    FS-55 four-step orchestrator (A-2 rev 5). This function performs none of the
    work itself — it delegates to four collaborators and isolates each one's
    failure so a later step never unwinds an earlier success.

    agent_name (FS-57): the signed-in agent's display name for the welcome
    sign-off; falls back to "The Curtis Sloane team" when None.
    """
    errors: List[str] = []
    criteria = _request_to_criteria(req)

    # ---- Step a: register in HubSpot — ALWAYS. Validation or step-a failure
    # returns early; steps b/c/d never run. -------------------------------
    try:
        reg = await register_applicant_in_hubspot(criteria, build_hubspot_client())
        applicant_id, created, diff = reg.contact_id, reg.created, reg.diff
    except RegistrationError as exc:
        errors.append(exc.code or "HUBSPOT_SYNC_FAIL")
        return RegisterApplicantResponse(
            status="error", applicant_id=None, first_matches=[],
            welcome_draft=None, draft_ref=None, errors=errors,
        )
    except Exception as exc:
        log.warning("Step a (register) failed: %s", exc)
        errors.append("HUBSPOT_SYNC_FAIL")
        return RegisterApplicantResponse(
            status="error", applicant_id=None, first_matches=[],
            welcome_draft=None, draft_ref=None, errors=errors,
        )

    # ===== applicant STAYS REGISTERED regardless of what b/c/d do =====

    # ---- Step b: matching — ALWAYS; isolated. --------------------------
    first_matches: List[dict] = []
    try:
        # FS-70: Direction-1 deterministic engine (fetches listings live).
        first_matches = await find_matching_listings(criteria, limit=3)
    except Exception as exc:
        log.warning("Step b (matching) failed: %s", exc)
        errors.append(f"MATCH_FAILED: {exc}")
        first_matches = []

    # ---- Step c: welcome composition — ALWAYS; isolated. ---------------
    welcome_draft: Optional[Dict[str, str]] = None
    try:
        # FS-57: deterministic template (no Claude call); composition runs on
        # every registration including dispatch=false per A-2 rev 5.
        welcome_draft = _compose_welcome_draft(req, first_matches, agent_name=agent_name)
    except Exception as exc:
        log.warning("Step c (welcome) failed: %s", exc)
        errors.append(f"WELCOME_FAILED: {exc}")
        welcome_draft = None

    # ---- Step d: create draft — ONLY when dispatch=True; isolated. ------
    draft_ref: Optional[Dict[str, str]] = None
    if getattr(req, "dispatch", False) and welcome_draft is not None:
        try:
            draft_ref = create_draft(welcome_draft)
        except Exception as exc:
            log.warning("Step d (draft) failed: %s", exc)
            errors.append(f"DRAFT_FAILED: {exc}")
            draft_ref = None

    return RegisterApplicantResponse(
        status="ok",
        applicant_id=applicant_id,
        created=created,
        diff=diff,
        first_matches=first_matches,
        welcome_draft=welcome_draft,
        draft_ref=draft_ref,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# fn_match_applicants  (M3 — HubSpot contacts.read)
# ---------------------------------------------------------------------------

_KYC_COMPLETE_STATES = {"complete", "verified", "approved"}


def _score_applicants_via_claude(property_summary: str, applicants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ask Claude to score each applicant. Returns list of dicts:
        [{"applicant_id": str, "match_score": float, "match_reason": str}, ...]
    Falls back to deterministic 0.7 scores if the call or parse fails.
    """
    client = _anthropic_client()
    fallback = [
        {
            "applicant_id": a.get("id"),
            "match_score":  0.7,
            "match_reason": "Meets core criteria for this property based on budget and bedroom requirements.",
        }
        for a in applicants
    ]
    if client is None or not applicants:
        return fallback

    applicant_blocks = []
    for i, a in enumerate(applicants[:20], start=1):  # cap at 20 for prompt size
        applicant_blocks.append(
            f"\nApplicant {i}: {a.get('name')} (ID: {a.get('id')})"
            f"\nBudget: £{float(a.get('budget_gbp') or 0):,.0f}"
            f"\nBedrooms wanted: {a.get('bedrooms_min')}-{a.get('bedrooms_max') or 'any'}"
            f"\nProperty types: {a.get('property_types')}"
            f"\nFinancing: {a.get('financing')}"
            f"\nMust-haves: {a.get('must_have')}"
            f"\nTimeline: {a.get('timeline_weeks')} weeks\n"
        )

    scoring_prompt = (
        "You are a property matching expert at Curtis Sloane estate agency.\n\n"
        "Score each applicant's fit for this property. Return ONLY valid JSON, no other text.\n\n"
        f"PROPERTY:\n{property_summary}\n\n"
        f"APPLICANTS:\n{''.join(applicant_blocks)}\n\n"
        "Return a JSON array with one object per applicant:\n"
        "[\n"
        "  {\n"
        "    \"applicant_id\": \"HubSpot contact ID\",\n"
        "    \"match_score\": 0.0 to 1.0,\n"
        "    \"match_reason\": \"Plain English explanation of at least 15 words referencing budget headroom, financing strength, feature alignment, and timeline urgency\"\n"
        "  }\n"
        "]\n\n"
        "Scoring criteria:\n"
        "- Cash buyer scores higher than mortgage when all else equal\n"
        "- Larger budget headroom scores higher\n"
        "- Must-have features present in listing score higher\n"
        "- Shorter timeline scores higher (more urgent buyer)\n"
        "- Score 0.9+ only for exceptional fit on all criteria\n"
    )

    try:
        msg = client.messages.create(
            model=MODEL_GENERATE,
            max_tokens=2000,
            messages=[{"role": "user", "content": scoring_prompt}],
        )
        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw, re.DOTALL)
            if m:
                raw = m.group(1)
        parsed = json.loads(raw)
        if isinstance(parsed, list) and all("applicant_id" in s for s in parsed):
            return parsed
        log.warning("Claude scoring returned unexpected shape; using fallback")
        return fallback
    except Exception as exc:
        log.warning("Claude scoring failed (%s); using fallback", exc)
        return fallback


async def fn_match_applicants(req: MatchApplicantsRequest) -> MatchApplicantsResponse:
    token = os.getenv("HUBSPOT_API_KEY")

    # Stage 1: Property lookup ---------------------------------------------
    try:
        listing = await hubspot_service.get_listing_by_address(req.property_ref, token)
    except Exception as exc:
        log.warning("HubSpot listing lookup failed: %s", exc)
        return MatchApplicantsResponse(
            status="error",
            error_code="HUBSPOT_SYNC_FAIL",
            message=f"Could not reach HubSpot — please try again in a few minutes. ({exc})",
            matches=[], count=0, total_searched=0,
        )

    if listing is None:
        return MatchApplicantsResponse(
            status="error",
            error_code="PROPERTY_NOT_FOUND",
            message=f"Property '{req.property_ref}' not found in HubSpot. Please provide price_gbp, bedrooms, and property_type.",
            matches=[], count=0, total_searched=0,
        )

    price         = float(listing.get("price_gbp") or 0)
    bedrooms      = int(listing.get("bedrooms") or 0)
    listing_type  = (listing.get("listing_type") or "").lower()
    outside_space = (listing.get("outside_space") or "").lower()

    # Stage 2: Applicant retrieval ------------------------------------------
    try:
        all_applicants = await hubspot_service.get_all_applicants(token)
    except Exception as exc:
        log.warning("HubSpot applicants fetch failed: %s", exc)
        return MatchApplicantsResponse(
            status="error",
            error_code="HUBSPOT_SYNC_FAIL",
            message=f"Could not reach HubSpot — please try again in a few minutes. ({exc})",
            matches=[], count=0, total_searched=0,
        )
    total_searched = len(all_applicants)

    # Stage 3: Hard filter --------------------------------------------------
    filtered: List[Dict[str, Any]] = []
    for a in all_applicants:
        budget  = float(a.get("budget_gbp") or 0)
        bed_min = int(a.get("bedrooms_min") or 0)
        bed_max = a.get("bedrooms_max")
        prop_types = [t.strip().lower() for t in (a.get("property_types") or "").split(";") if t.strip()]

        if budget > 0 and price > 0 and budget < price * 0.95:
            continue
        if bed_min > 0 and bedrooms > 0 and bed_min > bedrooms:
            continue
        if bed_max and int(bed_max) > 0 and bedrooms > 0 and int(bed_max) < bedrooms:
            continue
        if prop_types and listing_type and listing_type not in prop_types:
            continue

        filtered.append(a)

    if not filtered:
        return MatchApplicantsResponse(
            status="ok",
            matches=[], count=0, total_searched=total_searched,
            message="No matching applicants found for this property based on current search criteria.",
        )

    # Stage 4: AI scoring ---------------------------------------------------
    property_summary = (
        f"Property: {listing.get('name')}\n"
        f"Price: £{price:,.0f}\n"
        f"Bedrooms: {bedrooms}\n"
        f"Type: {listing_type}\n"
        f"Outside space: {outside_space}\n"
        f"Neighbourhood: {listing.get('neighborhood')}"
    )
    scores = _score_applicants_via_claude(property_summary, filtered)
    score_map = {s.get("applicant_id"): s for s in scores}

    # Stage 5: Assemble results with KYC flagging + sort + limit ------------
    match_records: List[Dict[str, Any]] = []
    for a in filtered:
        s = score_map.get(a.get("id"), {})
        # FS-67 KYC exception (blocked on item A, KYC-on-Deal): get_all_applicants
        # now parks kyc_status/kyc_documents_outstanding to None, so these reads
        # degrade to kyc_complete=False / no outstanding until KYC moves to the Deal.
        kyc_complete = (a.get("kyc_status") or "").lower() in _KYC_COMPLETE_STATES
        outstanding_raw = a.get("kyc_documents_outstanding") or ""
        # Support both comma- and semicolon-separated formats
        outstanding = [item.strip() for item in re.split(r"[,;]", outstanding_raw) if item.strip()]

        match_records.append({
            "applicant_id":          a.get("id"),
            "name":                  a.get("name"),
            "email":                 a.get("email"),
            "match_score":           float(s.get("match_score", 0.5)),
            "match_reason":          s.get("match_reason", "Meets core criteria."),
            "kyc_complete":          kyc_complete,
            "outstanding_kyc_items": [] if kyc_complete else outstanding,
            "financing":             a.get("financing"),
            "budget_gbp":            float(a.get("budget_gbp") or 0),
            "timeline_weeks":        int(a.get("timeline_weeks")) if a.get("timeline_weeks") else None,
        })

    match_records.sort(key=lambda x: x["match_score"], reverse=True)
    max_r = min(req.max_results or 5, 20)
    match_records = match_records[:max_r]

    return MatchApplicantsResponse(
        status="ok",
        matches=match_records,
        count=len(match_records),
        total_searched=total_searched,
    )


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
            # Distinct from a HubSpot exception: HubSpot answered, just had nothing.
            # Gherkin (m3_kyc_status.feature) expects status="error" + a message
            # containing "not found" for this case.
            return KYCStatusResponse(
                status="error",
                kyc_complete=None,
                outstanding_items=None,
                message=f"Contact not found for '{req.name_or_id}'",
            )

        props = contact.get("properties", {})
        # FS-67 KYC exception (blocked on item A, KYC-on-Deal): fn_kyc_status still
        # reads KYC from the contact; the new schema has no kyc_* on contacts, so
        # this returns "not found" live until KYC is read from the associated Deal.
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
        return KYCStatusResponse(
            status="error",
            kyc_complete=None,
            outstanding_items=None,
            message=f"HubSpot lookup failed: {exc}",
        )
