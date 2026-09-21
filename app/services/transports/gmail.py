"""
Draft transport for FS-55 step d (create_draft).

FS-55 only needs the FAKE transport: the orchestrator composes a welcome draft
and, when dispatch=True, persists it as a draft via create_draft(). The real
Gmail-backed transport is FS-57 (which also owns removing the dispatch flag from
fn_generate_welcome). Until then create_draft() returns a deterministic fake
draft reference in the A-2 rev 5 shape:

    {"transport": "fake", "draft_id": "<id>", "mailbox": "<from-address>"}
"""
from __future__ import annotations

import os
import uuid
from typing import Any, Dict


class FakeDraftTransport:
    """In-memory draft transport. Persists nothing; returns a stable ref shape."""

    name = "fake"

    def create_draft(self, message: Dict[str, Any]) -> Dict[str, str]:
        # message is the A-2 rev 5 welcome_draft: {subject, html_body, text_body}.
        draft_id = "draft_" + uuid.uuid4().hex[:12]
        mailbox = os.getenv("EMAIL_FROM_ADDRESS", "synch@futuresynch.com")
        return {"transport": self.name, "draft_id": draft_id, "mailbox": mailbox}


# Module-level default used by the orchestrator. Swapping this for a real
# Gmail transport is FS-57 — the create_draft() signature stays the same.
_DEFAULT_TRANSPORT = FakeDraftTransport()


def create_draft(message: Dict[str, Any]) -> Dict[str, str]:
    """Persist `message` as a draft and return its {transport, draft_id, mailbox}."""
    return _DEFAULT_TRANSPORT.create_draft(message)
