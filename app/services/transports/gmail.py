"""
Gmail draft transport (FS-42): one implementation, injected credentials.

Creates a DRAFT in the shared sending mailbox via users().drafts().create().
It never calls messages().send(): gmail.compose technically permits sending, so
the human-review guarantee is enforced here, in code, not by OAuth.

Configuration (names only; values live in the environment, never in git):

    DRAFT_TRANSPORT           fake | gmail          (read by app.services.transports)
    GMAIL_CREDENTIAL_MODE     futuresynch_dev | curtis_sloane_prod
    GMAIL_DEV_CLIENT_ID / _CLIENT_SECRET / _REFRESH_TOKEN / _MAILBOX
    GMAIL_PROD_CLIENT_ID / _CLIENT_SECRET / _REFRESH_TOKEN / _MAILBOX

No unprefixed GMAIL_* credential is ever read, so a production credential cannot
be reached by a name a development run uses.

Safety behaviour (FS-42 design record):
  * Mailbox guard: before the first draft, getProfile must return the mailbox
    expected for the active mode, or no draft is created.
  * Revoked / blocked sign-in (invalid_grant, admin_policy_enforced) puts the
    transport in an explicit "reconnect required" state. The caller keeps the
    composed message; nothing is lost.

Probe (creates one real draft addressed to the mailbox itself):
    python -m app.services.transports.gmail
"""
from __future__ import annotations

import base64
import logging
import os
import sys
import threading
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Any, Dict, Mapping, Optional

from app.services.transports.base import (
    ComposedMessage,
    DraftDeliveryError,
    DraftRef,
    GmailConfigError,
)

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]
TOKEN_URI = "https://oauth2.googleapis.com/token"

_MODE_PREFIX = {"futuresynch_dev": "GMAIL_DEV", "curtis_sloane_prod": "GMAIL_PROD"}
_REVOKED_MARKERS = ("invalid_grant", "admin_policy_enforced")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GmailSettings:
    mode: str
    mailbox: str
    client_id: str = field(repr=False)
    client_secret: str = field(repr=False)
    refresh_token: str = field(repr=False)


def load_settings(env: Optional[Mapping[str, str]] = None) -> GmailSettings:
    """Read the settings for the active credential mode. Raises GmailConfigError
    naming what is wrong; error text never contains a secret value."""
    env = os.environ if env is None else env
    allowed = ", ".join(sorted(_MODE_PREFIX))
    mode = (env.get("GMAIL_CREDENTIAL_MODE") or "").strip().lower()
    if not mode:
        raise GmailConfigError(f"GMAIL_CREDENTIAL_MODE is not set (expected one of: {allowed})")
    if mode not in _MODE_PREFIX:
        raise GmailConfigError(
            f"GMAIL_CREDENTIAL_MODE={mode!r} is not recognised (expected one of: {allowed})"
        )
    prefix = _MODE_PREFIX[mode]
    names = {
        "client_id": f"{prefix}_CLIENT_ID",
        "client_secret": f"{prefix}_CLIENT_SECRET",
        "refresh_token": f"{prefix}_REFRESH_TOKEN",
        "mailbox": f"{prefix}_MAILBOX",
    }
    values = {key: (env.get(name) or "").strip() for key, name in names.items()}
    missing = [names[key] for key, value in values.items() if not value]
    if missing:
        raise GmailConfigError("Missing required setting(s): " + ", ".join(missing))
    return GmailSettings(mode=mode, **values)


class RefreshTokenCredentialProvider:
    """The one CredentialProvider: OAuth client + a long-lived refresh token for
    the shared sending mailbox. Development and production differ only in the
    configuration it reads."""

    def __init__(self, settings: GmailSettings) -> None:
        self._settings = settings

    def credentials_for(self, agent: Optional[Any] = None) -> Any:
        # One shared mailbox (Q24): the agent does not change the credential.
        try:
            from google.oauth2.credentials import Credentials
        except ImportError as exc:  # pragma: no cover - environment problem
            raise GmailConfigError(
                "google-auth is not installed; run: pip install -r requirements.txt"
            ) from exc
        return Credentials(
            token=None,
            refresh_token=self._settings.refresh_token,
            token_uri=TOKEN_URI,
            client_id=self._settings.client_id,
            client_secret=self._settings.client_secret,
            scopes=SCOPES,
        )


# ---------------------------------------------------------------------------
# Message building
# ---------------------------------------------------------------------------


def build_raw(to: str, subject: str, text_body: str, html_body: str) -> str:
    """MIME multipart/alternative (text + html), base64url for the Gmail API.

    No From header (implied by the mailbox; a mismatch fails) and no Bcc.
    EmailMessage rejects header values containing line breaks, so a crafted
    recipient or subject cannot inject headers.
    """
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


