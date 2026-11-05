"""In-memory draft transport (FS-42). Used by the whole automated suite and as
the default when DRAFT_TRANSPORT is unset. Persists nothing outside the process."""
from __future__ import annotations

import uuid
from typing import List

from app.services.transports.base import ComposedMessage, DraftRef

FAKE_MAILBOX = "fake-mailbox@example.invalid"


class FakeDraftTransport:
    name = "fake"

    def __init__(self) -> None:
        self.created: List[ComposedMessage] = []

    def create_draft(self, message: ComposedMessage) -> DraftRef:
        self.created.append(message)
        return {
            "transport": self.name,
            "draft_id": "draft_" + uuid.uuid4().hex[:12],
            "mailbox": FAKE_MAILBOX,
        }
