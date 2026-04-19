"""
HubSpot REST v3 integration.
Account: FutureSynch (synch@futuresynch.com) for M1–M4.
At M5 go-live, HUBSPOT_API_KEY env var swaps to Curtis Sloane's token — no code change.

TS Section 5.2, 5.3, 5.6 — applicant registration, match, KYC lookup.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

log = logging.getLogger(__name__)

HUBSPOT_BASE = "https://api.hubapi.com"
TIMEOUT      = 15.0


# ---------------------------------------------------------------------------
# Custom contact property definitions
# Created idempotently on first boot (lifespan hook in app/main.py).
# Group "contactinformation" is HubSpot's built-in default — always exists.
# ---------------------------------------------------------------------------

_CUSTOM_PROPERTIES: List[Dict[str, Any]] = [
    {
        "name": "applicant_budget_gbp",
        "label": "Applicant Budget (GBP)",
        "description": "Maximum property budget in GBP",
        "type": "number", "fieldType": "number",
        "groupName": "contactinformation",
    },
    {
        "name": "applicant_bedrooms_min",
        "label": "Applicant Bedrooms (Min)",
        "type": "number", "fieldType": "number",
        "groupName": "contactinformation",
    },
    {
        "name": "applicant_bedrooms_max",
        "label": "Applicant Bedrooms (Max)",
        "type": "number", "fieldType": "number",
        "groupName": "contactinformation",
    },
    {
        "name": "applicant_property_types",
        "label": "Applicant Property Types",
        "type": "enumeration", "fieldType": "checkbox",
        "groupName": "contactinformation",
        "options": [
            {"label": "House",      "value": "house",      "displayOrder": 0},
            {"label": "Flat",       "value": "flat",       "displayOrder": 1},
            {"label": "Maisonette", "value": "maisonette", "displayOrder": 2},
            {"label": "Any",        "value": "any",        "displayOrder": 3},
        ],
    },
    {
        "name": "applicant_financing",
        "label": "Applicant Financing",
        "type": "enumeration", "fieldType": "select",
        "groupName": "contactinformation",
        "options": [
            {"label": "Cash",              "value": "cash",             "displayOrder": 0},
            {"label": "Mortgage (AIP)",    "value": "mortgage_aip",     "displayOrder": 1},
            {"label": "Mortgage (no AIP)", "value": "mortgage_no_aip",  "displayOrder": 2},
            {"label": "Unknown",           "value": "unknown",          "displayOrder": 3},
        ],
    },
    {
        "name": "applicant_preferred_channel",
        "label": "Applicant Preferred Channel",
        "type": "enumeration", "fieldType": "select",
        "groupName": "contactinformation",
        "options": [
            {"label": "Email",    "value": "email",    "displayOrder": 0},
            {"label": "Phone",    "value": "phone",    "displayOrder": 1},
            {"label": "WhatsApp", "value": "whatsapp", "displayOrder": 2},
        ],
    },
    {
        "name": "applicant_source",
        "label": "Applicant Source",
        "description": "Where the applicant came from (Rightmove, Zoopla, Referral, etc.)",
        "type": "string", "fieldType": "text",
        "groupName": "contactinformation",
    },
    {
        "name": "applicant_must_have",
        "label": "Applicant Must-Have",
        "type": "string", "fieldType": "textarea",
        "groupName": "contactinformation",
    },
    {
        "name": "applicant_timeline_weeks",
        "label": "Applicant Timeline (Weeks)",
        "type": "number", "fieldType": "number",
        "groupName": "contactinformation",
    },
    {
        "name": "kyc_status",
        "label": "KYC Status",
        "type": "enumeration", "fieldType": "select",
        "groupName": "contactinformation",
        "options": [
            {"label": "Complete",    "value": "complete",     "displayOrder": 0},
            {"label": "In Progress", "value": "in_progress",  "displayOrder": 1},
            {"label": "Outstanding", "value": "outstanding",  "displayOrder": 2},
            {"label": "Not Started", "value": "not_started",  "displayOrder": 3},
        ],
    },
    {
        "name": "kyc_documents_outstanding",
        "label": "KYC Documents Outstanding",
        "description": "Semicolon-separated list of missing KYC documents",
        "type": "string", "fieldType": "textarea",
        "groupName": "contactinformation",
    },
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _headers() -> Dict[str, str]:
    token = os.getenv("HUBSPOT_API_KEY")
    if not token:
        raise RuntimeError("HUBSPOT_API_KEY is not set")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }


class HubSpotError(Exception):
    """Raised when HubSpot returns a non-2xx response."""


# ---------------------------------------------------------------------------
# Property bootstrap
# ---------------------------------------------------------------------------

async def ensure_custom_properties() -> Dict[str, int]:
    """
    Create any missing custom contact properties. Idempotent — safe on every boot.
    Returns counts: {"created": N, "existed": M, "failed": K}
    """
    created = existed = failed = 0

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(
            f"{HUBSPOT_BASE}/crm/v3/properties/contacts",
            headers=_headers(),
        )
        r.raise_for_status()
        existing_names = {p["name"] for p in r.json().get("results", [])}

        for spec in _CUSTOM_PROPERTIES:
            if spec["name"] in existing_names:
                existed += 1
                continue
            try:
                resp = await client.post(
                    f"{HUBSPOT_BASE}/crm/v3/properties/contacts",
                    headers=_headers(),
                    json=spec,
                )
                resp.raise_for_status()
                created += 1
                log.info("HubSpot property created: %s", spec["name"])
            except Exception as exc:
                failed += 1
                log.warning("Failed to create %s: %s", spec["name"], exc)

    return {"created": created, "existed": existed, "failed": failed}


# ---------------------------------------------------------------------------
# Contact CRUD
# ---------------------------------------------------------------------------

async def create_contact(properties: Dict[str, Any]) -> Dict[str, Any]:
    """POST /crm/v3/objects/contacts — returns the created contact record."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            f"{HUBSPOT_BASE}/crm/v3/objects/contacts",
            headers=_headers(),
            json={"properties": properties},
        )
        if r.status_code >= 400:
            raise HubSpotError(f"{r.status_code}: {r.text}")
        return r.json()


