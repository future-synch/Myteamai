"""
Server-side counterpart of the browser network guard (FS-75).

The browser guard proves the *page* stays on localhost. This proves the *server*
does too: while an e2e session runs, any ``httpx`` request from the test process
to a host other than loopback is refused and recorded. That is how the app
would reach HubSpot or Anthropic (hubspot_client, hubspot_service and the
anthropic SDK all use httpx). The credentials are already stripped from the
environment (live_server.py); this is the second, independent check.

The refused request raises ``httpx.ConnectError``. App code that swallows
exceptions would hide that, so the test fails in teardown from the recorded
list, whatever the app did with the error.
"""
from __future__ import annotations

import contextlib
from typing import Iterator

import httpx

# "testserver" is the host Starlette's TestClient uses; it is in-process.
_LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "testserver"})


class OutboundTripwire:
    def __init__(self) -> None:
        self.blocked: list[str] = []

    def _check(self, request: httpx.Request) -> None:
        if request.url.host in _LOCAL_HOSTS:
            return
        # Host and path only: a query string can carry a token.
        self.blocked.append(
            f"{request.method} {request.url.scheme}://{request.url.host}{request.url.path}"
        )
        raise httpx.ConnectError(
            "Blocked by the e2e outbound tripwire (FS-75): the e2e server must not "
            "call out to anything but localhost.",
            request=request,
        )

    @contextlib.contextmanager
    def installed(self) -> Iterator["OutboundTripwire"]:
        real_send = httpx.Client.send
        real_async_send = httpx.AsyncClient.send
        tripwire = self

        def send(client, request, *args, **kwargs):
            tripwire._check(request)
            return real_send(client, request, *args, **kwargs)

        async def async_send(client, request, *args, **kwargs):
            tripwire._check(request)
            return await real_async_send(client, request, *args, **kwargs)

        httpx.Client.send = send
        httpx.AsyncClient.send = async_send
        try:
            yield self
        finally:
            httpx.Client.send = real_send
            httpx.AsyncClient.send = real_async_send
