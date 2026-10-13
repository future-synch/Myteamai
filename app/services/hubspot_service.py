"""
HubSpot REST v3 integration.
Account: FutureSynch (synch@futuresynch.com) for M1–M4.
At M5 go-live, HUBSPOT_API_KEY env var swaps to Curtis Sloane's token — no code change.

TS Section 5.2, 5.3, 5.6 — applicant registration, match, KYC lookup.
"""

from __future__ import annotations

import logging
import os
import re
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
# FS-67: the dev/test tenant's Contacts schema is provisioned out-of-band from
# the definitive Confluence schema ("Contacts schema definitive", page 74907651).
# The app no longer bootstraps contact properties — doing so against the dev
# tenant risked re-creating stale, pre-FS-44 applicant_*/kyc_* properties (now
# deleted from the schema) and drifting option sets away from the source of
# truth. ensure_custom_properties() is therefore a no-op (see below). This list
# is intentionally empty; property definitions live in HubSpot, not in code.
_CUSTOM_PROPERTIES: List[Dict[str, Any]] = []


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
    No-op since FS-67. The dev/test tenant's Contacts schema is managed
    out-of-band from the definitive Confluence schema (page 74907651); the app
    must never create contact properties at startup — doing so previously
    re-created stale pre-FS-44 applicant_*/kyc_* properties against the dev
    tenant. Kept callable so the app/main.py lifespan hook stays harmless.

    Performs NO network I/O. Returns {"created": 0, "existed": 0, "failed": 0}.
    """
    log.info(
        "ensure_custom_properties: no-op (contact schema managed out-of-band per "
        "Confluence page 74907651); no properties created on startup."
    )
    return {"created": 0, "existed": 0, "failed": 0}


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


# ---------------------------------------------------------------------------
# FS-67 read-path parsers / normalisers (importable; reused by FS-70).
# Never raise — unknown/empty/None always return a safe default.
# ---------------------------------------------------------------------------

def _budget_ceiling(value: Optional[str]) -> Optional[int]:
    """
    Numeric upper budget limit (GBP) from a `budget` band:
      up_to_Nm -> N * 1_000_000 ; ten_plus -> None ; unknown/empty/None -> None.
    """
    if not value:
        return None
    m = re.match(r"^up_to_(\d+)m$", str(value).strip().lower())
    if m:
        return int(m.group(1)) * 1_000_000
    # PENDING owner confirmation: ten_plus has no numeric ceiling.
    return None


def _beds_minimum(value: Optional[str]) -> Optional[int]:
    """
    Floor bedroom count from a `beds_required` band:
      N_plus -> N (upper bound unresolved on the schema, which is fine) ;
      unknown/empty/None -> None.
    """
    if not value:
        return None
    m = re.match(r"^(\d+)_plus$", str(value).strip().lower())
    return int(m.group(1)) if m else None


def _split_multi(value: Optional[str]) -> List[str]:
    """
    Normalise a HubSpot multi-checkbox value (semicolon-separated string) to a
    list. Empty string / None -> [].
    """
    if not value:
        return []
    return [v.strip() for v in str(value).split(";") if v.strip()]


# Applicant properties read on match/kyc lookups.
# Verified against Confluence test_2 snapshot 2026-09-10, NOT yet verified
# against the demo portal. Post-FS-44 schema names. KYC props (kyc_status /
# kyc_documents_outstanding) intentionally absent — moved to the Deal object
# (item A, blocked until the Deals schema + associations exist).
APPLICANT_READ_PROPS = [
    "firstname", "lastname", "email", "phone",
    "type_of_customer", "applicant_status",
    "budget", "beds_required", "property_types",
    "financing_status", "source", "preferred_channel", "timeline",
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
    """
    Return applicants: contacts where type_of_customer='applicant' OR budget is
    set. FS-67: the old server-side numeric filters on applicant_budget_gbp /
    applicant_bedrooms_min are gone — budget/beds_required are enum bands now,
    not numeric, so max_budget/min_bedrooms cannot be filtered server-side. They
    remain in the signature for compatibility; filter client-side on the parsed
    values (_budget_ceiling/_beds_minimum) if needed.
    """
    # OR across filterGroups: applicant by type OR by having a budget band.
    filter_groups = [
        {"filters": [{"propertyName": "type_of_customer", "operator": "EQ", "value": "applicant"}]},
        {"filters": [{"propertyName": "budget", "operator": "HAS_PROPERTY"}]},
    ]
    return await search_contacts(
        filter_groups=filter_groups,
        properties=APPLICANT_READ_PROPS,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# FS-16: Listings custom object + full applicant fetch
# ---------------------------------------------------------------------------

LISTINGS_OBJECT_ID = "0-420"

LISTING_READ_PROPS = [
    "hs_name", "hs_price", "hs_bedrooms", "hs_listing_type",
    "hs_neighborhood", "hs_address_1",
    "postcode", "outside_space", "works_required",
]


async def get_listing_by_address(address: str, token: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Search HubSpot Listings (object 0-420) for a record matching the given
    address string. Returns a normalised dict or None if not found.
    """
    if not (token or os.getenv("HUBSPOT_API_KEY")):
        return None

    headers = _headers() if token is None else {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }

    payload = {
        "filterGroups": [
            {"filters": [{"propertyName": "hs_name", "operator": "CONTAINS_TOKEN", "value": address}]},
            {"filters": [{"propertyName": "hs_address_1", "operator": "CONTAINS_TOKEN", "value": address}]},
        ],
        "properties": LISTING_READ_PROPS,
        "limit":      1,
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            f"{HUBSPOT_BASE}/crm/v3/objects/{LISTINGS_OBJECT_ID}/search",
            headers=headers,
            json=payload,
        )
        if r.status_code >= 400:
            raise HubSpotError(f"{r.status_code}: {r.text}")
        results = r.json().get("results", [])
        if not results:
            return None
        rec = results[0]
        props = rec.get("properties", {})
        return {
            "id":             rec.get("id"),
            "name":           props.get("hs_name") or props.get("hs_address_1"),
            "price_gbp":      props.get("hs_price"),
            "bedrooms":       props.get("hs_bedrooms"),
            "listing_type":   props.get("hs_listing_type"),
            "neighborhood":   props.get("hs_neighborhood"),
            "address_1":      props.get("hs_address_1"),
            "postcode":       props.get("postcode"),
            "outside_space":  props.get("outside_space"),
            "works_required": props.get("works_required"),
        }


