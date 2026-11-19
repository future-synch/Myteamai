"""
Browser network guard for the Playwright e2e suite (FS-75).

"Offline" is a checked property, not an assumption. Every browser context gets
this guard. A request to anything other than the local test server is aborted
before it leaves the machine and recorded; the test then fails in teardown
with the list of what was attempted.

Playwright does not route ``data:``, ``blob:`` or ``about:`` URLs, and they never
reach the network, so they are always allowed.

Known gap: WebSocket connections do not pass through ``context.route()``, so they
are not guarded. The app opens none. (``context.route_web_socket()`` exists, but
calling ``ws.close()`` or ``ws.connect_to_server()`` inside its handler deadlocks
the sync API on Playwright 1.63, so it is not used.)
"""
from __future__ import annotations

from urllib.parse import urlsplit

from playwright.sync_api import BrowserContext, Route

_LOCAL_SCHEMES = frozenset({"data", "blob", "about"})


def _without_query(url: str) -> str:
    return urlsplit(url)._replace(query="", fragment="").geturl()


class NetworkGuard:
    def __init__(self, allowed_origin: str) -> None:
        parts = urlsplit(allowed_origin)
        self._allowed = (parts.scheme, parts.netloc)
        self.allowed_origin = allowed_origin
        self.violations: list[str] = []

    def install(self, context: BrowserContext) -> None:
        context.route("**/*", self._handle_request)

    def is_allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        if parts.scheme in _LOCAL_SCHEMES:
            return True
        # Compare the whole netloc: "http://127.0.0.1:1234@evil.example" is not
        # the local server.
        return (parts.scheme, parts.netloc) == self._allowed

    def _handle_request(self, route: Route) -> None:
        request = route.request
        if self.is_allowed(request.url):
            # fallback(), not continue_(): lets a page.route() stub registered by
            # a test (FS-76) answer first, and still guards whatever it passes on.
            route.fallback()
            return
        self.violations.append(f"{request.method} {_without_query(request.url)}")
        route.abort("blockedbyclient")
