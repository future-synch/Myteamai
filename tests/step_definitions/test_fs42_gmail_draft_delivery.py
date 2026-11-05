"""
FS-42 Gmail draft delivery — step definitions for fs42_gmail_draft_delivery.feature.

A stub Google service stands in for the Gmail API, so nothing here touches a
network or a mailbox. The stub records every call and raises on any attempt to
send, so "the platform never sends" is checked, not assumed.
"""
from __future__ import annotations

import base64
import email
import email.policy
from typing import Any, Dict, List, Optional

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from app.services.transports.base import DraftDeliveryError
from app.services.transports.gmail import GmailDraftTransport, GmailSettings
from tests.support.gmail_stub import MAILBOX, GmailApiError, StubGmail

scenarios("../features/fs42_gmail_draft_delivery.feature")

class Ctx:
    stub: StubGmail
    transport: GmailDraftTransport
    ref: Optional[Dict[str, str]] = None
    error: Optional[DraftDeliveryError] = None


@pytest.fixture
def ctx() -> Ctx:
    return Ctx()


def _make_transport(c: Ctx) -> None:
    settings = GmailSettings(
        mode="futuresynch_dev",
        mailbox=MAILBOX,
        client_id="stub-client-id",
        client_secret="stub-client-secret",
        refresh_token="stub-refresh-token",
    )
    c.transport = GmailDraftTransport(settings=settings, service=c.stub)


def _message(to: str, subject: str) -> Dict[str, str]:
    return {
        "to": to,
        "subject": subject,
        "text_body": "Plain text body.",
        "html_body": "<p>HTML <strong>body</strong>.</p>",
    }


def _parsed_draft(c: Ctx):
    assert c.stub.created, "no draft was created"
    raw = c.stub.created[-1]["message"]["raw"]
    return email.message_from_bytes(base64.urlsafe_b64decode(raw), policy=email.policy.default)


# --- Given -----------------------------------------------------------------


@given("a Gmail transport for the futuresynch_dev mailbox backed by a stub Google service")
def given_transport(ctx: Ctx) -> None:
    ctx.stub = StubGmail()
    _make_transport(ctx)


@given("the Google account behind the credentials is a different mailbox")
def given_other_mailbox(ctx: Ctx) -> None:
    ctx.stub.account = "someone.else@client.example.test"


@given(parsers.parse('Gmail rejects the sign-in with "{text}"'))
def given_signin_rejected(ctx: Ctx, text: str) -> None:
    ctx.stub.create_failures = [RuntimeError(text)] * 5


@given(parsers.parse("Gmail fails once with HTTP status {status:d}"))
def given_fails_once(ctx: Ctx, status: int) -> None:
    ctx.stub.create_failures = [GmailApiError(status)]


# --- When ------------------------------------------------------------------


@when(parsers.parse('the transport creates a draft for "{to}" with subject "{subject}"'))
def when_creates(ctx: Ctx, to: str, subject: str) -> None:
    ctx.ref = ctx.transport.create_draft(_message(to, subject))


@when(parsers.parse('the transport creates two drafts for "{to}"'))
def when_creates_two(ctx: Ctx, to: str) -> None:
    ctx.ref = ctx.transport.create_draft(_message(to, "First"))
    ctx.ref = ctx.transport.create_draft(_message(to, "Second"))


def _try(ctx: Ctx, to: str, subject: str) -> None:
    ctx.stub.snapshot = (ctx.stub.profile_calls, ctx.stub.create_calls)
    try:
        ctx.ref = ctx.transport.create_draft(_message(to, subject))
    except DraftDeliveryError as exc:
        ctx.error = exc


@when(parsers.parse('the transport tries to create a draft for "{to}" with subject "{subject}"'))
def when_tries(ctx: Ctx, to: str, subject: str) -> None:
    _try(ctx, to.replace("\\n", "\n"), subject)  # Gherkin cannot hold a raw line break


@when("the transport tries to create a draft with no recipient")
def when_tries_blank(ctx: Ctx) -> None:
    _try(ctx, "", "Welcome")