class GmailDraftTransport:
    name = "gmail"

    def __init__(
        self,
        *,
        settings: GmailSettings,
        service: Any = None,
        provider: Optional[RefreshTokenCredentialProvider] = None,
    ) -> None:
        self._settings = settings
        self._service = service  # injected in tests; built lazily otherwise
        self._provider = provider or RefreshTokenCredentialProvider(settings)
        self._guard_passed = False
        self._blocked: Optional[DraftDeliveryError] = None
        # The Google client (httplib2) is not safe to share across threads, and the
        # orchestrator calls create_draft from worker threads. One draft at a time.
        self._lock = threading.Lock()

    # -- internals ---------------------------------------------------------

    def _get_service(self) -> Any:
        if self._service is None:
            try:
                from googleapiclient.discovery import build
            except ImportError as exc:  # pragma: no cover - environment problem
                raise GmailConfigError(
                    "google-api-python-client is not installed; run: pip install -r requirements.txt"
                ) from exc
            self._service = build(
                "gmail", "v1", credentials=self._provider.credentials_for(), cache_discovery=False
            )
        return self._service

    def _check_mailbox(self, service: Any) -> None:
        profile = service.users().getProfile(userId="me").execute()
        actual = str(profile.get("emailAddress", "")).strip().lower()
        if actual != self._settings.mailbox.strip().lower():
            # Abort unconditionally: a draft in a live client mailbox from a dev
            # or CI run would be seen by the client. Addresses are not echoed.
            self._blocked = DraftDeliveryError(
                "Mailbox guard: the connected Google account is not the mailbox expected for "
                f"GMAIL_CREDENTIAL_MODE={self._settings.mode}. No draft was created."
            )
            raise self._blocked
        self._guard_passed = True

    def _raise_mapped(self, exc: Exception) -> None:
        lowered = f"{exc.__class__.__name__}: {exc}".lower()
        if any(marker in lowered for marker in _REVOKED_MARKERS):
            self._blocked = DraftDeliveryError(
                "Gmail reconnect required: the saved Google sign-in was revoked or blocked. "
                "A person must reconnect the mailbox. The composed email has been kept.",
                reconnect_required=True,
            )
            raise self._blocked from exc
        status = getattr(getattr(exc, "resp", None), "status", None)
        if status:
            raise DraftDeliveryError(f"Gmail API error (HTTP {status}). No draft was created.") from exc
        raise DraftDeliveryError(
            f"The Gmail draft could not be created ({exc.__class__.__name__})."
        ) from exc

    # -- public ------------------------------------------------------------

    def create_draft(self, message: ComposedMessage) -> DraftRef:
        if self._blocked is not None:
            raise self._blocked  # explicit state: fail fast, no Gmail call

        to = str(message.get("to") or "").strip()
        if not to:
            raise DraftDeliveryError("The draft needs a recipient address; none was supplied.")
        try:
            raw = build_raw(
                to,
                str(message.get("subject") or ""),
                str(message.get("text_body") or ""),
                str(message.get("html_body") or ""),
            )
        except ValueError as exc:
            raise DraftDeliveryError("The draft message was rejected as malformed.") from exc

        with self._lock:
            if self._blocked is not None:  # another thread tripped it while we waited
                raise self._blocked
            try:
                service = self._get_service()
                if not self._guard_passed:
                    self._check_mailbox(service)
                draft = (
                    service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
                )
            except (DraftDeliveryError, GmailConfigError):
                raise
            except Exception as exc:
                self._raise_mapped(exc)
                raise  # pragma: no cover - _raise_mapped always raises

        log.info("Gmail draft created in the %s mailbox", self._settings.mode)
        return {
            "transport": self.name,
            "draft_id": str(draft["id"]),
            "mailbox": self._settings.mailbox,
        }


# ---------------------------------------------------------------------------
# Probe: python -m app.services.transports.gmail
# ---------------------------------------------------------------------------


def _probe() -> int:
    try:
        settings = load_settings()
        transport = GmailDraftTransport(settings=settings)
        ref = transport.create_draft(
            {
                "to": settings.mailbox,
                "subject": "MyTeamAI test draft (safe to delete)",
                "text_body": "Plain-text part of the MyTeamAI test draft.",
                "html_body": "<p>HTML part of the <strong>MyTeamAI</strong> test draft.</p>",
            }
        )
    except (GmailConfigError, DraftDeliveryError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 2
    print(f"OK: draft {ref['draft_id']} created in the {settings.mode} mailbox ({ref['mailbox']})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_probe())
