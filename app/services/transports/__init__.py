"""Outbound draft transports (FS-42).

create_draft(message) is what the orchestrator calls. Which transport answers
is configuration only: DRAFT_TRANSPORT=fake (default) or gmail.
"""
from __future__ import annotations

import os
from typing import Optional

from app.services.transports.base import ComposedMessage, DraftRef, DraftTransport
from app.services.transports.fake import FakeDraftTransport

_TRANSPORT: Optional[DraftTransport] = None


def _build_transport() -> DraftTransport:
    mode = (os.getenv("DRAFT_TRANSPORT") or "fake").strip().lower()
    if mode == "fake":
        return FakeDraftTransport()
    if mode == "gmail":
        # Imported here so the fake path never needs the Google libraries.
        from app.services.transports.gmail import GmailDraftTransport, load_settings

        return GmailDraftTransport(settings=load_settings())
    raise ValueError(f"DRAFT_TRANSPORT={mode!r} is not recognised (expected 'fake' or 'gmail')")


def get_draft_transport() -> DraftTransport:
    """One transport per process, so its guard and reconnect state persist."""
    global _TRANSPORT
    if _TRANSPORT is None:
        _TRANSPORT = _build_transport()
    return _TRANSPORT


def reset_draft_transport() -> None:
    """Forget the cached transport (tests, or after configuration changes)."""
    global _TRANSPORT
    _TRANSPORT = None


def create_draft(message: ComposedMessage) -> DraftRef:
    """Persist ``message`` as a draft and return {transport, draft_id, mailbox}."""
    return get_draft_transport().create_draft(message)
