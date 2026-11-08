"""
FS-67 item 1 — live @integration test for the migrated read-path match.

Self-provisioning: creates a TEST- Listing + two TEST- applicant Contacts on the
new-schema dev tenant, runs the live match, asserts the budget/beds-fit applicant
is returned and the unfit one is filtered, then archives everything in teardown —
even on failure. Tenant-guarded: refuses to run unless the token resolves to the
configured DEV_PORTAL_ID, and the production portal is always refused.

NOT run in CI / offline: marked @integration (deselected by default). Execute with
  HS_DEV_TOKEN=<dev> HUBSPOT_API_KEY=<dev> pytest -m integration
only after the demo token + DEV_PORTAL_ID are set. No live calls happen otherwise.

Verified against Confluence test_2 snapshot 2026-09-10, NOT yet verified against
the demo portal.
"""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from typing import Any, Dict, List

import httpx
import pytest

from app.constants.registration_constants import DEV_PORTAL_ID, FORBIDDEN_PORTAL_IDS
from app.models.schemas import MatchApplicantsRequest
from app.services import hubspot_service
from app.functions.bot_functions import fn_match_applicants

pytestmark = pytest.mark.integration

HUBSPOT_BASE = "https://api.hubapi.com"
LISTINGS_OBJECT_ID = "0-420"
TIMEOUT = 30.0
SEARCH_TIMEOUT = 40.0   # max wait for the search index to see a new record
POLL_INTERVAL = 2.0
TEST_PREFIX = "TEST-"
SKIP_REASON = "HS_DEV_TOKEN not set — FS-67 live match integration needs the dev tenant token."


def _run(coro):
    return asyncio.run(coro)


def _headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# HubSpot's search index is eventually consistent: a just-created record is not
# instantly returned by search. Poll the same query the code under test uses, with
# a timeout, before asserting. Not a blind sleep: that always pays the full wait
# and still fails when the lag exceeds the guess.
async def _wait_until_searchable(address: str, token: str) -> bool:
    deadline = time.monotonic() + SEARCH_TIMEOUT
    while time.monotonic() < deadline:
        if await hubspot_service.get_listing_by_address(address, token=token):
            return True
        await asyncio.sleep(POLL_INTERVAL)
    return False


async def _wait_until_applicants_searchable(emails, token: str) -> bool:
    want = {e.lower() for e in emails}
    deadline = time.monotonic() + SEARCH_TIMEOUT
    while time.monotonic() < deadline:
        present = {(a.get("email") or "").lower() for a in await hubspot_service.get_all_applicants(token=token)}
        if want <= present:
            return True
        await asyncio.sleep(POLL_INTERVAL)
    return False


class _DevClient:
    """Minimal HubSpot client for provisioning/teardown against the dev tenant."""

    def __init__(self, token: str):
        self._h = _headers(token)

    async def portal_id(self) -> int:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.get(f"{HUBSPOT_BASE}/account-info/v3/details", headers=self._h)
            r.raise_for_status()
            return r.json().get("portalId")

    async def create(self, object_id: str, properties: Dict[str, Any]) -> str:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.post(
                f"{HUBSPOT_BASE}/crm/v3/objects/{object_id}",
                headers=self._h, json={"properties": properties},
            )
            r.raise_for_status()
            return r.json()["id"]

    async def archive(self, object_id: str, record_id: str) -> None:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.delete(
                f"{HUBSPOT_BASE}/crm/v3/objects/{object_id}/{record_id}", headers=self._h
            )
            if r.status_code not in (200, 204, 404):
                r.raise_for_status()


@pytest.fixture(scope="module")
def dev_session():
    token = os.getenv("HS_DEV_TOKEN")
    if not token:
        pytest.skip(SKIP_REASON)

    client = _DevClient(token)
    portal = _run(client.portal_id())

    # Tenant guard: deny-list first, then require the configured dev portal.
    if portal in FORBIDDEN_PORTAL_IDS:
        pytest.fail(f"Refusing to run: token resolves to forbidden portal {portal}.", pytrace=False)
    if DEV_PORTAL_ID is None or portal != DEV_PORTAL_ID:
        pytest.fail(
            f"Refusing to run: token portal {portal} != DEV_PORTAL_ID={DEV_PORTAL_ID}.",
            pytrace=False,
        )

    created: List[tuple[str, str]] = []  # (object_id, record_id)
    run_id = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"

    try:
        yield {"client": client, "created": created, "run_id": run_id}
    finally:
        # Archive everything created this run — on success AND failure.
        for object_id, record_id in reversed(created):
            try:
                _run(client.archive(object_id, record_id))
            except Exception:  # noqa: BLE001 — teardown is best-effort
                pass


def test_live_match_returns_fit_applicant_and_filters_unfit(dev_session):
    client = _DevClient(os.environ["HS_DEV_TOKEN"])
    created = dev_session["created"]
    run_id = dev_session["run_id"]

    address = f"{TEST_PREFIX}{run_id} 1 Test Row, W11"
    # A £3M, 4-bed house listing.
    listing_id = _run(client.create(LISTINGS_OBJECT_ID, {
        "hs_name": address,
        "hs_address_1": address,
        "hs_price": "3000000",
        "hs_bedrooms": "4",
        "hs_listing_type": "house",
        "postcode": "W11 1AA",
    }))
    created.append((LISTINGS_OBJECT_ID, listing_id))

    fit_email = f"{TEST_PREFIX}{run_id}-fit@example.com"
    unfit_email = f"{TEST_PREFIX}{run_id}-unfit@example.com"

    # Fit: budget up_to_3m (>= £3M), beds 4_plus, house.
    fit_id = _run(client.create("contacts", {
        "firstname": "TEST", "lastname": "Fit", "email": fit_email,
        "type_of_customer": "applicant",
        "budget": "up_to_3m", "beds_required": "4_plus", "property_types": "house",
        "financing_status": "cash", "source": "direct", "preferred_channel": "email",
    }))
    created.append(("contacts", fit_id))

    # Unfit: budget up_to_1m (below the £3M asking) — filtered out.
    unfit_id = _run(client.create("contacts", {
        "firstname": "TEST", "lastname": "Unfit", "email": unfit_email,
        "type_of_customer": "applicant",
        "budget": "up_to_1m", "beds_required": "4_plus", "property_types": "house",
        "financing_status": "cash", "source": "direct", "preferred_channel": "email",
    }))
    created.append(("contacts", unfit_id))

    # Wait for the search index to see the new records before matching.
    token = os.environ["HS_DEV_TOKEN"]
    assert _run(_wait_until_searchable(address, token)), \
        f"listing {address!r} not searchable after {SEARCH_TIMEOUT}s"
    assert _run(_wait_until_applicants_searchable([fit_email, unfit_email], token)), \
        f"applicants not searchable after {SEARCH_TIMEOUT}s"

    # Run the live match against the listing address.
    resp = _run(fn_match_applicants(MatchApplicantsRequest(property_ref=address)))

    assert resp.status == "ok", resp
    emails = {m.email for m in resp.matches}
    assert fit_email in emails, f"fit applicant missing: {emails}"
    assert unfit_email not in emails, f"unfit applicant should have been filtered: {emails}"
