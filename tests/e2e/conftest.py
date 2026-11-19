"""
Fixtures for the Playwright e2e suite (FS-75). Start with docs/E2E.md.

Nothing here runs unless an ``e2e`` test is selected: the marker is excluded
from the default run (pytest.ini), so a plain ``pytest`` starts no server and
needs no browser.
"""
from __future__ import annotations

import pytest

from tests.e2e.live_server import LiveServer, start_live_server
from tests.e2e.network_guard import NetworkGuard


@pytest.fixture(scope="session")
def live_server() -> LiveServer:
    """The real app on a free localhost port, healthy before it is yielded."""
    with start_live_server() as server:
        yield server


@pytest.fixture(scope="session")
def base_url(live_server: LiveServer) -> str:
    """Overrides pytest-playwright's ``base_url``: ``page.goto("/chat")`` works."""
    return live_server.url


# ---------------------------------------------------------------------------
# Network guard: the browser may talk to the local test server and nothing else
# ---------------------------------------------------------------------------

@pytest.fixture
def network_guard(live_server: LiveServer) -> NetworkGuard:
    return NetworkGuard(live_server.url)


@pytest.fixture
def new_context(new_context, network_guard: NetworkGuard):
    """Wraps pytest-playwright's factory so every context gets the guard.

    ``context`` and ``page`` are built from ``new_context``, and so is any extra
    context a test creates itself.
    """
    def guarded_new_context(**kwargs):
        context = new_context(**kwargs)
        network_guard.install(context)
        return context

    return guarded_new_context


@pytest.fixture(autouse=True)
def _browser_stayed_on_localhost(network_guard: NetworkGuard):
    """Fail the test if the browser tried to reach anything but the test server.

    Runs in teardown, after the contexts are closed. The request itself was
    already aborted, so nothing left the machine.
    """
    yield
    if network_guard.violations:
        attempted = "\n  ".join(network_guard.violations)
        pytest.fail(
            "e2e tests must stay on the local test server "
            f"({network_guard.allowed_origin}), but the browser requested:\n  "
            f"{attempted}",
            pytrace=False,
        )
