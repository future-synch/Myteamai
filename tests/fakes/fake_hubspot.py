"""
FS-50 — Fake HubSpot client for the unit suite.

Satisfies the HubspotClient protocol from app.services.hubspot_registration
without touching the network. Records every call for assertion, and can
be configured to simulate specific error modes for §7 scenarios.
"""
from __future__ import annotations

from typing import Any

from app.constants.registration_constants import DEV_PORTAL_ID
from app.services.hubspot_registration import HubspotError, HubspotTimeoutError


class FakeHubspotClient:
    """
    In-memory HubSpot double.

    Usage:
        client = FakeHubspotClient(portal_id=DEV_PORTAL_ID)
        # optionally pre-queue simulated errors before the call under test:
        client.queue_error(503)                    # one 503, then success
        client.queue_error(429, retry_after=1)     # 429 with Retry-After
        client.queue_timeout()                     # a bare timeout
        client.queue_missing_property("budget")    # missing-property 400

        contact_id = await register_applicant_in_hubspot(criteria, client)

        # inspection:
        assert client.calls[-1]["endpoint"] == "create_contact"
        assert client.contacts[contact_id]["email"] == "sarah@example.com"
    """

    def __init__(self, portal_id: int = DEV_PORTAL_ID):
        self.portal_id: int = portal_id
        self._contacts: dict[str, dict[str, Any]] = {}
        self._next_id: int = 1000
        self._error_queue: list[tuple] = []
        self.calls: list[dict[str, Any]] = []

    # ---- Error mode configuration (test-only) --------------------------

    def queue_error(self, status_code: int, retry_after: int | None = None) -> None:
        """Queue a simulated HTTP error for the next create_contact call."""
        self._error_queue.append(("HTTP", status_code, retry_after, None))

    def queue_timeout(self) -> None:
        """Queue a simulated timeout for the next create_contact call."""
        self._error_queue.append(("TIMEOUT", None, None, None))

    def queue_missing_property(self, property_name: str) -> None:
        """Queue a simulated 'property does not exist' 400 for next call."""
        self._error_queue.append(("MISSING_PROP", 400, None, property_name))

    # ---- HubspotClient protocol ---------------------------------------

    async def get_portal_info(self) -> dict[str, Any]:
        self.calls.append({"endpoint": "get_portal_info"})
        return {"portalId": self.portal_id}

    async def create_contact(self, properties: dict[str, Any]) -> dict[str, Any]:
        # Copy so external mutation of `properties` doesn't affect our record.
        self.calls.append({
            "endpoint":   "create_contact",
            "properties": dict(properties),
        })

        if self._error_queue:
            kind, code, retry_after, prop_name = self._error_queue.pop(0)
            if kind == "TIMEOUT":
                raise HubspotTimeoutError("simulated timeout")
            if kind == "MISSING_PROP":
                raise HubspotError(
                    code,
                    f"property '{prop_name}' does not exist",
                    missing_property=prop_name,
                )
            raise HubspotError(code, f"simulated {code}", retry_after=retry_after)

        # Success path — assign an id, store the properties byte-for-byte
        contact_id = str(self._next_id)
        self._next_id += 1
        self._contacts[contact_id] = dict(properties)
        return {"id": contact_id, "properties": dict(properties)}

    # ---- Inspection helpers (test-only) --------------------------------

    @property
    def contacts(self) -> dict[str, dict[str, Any]]:
        """Snapshot of all created contacts, keyed by id."""
        return {k: dict(v) for k, v in self._contacts.items()}

    def create_calls(self) -> list[dict[str, Any]]:
        """All create_contact call records, in order."""
        return [c for c in self.calls if c["endpoint"] == "create_contact"]

    def any_create_attempted(self) -> bool:
        return len(self.create_calls()) > 0
