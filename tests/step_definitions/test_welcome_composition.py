"""
BDD step definitions — FS-57 deterministic welcome email.

Tests-first. All offline:
  - register_applicant_in_hubspot is patched to a deterministic fake (no network)
  - find_matching_listings is patched to a controlled match list, so first_matches
    is exact and composition is tested independently of the matching engine
  - the body is a deterministic template (no Claude call); ANTHROPIC_MODE=mock is
    set in conftest regardless

Template under test (plain text):

    Subject: {count_word} {property|properties} to start your search

    Hi {first_name},                 # "Hello," when no first name

    Thank you for registering with Curtis Sloane. Here is what we have noted for
    your search:

    {search_line}                    # whole sentence+line omitted when empty

    To start, {this one stands out|these are the {count_word} that fit best}:

    {listing_lines}

    If any of these catch your eye, reply to this email and I will arrange a
    viewing and send you the full details.

    Best wishes,
    {agent_name}
    Curtis Sloane

Pinned decisions:
  - listing line: "{n}. {address}, £{price_gbp:,}, {bedrooms} bedroom[s]"
      * 1 bedroom -> singular "1 bedroom"
      * bedrooms missing -> that part dropped entirely
  - allowlist = {address, price_gbp, bedrooms}; nothing else from a match appears
  - search_line parts joined by " · ", supplied parts only, never the HubSpot band
      * property type "flat" -> "Flat"
      * budget: < £1m -> whole thousands "around £750k"; >= £1m -> up to two
        decimals, trailing zeros trimmed ("around £1m", "around £1.5m",
        "around £1.25m")
      * timeline 12 -> "within 12 weeks"
  - zero matches -> holding message + subject "Thank you for registering with
    Curtis Sloane"
  - agent_name: display name from app.auth._USERS (injected by test); fallback
    "The Curtis Sloane team". _USERS has NO names in source.
"""
import sys, os, re, html, itertools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from fastapi.testclient import TestClient

from app.main import app
import app.auth as auth
import app.functions.bot_functions as bot_functions
from app.services.hubspot_registration import RegistrationResult

scenarios("../features/welcome_composition.feature")

client = TestClient(app)
_id_seq = itertools.count(start=9001)

AGENT_EMAIL = "agent@curtissloane.com"
AGENT_PASSWORD = "agent123"

_STATE = {"matches": []}


def _match(address, price, bedrooms, pid):
    """A PropertyMatch dict as find_matching_listings returns it, carrying the
    internal fields the allowlist must exclude (distinctive sentinels)."""
    return {
        "property_id":  pid,
        "address":      address,
        "price_gbp":    price,
        "bedrooms":     bedrooms,
        "match_score":  0.87,                      # sentinel — must never appear
        "match_reason": "INTERNAL-REASON-XYZ",     # sentinel — must never appear
        "notes":        "SECRET-NOTE-LEAK",        # sentinel — must never appear
    }


THREE = [
    _match("105 Pine Street", 780_000, 2, "PROP-SECRET-1"),
    _match("22 Oak Lane",     910_000, 3, "PROP-SECRET-2"),
    _match("8 Birch Mews",  1_010_000, 2, "PROP-SECRET-3"),
]
TWO = THREE[:2]
ONE = THREE[:1]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    async def fake_register(criteria, hs_client):
        return RegistrationResult(contact_id=str(next(_id_seq)), created=True)
    monkeypatch.setattr(bot_functions, "register_applicant_in_hubspot", fake_register)

    async def fake_matching(criteria, limit=3):
        return list(_STATE["matches"])
    monkeypatch.setattr(bot_functions, "find_matching_listings", fake_matching)

    _STATE["matches"] = []
    yield


class Ctx:
    def __init__(self):
        self.headers = {}
        self.email = AGENT_EMAIL
        self.response = None
        self.rendered = None       # set by the direct-builder scenario
        self.body = {
            "full_name": "Sarah Chen",
            "email": "sarah.chen@example.com",
            "phone": "07700900123",
            "budget_gbp": 2_000_000,
            "bedrooms_min": 2,
            "property_types": ["house"],
            "financing": "cash",
            "preferred_channel": "email",
            "source": "Referral",
        }


@pytest.fixture
def ctx():
    return Ctx()


def _login(email=AGENT_EMAIL, password=AGENT_PASSWORD):
    r = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json().get('access_token', '')}"}


def _wd(ctx):
    if ctx.rendered is not None:
        return ctx.rendered
    return ctx.response.json().get("welcome_draft") or {}


def _text(ctx):
    return _wd(ctx).get("text_body") or ""


def _html(ctx):
    return _wd(ctx).get("html_body") or ""


def _subject(ctx):
    return _wd(ctx).get("subject") or ""


def _both(ctx):
    return _text(ctx) + "\n" + _html(ctx)


