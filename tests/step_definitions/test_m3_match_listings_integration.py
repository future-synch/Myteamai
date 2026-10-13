"""
FS-70 — OPTIONAL live @integration test for find_matching_listings (Direction 1).

Self-provisions TEST- listings on the dev tenant, runs the real matching engine
against a buyer's criteria, asserts the stronger-fit listing outranks the weaker
one, and archives everything in teardown — even on failure. Tenant-guarded:
deny-list first, then requires the configured DEV_PORTAL_ID; production refused.

NOT run offline/CI (marked @integration, deselected by default). Run only with
  HS_DEV_TOKEN=<dev> HUBSPOT_API_KEY=<dev> pytest -m integration
after the demo token + DEV_PORTAL_ID are set. No live calls happen otherwise.
Verified against Confluence Listings schema 2026-10-06; not verified against demo portal.
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
from app.services.matching import find_matching_listings

pytestmark = pytest.mark.integration

HUBSPOT_BASE = "https://api.hubapi.com"
LISTINGS_OBJECT_ID = "0-420"
TIMEOUT = 30.0
TEST_PREFIX = "TEST-"
SKIP_REASON = "HS_DEV_TOKEN not set — FS-70 live listings match needs the dev tenant token."


def _run(coro):
    return asyncio.run(coro)


class _DevClient:
    def __init__(self, token: str):
        self._h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def portal_id(self) -> int:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.get(f"{HUBSPOT_BASE}/account-info/v3/details", headers=self._h)
            r.raise_for_status()
            return r.json().get("portalId")

    async def create(self, object_id: str, properties: Dict[str, Any]) -> str:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.post(f"{HUBSPOT_BASE}/crm/v3/objects/{object_id}",
                             headers=self._h, json={"properties": properties})
            r.raise_for_status()
            return r.json()["id"]

    async def archive(self, object_id: str, record_id: str) -> None:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.delete(f"{HUBSPOT_BASE}/crm/v3/objects/{object_id}/{record_id}", headers=self._h)
            if r.status_code not in (200, 204, 404):
                r.raise_for_status()


@pytest.fixture(scope="module")
def dev_session():
    token = os.getenv("HS_DEV_TOKEN")
    if not token:
        pytest.skip(SKIP_REASON)
    client = _DevClient(token)
    portal = _run(client.portal_id())
    if portal in FORBIDDEN_PORTAL_IDS:
        pytest.fail(f"Refusing to run: token resolves to forbidden portal {portal}.", pytrace=False)
    if DEV_PORTAL_ID is None or portal != DEV_PORTAL_ID:
        pytest.fail(f"Refusing to run: token portal {portal} != DEV_PORTAL_ID={DEV_PORTAL_ID}.", pytrace=False)

    created: List[tuple] = []
    try:
        yield {"client": client, "created": created, "run_id": f"{int(time.time())}-{uuid.uuid4().hex[:6]}"}
    finally:
        for object_id, record_id in reversed(created):
            try:
                _run(client.archive(object_id, record_id))
            except Exception:  # noqa: BLE001 — teardown is best-effort
                pass


def test_live_match_ranks_stronger_fit_first(dev_session):
    client = dev_session["client"]
    created = dev_session["created"]
    run = dev_session["run_id"]

    # Strong fit: on-type, good headroom, has garden + parking.
    strong = _run(client.create(LISTINGS_OBJECT_ID, {
        "hs_name": f"{TEST_PREFIX}{run} strong", "hs_address_1": f"{TEST_PREFIX}{run} 1 Strong Rd",
        "hs_price": "2000000", "hs_bedrooms": "3", "hs_listing_type": "house",
        "listing_status": "available_for_sale", "off_market": "false",
        "outside_space": "garden", "parking": "true", "area": "chelsea",
    }))
    created.append((LISTINGS_OBJECT_ID, strong))
    # Weak fit: near ceiling, wrong type, no features.
    weak = _run(client.create(LISTINGS_OBJECT_ID, {
        "hs_name": f"{TEST_PREFIX}{run} weak", "hs_address_1": f"{TEST_PREFIX}{run} 2 Weak Rd",
        "hs_price": "3100000", "hs_bedrooms": "3", "hs_listing_type": "apartment",
        "listing_status": "available_for_sale", "off_market": "false",
        "outside_space": "none", "parking": "false", "area": "other",
    }))
    created.append((LISTINGS_OBJECT_ID, weak))

    buyer = {
        "budget": "up_to_3m", "beds_required": "3_plus", "property_types": ["house"],
        "outside_space": ["garden"], "parking": True, "area": ["chelsea"],
    }
    # Use a high limit so both survive unranked OR, if the tenant has many
    # listings, ranking applies; either way compare our two records' order.
    results = _run(find_matching_listings(buyer, limit=50))

    order = [m["property_id"] for m in results]
    assert strong in order and weak in order, f"our TEST- listings missing: {order}"
    assert order.index(strong) < order.index(weak), "strong-fit listing should rank before weak-fit"
