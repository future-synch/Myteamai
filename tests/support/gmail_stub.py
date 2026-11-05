"""Offline stand-in for the Gmail API service object (FS-42 tests).

Mirrors only the calls the transport makes:
    service.users().getProfile(userId="me").execute()
    service.users().drafts().create(userId="me", body=...).execute()
and fails loudly if anything touches messages(), which is where send lives.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List

MAILBOX = "drafts@dev.example.test"


class _Exec:
    def __init__(self, fn):
        self._fn = fn

    def execute(self):
        return self._fn()


class _HttpStatus:
    def __init__(self, status: int) -> None:
        self.status = status


class GmailApiError(Exception):
    """Shaped like googleapiclient.errors.HttpError (has .resp.status)."""

    def __init__(self, status: int) -> None:
        super().__init__(f"HTTP {status}")
        self.resp = _HttpStatus(status)


class StubGmail:
    def __init__(self) -> None:
        self.account = MAILBOX
        self.profile_calls = 0
        self.create_calls = 0
        self.send_attempts = 0
        self.created: List[Dict[str, Any]] = []
        self.create_failures: List[Exception] = []  # raised once each, in order
        self.profile_delay = 0.0  # widen race windows in concurrency tests
        self.threads_seen: set = set()

    # users().getProfile / users().drafts().create / users().messages()
    def users(self):
        return self

    def getProfile(self, userId):  # noqa: N802 - Google API naming
        def run():
            self.threads_seen.add(threading.current_thread().name)
            time.sleep(self.profile_delay)
            self.profile_calls += 1
            return {"emailAddress": self.account}

        return _Exec(run)

    def drafts(self):
        return self

    def create(self, userId, body):
        def run():
            self.threads_seen.add(threading.current_thread().name)
            self.create_calls += 1
            if self.create_failures:
                raise self.create_failures.pop(0)
            self.created.append(body)
            return {"id": f"gmail-draft-{len(self.created)}"}

        return _Exec(run)

    def messages(self):
        self.send_attempts += 1
        raise AssertionError("the platform must never touch messages(): drafts only")