# --- Then ------------------------------------------------------------------


@then("exactly one draft is created")
def then_one(ctx: Ctx) -> None:
    assert len(ctx.stub.created) == 1


@then(parsers.parse("exactly {n:d} drafts are created"))
def then_n(ctx: Ctx, n: int) -> None:
    assert len(ctx.stub.created) == n


@then("the draft has a plain-text part and an HTML part")
def then_parts(ctx: Ctx) -> None:
    msg = _parsed_draft(ctx)
    assert msg.get_content_type() == "multipart/alternative"
    assert "Plain text body." in msg.get_body(("plain",)).get_content()
    assert "<strong>body</strong>" in msg.get_body(("html",)).get_content()


@then(parsers.parse('the draft is addressed to "{to}"'))
def then_to(ctx: Ctx, to: str) -> None:
    assert _parsed_draft(ctx)["To"] == to


@then(parsers.parse('the draft subject is "{subject}"'))
def then_subject(ctx: Ctx, subject: str) -> None:
    assert _parsed_draft(ctx)["Subject"] == subject


@then("the draft has no From header")
def then_no_from(ctx: Ctx) -> None:
    assert _parsed_draft(ctx)["From"] is None


@then("the draft has no Bcc header")
def then_no_bcc(ctx: Ctx) -> None:
    assert _parsed_draft(ctx)["Bcc"] is None


@then("no send was attempted")
def then_no_send(ctx: Ctx) -> None:
    assert ctx.stub.send_attempts == 0


@then(parsers.parse('the draft reference has transport "{name}"'))
def then_ref_transport(ctx: Ctx, name: str) -> None:
    assert ctx.ref["transport"] == name


@then("the draft reference has the draft id Gmail returned")
def then_ref_id(ctx: Ctx) -> None:
    assert ctx.ref["draft_id"] == "gmail-draft-1"


@then("the draft reference has the configured mailbox")
def then_ref_mailbox(ctx: Ctx) -> None:
    assert ctx.ref["mailbox"] == MAILBOX


@then("the mailbox was checked exactly once")
def then_checked_once(ctx: Ctx) -> None:
    assert ctx.stub.profile_calls == 1


@then("the draft is refused with a message that mentions the mailbox guard")
def then_refused_guard(ctx: Ctx) -> None:
    assert ctx.error is not None and "mailbox guard" in str(ctx.error).lower()
    assert "someone.else@client.example.test" not in str(ctx.error)  # addresses are not echoed


@then(parsers.parse('the draft is refused with a message that mentions "{word}"'))
def then_refused_mentions(ctx: Ctx, word: str) -> None:
    assert ctx.error is not None, "expected the draft to be refused"
    assert word.lower() in str(ctx.error).lower(), str(ctx.error)


@then("the refusal does not say a reconnect is needed")
def then_no_reconnect(ctx: Ctx) -> None:
    assert ctx.error is not None and ctx.error.reconnect_required is False


@then("the draft is refused and a reconnect is required")
def then_reconnect(ctx: Ctx) -> None:
    assert ctx.error is not None and ctx.error.reconnect_required is True
    assert "reconnect" in str(ctx.error).lower()


@then("a second attempt is refused without asking Gmail again")
def then_second_fails_fast(ctx: Ctx) -> None:
    before = (ctx.stub.profile_calls, ctx.stub.create_calls)
    with pytest.raises(DraftDeliveryError):
        ctx.transport.create_draft(_message("applicant@example.com", "Again"))
    assert (ctx.stub.profile_calls, ctx.stub.create_calls) == before


@then(parsers.parse('a later draft for "{to}" is created'))
def then_later_ok(ctx: Ctx, to: str) -> None:
    ctx.error = None
    ref = ctx.transport.create_draft(_message(to, "Later"))
    assert ref["transport"] == "gmail" and len(ctx.stub.created) == 1


@then("Gmail was not contacted")
def then_not_contacted(ctx: Ctx) -> None:
    assert (ctx.stub.profile_calls, ctx.stub.create_calls) == ctx.stub.snapshot