APPLICANT_FULL_PROPS = list(APPLICANT_READ_PROPS)  # type_of_customer already included


def _normalise_applicant(props: Dict[str, Any], record_id: Any) -> Dict[str, Any]:
    """
    Map a raw contact `properties` dict (new-schema names) to the stable
    normalised shape fn_match_applicants consumes. Output keys are unchanged from
    the pre-FS-67 shape so fn_match_applicants stays untouched; the only addition
    is the "timeline" key (raw band string, not mapped to weeks).
    """
    return {
        "id":                        record_id,
        "name":                      f"{props.get('firstname') or ''} {props.get('lastname') or ''}".strip(),
        "email":                     props.get("email"),
        "budget_gbp":                _budget_ceiling(props.get("budget")),
        "bedrooms_min":              _beds_minimum(props.get("beds_required")),
        # NO clean new source (beds_required is floor-only) — reported.
        "bedrooms_max":              None,
        # Raw semicolon string kept so fn_match_applicants is untouched;
        # callers wanting a list use _split_multi().
        "property_types":            props.get("property_types"),
        "financing":                 props.get("financing_status"),
        # NO clean new source — FS-16 (Direction 2) needs a proper source:
        # outside_space + parking.
        "must_have":                 None,
        # 'timeline' is a banded enum, not weeks: keep timeline_weeks None and
        # surface the raw band under the additive "timeline" key (not mapped).
        "timeline_weeks":            None,
        "timeline":                  props.get("timeline"),
        # KYC parked — moved to the Deal object (item A, blocked).
        "kyc_status":                None,
        "kyc_documents_outstanding": None,
    }


async def get_all_applicants(token: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch every contact that is an applicant. An applicant is any contact where
    type_of_customer='applicant' OR budget is set. Paginates through HubSpot's
    cursor-based results (limit 100 per page).
    """
    if not (token or os.getenv("HUBSPOT_API_KEY")):
        return []

    headers = _headers() if token is None else {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }

    results: List[Dict[str, Any]] = []
    after: Optional[str] = None
    max_pages = 20  # 20 * 100 = 2000-applicant safety cap

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for _ in range(max_pages):
            payload: Dict[str, Any] = {
                # Match on either signal — HubSpot search supports OR across filterGroups.
                "filterGroups": [
                    {"filters": [{"propertyName": "type_of_customer", "operator": "EQ", "value": "applicant"}]},
                    {"filters": [{"propertyName": "budget", "operator": "HAS_PROPERTY"}]},
                ],
                "properties": APPLICANT_FULL_PROPS,
                "limit":      100,
            }
            if after:
                payload["after"] = after

            r = await client.post(
                f"{HUBSPOT_BASE}/crm/v3/objects/contacts/search",
                headers=headers,
                json=payload,
            )
            if r.status_code >= 400:
                raise HubSpotError(f"{r.status_code}: {r.text}")
            body = r.json()
            for rec in body.get("results", []):
                results.append(_normalise_applicant(rec.get("properties", {}), rec.get("id")))

            paging = body.get("paging", {}).get("next", {})
            after = paging.get("after")
            if not after:
                break

    return results
