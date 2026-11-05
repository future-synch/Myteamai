"""
FS-55 orchestration — failure isolation between the five steps.

Binds tests/features/fs55_failure_isolation.feature: one scenario per row of
the ticket's failure table (validation, registration, matching, composition,
Gmail draft) plus the dispatch gate. The delegates are replaced by spies, so
the suite is offline and tests only the orchestration, not the delegates.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from app.functions import bot_functions as bf
from app.models.schemas import RegisterApplicantRequest
from app.services.brochures import FakeBrochureLinkSource
from app.services.hubspot_registration import RegistrationError, RegistrationResult

scenarios("../features/fs55_failure_isolation.feature")


def _request(dispatch: bool) -> RegisterApplicantRequest:
    return RegisterApplicantRequest(
        full_name="Test Applicant",
        email="test.applicant@example.com",
        phone="+447700900000",
        budget_gbp=2_000_000,
        bedrooms_min=2,
        property_types=["house"],
        financing="cash",
        preferred_channel="email",
        source="direct",
        dispatch=dispatch,
    )


class _Spies:
    """Records every delegate call and holds the failure switches."""

    def __init__(self) -> None:
        self.registration_mode = "ok"      # ok | invalid | fails
        self.matches: List[dict] = []
        self.matching_raises = False
        self.composition_raises = False
        self.draft_raises = False
        self.register_calls = 0
        self.match_calls = 0
        self.compose_calls = 0
        self.draft_calls = 0
        self.source = FakeBrochureLinkSource()
        self.response: Optional[Any] = None


@pytest.fixture
def ctx(monkeypatch: pytest.MonkeyPatch) -> _Spies:
    s = _Spies()

    async def _register(criteria: dict, client: Any) -> RegistrationResult:
        s.register_calls += 1
        if s.registration_mode == "invalid":
            raise RegistrationError(
                "payload rejected", fields=["email"], code="VALIDATION_ERROR", payload=criteria
            )
        if s.registration_mode == "fails":
            raise RuntimeError("HubSpot is unreachable")
        return RegistrationResult(contact_id="contact-FS55-FAIL", created=True)

    async def _match(criteria: dict, limit: int = 3) -> List[dict]:
        s.match_calls += 1
        if s.matching_raises:
            raise RuntimeError("listings fetch failed")
        return [dict(m) for m in s.matches]

    def _compose(req: Any, matches: List[dict], agent_name: Optional[str] = None) -> Dict[str, str]:
        s.compose_calls += 1
        if s.composition_raises:
            raise RuntimeError("composition failed")
        return {"subject": "Welcome", "html_body": "<p>ok</p>", "text_body": "ok"}

    def _create_draft(message: Dict[str, str]) -> Dict[str, str]:
        s.draft_calls += 1
        if s.draft_raises:
            raise RuntimeError("Gmail is unreachable")
        return {"transport": "fake", "draft_id": "draft_test", "mailbox": "agent@example.com"}

    monkeypatch.setattr(bf, "register_applicant_in_hubspot", _register)
    monkeypatch.setattr(bf, "find_matching_listings", _match)
    monkeypatch.setattr(bf, "_compose_welcome_draft", _compose)
    monkeypatch.setattr(bf, "create_draft", _create_draft)
    monkeypatch.setattr(bf, "build_hubspot_client", lambda: object())
    return s


# --- Given -----------------------------------------------------------------


@given("the five delegates are replaced by recording spies")
def given_spies(ctx: _Spies) -> None:
    pass  # the ctx fixture installs them


@given("registration rejects the payload as invalid")
def given_invalid(ctx: _Spies) -> None:
    ctx.registration_mode = "invalid"


@given("registration fails with an unexpected error")
def given_registration_fails(ctx: _Spies) -> None:
    ctx.registration_mode = "fails"


@given(parsers.parse("matching returns {n:d} listings"))
def given_matches(ctx: _Spies, n: int) -> None:
    ctx.matches = [
        {"property_id": f"listing-{i + 1}", "address": f"{i + 1} Example Rd", "price_gbp": 2_000_000}
        for i in range(n)
    ]


@given("matching raises an error")
def given_matching_raises(ctx: _Spies) -> None:
    ctx.matches = [{"property_id": "listing-1", "address": "1 Example Rd"}]
    ctx.matching_raises = True


@given("composition raises an error")
def given_composition_raises(ctx: _Spies) -> None:
    ctx.composition_raises = True


@given("draft creation raises an error")
def given_draft_raises(ctx: _Spies) -> None:
    ctx.draft_raises = True


# --- When ------------------------------------------------------------------


@when(parsers.parse("fn_register_applicant runs with dispatch {flag}"))
def when_run(ctx: _Spies, flag: str) -> None:
    ctx.response = asyncio.run(
        bf.fn_register_applicant(_request(flag == "true"), agent_name="Agent", source=ctx.source)
    )


# --- Then ------------------------------------------------------------------


@then(parsers.parse("the response status is {status}"))
def then_status(ctx: _Spies, status: str) -> None:
    assert ctx.response.status == status, ctx.response


@then(parsers.parse("the error code is {code}"))
def then_error_code(ctx: _Spies, code: str) -> None:
    assert ctx.response.errors == [code], ctx.response.errors


@then(parsers.parse("the first error starts with {prefix}"))
def then_first_error(ctx: _Spies, prefix: str) -> None:
    assert ctx.response.errors, "expected an error to be reported"
    assert ctx.response.errors[0].startswith(prefix), ctx.response.errors


@then("the applicant id is returned")
def then_applicant_id(ctx: _Spies) -> None:
    assert ctx.response.applicant_id == "contact-FS55-FAIL", ctx.response


@then("no applicant id is returned")
def then_no_applicant_id(ctx: _Spies) -> None:
    assert ctx.response.applicant_id is None, ctx.response


@then("the matches are returned")
def then_matches(ctx: _Spies) -> None:
    assert [m["property_id"] for m in ctx.response.first_matches] == [
        "listing-1", "listing-2", "listing-3"
    ], ctx.response.first_matches


@then("no matches are returned")
def then_no_matches(ctx: _Spies) -> None:
    assert ctx.response.first_matches == [], ctx.response.first_matches


@then("the welcome draft is returned")
def then_welcome(ctx: _Spies) -> None:
    assert ctx.response.welcome_draft is not None
    assert ctx.response.welcome_draft.subject == "Welcome"


@then("no welcome draft is returned")
def then_no_welcome(ctx: _Spies) -> None:
    assert ctx.response.welcome_draft is None


@then("a draft reference is returned")
def then_draft_ref(ctx: _Spies) -> None:
    assert ctx.response.draft_ref is not None
    assert ctx.response.draft_ref.draft_id == "draft_test"


@then("no draft reference is returned")
def then_no_draft_ref(ctx: _Spies) -> None:
    assert ctx.response.draft_ref is None


@then("matching was not called")
def then_no_matching(ctx: _Spies) -> None:
    assert ctx.match_calls == 0


@then("the brochure source was not asked")
def then_source_not_asked(ctx: _Spies) -> None:
    assert ctx.source.requested == [], ctx.source.requested


@then("composition was not called")
def then_no_composition(ctx: _Spies) -> None:
    assert ctx.compose_calls == 0


@then("draft creation was not called")
def then_no_draft_call(ctx: _Spies) -> None:
    assert ctx.draft_calls == 0


@then("draft creation was called once")
def then_draft_once(ctx: _Spies) -> None:
    assert ctx.draft_calls == 1
