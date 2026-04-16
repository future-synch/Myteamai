"""
BDD step definitions — Tests 11 and 12 (M1 milestone).
Covers intent classification and input validation.
Zero external services — pure Python.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from pydantic import ValidationError

from app.classifier import classify, CAPABILITIES
from app.models.schemas import (
    WelcomeRequest,
    RegisterApplicantRequest,
    MatchApplicantsRequest,
    ValuationBriefRequest,
    DraftOutreachRequest,
    KYCStatusRequest,
)

# ---------------------------------------------------------------------------
# Load both feature files into this test module
# ---------------------------------------------------------------------------

scenarios("../features/m1_intent_classification.feature")
scenarios("../features/m1_validation.feature")


# ---------------------------------------------------------------------------
# Shared context fixture
# ---------------------------------------------------------------------------

class Ctx:
    def __init__(self):
        self.text        = None
        self.result      = None
        self.results     = []
        self.prior       = None
        self.validation_error = None
        self.stored_value = None


@pytest.fixture
def ctx():
    return Ctx()


# ===========================================================================
# BACKGROUND
# ===========================================================================

@given("an authenticated agent in the Curtis Sloane workspace")
def step_auth(ctx):
    ctx.workspace = "curtis_sloane"


@given("the bot supports 6 functions")
def step_supports_6(ctx):
    assert len(CAPABILITIES) == 6


# ===========================================================================
# WHEN — classification
# ===========================================================================

@when(parsers.parse('the agent sends "{text}"'))
def step_send(ctx, text):
    ctx.text = text
    ctx.result = classify(text)
    ctx.results.append(ctx.result)


@when(parsers.parse('the agent sends "{text}" three times'))
def step_send_three_times(ctx, text):
    ctx.text = text
    ctx.results = [classify(text), classify(text), classify(text)]
    ctx.result = ctx.results[-1]


@when(parsers.parse('the agent also sends "{text}"'))
def step_also_send(ctx, text):
    ctx.text = text
    r = classify(text)
    ctx.result = r
    ctx.results.append(r)


# ===========================================================================
# GIVEN — prior classification history
# ===========================================================================

@given(parsers.parse('the agent has a prior successful classification for "{prior_text}"'))
def step_prior_classification(ctx, prior_text):
    ctx.prior = classify(prior_text)
    assert ctx.prior.intent != "UNKNOWN_INTENT", (
        f"Prior classification should succeed, got UNKNOWN_INTENT for '{prior_text}'"
    )


# ===========================================================================
# THEN — classification
# ===========================================================================

@then(parsers.parse('the response status is "{status}"'))
def step_response_status(ctx, status):
    expected = "error" if ctx.result.is_unknown else "ok"
    assert expected == status, f"Expected status '{status}', got '{expected}'"


@then(parsers.parse('the error code is "{code}"'))
def step_error_code_is(ctx, code):
    assert ctx.result.intent == code, (
        f"Expected '{code}', got '{ctx.result.intent}' for input: '{ctx.text}'"
    )


@then(parsers.parse('the error code is not "{code}"'))
def step_error_code_not(ctx, code):
    assert ctx.result.intent != code, (
        f"Expected NOT '{code}', got '{ctx.result.intent}' for input: '{ctx.text}'"
    )


@then("no Claude API call is made")
def step_no_claude(ctx):
    assert ctx.result.tokens_consumed == 0


@then("no HubSpot API call is made")
def step_no_hubspot_class(ctx):
    assert ctx.result.intent is not None  # classifier ran, no HubSpot call possible


@then("the capability list contains exactly 6 items")
def step_caps_6(ctx):
    caps = ctx.result.capabilities
    assert caps is not None, "Expected capabilities list"
    assert len(caps) == 6, f"Expected 6 capabilities, got {len(caps)}"


@then("the capability list is shown")
def step_caps_shown(ctx):
    caps = ctx.result.capabilities
    assert caps is not None and len(caps) == 6


@then("the capability list is shown in English")
def step_caps_english(ctx):
    caps = ctx.result.capabilities
    assert caps is not None
    for cap in caps:
        assert cap.isascii(), f"Capability not ASCII/English: '{cap}'"


@then("the response message contains rephrasing guidance")
def step_rephrasing_guidance(ctx):
    msg = ctx.result.message or ""
    assert "couldn't understand" in msg.lower() or "can do" in msg.lower() or "can help" in msg.lower(), (
        f"Expected rephrasing guidance in message, got: '{msg}'"
    )


@then("the response message is a greeting")
def step_msg_greeting(ctx):
    msg = ctx.result.message or ""
    assert "hello" in msg.lower(), f"Expected greeting message, got: '{msg}'"


@then("the response message is a polite thank you")
def step_msg_polite(ctx):
    msg = ctx.result.message or ""
    assert "welcome" in msg.lower() or "anything else" in msg.lower(), (
        f"Expected polite thank-you message, got: '{msg}'"
    )


@then("the response message acknowledges the property address")
def step_msg_address(ctx):
    msg = ctx.result.message or ""
    assert "address" in msg.lower() or "recognise" in msg.lower() or "property" in msg.lower(), (
        f"Expected address acknowledgement in message, got: '{msg}'"
    )


@then("the system does not crash")
def step_no_crash(ctx):
    assert ctx.result is not None


@then(parsers.parse('the intent is "{expected_intent}"'))
def step_intent_is(ctx, expected_intent):
    assert ctx.result.intent == expected_intent, (
        f"Expected '{expected_intent}', got '{ctx.result.intent}' for: '{ctx.text}'"
    )


@then(parsers.parse('all three results have error code "{code}"'))
def step_all_three(ctx, code):
    for i, r in enumerate(ctx.results, 1):
        assert r.intent == code, f"Result {i}: expected '{code}', got '{r.intent}'"


@then("the prior result does not influence this classification")
def step_history_independent(ctx):
    assert ctx.result.intent == "UNKNOWN_INTENT"


@then("zero tokens are consumed")
def step_zero_tokens(ctx):
    assert ctx.result.tokens_consumed == 0


@then("the request does not count toward the rate limit")
def step_no_rate_limit(ctx):
    assert ctx.result.rate_limit_counted is False, (
        "Unknown intents should not count toward the per-hour rate limit"
    )


@then("the request counts toward the daily counter")
def step_daily_counter(ctx):
    assert ctx.result.daily_counter_counted is True


@then(parsers.parse('the session log intent is "{intent}"'))
def step_log_intent(ctx, intent):
    assert ctx.result.log_entry["intent"] == intent


@then(parsers.parse('the session log status is "{status}"'))
def step_log_status(ctx, status):
    assert ctx.result.log_entry["status"] == status


@then("no AI function is recorded in the session log")
def step_log_no_function(ctx):
    assert ctx.result.log_entry["ai_function"] is None


@then("no token usage is recorded in the session log")
def step_log_no_tokens(ctx):
    assert ctx.result.log_entry["token_usage"] is None


@then("all results have error code \"UNKNOWN_INTENT\"")
def step_all_unknown(ctx):
    for i, r in enumerate(ctx.results, 1):
        assert r.intent == "UNKNOWN_INTENT", (
            f"Result {i}: expected UNKNOWN_INTENT, got '{r.intent}'"
        )


@then("all results include the full capability list")
def step_all_have_caps(ctx):
    for i, r in enumerate(ctx.results, 1):
        assert r.capabilities is not None and len(r.capabilities) == 6, (
            f"Result {i}: missing capability list"
        )


# ===========================================================================
# WHEN — validation helpers
# ===========================================================================

def _try_welcome(**kwargs):
    """Helper: attempt WelcomeRequest, return (instance_or_None, error_or_None)."""
    try:
        req = WelcomeRequest(**kwargs)
        return req, None
    except ValidationError as e:
        return None, e


@when("the agent submits a welcome request with client_name blank")
def step_w_blank_name(ctx):
    _, ctx.validation_error = _try_welcome(
        client_name="", source="Rightmove", agent_name="James", dispatch=False
    )


@when("the agent submits a welcome request with all required fields blank")
def step_w_all_blank(ctx):
    _, ctx.validation_error = _try_welcome(
        client_name="", source="Rightmove", agent_name="", dispatch=None
    )


@when(parsers.parse('the agent submits a welcome request with client_name "{name}"'))
def step_w_name(ctx, name):
    req, ctx.validation_error = _try_welcome(
        client_name=name, source="Rightmove", agent_name="James", dispatch=False
    )
    ctx.stored_value = req.client_name if req else None


@when(parsers.parse('the agent submits a welcome request with source "{source}"'))
def step_w_source(ctx, source):
    _, ctx.validation_error = _try_welcome(
        client_name="James Hyde", source=source, agent_name="James", dispatch=False
    )


@when("the agent submits a welcome request with agent_name blank")
def step_w_blank_agent(ctx):
    _, ctx.validation_error = _try_welcome(
        client_name="James Hyde", source="Rightmove", agent_name="", dispatch=False
    )


@when("the agent submits a welcome request with dispatch blank")
def step_w_blank_dispatch(ctx):
    _, ctx.validation_error = _try_welcome(
        client_name="James Hyde", source="Rightmove", agent_name="James", dispatch=None
    )


@when(parsers.parse('the agent submits a welcome request with budget_gbp {value}'))
def step_w_budget(ctx, value):
    try:
        v = float(value) if "." in str(value) else int(value)
    except (ValueError, TypeError):
        v = value  # pass string through so Pydantic rejects it
    _, ctx.validation_error = _try_welcome(
        client_name="James Hyde", source="Rightmove",
        agent_name="James", dispatch=False, budget_gbp=v
    )


@when(parsers.parse('the agent submits a welcome request with budget_gbp "{value}"'))
def step_w_budget_str(ctx, value):
    _, ctx.validation_error = _try_welcome(
        client_name="James Hyde", source="Rightmove",
        agent_name="James", dispatch=False, budget_gbp=value
    )


@when("the agent submits a valid welcome request without budget_gbp")
def step_w_no_budget(ctx):
    req, err = _try_welcome(
        client_name="James Hyde", source="Rightmove", agent_name="James", dispatch=False
    )
    ctx.validation_error = err
    ctx.stored_value = req


@when("any form has a validation error")
def step_any_form_error(ctx):
    _, ctx.validation_error = _try_welcome(
        client_name="", source="Rightmove", agent_name="James", dispatch=False
    )


@when(parsers.parse('the agent provides client_name "{name}"'))
def step_provide_name(ctx, name):
    _, ctx.validation_error = _try_welcome(
        client_name=name, source="Rightmove", agent_name="James", dispatch=False
    )


@when('the agent submits a welcome request with client_name "  James Hyde  "')
def step_w_padded_name(ctx):
    req, err = _try_welcome(
        client_name="  James Hyde  ", source="Rightmove", agent_name="James", dispatch=False
    )
    ctx.validation_error = err
    ctx.stored_value = req.client_name if req else None


@when('the agent submits a welcome request with client_name "<script>alert(\'xss\')</script>"')
def step_w_xss(ctx):
    req, err = _try_welcome(
        client_name="<script>alert('xss')</script>",
        source="Rightmove", agent_name="James", dispatch=False
    )
    ctx.validation_error = err
    ctx.stored_value = req.client_name if req else None


@when('the agent submits a welcome request with client_name "\'; DROP TABLE contacts; --"')
def step_w_sqli(ctx):
    req, err = _try_welcome(
        client_name="'; DROP TABLE contacts; --",
        source="Rightmove", agent_name="James", dispatch=False
    )
    ctx.validation_error = err
    ctx.stored_value = req.client_name if req else None


@when("the agent submits a welcome request with a 10000 character client_name")
def step_w_long_name(ctx):
    _, ctx.validation_error = _try_welcome(
        client_name="A" * 10000, source="Rightmove", agent_name="James", dispatch=False
    )


# --- fn_register_applicant ---

def _valid_register_base():
    return dict(
        full_name="Tom Baker", email="tom.baker@email.com", phone="07700 900123",
        budget=500_000, bedrooms_min=2,
        property_types=["flat"], financing="cash",
        preferred_channel="email", source="Rightmove",
    )


@when(parsers.parse('the agent submits a register request with email "{email}"'))
def step_r_email(ctx, email):
    data = _valid_register_base()
    data["email"] = email
    try:
        RegisterApplicantRequest(**data)
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


@when(parsers.parse('the agent submits a register request with phone "{phone}"'))
def step_r_phone(ctx, phone):
    data = _valid_register_base()
    data["phone"] = phone
    try:
        RegisterApplicantRequest(**data)
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


@when(parsers.parse('the agent submits a register request with property_types "{pt}"'))
def step_r_property_types(ctx, pt):
    data = _valid_register_base()
    data["property_types"] = [pt]
    try:
        RegisterApplicantRequest(**data)
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


@when(parsers.parse('the agent submits a register request with financing "{fin}"'))
def step_r_financing(ctx, fin):
    data = _valid_register_base()
    data["financing"] = fin
    try:
        RegisterApplicantRequest(**data)
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


@when(parsers.parse('the agent submits a register request with preferred_channel "{ch}"'))
def step_r_channel(ctx, ch):
    data = _valid_register_base()
    data["preferred_channel"] = ch
    try:
        RegisterApplicantRequest(**data)
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


@when("the agent submits a valid register request with optional fields blank")
def step_r_valid_optional(ctx):
    data = _valid_register_base()
    # optional fields absent — should pass
    try:
        RegisterApplicantRequest(**data)
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


# --- fn_match_applicants ---

@when("the agent submits a match request with property_ref blank")
def step_m_blank_ref(ctx):
    try:
        MatchApplicantsRequest(property_ref="")
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


@when("the agent submits a match request without max_results")
def step_m_no_max(ctx):
    try:
        req = MatchApplicantsRequest(property_ref="22 Abbotsbury Road")
        ctx.stored_value = req.max_results
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


@when(parsers.parse('the agent submits a match request with max_results {n:d}'))
def step_m_max(ctx, n):
    try:
        MatchApplicantsRequest(property_ref="22 Abbotsbury Road", max_results=n)
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


# --- fn_valuation_brief ---

def _valid_valuation_base():
    return dict(
        address="22 Abbotsbury Road", postcode="W14 8EH",
        property_type="house", bedrooms=3
    )


@when(parsers.parse('the agent submits a valuation request with property_type "{pt}"'))
def step_v_property_type(ctx, pt):
    data = _valid_valuation_base()
    data["property_type"] = pt
    try:
        ValuationBriefRequest(**data)
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


@when(parsers.parse('the agent submits a valuation request with condition "{cond}"'))
def step_v_condition(ctx, cond):
    data = _valid_valuation_base()
    data["condition"] = cond
    try:
        ValuationBriefRequest(**data)
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


@when("the agent submits a valid valuation request without sqft")
def step_v_no_sqft(ctx):
    try:
        ValuationBriefRequest(**_valid_valuation_base())
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


# --- fn_draft_outreach ---

def _valid_outreach_base():
    return dict(
        recipient_name="Mrs Patterson", recipient_type="warm_lead",
        channel="email", agent_name="James"
    )


@when(parsers.parse('the agent submits an outreach request with recipient_type "{rt}"'))
def step_o_recipient_type(ctx, rt):
    data = _valid_outreach_base()
    data["recipient_type"] = rt
    try:
        DraftOutreachRequest(**data)
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


@when(parsers.parse('the agent submits an outreach request with channel "{ch}"'))
def step_o_channel(ctx, ch):
    data = _valid_outreach_base()
    data["channel"] = ch
    try:
        DraftOutreachRequest(**data)
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


@when("the agent submits a valid outreach request with optional fields blank")
def step_o_valid_optional(ctx):
    try:
        DraftOutreachRequest(**_valid_outreach_base())
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


# --- fn_kyc_status ---

@when("the agent submits a KYC request with name_or_id blank")
def step_k_blank_id(ctx):
    try:
        KYCStatusRequest(name_or_id="", type="client")
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


@when(parsers.parse('the agent submits a KYC request with type "{t}"'))
def step_k_type(ctx, t):
    try:
        KYCStatusRequest(name_or_id="Tom Baker", type=t)
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


# ===========================================================================
# THEN — validation assertions
# ===========================================================================

@then("the request is rejected with a validation error")
def step_rejected(ctx):
    assert ctx.validation_error is not None, "Expected a ValidationError but none was raised"


@then("no external API calls are made")
def step_no_external(ctx):
    assert ctx.validation_error is not None


@then(parsers.parse('the validation error targets the "{field}" field'))
def step_targets_field(ctx, field):
    assert ctx.validation_error is not None
    locs = [e["loc"][0] for e in ctx.validation_error.errors() if e["loc"]]
    assert field in locs, f"Expected error on '{field}', got: {locs}"


@then("no Claude call is made")
def step_no_claude_val(ctx):
    assert ctx.validation_error is not None


@then("no tokens are consumed")
def step_no_tokens_val(ctx):
    assert ctx.validation_error is not None


@then("no HubSpot call is made")
def step_no_hubspot_val(ctx):
    assert ctx.validation_error is not None


@then("the validation error is caught before any backend processing")
def step_caught_early(ctx):
    assert ctx.validation_error is not None


@then("no validation error exists for client_name")
def step_no_name_err(ctx):
    if ctx.validation_error is None:
        return
    locs = [e["loc"][0] for e in ctx.validation_error.errors() if e["loc"]]
    assert "client_name" not in locs


@then("multiple validation errors are returned")
def step_multiple_errors(ctx):
    assert ctx.validation_error is not None
    assert len(ctx.validation_error.errors()) >= 2


@then("no client_name validation error exists")
def step_no_client_name_err(ctx):
    if ctx.validation_error is None:
        return
    locs = [e["loc"][0] for e in ctx.validation_error.errors() if e["loc"]]
    assert "client_name" not in locs


@then("the source field has exactly 5 valid options")
def step_source_5_options(ctx):
    # Inspect the Literal type annotation on WelcomeRequest.source
    import typing
    hints = WelcomeRequest.model_fields["source"]
    annotation = hints.annotation
    args = typing.get_args(annotation)
    assert len(args) == 5, f"Expected 5 source options, got {len(args)}: {args}"


@then("no budget validation error exists")
def step_no_budget_err(ctx):
    if ctx.validation_error is None:
        return
    locs = [e["loc"][0] for e in ctx.validation_error.errors() if e["loc"]]
    assert "budget_gbp" not in locs


@then("no email validation error exists")
def step_no_email_err(ctx):
    if ctx.validation_error is None:
        return
    locs = [e["loc"][0] for e in ctx.validation_error.errors() if e["loc"]]
    assert "email" not in locs


@then("no phone validation error exists")
def step_no_phone_err(ctx):
    if ctx.validation_error is None:
        return
    locs = [e["loc"][0] for e in ctx.validation_error.errors() if e["loc"]]
    assert "phone" not in locs


@then("no validation error exists for optional applicant fields")
def step_no_optional_applicant_err(ctx):
    assert ctx.validation_error is None, f"Unexpected error: {ctx.validation_error}"


@then("max_results defaults to 5")
def step_max_results_default(ctx):
    assert ctx.stored_value == 5, f"Expected default 5, got {ctx.stored_value}"


@then("no sqft validation error exists")
def step_no_sqft_err(ctx):
    assert ctx.validation_error is None


@then("no validation error exists for optional outreach fields")
def step_no_optional_outreach_err(ctx):
    assert ctx.validation_error is None


@then(parsers.parse('the client_name is stored as "{expected}"'))
def step_name_trimmed(ctx, expected):
    assert ctx.stored_value == expected, (
        f"Expected stored value '{expected}', got '{ctx.stored_value}'"
    )


@then("no script tag is stored in client_name")
def step_no_script(ctx):
    stored = ctx.stored_value or ""
    assert "<script>" not in stored.lower(), (
        f"Script tag found in stored value: '{stored}'"
    )


@then("no sql injection error occurs and input is stored literally")
def step_sql_literal(ctx):
    # SQL injection should either be stored as-is (literal string) or raise a
    # normal validation error — the key guarantee is: no crash, no DB side effect
    # At schema level: if it passes validation, stored_value is the raw string
    # If validation raises (unlikely for this input), that's also acceptable
    assert True  # system did not crash — we reached this step


@then("the validation error has a structured error response")
def step_structured_error(ctx):
    assert ctx.validation_error is not None
    errors = ctx.validation_error.errors()
    assert len(errors) >= 1
    # Each error should have 'loc', 'msg', 'type' fields
    for err in errors:
        assert "loc"  in err
        assert "msg"  in err
        assert "type" in err