def _first_matches(ctx):
    return ctx.response.json().get("first_matches") or []


def _numbered_lines(text):
    return re.findall(r"^\s*\d+\.\s+.+$", text, flags=re.MULTILINE)


def _search_line(text):
    marker = "noted for your search:"
    idx = text.find(marker)
    if idx == -1:
        return ""
    rest = text[idx + len(marker):].strip().splitlines()
    return rest[0].strip() if rest else ""


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------

@given("an authenticated agent in the Curtis Sloane workspace")
def step_auth(ctx):
    ctx.headers = _login(ctx.email)


@given("HubSpot registration is served by an offline fake")
def step_offline_hs(ctx):
    pass


@given("matching is served by an offline fake")
def step_offline_matching(ctx):
    pass


# ---------------------------------------------------------------------------
# Givens — match sets and payload shape
# ---------------------------------------------------------------------------

@given("the applicant has three matched listings")
@given("the applicant has three matched listings carrying internal fields")
def step_three(ctx):
    _STATE["matches"] = [dict(m) for m in THREE]


@given("the applicant has two matched listings")
def step_two(ctx):
    _STATE["matches"] = [dict(m) for m in TWO]


@given("the applicant has one matched listing")
def step_one(ctx):
    _STATE["matches"] = [dict(m) for m in ONE]


@given("the applicant has no matched listings")
def step_none(ctx):
    _STATE["matches"] = []


@given("a matched listing with one bedroom")
def step_one_bed(ctx):
    _STATE["matches"] = [_match("3 Maple Court", 650_000, 1, "PROP-1BED")]


@given("a matched listing with no bedroom count")
def step_no_bed(ctx):
    _STATE["matches"] = [_match("7 Cedar Rise", 680_000, None, "PROP-NOBED")]


@given("a matched listing whose address contains \"<\" \"&\" and \">\"")
def step_escape_listing(ctx):
    _STATE["matches"] = [_match("5 <Script> & Co", 800_000, 2, "PROP-ESC")]


@given(parsers.parse("the applicant supplied a flat and a {budget:d} budget but no timeline"))
def step_flat_budget_no_timeline(ctx, budget):
    ctx.body["property_types"] = ["flat"]
    ctx.body["budget_gbp"] = budget
    ctx.body.pop("timeline_weeks", None)


@given(parsers.parse("the applicant supplied a flat, a {budget:d} budget and a {weeks:d} week timeline"))
def step_flat_budget_timeline(ctx, budget, weeks):
    ctx.body["property_types"] = ["flat"]
    ctx.body["budget_gbp"] = budget
    ctx.body["timeline_weeks"] = weeks


@given("the applicant's name is a single word")
def step_single_word_name(ctx):
    ctx.body["full_name"] = "Cher"


@given(parsers.parse('the agent has a configured display name "{name}"'))
def step_set_display_name(ctx, monkeypatch, name):
    user = dict(auth._USERS[AGENT_EMAIL])
    user["name"] = name
    monkeypatch.setitem(auth._USERS, AGENT_EMAIL, user)
    ctx.headers = _login(ctx.email)


@given("the agent has no configured display name")
def step_no_display_name(ctx, monkeypatch):
    user = dict(auth._USERS[AGENT_EMAIL])
    user.pop("name", None)
    monkeypatch.setitem(auth._USERS, AGENT_EMAIL, user)
    ctx.headers = _login(ctx.email)


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------

@when("the applicant is registered")
def step_register(ctx):
    ctx.response = client.post("/bot/register-applicant", json=ctx.body, headers=ctx.headers)
    assert ctx.response.status_code == 200, ctx.response.text
    assert ctx.response.json().get("status") == "ok", ctx.response.text


@when("the welcome email is rendered with no supplied search criteria")
def step_render_empty_search(ctx):
    builder = getattr(bot_functions, "_render_welcome_email", None)
    assert builder, "FS-57 builder bot_functions._render_welcome_email not implemented yet"
    ctx.rendered = builder(
        first_name="Sarah",
        search_parts=[],
        matches=[dict(ONE[0])],
        agent_name="The Curtis Sloane team",
    )


# ---------------------------------------------------------------------------
# Then — listings from first_matches only
# ---------------------------------------------------------------------------

@then("the email lists exactly the three matched listings, numbered")
def step_three_numbered(ctx):
    lines = _numbered_lines(_text(ctx))
    assert len(lines) == 3, f"expected 3 numbered lines, got {lines}"
    for i, m in enumerate(_first_matches(ctx), start=1):
        bed = "" if m["bedrooms"] is None else f", {m['bedrooms']} bedroom{'' if m['bedrooms'] == 1 else 's'}"
        expected = f"{i}. {m['address']}, £{m['price_gbp']:,}{bed}"
        assert expected in _text(ctx), f"missing listing line: {expected!r}"


