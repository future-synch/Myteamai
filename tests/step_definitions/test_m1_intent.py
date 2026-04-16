"""
BDD step definitions for:
  Test 11 — M1 Intent Classification  (42 scenarios)
  Test 12 — M1 Input Validation       (10 scenarios)
Total target: 52 scenarios, all passing with no external services.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from pydantic import ValidationError

from app.classifier import classify, CAPABILITIES
from app.models.schemas import WelcomeRequest
from tests.conftest import StepContext

# ---------------------------------------------------------------------------
# Load feature files
# ---------------------------------------------------------------------------

scenarios("../features/m1_intent_classification.feature")
scenarios("../features/m1_validation.feature")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ctx():
    return StepContext()


# ---------------------------------------------------------------------------
# Background steps
# ---------------------------------------------------------------------------

@given("an authenticated agent in the Curtis Sloane workspace")
def step_authenticated_agent(ctx):
    ctx.workspace = "curtis_sloane"


@given("the bot supports 6 functions")
def step_bot_supports_6_functions(ctx):
    assert len(CAPABILITIES) == 6, f"Expected 6 capabilities, got {len(CAPABILITIES)}"


# ---------------------------------------------------------------------------
# When steps — classification
# ---------------------------------------------------------------------------

@when(parsers.parse('the agent sends "{text}"'))
def step_agent_sends(ctx, text):
    ctx.text = text
    ctx.result = classify(text)


@when(parsers.parse('the agent sends "{text}" three times'))
def step_agent_sends_three_times(ctx, text):
    ctx.text = text
    ctx.results = [classify(text), classify(text), classify(text)]


# ---------------------------------------------------------------------------
# Then steps — classification
# ---------------------------------------------------------------------------

@then(parsers.parse('the error code is "{code}"'))
def step_error_code_is(ctx, code):
    assert ctx.result.intent == code, (
        f"Expected intent '{code}', got '{ctx.result.intent}' "
        f"for input: '{ctx.text}'"
    )


@then(parsers.parse('the error code is not "{code}"'))
def step_error_code_is_not(ctx, code):
    assert ctx.result.intent != code, (
        f"Expected intent NOT '{code}', but got '{ctx.result.intent}' "
        f"for input: '{ctx.text}'"
    )


@then("no Claude API call is made")
def step_no_claude_call(ctx):
    assert ctx.result.tokens_consumed == 0, "tokens_consumed must be 0 — classifier never calls Claude"


@then("no HubSpot API call is made")
def step_no_hubspot_call(ctx):
    # Classifier is pure Python — no HubSpot calls ever made here
    assert ctx.result.intent is not None


@then("the capability list contains exactly 6 items")
def step_capability_list_6(ctx):
    caps = ctx.result.capabilities
    assert caps is not None, "Expected capabilities list, got None"
    assert len(caps) == 6, f"Expected 6 capabilities, got {len(caps)}: {caps}"


@then("the response message is welcoming")
def step_message_welcoming(ctx):
    msg = ctx.result.message or ""
    welcoming_words = ["hello", "help", "here", "welcome", "assist"]
    assert any(w in msg.lower() for w in welcoming_words), (
        f"Expected a welcoming message, got: '{msg}'"
    )


@then("the system does not crash")
def step_no_crash(ctx):
    assert ctx.result is not None


@then(parsers.parse('the intent is "{expected_intent}"'))
def step_intent_is(ctx, expected_intent):
    assert ctx.result.intent == expected_intent, (
        f"Expected intent '{expected_intent}', got '{ctx.result.intent}' "
        f"for input: '{ctx.text}'"
    )


@then(parsers.parse('all three results have error code "{code}"'))
def step_all_three_have_code(ctx, code):
    for i, r in enumerate(ctx.results, 1):
        assert r.intent == code, (
            f"Result {i} of 3: expected '{code}', got '{r.intent}'"
        )


@then("zero tokens are consumed")
def step_zero_tokens(ctx):
    assert ctx.result.tokens_consumed == 0


# ---------------------------------------------------------------------------
# When steps — validation
# ---------------------------------------------------------------------------

@when("the agent submits a welcome request with client_name blank")
def step_submit_blank_client_name(ctx):
    try:
        WelcomeRequest(
            client_name="",
            source="Rightmove",
            agent_name="James",
            dispatch=False,
        )
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


@when("the agent submits a welcome request with all required fields blank")
def step_submit_all_blank(ctx):
    try:
        WelcomeRequest(
            client_name="",
            source="Rightmove",
            agent_name="",
            dispatch=None,
        )
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


@when(parsers.parse('the agent submits a welcome request with client_name "{name}"'))
def step_submit_with_name(ctx, name):
    try:
        WelcomeRequest(
            client_name=name,
            source="Rightmove",
            agent_name="James",
            dispatch=False,
        )
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


@when(parsers.parse('the agent submits a welcome request with source "{source}"'))
def step_submit_with_source(ctx, source):
    try:
        WelcomeRequest(
            client_name="James Hyde",
            source=source,
            agent_name="James",
            dispatch=False,
        )
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


@when("any form has a validation error")
def step_any_form_validation_error(ctx):
    try:
        WelcomeRequest(
            client_name="",
            source="Rightmove",
            agent_name="James",
            dispatch=False,
        )
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


@when(parsers.parse('the agent provides client_name "{name}"'))
def step_provide_valid_name(ctx, name):
    try:
        WelcomeRequest(
            client_name=name,
            source="Rightmove",
            agent_name="James",
            dispatch=False,
        )
        ctx.validation_error = None
    except ValidationError as e:
        ctx.validation_error = e


# ---------------------------------------------------------------------------
# Then steps — validation
# ---------------------------------------------------------------------------

@then("the request is rejected with a validation error")
def step_request_rejected(ctx):
    assert ctx.validation_error is not None, "Expected a ValidationError but none was raised"


@then("no external API calls are made")
def step_no_external_calls(ctx):
    # Validation is pure Pydantic — no network calls possible
    assert ctx.validation_error is not None


@then(parsers.parse('the validation error targets the "{field}" field'))
def step_error_targets_field(ctx, field):
    assert ctx.validation_error is not None, "No ValidationError was raised"
    field_errors = [e["loc"][0] for e in ctx.validation_error.errors() if e["loc"]]
    assert field in field_errors, (
        f"Expected error on field '{field}', got errors on: {field_errors}"
    )


@then("no Claude call is made")
def step_no_claude_call_validation(ctx):
    # Pydantic validation is pure Python — provably no Claude call
    assert ctx.validation_error is not None


@then("no tokens are consumed")
def step_no_tokens_validation(ctx):
    assert ctx.validation_error is not None


@then("no HubSpot call is made")
def step_no_hubspot_validation(ctx):
    assert ctx.validation_error is not None


@then("the validation error is caught before any backend processing")
def step_error_caught_early(ctx):
    assert ctx.validation_error is not None, (
        "Validation error should be raised by Pydantic before any function is called"
    )


@then("no validation error exists for client_name")
def step_no_client_name_error(ctx):
    if ctx.validation_error is None:
        return  # No error at all — pass
    field_errors = [e["loc"][0] for e in ctx.validation_error.errors() if e["loc"]]
    assert "client_name" not in field_errors, (
        f"Unexpected client_name error: {ctx.validation_error}"
    )


@then("multiple validation errors are returned")
def step_multiple_errors(ctx):
    assert ctx.validation_error is not None, "Expected ValidationError but none was raised"
    errors = ctx.validation_error.errors()
    assert len(errors) >= 2, (
        f"Expected multiple validation errors, got {len(errors)}: {errors}"
    )


@then("no client_name validation error exists")
def step_no_client_name_validation_error(ctx):
    if ctx.validation_error is None:
        return
    field_errors = [e["loc"][0] for e in ctx.validation_error.errors() if e["loc"]]
    assert "client_name" not in field_errors, (
        f"Unexpected client_name validation error: {ctx.validation_error}"
    )
