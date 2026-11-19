"""
Fixtures for the Playwright e2e suite (FS-75). Start with docs/E2E.md.

Nothing here runs unless an ``e2e`` test is selected: the marker is excluded
from the default run (pytest.ini), so a plain ``pytest`` starts no server and
needs no browser.
"""
from __future__ import annotations

import os
import re

import httpx
import pytest
from playwright.sync_api import Page, expect
from pytest_bdd import given, parsers, then, when

from tests.e2e.live_server import STRIPPED_ENV, LiveServer, start_live_server
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


# ---------------------------------------------------------------------------
# Steps shared by every e2e feature file (current /chat now, /workspace in FS-76)
# ---------------------------------------------------------------------------

@given("the app is running offline with the mock Claude client")
def step_app_running_offline(live_server: LiveServer):
    """Checks the safety properties of the server environment, every scenario."""
    assert os.environ.get("ANTHROPIC_MODE") == "mock", "Claude must be in mock mode"
    leaked = [name for name in STRIPPED_ENV if os.environ.get(name)]
    assert not leaked, f"credentials must not be in the e2e server environment: {leaked}"
    health = httpx.get(f"{live_server.url}/health", timeout=2.0, trust_env=False)
    assert health.json()["status"] == "ok"


@given("I am signed in as the agent on the chat page")
def step_signed_in_on_chat(page: Page, token_login):
    token_login()
    page.goto("/chat")
    expect(page.locator("#freeText")).to_be_visible()


@when("I open the chat page with no stored session")
def step_open_chat_without_session(page: Page):
    page.goto("/chat")


@when("I sign in through the login page as the agent")
def step_sign_in_as_agent(ui_login):
    ui_login()


@when("I try to sign in through the login page with a wrong password")
def step_sign_in_with_wrong_password(ui_login, agent_credentials: Credentials):
    wrong = Credentials(agent_credentials.email, "not-the-password")
    ui_login(wrong, wait_for_chat=False)


@when(parsers.parse('I click "{label}"'))
def step_click_label(page: Page, label: str):
    page.get_by_text(label, exact=True).click()


@then("I am on the login page")
def step_on_login_page(page: Page, base_url: str):
    expect(page).to_have_url(f"{base_url}/")


@then("I am on the chat page")
def step_on_chat_page(page: Page):
    expect(page).to_have_url(re.compile(r"/chat$"))
    expect(page.locator("#freeText")).to_be_visible()


@then(parsers.parse('the login page shows the error "{message}"'))
def step_login_error(page: Page, message: str):
    expect(page.locator("#globalError")).to_have_text(message)


@then("a session token is stored in the browser")
def step_token_stored(page: Page):
    assert page.evaluate("localStorage.getItem('token')"), "no token in localStorage"
    assert page.evaluate("localStorage.getItem('role')") == "agent"


@then("no session token is stored in the browser")
def step_no_token_stored(page: Page):
    assert page.evaluate("localStorage.getItem('token')") is None


@then("the browser's local storage is empty")
def step_local_storage_empty(page: Page):
    assert page.evaluate("localStorage.length") == 0
