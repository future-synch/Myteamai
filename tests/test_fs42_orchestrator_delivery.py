"""
FS-42 through the FS-55 orchestrator: step (e) hands the composed email to the
transport with the applicant as recipient, off the event loop, and a delivery
failure never costs the registration or the composed text.

The real FS-70 matcher and the real FS-57 composer stay in the loop; only the
HubSpot reads/writes and the Google service are faked.
"""
from __future__ import annotations

import base64
import email
import email.policy
import threading
from typing import Any, Dict, List

import pytest

import app.services.hubspot_service as hs
from app.functions import bot_functions as bf
from app.models.schemas import RegisterApplicantRequest
from app.services import transports
from app.services.brochures import FakeBrochureLinkSource
from app.services.hubspot_registration import RegistrationResult
from app.services.transports.gmail import GmailDraftTransport, GmailSettings
from tests.support.gmail_stub import MAILBOX, GmailApiError, StubGmail

LINK = "https://cdn.example-hubfs.test/1393968357613-brochure.pdf"
APPLICANT = "test.applicant@example.com"


def _request(dispatch: bool) -> RegisterApplicantRequest:
    return RegisterApplicantRequest(
        full_name="Test Applicant",
        email=APPLICANT,
        phone="+447700900000",
        budget_gbp=2_000_000,
        bedrooms_min=2,
        property_types=["house"],
        financing="cash",
        preferred_channel="email",
        source="direct",
        dispatch=dispatch,
    )


def _listing(listing_id: str, price: int) -> Dict[str, Any]:
    return {
        "id": listing_id, "address": f"{listing_id} Test Street", "price_gbp": price,
        "bedrooms": 3, "listing_type": "house", "outside_space": "", "parking": "false",
        "works_required": "", "area": "", "listing_status": "available_for_sale",
    }


@pytest.fixture(autouse=True)
def _hubspot_faked(monkeypatch: pytest.MonkeyPatch) -> None:
    listings = [_listing("1393968357613", 1_100_000), _listing("1393968357614", 1_200_000)]

    async def _fake_listings(*a: Any, **k: Any) -> List[Dict[str, Any]]:
        return [dict(l) for l in listings]

    async def _fake_register(criteria: dict, client: Any) -> RegistrationResult:
        return RegistrationResult(contact_id="contact-FS42", created=True)

    monkeypatch.setattr(hs, "get_all_listings", _fake_listings)
    monkeypatch.setattr(bf, "register_applicant_in_hubspot", _fake_register)
    monkeypatch.setattr(bf, "build_hubspot_client", lambda: object())


@pytest.fixture
def gmail(monkeypatch: pytest.MonkeyPatch) -> StubGmail:
    """The real GmailDraftTransport, wired in as the process transport, talking to a stub."""
    stub = StubGmail()
    settings = GmailSettings(mode="futuresynch_dev", mailbox=MAILBOX, client_id="i",
                             client_secret="s", refresh_token="r")
    monkeypatch.setattr(transports, "_TRANSPORT", GmailDraftTransport(settings=settings, service=stub))
    return stub


def _draft_message(stub: StubGmail):
    raw = stub.created[-1]["message"]["raw"]
    return email.message_from_bytes(base64.urlsafe_b64decode(raw), policy=email.policy.default)


async def test_dispatch_true_puts_the_brochure_email_in_the_gmail_drafts(gmail):
    source = FakeBrochureLinkSource({"1393968357613": LINK})

    response = await bf.fn_register_applicant(_request(True), agent_name="Agent", source=source)

    assert response.errors == []
    assert response.draft_ref is not None
    assert response.draft_ref.transport == "gmail" and response.draft_ref.mailbox == MAILBOX
    assert response.draft_ref.draft_id == "gmail-draft-1"

    msg = _draft_message(gmail)
    assert msg["To"] == APPLICANT
    assert LINK in msg.get_body(("html",)).get_content()
    assert "View brochure: " + LINK in msg.get_body(("plain",)).get_content()
    assert gmail.send_attempts == 0


async def test_dispatch_false_creates_no_draft_and_still_returns_the_preview(gmail):
    response = await bf.fn_register_applicant(_request(False), agent_name="Agent",
                                              source=FakeBrochureLinkSource())

    assert gmail.create_calls == 0 and gmail.profile_calls == 0
    assert response.draft_ref is None
    assert response.welcome_draft is not None and response.welcome_draft.text_body


async def test_the_draft_is_created_off_the_event_loop(monkeypatch):
    seen: Dict[str, str] = {}

    def spy(message):
        seen["thread"] = threading.current_thread().name
        return {"transport": "fake", "draft_id": "d", "mailbox": "m"}

    monkeypatch.setattr(bf, "create_draft", spy)

    await bf.fn_register_applicant(_request(True), agent_name="Agent", source=FakeBrochureLinkSource())

    assert seen["thread"] != threading.main_thread().name, (
        "create_draft does blocking network I/O; it must not run on the event loop thread"
    )


async def test_a_revoked_sign_in_keeps_the_registration_and_the_composed_email(gmail):
    gmail.create_failures = [RuntimeError("invalid_grant: Token has been expired or revoked.")]

    response = await bf.fn_register_applicant(_request(True), agent_name="Agent",
                                              source=FakeBrochureLinkSource({"1393968357613": LINK}))

    assert response.status == "ok" and response.applicant_id == "contact-FS42"
    assert response.draft_ref is None
    assert any(e.startswith("DRAFT_FAILED") and "reconnect" in e.lower() for e in response.errors)
    assert LINK in response.welcome_draft.html_body and LINK in response.welcome_draft.text_body


async def test_the_failure_text_returned_to_the_agent_contains_no_credentials(gmail):
    gmail.create_failures = [RuntimeError("invalid_grant for refresh token r and secret s")]

    response = await bf.fn_register_applicant(_request(True), agent_name="Agent",
                                              source=FakeBrochureLinkSource())

    joined = " ".join(response.errors)
    assert "refresh token" not in joined and "secret" not in joined


async def test_a_gmail_outage_is_reported_and_later_registrations_can_still_draft(gmail):
    gmail.create_failures = [GmailApiError(503)]

    first = await bf.fn_register_applicant(_request(True), agent_name="Agent",
                                           source=FakeBrochureLinkSource())
    second = await bf.fn_register_applicant(_request(True), agent_name="Agent",
                                            source=FakeBrochureLinkSource())

    assert first.draft_ref is None and any("DRAFT_FAILED" in e and "503" in e for e in first.errors)
    assert second.draft_ref is not None and second.errors == []


async def test_a_misconfigured_gmail_transport_is_a_draft_failure_not_a_crash(monkeypatch):
    monkeypatch.setattr(transports, "_TRANSPORT", None)
    monkeypatch.setenv("DRAFT_TRANSPORT", "gmail")
    monkeypatch.delenv("GMAIL_CREDENTIAL_MODE", raising=False)

    response = await bf.fn_register_applicant(_request(True), agent_name="Agent",
                                              source=FakeBrochureLinkSource())

    assert response.status == "ok" and response.applicant_id == "contact-FS42"
    assert any("DRAFT_FAILED" in e and "GMAIL_CREDENTIAL_MODE" in e for e in response.errors)
