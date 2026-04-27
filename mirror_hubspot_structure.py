"""
mirror_hubspot_structure.py — M3 prep utility (one-shot, run manually)

Mirrors Curtis Sloane's 13 custom Contact properties into the FutureSynch
HubSpot dev account via the HubSpot CRM v3 Properties API.

Reads HUBSPOT_API_KEY from .env in the project root. The token MUST belong to
FutureSynch (app-eu1.hubspot.com, account 148226118), NOT Curtis Sloane.

Idempotent:
  - GET each property by internal name
  - 404 → POST to create
  - 200 with matching type/fieldType/options → skip (counted as "existed")
  - 200 with mismatched config → warn, skip (never overwrites or deletes)

Run from project root:
    python mirror_hubspot_structure.py

Notes on schema fidelity vs Curtis Sloane source:
  * Internal property names are preserved exactly, including the trailing-
    underscore quirks ("property_to_sell_", "when_are_you_thinking_of_moving_")
    and the "Suppresed" typo in PIPELINE STATUS option labels.
  * Multi-checkbox option *internal* names in source are random IDs
    (e.g. "eVBDCMcqw9xhXNH8IfA5U"). Per handover, we use readable
    snake_case values here — labels remain identical to source.
  * Property groups: contactinformation and contactinformation are HubSpot
    built-ins. Curtis Sloane's MINIMUM SIZE SQFT lives in a custom group
    "minimum_size"; we collapse that into contactinformation so this script
    does not depend on creating a group object first.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv

HUBSPOT_BASE = "https://api.hubapi.com"
TIMEOUT = 15.0


# ---------------------------------------------------------------------------
# Property specs — mirrors Curtis Sloane's 13 custom Contact properties.
# Order matches the handover doc (1..13).
# ---------------------------------------------------------------------------

PROPERTIES: List[Dict[str, Any]] = [
    # 1. BUDGET — dropdown, property-price tier (prime London market)
    {
        "name":      "budget",
        "label":     "Budget",
        "type":      "enumeration",
        "fieldType": "select",
        "groupName": "contactinformation",
        "options": [
            {"label": "Up to 1M",  "value": "up_to_1m",  "displayOrder": 0},
            {"label": "Up to 2M",  "value": "up_to_2m",  "displayOrder": 1},
            {"label": "Up to 3M",  "value": "up_to_3m",  "displayOrder": 2},
            {"label": "Up to 4M",  "value": "up_to_4m",  "displayOrder": 3},
            {"label": "Up to 5M",  "value": "up_to_5m",  "displayOrder": 4},
            {"label": "Up to 6M",  "value": "up_to_6m",  "displayOrder": 5},
            {"label": "Up to 7M",  "value": "up_to_7m",  "displayOrder": 6},
            {"label": "Up to 8M",  "value": "up_to_8m",  "displayOrder": 7},
            {"label": "Up to 9M",  "value": "up_to_9m",  "displayOrder": 8},
            {"label": "Up to 10M", "value": "up_to_10m", "displayOrder": 9},
            {"label": "10+",       "value": "ten_plus",  "displayOrder": 10},
        ],
    },

    # 2. BUYER STATUS
    {
        "name":      "buyer_status",
        "label":     "Buyer Status",
        "type":      "enumeration",
        "fieldType": "select",
        "groupName": "contactinformation",
        "options": [
            {"label": "Passive Buyer",   "value": "passive_buyer",   "displayOrder": 0},
            {"label": "Motivated Buyer", "value": "motivated_buyer", "displayOrder": 1},
            {"label": "Priority Buyer",  "value": "priority_buyer",  "displayOrder": 2},
        ],
    },

    # 3. CONTACT STATUS — note: Curtis Sloane group "contactinformation" (built-in)
    {
        "name":      "contact_status",
        "label":     "Contact Status",
        "type":      "enumeration",
        "fieldType": "select",
        "groupName": "contactinformation",
        "options": [
            {"label": "Active",        "value": "active",         "displayOrder": 0},
            {"label": "Inactive",      "value": "inactive",       "displayOrder": 1},
            {"label": "Pending",       "value": "pending",        "displayOrder": 2},
            {"label": "Dormant",       "value": "dormant",        "displayOrder": 3},
            {"label": "Non-Marketing", "value": "non_marketing",  "displayOrder": 4},
            {"label": "Archived",      "value": "archived",       "displayOrder": 5},
        ],
    },

    # 4. DREAM HOME NOTES
    {
        "name":      "dream_home_notes",
        "label":     "Dream Home Notes",
        "type":      "string",
        "fieldType": "textarea",
        "groupName": "contactinformation",
    },

    # 5. LOOKING TO SELL — enumeration used as boolean (source values "true"/"false")
    {
        "name":      "looking_to_sell",
        "label":     "Looking to Sell",
        "type":      "enumeration",
        "fieldType": "select",
        "groupName": "contactinformation",
        "options": [
            {"label": "Yes", "value": "true",  "displayOrder": 0},
            {"label": "No",  "value": "false", "displayOrder": 1},
        ],
    },

    # 6. MINIMUM SIZE SQFT — source group "minimum_size" collapsed to contactinformation
    {
        "name":      "minimum_size_sqft",
        "label":     "Minimum Size Sqft",
        "type":      "number",
        "fieldType": "number",
        "groupName": "contactinformation",
    },

    # 7. NOTES
    {
        "name":      "notes",
        "label":     "Notes",
        "type":      "string",
        "fieldType": "textarea",
        "groupName": "contactinformation",
    },

    # 8. PIPELINE STATUS — preserve "Suppresed" typo from source exactly
    {
        "name":      "pipeline_status",
        "label":     "Pipeline Status",
        "type":      "enumeration",
        "fieldType": "select",
        "groupName": "contactinformation",
        "options": [
            {"label": "Active Buyer",        "value": "active_buyer",        "displayOrder": 0},
            {"label": "Nurture",             "value": "nurture",             "displayOrder": 1},
            {"label": "Re-engage",           "value": "re_engage",           "displayOrder": 2},
            {"label": "Suppresed",           "value": "suppresed",           "displayOrder": 3},
            {"label": "Attempting Contact", "value": "attempting_contact",  "displayOrder": 4},
            {"label": "Viewing Booked",      "value": "viewing_booked",      "displayOrder": 5},
            {"label": "Rental Enquiry",      "value": "rental_enquiry",      "displayOrder": 6},
        ],
    },

    # 9. PROPERTY TO SELL? — single-checkbox boolean (note trailing underscore in name)
    {
        "name":      "property_to_sell_",
        "label":     "Property to Sell?",
        "type":      "bool",
        "fieldType": "booleancheckbox",
        "groupName": "contactinformation",
        "options": [
            {"label": "Yes", "value": "true",  "displayOrder": 0},
            {"label": "No",  "value": "false", "displayOrder": 1},
        ],
    },

    # 10. TIMELINE — multi-checkbox; source option ids are random, we use readable values
    {
        "name":      "timeline",
        "label":     "Timeline",
        "type":      "enumeration",
        "fieldType": "checkbox",
        "groupName": "contactinformation",
        "options": [
            {"label": "As soon as possible", "value": "as_soon_as_possible", "displayOrder": 0},
            {"label": "Within 3 months",     "value": "within_3_months",     "displayOrder": 1},
            {"label": "3-6 months",          "value": "3_6_months",          "displayOrder": 2},
            {"label": "6-12 months",         "value": "6_12_months",         "displayOrder": 3},
            {"label": "Still Dreaming",      "value": "still_dreaming",      "displayOrder": 4},
        ],
    },

    # 11. TYPE OF CUSTOMER — Curtis Sloane's primary segmentation field (81% fill)
    {
        "name":      "type_of_customer",
        "label":     "Type of Customer",
        "type":      "enumeration",
        "fieldType": "select",
        "groupName": "contactinformation",
        "options": [
            {"label": "Agent",     "value": "agent",     "displayOrder": 0},
            {"label": "Applicant", "value": "applicant", "displayOrder": 1},
            {"label": "Client",    "value": "client",    "displayOrder": 2},
            {"label": "Landlord",  "value": "landlord",  "displayOrder": 3},
            {"label": "Solicitor", "value": "solicitor", "displayOrder": 4},
            {"label": "Supplier",  "value": "supplier",  "displayOrder": 5},
            {"label": "Tenant",    "value": "tenant",    "displayOrder": 6},
        ],
    },

    # 12. WHEN ARE YOU THINKING OF MOVING? — note trailing underscore in name
    {
        "name":      "when_are_you_thinking_of_moving_",
        "label":     "When Are You Thinking of Moving?",
        "type":      "enumeration",
        "fieldType": "select",
        "groupName": "contactinformation",
        "options": [
            {"label": "Yes",   "value": "yes",   "displayOrder": 0},
            {"label": "No",    "value": "no",    "displayOrder": 1},
            {"label": "Maybe", "value": "maybe", "displayOrder": 2},
        ],
    },

    # 13. WILLING TO DO WORKS — multi-checkbox, readable option values
    {
        "name":      "willing_to_do_works",
        "label":     "Willing to Do Works",
        "type":      "enumeration",
        "fieldType": "checkbox",
        "groupName": "contactinformation",
        "options": [
            {"label": "No",                       "value": "no",                       "displayOrder": 0},
            {"label": "Yes",                      "value": "yes",                      "displayOrder": 1},
            {"label": "Cosmetic works only",      "value": "cosmetic_works_only",      "displayOrder": 2},
            {"label": "Full renovation project", "value": "full_renovation_project",  "displayOrder": 3},
            {"label": "No preferences",           "value": "no_preferences",           "displayOrder": 4},
        ],
    },
]


# ---------------------------------------------------------------------------
# HubSpot client helpers
# ---------------------------------------------------------------------------

def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }


def _option_set(options: Optional[List[Dict[str, Any]]]) -> set:
    """Reduce options to a comparable set of (label, value) pairs."""
    if not options:
        return set()
    return {(o.get("label"), o.get("value")) for o in options}


def _config_matches(spec: Dict[str, Any], remote: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Compare the fields we care about between local spec and remote property.
    Returns (matches, reason_if_not).
    """
    if remote.get("type") != spec.get("type"):
        return False, f"type differs (local={spec['type']}, remote={remote.get('type')})"
    if remote.get("fieldType") != spec.get("fieldType"):
        return False, (
            f"fieldType differs "
            f"(local={spec['fieldType']}, remote={remote.get('fieldType')})"
        )
    if "options" in spec:
        if _option_set(spec["options"]) != _option_set(remote.get("options")):
            return False, "options differ"
    return True, ""