@then("every address, price and bedroom count in the email is one from first_matches")
def step_details_from_first_matches(ctx):
    addresses = {m["address"] for m in _first_matches(ctx)}
    prices = {f"£{m['price_gbp']:,}" for m in _first_matches(ctx)}
    for line in _numbered_lines(_text(ctx)):
        assert any(a in line for a in addresses), f"line has an address not in first_matches: {line!r}"
        assert any(p in line for p in prices), f"line has a price not in first_matches: {line!r}"


@then("no match score, property id, match reason or note appears in the email")
def step_no_internal(ctx):
    body = _both(ctx)
    for sentinel in ("0.87", "INTERNAL-REASON-XYZ", "SECRET-NOTE-LEAK",
                     "PROP-SECRET-1", "PROP-SECRET-2", "PROP-SECRET-3"):
        assert sentinel not in body, f"non-allowlisted field leaked into email: {sentinel!r}"


@then(parsers.parse('the listing line reads "{expected}"'))
def step_listing_line(ctx, expected):
    assert expected in _text(ctx), f"listing line not found: {expected!r}\n---\n{_text(ctx)}"


# ---------------------------------------------------------------------------
# Then — search line
# ---------------------------------------------------------------------------

@then(parsers.parse('the search line reads "{expected}"'))
def step_search_line(ctx, expected):
    actual = _search_line(_text(ctx))
    assert actual == expected, f"search line was {actual!r}, expected {expected!r}"


@then("the HubSpot budget band does not appear in the email")
def step_band_absent(ctx):
    body = _both(ctx).lower()
    assert "up_to_" not in body and "ten_plus" not in body, "HubSpot budget band leaked into email"


@then("the email omits the search sentence and line")
def step_search_omitted(ctx):
    assert "noted for your search" not in _text(ctx), "search sentence present when it should be omitted"


# ---------------------------------------------------------------------------
# Then — HTML escaping
# ---------------------------------------------------------------------------

@then("the html body contains the escaped address")
def step_html_escaped(ctx):
    raw = _STATE["matches"][0]["address"]
    assert html.escape(raw) in _html(ctx), "escaped address not found in html body"


@then("the html body does not contain the raw unescaped address")
def step_html_not_raw(ctx):
    raw = _STATE["matches"][0]["address"]
    assert raw not in _html(ctx), "raw unescaped address present in html body"


@then("the text body contains the raw address")
def step_text_raw(ctx):
    raw = _STATE["matches"][0]["address"]
    assert raw in _text(ctx), "raw address not found in text body"


# ---------------------------------------------------------------------------
# Then — count variants
# ---------------------------------------------------------------------------

@then(parsers.parse('the subject is "{expected}"'))
def step_subject(ctx, expected):
    assert _subject(ctx) == expected, f"subject was {_subject(ctx)!r}, expected {expected!r}"


@then("the email says no close match yet")
def step_holding(ctx):
    expected = ("We don't have a close match yet, but we will be in touch as soon "
                "as something suitable comes in.")
    assert expected in _text(ctx), "holding message missing for zero-match case"


@then("the email contains no numbered listing line")
def step_no_lines(ctx):
    assert _numbered_lines(_text(ctx)) == [], "a numbered listing line appeared with zero matches"


@then(parsers.parse('the email contains "{snippet}"'))
def step_contains(ctx, snippet):
    assert snippet in _text(ctx), f"email did not contain: {snippet!r}"


@then(parsers.parse('the email does not contain "{snippet}"'))
def step_not_contains(ctx, snippet):
    assert snippet not in _text(ctx), f"email unexpectedly contained: {snippet!r}"


@then("the email contains exactly one numbered listing line")
def step_one_line(ctx):
    assert len(_numbered_lines(_text(ctx))) == 1, _numbered_lines(_text(ctx))


@then("the email contains exactly two numbered listing lines")
def step_two_lines(ctx):
    assert len(_numbered_lines(_text(ctx))) == 2, _numbered_lines(_text(ctx))


@then("the email contains exactly three numbered listing lines")
def step_three_lines(ctx):
    assert len(_numbered_lines(_text(ctx))) == 3, _numbered_lines(_text(ctx))


# ---------------------------------------------------------------------------
# Then — sign-off
# ---------------------------------------------------------------------------

@then(parsers.parse('the email is signed off with "{name}"'))
def step_signoff_name(ctx, name):
    assert name in _both(ctx), f"sign-off did not use the display name {name!r}"


@then("the sign-off is not the agent's email local-part")
def step_signoff_not_email(ctx):
    local = ctx.email.split("@")[0]
    assert f"\n{local.capitalize()}\n" not in _both(ctx), "sign-off was derived from the email local-part"


@then(parsers.parse('the email is signed off as "{team}"'))
def step_signoff_team(ctx, team):
    assert team in _both(ctx), f"sign-off did not fall back to {team!r}"
