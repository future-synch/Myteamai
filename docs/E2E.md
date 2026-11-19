# End-to-end browser tests (Playwright)

**Ticket:** FS-75 (epic FS-74) · **Scope:** the current vanilla-JS UI (`frontend/index.html`, `frontend/chat.html`) driven in a real Chromium against an in-process copy of the app.

These tests run **offline**. They never call HubSpot or Anthropic, and they never touch the demo portal (149441587), Curtis production (143653372) or any other tenant. See [Safety rules](#safety-rules).

They are **not part of the default `pytest` run**. A plain `pytest` needs no browser and its pass count is unchanged by this suite.

---

## One-time setup (your machine)

```bash
pip install -r requirements.txt          # installs pytest-playwright + playwright (Python packages only)
python -m playwright install chromium    # downloads the browser — local step, see below
```

Chromium only. Python only. No Node tooling.

> **The browser download is a local step and must never go in the Render build.**
> `render.yaml` runs `pip install -r requirements.txt`, which installs the `playwright` *package* (a few MB, no browsers).
> Do not add `playwright install` to `buildCommand` or any start command. The deployed app does not import Playwright.

`playwright==1.63.0` is pinned next to `pytest-playwright==0.10.0` on purpose: each Playwright release expects one specific Chromium revision, so an unpinned upgrade makes your installed browser stale. When you bump the pin, run `python -m playwright install chromium` again.

---

## Running

| Goal | Command |
|---|---|
| Run the e2e suite (headless) | `pytest -m e2e` |
| Watch the browser | `pytest -m e2e --headed` |
| Slow it down while watching | `pytest -m e2e --headed --slowmo 500` |
| One scenario | `pytest -m e2e -k "blank_client_name"` |
| Step through in the Playwright Inspector | `PWDEBUG=1 pytest -m e2e -k "wrong_password"` |
| Default run (unit/BDD tests, **no** e2e, no browser) | `pytest` |

`-m e2e` on the command line overrides the `-m "not ... and not e2e"` in `pytest.ini`'s `addopts`.

**Do not combine `-m e2e` with `-m integration`.** Integration tests need a real HubSpot key; the e2e server deliberately has none.

Feature file: `tests/features/e2e_current_chat.feature` (tagged `@e2e`). Step definitions: `tests/e2e/`. `tests/test_every_feature_file_is_bound.py` covers the feature file like every other one, and runs in the default pass.

---

## When a test fails

pytest-playwright keeps a **trace** and a **screenshot** for every failing test, in `test-results/` (git-ignored):

```
test-results/<test-name>-chromium/
    trace.zip
    test-failed-1.png
```

Open the trace (DOM snapshots before/after each action, network, console):

```bash
python -m playwright show-trace test-results/<test-name>-chromium/trace.zip
```

Notes:

- **`test-results/` is emptied at the start of every pytest session**, including a plain default `pytest`. Copy anything you want to keep before running again.
- The options come from pytest-playwright and are set in `pytest.ini` `addopts` (`--tracing retain-on-failure --screenshot only-on-failure --output test-results`). If the plugin is not installed, **every** pytest run (even the default one) fails with `unrecognized arguments`. Fix: `pip install -r requirements.txt`.

---

## How it works

| File | Role |
|---|---|
| `tests/e2e/live_server.py` | Starts the real FastAPI app with uvicorn in a background thread of the test process. Binds `127.0.0.1:0` first, so the OS picks a free port (no race). Polls `GET /health` before any test runs. Builds the offline environment. |
| `tests/e2e/network_guard.py` | Browser-side guard (below). |
| `tests/e2e/outbound_tripwire.py` | Server-side guard (below). |
| `tests/e2e/login_helpers.py` | `sign_in_through_login_page()` for the login UI; `seed_session()` to skip the UI and plant a token (for tests that are about something else). |
| `tests/e2e/conftest.py` | Fixtures and the steps shared across e2e features (offline Background, login, request recorder). |
| `tests/e2e/test_e2e_current_chat.py` | Binds the feature file; steps specific to `/chat`. |

The server runs with:

- `ANTHROPIC_MODE=mock`
- `BROCHURE_LINK_SOURCE=fake` (and `DRAFT_TRANSPORT=fake`)
- `HUBSPOT_API_KEY`, `HS_DEV_TOKEN` and `ANTHROPIC_API_KEY` **removed** from its environment, even if exported in your shell. They are restored when the session ends.

The `Background` step of every scenario re-asserts this (mock mode, no credentials set, `/health` ok), so a scenario cannot start in a non-offline state.

Agent login defaults to the MVP agent account. Override with `E2E_AGENT_EMAIL` / `E2E_AGENT_PASSWORD` if the account changes.

### Safety rules

1. **Browser guard.** Every request the browser makes is routed through `NetworkGuard`. Anything not on the test server's own origin (`http://127.0.0.1:<port>`) is aborted and recorded; `data:`, `blob:` and `about:` are allowed. After each test, a recorded violation **fails the test**, so a page that quietly loads an external script or font cannot pass.
2. **Server guard.** While the server runs, `httpx` is patched so any request to a non-loopback host is refused and recorded. An app that *catches* the resulting error (HubSpot calls are wrapped in try/except in places) still fails the test, because the violation is checked in teardown, not by the app's behaviour.
3. **No credentials.** There is nothing in the process that could authenticate to HubSpot or Anthropic.

**Known gap — WebSockets are not guarded.** Playwright 1.63's `route_web_socket` handlers deadlock the sync API, so the browser guard does not intercept `ws://`/`wss://`. The current UI opens none, and the server-side stripping above means a socket to a real tenant could not authenticate anyway. Revisit when the sync API allows it.

### Gotchas

- **Import-time config.** The app reads `JWT_SECRET`, `ALLOWED_ORIGINS` and `DEV_PORTAL_ID` when `app.auth` / `app.main` are first imported, and mounts `frontend/` only if the cwd is the repo root. The fixture sets the environment first, `chdir`s to the repo root for the session, and patches `app.auth.SECRET_KEY` directly in case the module was imported earlier by another test. `ALLOWED_ORIGINS` is set to the test origin but is not needed: the UI is same-origin, so CORS is never exercised. Do not rely on these tests for CORS behaviour.
- **`DEV_PORTAL_ID`** defaults to the FutureSynch dev sandbox ID (same default as `tests/conftest.py`) unless you export one. It is only an identifier: with no API key, no HubSpot client is ever built.
- Shared steps live in `tests/e2e/conftest.py`; steps used by one feature live next to its `scenarios(...)` call. pytest-bdd resolves both.

---

## Adding a scenario

1. Add it to `tests/features/e2e_current_chat.feature` (the file is already `@e2e`; a new feature file needs the tag too).
2. Reuse existing steps first (`grep -rn "@given\|@when\|@then" tests/e2e/`).
3. If the scenario asserts *"nothing was sent"*, add a **control** scenario that shows the same request *is* sent when the action is valid — otherwise the "nothing was sent" check can pass vacuously. See "TS Test 12" and its control.
4. Run `pytest -m e2e`, then plain `pytest` (counts must match before and after; `tests/test_every_feature_file_is_bound.py` must pass).
5. For a negative assertion, break the thing under test once (for example change a label in `frontend/chat.html`), confirm the scenario fails, and revert.

## Not covered here

- Register applicant submission (FS-76).
- Anything that needs a real HubSpot or Anthropic response. Those stay in `integration`-marked tests.
