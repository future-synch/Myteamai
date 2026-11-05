"""
FS-42 configuration and wiring: which transport answers, which credentials it
reads, and what error text is allowed to say. All offline.
"""
from __future__ import annotations

import threading

import pytest

from app.services import transports
from app.services.transports.base import DraftDeliveryError, GmailConfigError
from app.services.transports.fake import FakeDraftTransport
from app.services.transports.gmail import GmailDraftTransport, GmailSettings, load_settings
from tests.support.gmail_stub import MAILBOX, StubGmail

DEV = {
    "GMAIL_CREDENTIAL_MODE": "futuresynch_dev",
    "GMAIL_DEV_CLIENT_ID": "dev-client-id-AAAA",
    "GMAIL_DEV_CLIENT_SECRET": "dev-client-secret-BBBB",
    "GMAIL_DEV_REFRESH_TOKEN": "dev-refresh-token-CCCC",
    "GMAIL_DEV_MAILBOX": MAILBOX,
}
PROD = {
    "GMAIL_PROD_CLIENT_ID": "prod-client-id-ZZZZ",
    "GMAIL_PROD_CLIENT_SECRET": "prod-client-secret-YYYY",
    "GMAIL_PROD_REFRESH_TOKEN": "prod-refresh-token-XXXX",
    "GMAIL_PROD_MAILBOX": "agents@client.example.test",
}


# --- load_settings ----------------------------------------------------------


def test_dev_mode_reads_only_the_dev_prefixed_settings():
    s = load_settings({**DEV, **PROD})
    assert (s.mode, s.mailbox) == ("futuresynch_dev", MAILBOX)
    assert (s.client_id, s.client_secret, s.refresh_token) == (
        "dev-client-id-AAAA", "dev-client-secret-BBBB", "dev-refresh-token-CCCC",
    )


def test_prod_mode_reads_only_the_prod_prefixed_settings():
    s = load_settings({**DEV, **PROD, "GMAIL_CREDENTIAL_MODE": "curtis_sloane_prod"})
    assert s.mailbox == "agents@client.example.test"
    assert s.refresh_token == "prod-refresh-token-XXXX"


def test_production_credentials_are_unreachable_in_dev_mode():
    only_prod = {"GMAIL_CREDENTIAL_MODE": "futuresynch_dev", **PROD}
    with pytest.raises(GmailConfigError) as exc:
        load_settings(only_prod)
    message = str(exc.value)
    assert "GMAIL_DEV_CLIENT_ID" in message
    assert "prod-" not in message and "client.example.test" not in message


def test_unprefixed_credential_names_are_never_read():
    unprefixed = {
        "GMAIL_CREDENTIAL_MODE": "futuresynch_dev",
        "GMAIL_CLIENT_ID": "x", "GMAIL_CLIENT_SECRET": "x",
        "GMAIL_REFRESH_TOKEN": "x", "GMAIL_MAILBOX": "x@example.test",
    }
    with pytest.raises(GmailConfigError, match="GMAIL_DEV_REFRESH_TOKEN"):
        load_settings(unprefixed)


def test_missing_mode_is_named():
    with pytest.raises(GmailConfigError, match="GMAIL_CREDENTIAL_MODE is not set"):
        load_settings({})


def test_unknown_mode_is_rejected_and_lists_the_allowed_ones():
    with pytest.raises(GmailConfigError) as exc:
        load_settings({"GMAIL_CREDENTIAL_MODE": "staging"})
    assert "futuresynch_dev" in str(exc.value) and "curtis_sloane_prod" in str(exc.value)


def test_missing_settings_are_named_without_leaking_the_ones_that_are_set():
    partial = {k: v for k, v in DEV.items() if k != "GMAIL_DEV_REFRESH_TOKEN"}
    with pytest.raises(GmailConfigError) as exc:
        load_settings(partial)
    message = str(exc.value)
    assert "GMAIL_DEV_REFRESH_TOKEN" in message
    for secret in ("dev-client-id-AAAA", "dev-client-secret-BBBB"):
        assert secret not in message


def test_whitespace_only_values_count_as_missing():
    with pytest.raises(GmailConfigError, match="GMAIL_DEV_MAILBOX"):
        load_settings({**DEV, "GMAIL_DEV_MAILBOX": "   "})


