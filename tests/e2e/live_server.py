"""
In-process live server for the Playwright e2e suite (FS-75).

The real application (``app.main:app``) is served by uvicorn on a free
127.0.0.1 port, in a background thread of the test process. In-process is
deliberate: later tickets monkeypatch the same seams the TestClient suites use
(``bot_functions.register_applicant_in_hubspot``,
``hubspot_service.get_all_listings``), and a subprocess would not see the patch.

Offline by construction. While the server runs, its environment has:

* ``ANTHROPIC_MODE=mock``, ``BROCHURE_LINK_SOURCE=fake``, ``DRAFT_TRANSPORT=fake``
* no ``HUBSPOT_API_KEY``, ``HS_DEV_TOKEN`` or ``ANTHROPIC_API_KEY``, so the
  startup hook in ``lifespan()`` makes no HubSpot call (FS-73)

The original environment is restored when the server stops.

Two values are read by ``app`` at import time, which has usually happened
already by the time this runs (every test module imports ``app.main`` during
collection):

* ``JWT_SECRET``: handled by also patching ``app.auth.SECRET_KEY`` for the
  session, so the test secret is the one actually in force.
* ``ALLOWED_ORIGINS``: set in the environment for fidelity, but the middleware
  list is already built. This does not matter here: the browser and the app
  share one origin, and same-origin requests do not use CORS.
"""
from __future__ import annotations

import contextlib
import os
import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Mapping, Optional

import httpx
import uvicorn

REPO_ROOT = Path(__file__).resolve().parents[2]

E2E_JWT_SECRET = "e2e-test-secret-not-for-production"

# Credentials the server process must never see. With none of them set, no code
# path can reach HubSpot or Anthropic even by accident.
STRIPPED_ENV = ("HUBSPOT_API_KEY", "HS_DEV_TOKEN", "ANTHROPIC_API_KEY")


@dataclass(frozen=True)
class LiveServer:
    host: str
    port: int

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


@contextlib.contextmanager
def patched_environ(changes: Mapping[str, Optional[str]]) -> Iterator[None]:
    """Apply environment changes (``None`` removes a variable); restore on exit."""
    saved = {name: os.environ.get(name) for name in changes}
    try:
        for name, value in changes.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def server_environment(origin: str) -> dict[str, Optional[str]]:
    """The environment the e2e server runs under (``None`` = removed)."""
    env: dict[str, Optional[str]] = {
        "ANTHROPIC_MODE": "mock",
        "BROCHURE_LINK_SOURCE": "fake",
        "DRAFT_TRANSPORT": "fake",
        # Same default as tests/conftest.py; an exported value is left alone.
        "DEV_PORTAL_ID": os.environ.get("DEV_PORTAL_ID", "148226118"),
        "JWT_SECRET": E2E_JWT_SECRET,
        "ALLOWED_ORIGINS": origin,
    }
    env.update({name: None for name in STRIPPED_ENV})
    return env


def wait_until_healthy(base_url: str, thread: threading.Thread, timeout: float = 15.0) -> None:
    """Poll ``GET /health`` until it answers ``{"status": "ok"}``."""
    deadline = time.monotonic() + timeout
    last = "no response yet"
    while time.monotonic() < deadline:
        if not thread.is_alive():
            raise RuntimeError(
                "The uvicorn thread exited before /health answered. "
                "Its traceback is in the captured output above."
            )
        try:
            # trust_env=False: a proxy variable in the shell must not sit between
            # the test process and its own server.
            response = httpx.get(f"{base_url}/health", timeout=1.0, trust_env=False)
            if response.status_code == 200 and response.json().get("status") == "ok":
                return
            last = f"HTTP {response.status_code}: {response.text[:200]}"
        except (httpx.HTTPError, ValueError) as exc:
            last = repr(exc)
        time.sleep(0.05)
    raise RuntimeError(f"Live server not healthy after {timeout:.0f}s (last: {last})")


@contextlib.contextmanager
def start_live_server(startup_timeout: float = 15.0) -> Iterator[LiveServer]:
    """Serve ``app.main:app`` on a free localhost port until the block exits."""
    # Bind first and hand the socket to uvicorn: no race for the port, and the
    # origin is known before the app is touched.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    info = LiveServer("127.0.0.1", sock.getsockname()[1])

    previous_cwd = os.getcwd()
    # app.main mounts frontend/ and serves it by relative path, so the working
    # directory must be the repo root for the whole session.
    os.chdir(REPO_ROOT)
    try:
        with patched_environ(server_environment(info.url)):
            import app.auth
            import app.main

            routes = {getattr(route, "path", None) for route in app.main.app.routes}
            if not {"/", "/chat"} <= routes:
                raise RuntimeError(
                    "app.main was imported while the working directory was not the "
                    "repository root, so frontend/ was never mounted. Run pytest "
                    "from the repository root."
                )

            original_secret = app.auth.SECRET_KEY
            app.auth.SECRET_KEY = E2E_JWT_SECRET

            config = uvicorn.Config(
                app.main.app,
                host=info.host,
                port=info.port,
                log_level="warning",
                log_config=None,   # leave pytest's logging alone
                loop="asyncio",    # uvloop is not worth the trouble in a thread
                lifespan="on",
            )
            server = uvicorn.Server(config)
            thread = threading.Thread(
                target=server.run,
                kwargs={"sockets": [sock]},
                name="e2e-live-server",
                daemon=True,
            )
            thread.start()
            try:
                wait_until_healthy(info.url, thread, startup_timeout)
                yield info
            finally:
                server.should_exit = True
                thread.join(timeout=10)
                app.auth.SECRET_KEY = original_secret
    finally:
        os.chdir(previous_cwd)
        with contextlib.suppress(OSError):
            sock.close()
