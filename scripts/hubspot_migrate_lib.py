"""
hubspot_migrate_lib.py — shared plumbing for the Contacts schema migrations.

Guards, HubSpot v3 Properties API wrappers, and the diff logic both scripts
use. Kept separate so the two migration scripts contain only the decisions
about what to change, not the mechanics of changing it.

Nothing in this module knows which tenant it is talking to. The caller passes
the expected portal ID and the module refuses to proceed on a mismatch.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import httpx

from contacts_schema import (
    ASSUMED_PRESENT,
    CANONICAL_PROPERTIES,
    FORBIDDEN_PORTAL_IDS,
    OPEN_DECISIONS,
    RETIRED_OPTION_VALUES,
)

HUBSPOT_BASE = "https://api.hubapi.com"
TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# Token and tenant guards
# ---------------------------------------------------------------------------

def read_token(env_var: str) -> str:
    """
    Read the API token from a NAMED environment variable.

    The variable name is always passed explicitly by the caller and always
    identifies its tenant. There is no fallback to a generic name.

    A bare HUBSPOT_TOKEN has held the Curtis Sloane production token on this
    project before now. Reading whatever happens to be in the environment is
    how a dev migration becomes a production incident.
    """
    token = os.environ.get(env_var)
    if not token:
        sys.exit(
            f"ERROR: {env_var} is not set.\n"
            f"       Export the token for this tenant under that exact name.\n"
            f"       Do not substitute a generic HUBSPOT_TOKEN."
        )
    return token.strip()


def headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def assert_correct_tenant(client: httpx.Client, token: str, expected_portal_id: int) -> int:
    """
    First network call of any run. Session level, not per operation.

    Aborts unconditionally on a Curtis Sloane production token regardless of
    what was expected, then aborts on any portal that is not the expected one.
    A misconfigured token fails once, here, before anything is written.
    """
    r = client.get(f"{HUBSPOT_BASE}/account-info/v3/details", headers=headers(token))
    if r.status_code == 401:
        sys.exit("ERROR: token rejected (401). Check the value, not the name.")
    r.raise_for_status()
    portal_id = int(r.json()["portalId"])

    if portal_id in FORBIDDEN_PORTAL_IDS:
        sys.exit(
            f"ABORT: token resolves to portal {portal_id}, which is Curtis Sloane\n"
            f"       production. Schema migrations never run there. FS-25 standing rule.\n"
            f"       No request has been made beyond this check."
        )

    if portal_id != expected_portal_id:
        sys.exit(
            f"ABORT: token resolves to portal {portal_id}, expected {expected_portal_id}.\n"
            f"       If you meant to target {portal_id}, change the constant in the\n"
            f"       script deliberately rather than relaxing this check."
        )

    print(f"  Tenant guard OK: portal {portal_id}")
    return portal_id


# ---------------------------------------------------------------------------
# Properties API
# ---------------------------------------------------------------------------

def get_property(client: httpx.Client, token: str, name: str) -> Optional[Dict[str, Any]]:
    r = client.get(
        f"{HUBSPOT_BASE}/crm/v3/properties/contacts/{name}", headers=headers(token)
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def list_custom_properties(client: httpx.Client, token: str) -> List[Dict[str, Any]]:
    """
    Every non-system Contact property.

    hubspotDefined and the hs_ prefix are both reliable markers of HubSpot's
    own properties. Neither alone is sufficient, so both are applied.
    """
    r = client.get(f"{HUBSPOT_BASE}/crm/v3/properties/contacts", headers=headers(token))
    r.raise_for_status()
    return [
        p
        for p in r.json().get("results", [])
        if not p.get("hubspotDefined") and not p["name"].startswith("hs_")
    ]


def create_property(client: httpx.Client, token: str, spec: Dict[str, Any]) -> None:
    r = client.post(
        f"{HUBSPOT_BASE}/crm/v3/properties/contacts",
        headers=headers(token),
        json=spec,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"create {spec['name']} failed {r.status_code}: {r.text}")


def patch_property(
    client: httpx.Client, token: str, name: str, body: Dict[str, Any]
) -> None:
    r = client.patch(
        f"{HUBSPOT_BASE}/crm/v3/properties/contacts/{name}",
        headers=headers(token),
        json=body,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"patch {name} failed {r.status_code}: {r.text}")


def delete_property(client: httpx.Client, token: str, name: str) -> None:
    r = client.delete(
        f"{HUBSPOT_BASE}/crm/v3/properties/contacts/{name}", headers=headers(token)
    )
    if r.status_code not in (204, 404):
        raise RuntimeError(f"delete {name} failed {r.status_code}: {r.text}")


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def option_pairs(options: Optional[List[Dict[str, Any]]]) -> List[Tuple[str, str]]:
    """
    (label, value) pairs in displayOrder.

    Compared as an ordered list rather than a set. Order is user-visible in
    HubSpot's dropdowns, so a reordered set is a real difference even though
    the values are identical.
    """
    if not options:
        return []
    ordered = sorted(options, key=lambda o: o.get("displayOrder", 0))
    return [(o["label"], o["value"]) for o in ordered]


def diff_property(spec: Dict[str, Any], remote: Dict[str, Any]) -> List[str]:
    """Return a list of human-readable differences. Empty means conformant."""
    diffs: List[str] = []

    for key in ("type", "fieldType"):
        if spec.get(key) != remote.get(key):
            diffs.append(f"{key}: {remote.get(key)!r} -> {spec.get(key)!r}")

    if spec.get("label") != remote.get("label"):
        diffs.append(f"label: {remote.get('label')!r} -> {spec.get('label')!r}")

    want = option_pairs(spec.get("options"))
    have = option_pairs(remote.get("options"))
    if want != have:
        want_v = [v for _, v in want]
        have_v = [v for _, v in have]
        added = [v for v in want_v if v not in have_v]
        removed = [v for v in have_v if v not in want_v]
        if added or removed:
            parts = []
            if removed:
                parts.append(f"retires {removed}")
            if added:
                parts.append(f"adds {added}")
            diffs.append("options: " + ", ".join(parts))
        else:
            diffs.append("options: labels or order differ")

    return diffs


def requires_recreate(spec: Dict[str, Any], remote: Dict[str, Any]) -> bool:
    """
    fieldType and type are immutable in the v3 Properties API. Changing either
    means delete and recreate, which destroys any data held in the property.
    Everything else, including option sets, can be PATCHed in place.
    """
    return (
        spec.get("fieldType") != remote.get("fieldType")
        or spec.get("type") != remote.get("type")
    )


# ---------------------------------------------------------------------------
# Data safety
# ---------------------------------------------------------------------------

def count_records_holding_retired_values(
    client: httpx.Client, token: str, prop: str, retired: Dict[str, Optional[str]]
) -> Dict[str, int]:
    """
    Count contacts holding an option value the new schema no longer offers.

    HubSpot does not reject a record whose stored value is no longer a valid
    option. It keeps the value and renders it oddly in the UI. That is worse
    than an error, because nothing surfaces it. Counting first means the
    operator sees the blast radius before agreeing to it.
    """
    counts: Dict[str, int] = {}
    for value in retired:
        r = client.post(
            f"{HUBSPOT_BASE}/crm/v3/objects/contacts/search",
            headers=headers(token),
            json={
                "filterGroups": [
                    {"filters": [{"propertyName": prop, "operator": "EQ", "value": value}]}
                ],
                "limit": 1,
            },
        )
        if r.status_code >= 400:
            counts[value] = -1  # unknown; surfaced as such by the caller
        else:
            counts[value] = int(r.json().get("total", 0))
    return counts


def remap_retired_values(
    client: httpx.Client,
    token: str,
    prop: str,
    retired: Dict[str, Optional[str]],
    apply: bool,
) -> None:
    """
    Rewrite records holding a retired value to its decided successor.

    Values with no successor (None) are reported and left alone. Guessing a
    replacement for a concept Olesya deliberately dropped would put an
    invented answer into the client's CRM.
    """
    for old, new in retired.items():
        if new is None:
            print(f"    {old}: no successor decided, records left unchanged")
            continue

        after: Optional[str] = None
        moved = 0
        while True:
            body: Dict[str, Any] = {
                "filterGroups": [
                    {"filters": [{"propertyName": prop, "operator": "EQ", "value": old}]}
                ],
                "properties": [prop],
                "limit": 100,
            }
            if after:
                body["after"] = after
            r = client.post(
                f"{HUBSPOT_BASE}/crm/v3/objects/contacts/search",
                headers=headers(token),
                json=body,
            )
            r.raise_for_status()
            payload = r.json()
            results = payload.get("results", [])
            if not results:
                break

            batch = [{"id": rec["id"], "properties": {prop: new}} for rec in results]
            if apply:
                u = client.post(
                    f"{HUBSPOT_BASE}/crm/v3/objects/contacts/batch/update",
                    headers=headers(token),
                    json={"inputs": batch},
                )
                if u.status_code >= 400:
                    raise RuntimeError(f"batch update failed {u.status_code}: {u.text}")
            moved += len(batch)

            after = payload.get("paging", {}).get("next", {}).get("after")
            if not after:
                break

        verb = "remapped" if apply else "would remap"
        print(f"    {old} -> {new}: {verb} {moved} record(s)")


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_open_decisions() -> None:
    print("\nOPEN DECISIONS not encoded by this script:")
    for item in OPEN_DECISIONS:
        print(f"  - {item}")


def verify(client: httpx.Client, token: str, dump_path: Optional[str] = None) -> bool:
    """Confirm the tenant now matches the canonical schema. Returns True if clean."""
    print("\n" + "=" * 72)
    print("VERIFY")
    print("=" * 72)

    remote = {p["name"]: p for p in list_custom_properties(client, token)}
    ok = True

    for spec in CANONICAL_PROPERTIES:
        got = remote.get(spec["name"])
        if got is None:
            print(f"  MISSING  {spec['name']}")
            ok = False
            continue
        diffs = diff_property(spec, got)
        if diffs:
            print(f"  DIFFERS  {spec['name']}: {'; '.join(diffs)}")
            ok = False
        else:
            print(f"  ok       {spec['name']}")

    for name, note in ASSUMED_PRESENT.items():
        if name in remote:
            print(f"  ok       {name} (untouched: {note})")
        else:
            print(f"  MISSING  {name} - expected to exist already. {note}")
            ok = False

    expected = {s["name"] for s in CANONICAL_PROPERTIES} | set(ASSUMED_PRESENT)
    unexpected = sorted(set(remote) - expected)
    if unexpected:
        print(f"\n  {len(unexpected)} property(ies) present but not in the canonical schema:")
        for name in unexpected:
            print(f"    - {name}")
        print("  Not removed automatically. Decide each one deliberately.")

    print(f"\n  Custom properties: {len(remote)}  Canonical: {len(expected)}")

    # Records still holding a value the schema no longer offers.
    for prop, retired in RETIRED_OPTION_VALUES.items():
        if prop in remote:
            counts = count_records_holding_retired_values(client, token, prop, retired)
            stranded = {v: n for v, n in counts.items() if n > 0}
            if stranded:
                print(f"\n  WARNING: {prop} holds retired values in live records: {stranded}")
                print("  HubSpot does not reject these. They will not match anything.")
                ok = False

    if dump_path:
        r = client.get(
            f"{HUBSPOT_BASE}/crm/v3/properties/contacts", headers=headers(token)
        )
        r.raise_for_status()
        with open(dump_path, "w") as fh:
            json.dump(r.json(), fh, indent=2)
        print(f"\n  Schema dumped to {dump_path}")

    print("\n  RESULT: " + ("conformant" if ok else "NOT conformant"))
    return ok