def get_property(client: httpx.Client, token: str, name: str) -> Optional[Dict[str, Any]]:
    """Returns the property dict if it exists, None if 404."""
    r = client.get(
        f"{HUBSPOT_BASE}/crm/v3/properties/contacts/{name}",
        headers=_headers(token),
    )
    if r.status_code == 404:
        return None
    if r.status_code == 401:
        raise SystemExit("HubSpot returned 401 Unauthorized — check HUBSPOT_API_KEY in .env")
    if r.status_code >= 400:
        raise httpx.HTTPStatusError(
            f"GET {name} failed: {r.status_code} {r.text}",
            request=r.request, response=r,
        )
    return r.json()


def create_property(client: httpx.Client, token: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    r = client.post(
        f"{HUBSPOT_BASE}/crm/v3/properties/contacts",
        headers=_headers(token),
        json=spec,
    )
    if r.status_code >= 400:
        raise httpx.HTTPStatusError(
            f"POST {spec['name']} failed: {r.status_code} {r.text}",
            request=r.request, response=r,
        )
    return r.json()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    load_dotenv()
    token = os.getenv("HUBSPOT_API_KEY")
    if not token:
        print("ERROR: HUBSPOT_API_KEY not set (check .env in project root).", file=sys.stderr)
        return 1

    print(f"Mirroring {len(PROPERTIES)} custom Contact properties into HubSpot…")
    print(f"Endpoint: {HUBSPOT_BASE}/crm/v3/properties/contacts")
    print("-" * 72)

    created: List[str] = []
    existed: List[str] = []
    mismatched: List[Tuple[str, str]] = []
    failed: List[Tuple[str, str]] = []

    with httpx.Client(timeout=TIMEOUT) as client:
        for spec in PROPERTIES:
            name = spec["name"]
            try:
                remote = get_property(client, token, name)
                if remote is None:
                    create_property(client, token, spec)
                    created.append(name)
                    print(f"  [CREATED] {name}")
                else:
                    matches, reason = _config_matches(spec, remote)
                    if matches:
                        existed.append(name)
                        print(f"  [EXISTS ] {name}")
                    else:
                        mismatched.append((name, reason))
                        print(f"  [WARN   ] {name} — exists with different config: {reason} (skipped)")
            except SystemExit:
                raise
            except Exception as exc:
                failed.append((name, str(exc)))
                print(f"  [FAILED ] {name} — {exc}")

    print("-" * 72)
    print(f"Summary: created={len(created)}  existed={len(existed)}  "
          f"mismatched={len(mismatched)}  failed={len(failed)}")
    if mismatched:
        print("\nMismatched (NOT overwritten):")
        for n, why in mismatched:
            print(f"  - {n}: {why}")
    if failed:
        print("\nFailed:")
        for n, err in failed:
            print(f"  - {n}: {err}")

    return 0 if not failed else 2


if __name__ == "__main__":
    sys.exit(main())
