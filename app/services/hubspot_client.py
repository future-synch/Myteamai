"""
Production HubSpot client satisfying the HubspotClient protocol used by
register_applicant_in_hubspot() (FS-50).

FS-50 defined the protocol (get_portal_info + create_contact) and a matching
client inside its integration test. FS-55 needs the same client in production
code so the orchestrator can supply it to register_applicant_in_hubspot(). This
module is that lift — the network behaviour mirrors the FS-50 test client
exactly, including translating non-2xx responses into HubspotError with
missing-property detection so the retry/tenant logic in the service keeps
working unchanged.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional

import httpx

from app.services.hubspot_registration import HubspotError

HUBSPOT_BASE = "https://api.hubapi.com"
TIMEOUT = 30.0


def _extract_missing_property(body: str) -> Optional[str]:
    m = re.search(r'[Pp]roperty\s+"([^"]+)"\s+does not exist', body or "")
    return m.group(1) if m else None


def _extract_retry_after(headers: httpx.Headers) -> Optional[int]:
    ra = headers.get("Retry-After")
    try:
        return int(ra) if ra is not None else None
    except (TypeError, ValueError):
        return None


class HubSpotClient:
    """Live HubSpot client. __init__ does not validate the token — the tenant
    guard in register_applicant_in_hubspot() verifies the portal on first call."""

    def __init__(self, token: Optional[str]):
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def get_portal_info(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.get(f"{HUBSPOT_BASE}/account-info/v3/details", headers=self._headers)
            if r.status_code >= 400:
                raise HubspotError(r.status_code, r.text)
            return r.json()

    async def create_contact(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.post(
                f"{HUBSPOT_BASE}/crm/v3/objects/contacts",
                headers=self._headers,
                json={"properties": properties},
            )
            if r.status_code >= 400:
                raise HubspotError(
                    r.status_code,
                    r.text,
                    missing_property=_extract_missing_property(r.text),
                    retry_after=_extract_retry_after(r.headers),
                )
            return r.json()


def build_hubspot_client(token: Optional[str] = None) -> HubSpotClient:
    """
    Construct a HubSpotClient from the app's HubSpot token.

    Uses HUBSPOT_API_KEY (the app-wide var — dev tenant 148226118 now; swaps to
    Curtis Sloane at M5 go-live with no code change). The tenant guard inside
    register_applicant_in_hubspot() is what actually decides whether the bound
    portal is safe to write to.
    """
    return HubSpotClient(token or os.getenv("HUBSPOT_API_KEY"))
