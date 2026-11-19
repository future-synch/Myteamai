"""
Login helpers for the Playwright e2e suite (FS-75).

Two ways to be signed in:

* ``sign_in_through_login_page``: drives the real login page. Use it for tests
  that are about login.
* ``seed_session``: calls ``POST /auth/login`` and puts ``token`` and ``role`` in
  ``localStorage``, the same two keys ``index.html`` stores. Faster; use it for
  every test that only needs to be signed in.

Credentials default to the hardcoded MVP agent in ``app/auth.py``. The hardcoded
logins are replaced at M5, so both can be overridden from the environment:
``E2E_AGENT_EMAIL`` and ``E2E_AGENT_PASSWORD``.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Optional

from playwright.sync_api import Page, expect

DEFAULT_AGENT_EMAIL = "agent@curtissloane.com"
DEFAULT_AGENT_PASSWORD = "agent123"


@dataclass(frozen=True)
class Credentials:
    email: str
    password: str


def load_agent_credentials() -> Credentials:
    return Credentials(
        email=os.getenv("E2E_AGENT_EMAIL") or DEFAULT_AGENT_EMAIL,
        password=os.getenv("E2E_AGENT_PASSWORD") or DEFAULT_AGENT_PASSWORD,
    )


def sign_in_through_login_page(
    page: Page,
    credentials: Credentials,
    *,
    wait_for_chat: bool = True,
) -> None:
    """Fill in and submit the real login form at ``/``.

    With ``wait_for_chat=False`` it returns right after the click, for tests that
    expect the login to be refused.
    """
    page.goto("/")
    page.fill("#email", credentials.email)
    page.fill("#password", credentials.password)
    page.click("#submitBtn")
    if wait_for_chat:
        expect(page).to_have_url(re.compile(r"/chat$"))


def seed_session(page: Page, credentials: Credentials) -> str:
    """Log in over the API and store the session the way the login page does.

    Leaves the page on ``/`` (the login page, which does not redirect when a
    token exists); navigate to the page under test afterwards. Returns the token.
    """
    response = page.request.post(
        "/auth/login",
        data={"email": credentials.email, "password": credentials.password},
    )
    assert response.ok, (
        f"POST /auth/login answered {response.status} for {credentials.email}; "
        "check E2E_AGENT_EMAIL / E2E_AGENT_PASSWORD"
    )
    body = response.json()
    # localStorage belongs to an origin, so load a page of the app first.
    page.goto("/")
    page.evaluate(
        "([token, role]) => {"
        " localStorage.setItem('token', token);"
        " localStorage.setItem('role', role);"
        "}",
        [body["access_token"], body["role"]],
    )
    return body["access_token"]
