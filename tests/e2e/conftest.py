"""
Fixtures for the Playwright e2e suite (FS-75). Start with docs/E2E.md.

Nothing here runs unless an ``e2e`` test is selected: the marker is excluded
from the default run (pytest.ini), so a plain ``pytest`` starts no server and
needs no browser.
"""
from __future__ import annotations

import pytest

from tests.e2e.live_server import LiveServer, start_live_server


@pytest.fixture(scope="session")
def live_server() -> LiveServer:
    """The real app on a free localhost port, healthy before it is yielded."""
    with start_live_server() as server:
        yield server


@pytest.fixture(scope="session")
def base_url(live_server: LiveServer) -> str:
    """Overrides pytest-playwright's ``base_url``: ``page.goto("/chat")`` works."""
    return live_server.url