def test_settings_repr_does_not_contain_secrets():
    text = repr(load_settings(DEV))
    for secret in ("dev-client-id-AAAA", "dev-client-secret-BBBB", "dev-refresh-token-CCCC"):
        assert secret not in text


# --- factory ----------------------------------------------------------------


def test_default_transport_is_the_fake(monkeypatch):
    monkeypatch.delenv("DRAFT_TRANSPORT", raising=False)
    assert isinstance(transports.get_draft_transport(), FakeDraftTransport)


def test_gmail_transport_is_built_from_the_dev_settings(monkeypatch):
    monkeypatch.setenv("DRAFT_TRANSPORT", "gmail")
    for name, value in DEV.items():
        monkeypatch.setenv(name, value)
    transport = transports.get_draft_transport()
    assert isinstance(transport, GmailDraftTransport)
    assert transport._settings.mailbox == MAILBOX


def test_gmail_transport_with_incomplete_settings_fails_by_name(monkeypatch):
    monkeypatch.setenv("DRAFT_TRANSPORT", "gmail")
    monkeypatch.setenv("GMAIL_CREDENTIAL_MODE", "futuresynch_dev")
    for name in DEV:
        if name != "GMAIL_CREDENTIAL_MODE":
            monkeypatch.delenv(name, raising=False)
    with pytest.raises(GmailConfigError, match="GMAIL_DEV_CLIENT_ID"):
        transports.get_draft_transport()


def test_unknown_transport_name_is_rejected(monkeypatch):
    monkeypatch.setenv("DRAFT_TRANSPORT", "smtp")
    with pytest.raises(ValueError, match="not recognised"):
        transports.get_draft_transport()


def test_one_transport_per_process_until_reset(monkeypatch):
    monkeypatch.setenv("DRAFT_TRANSPORT", "fake")
    first = transports.get_draft_transport()
    assert transports.get_draft_transport() is first
    transports.reset_draft_transport()
    assert transports.get_draft_transport() is not first


def test_the_test_suite_cannot_reach_gmail():
    """conftest forces the fake, so an exported DRAFT_TRANSPORT=gmail is harmless here."""
    assert isinstance(transports.get_draft_transport(), FakeDraftTransport)


def test_fake_transport_returns_a_transport_neutral_reference():
    ref = FakeDraftTransport().create_draft(
        {"to": "a@example.com", "subject": "s", "html_body": "<p>h</p>", "text_body": "t"}
    )
    assert set(ref) == {"transport", "draft_id", "mailbox"} and ref["transport"] == "fake"


# --- concurrency ------------------------------------------------------------


def _settings() -> GmailSettings:
    return GmailSettings(mode="futuresynch_dev", mailbox=MAILBOX, client_id="i", client_secret="s",
                         refresh_token="r")


def test_concurrent_drafts_run_the_mailbox_guard_once_and_one_at_a_time():
    stub = StubGmail()
    stub.profile_delay = 0.05  # long enough that unsynchronised threads would all pass the guard check
    transport = GmailDraftTransport(settings=_settings(), service=stub)
    message = {"to": "a@example.com", "subject": "s", "html_body": "<p>h</p>", "text_body": "t"}
    errors: list = []

    def run():
        try:
            transport.create_draft(message)
        except Exception as exc:  # pragma: no cover - would be reported below
            errors.append(exc)

    threads = [threading.Thread(target=run) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert stub.profile_calls == 1, "the mailbox guard must run once, not once per racing thread"
    assert len(stub.created) == 6


def test_a_blocked_state_set_by_one_thread_stops_the_threads_waiting_behind_it():
    stub = StubGmail()
    stub.create_failures = [RuntimeError("invalid_grant")] * 10
    transport = GmailDraftTransport(settings=_settings(), service=stub)
    message = {"to": "a@example.com", "subject": "s", "html_body": "<p>h</p>", "text_body": "t"}
    outcomes: list = []

    def run():
        try:
            transport.create_draft(message)
            outcomes.append("created")
        except DraftDeliveryError as exc:
            outcomes.append("reconnect" if exc.reconnect_required else "other")

    threads = [threading.Thread(target=run) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert outcomes == ["reconnect"] * 6
    assert stub.create_calls == 1, "after the first revoked sign-in Gmail must not be asked again"