async def search_contacts(
    filter_groups: Optional[List[Dict[str, Any]]] = None,
    properties: Optional[List[str]] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """POST /crm/v3/objects/contacts/search — returns list of matches."""
    payload: Dict[str, Any] = {
        "filterGroups": filter_groups or [],
        "properties":   properties or ["firstname", "lastname", "email", "phone"],
        "limit":        limit,
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            f"{HUBSPOT_BASE}/crm/v3/objects/contacts/search",
            headers=_headers(),
            json=payload,
        )
        if r.status_code >= 400:
            raise HubSpotError(f"{r.status_code}: {r.text}")
        return r.json().get("results", [])


# All applicant-related properties we read back on match/kyc lookups
APPLICANT_READ_PROPS = [
    "firstname", "lastname", "email", "phone",
    "applicant_budget_gbp", "applicant_bedrooms_min", "applicant_bedrooms_max",
    "applicant_property_types", "applicant_financing", "applicant_preferred_channel",
    "applicant_source", "applicant_must_have", "applicant_timeline_weeks",
    "kyc_status", "kyc_documents_outstanding",
]


async def find_contact_by_name_or_email(query: str) -> Optional[Dict[str, Any]]:
    """Look up a contact by exact email match or by firstname+lastname."""
    query = query.strip()
    if "@" in query:
        filters = [{"propertyName": "email", "operator": "EQ", "value": query}]
    else:
        parts = query.split()
        if len(parts) == 1:
            filters = [{"propertyName": "firstname", "operator": "EQ", "value": parts[0]}]
        else:
            filters = [
                {"propertyName": "firstname", "operator": "EQ", "value": parts[0]},
                {"propertyName": "lastname",  "operator": "EQ", "value": parts[-1]},
            ]

    results = await search_contacts(
        filter_groups=[{"filters": filters}],
        properties=APPLICANT_READ_PROPS,
        limit=1,
    )
    return results[0] if results else None


async def list_applicant_contacts(
    max_budget: Optional[int] = None,
    min_bedrooms: Optional[int] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Return applicants (contacts with applicant_source set), optionally filtered."""
    filters: List[Dict[str, Any]] = [
        {"propertyName": "applicant_source", "operator": "HAS_PROPERTY"},
    ]
    if max_budget is not None:
        filters.append({
            "propertyName": "applicant_budget_gbp",
            "operator":     "GTE",
            "value":        max_budget,
        })
    if min_bedrooms is not None:
        filters.append({
            "propertyName": "applicant_bedrooms_min",
            "operator":     "LTE",
            "value":        min_bedrooms,
        })

    return await search_contacts(
        filter_groups=[{"filters": filters}],
        properties=APPLICANT_READ_PROPS,
        limit=limit,
    )
