"""
Fixtures for the Playwright e2e suite (FS-75). Start with docs/E2E.md.

Nothing here runs unless an ``e2e`` test is selected: the marker is excluded
from the default run (pytest.ini), so a plain ``pytest`` starts no server and
needs no browser.
"""
from __future__ import annotations

import pytest

from tests.e2e.live_server import LiveServer, start_live_server
from tests.e2e.login_helpers import (
    Credentials,
    load_agent_credentials,
    seed_session,
    sign_in_through_login_page,
)
from tests.e2e.network_guard import NetworkGuard
from tests.e2e.outbound_tripwire import OutboundTripwire


@pytest.fixture(scope="session")
def outbound_tripwire() -> OutboundTripwire:
    """Refuses (and records) httpx requests from this process to non-loopback hosts."""
    with OutboundTripwire().installed() as tripwire:
        yield tripwire


@pytest.fixture(scope="session")
def live_server(outbound_tripwire: OutboundTripwire) -> LiveServer:
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


@pytest.fixture(autouse=True)
def _server_made_no_outbound_calls(outbound_tripwire: OutboundTripwire):
    """Fail the test if the app server tried to call out (HubSpot, Anthropic, ...)."""
    outbound_tripwire.blocked.clear()
    yield
    if outbound_tripwire.blocked:
        attempted = "\n  ".join(outbound_tripwire.blocked)
        pytest.fail(
            "the e2e app server must not call out to anything but localhost, but it tried:\n  "
            f"{attempted}",
            pytrace=False,
        )


# ---------------------------------------------------------------------------
# Login helpers (see login_helpers.py)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def agent_credentials() -> Credentials:
    """The MVP agent account; E2E_AGENT_EMAIL / E2E_AGENT_PASSWORD override it."""
    return load_agent_credentials()


@pytest.fixture
def ui_login(page, agent_credentials: Credentials):
    """Callable: sign in through the real login page (for tests about login)."""
    def _ui_login(credentials: Credentials | None = None, *, wait_for_chat: bool = True) -> None:
        sign_in_through_login_page(
            page, credentials or agent_credentials, wait_for_chat=wait_for_chat
        )

    return _ui_login


@pytest.fixture
def token_login(page, agent_credentials: Credentials):
    """Callable: POST /auth/login and seed localStorage (fast, for everything else)."""
    def _token_login(credentials: Credentials | None = None) -> str:
        return seed_session(page, credentials or agent_credentials)

    return _token_login
