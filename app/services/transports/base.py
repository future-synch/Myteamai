"""
Draft-delivery contracts (FS-42).

A transport takes an already-composed message and places it in a mailbox as a
DRAFT a human can review, edit and send. Nothing in this package ever sends.
The credential provider is the seam between environments, not the transport:
one transport implementation, configured differently for development and
production.
"""
from __future__ import annotations

from typing import Any, Optional, Protocol, TypedDict


class ComposedMessage(TypedDict):
    """Input contract. Produced by composition (FS-57) plus the recipient."""

    to: str
    subject: str
    html_body: str
    text_body: str


class DraftRef(TypedDict):
    """Where the draft landed. Deliberately transport-neutral."""

    transport: str   # "gmail" | "fake"
    draft_id: str
    mailbox: str


class DraftTransport(Protocol):
    def create_draft(self, message: ComposedMessage) -> DraftRef: ...


class CredentialProvider(Protocol):
    def credentials_for(self, agent: Optional[Any] = None) -> Any: ...


class DraftDeliveryError(Exception):
    """The draft could not be created.

    The message is safe to show to an agent: it never contains credentials or
    message content. ``reconnect_required`` is True when a person has to
    reconnect the mailbox (revoked or blocked sign-in); retrying cannot help.
    """

    def __init__(self, message: str, *, reconnect_required: bool = False) -> None:
        super().__init__(message)
        self.reconnect_required = reconnect_required


class GmailConfigError(ValueError):
    """Configuration is missing or invalid. Names settings, never their values."""
