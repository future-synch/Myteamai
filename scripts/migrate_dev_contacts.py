"""
migrate_dev_contacts.py — FS-44 (one-shot, run manually)

TENANT: FutureSynch DEV, portal 148226118
FROM:   the legacy as-built schema (24 custom Contact properties)
TO:     the canonical schema in contacts_schema.py

Successor to migrate_contacts_schema.py. Two things changed:

  1. works_required carries Olesya's five-point scale from 50823188 s1.7
     (Q8, 17 Aug 2026), which supersedes the scale on 42106882. The previous
     script created None / Cosmetic / Modernisation / Full Refurb /
     Development Potential. Three of those five values were wrong.

  2. The schema lives in contacts_schema.py, shared with the sandbox
     migration, so the two tenants cannot drift apart.

DESTRUCTIVE. Deletes 19 Contact properties and creates 20. Per FS-44 dev
records are disposable and are NOT backed up or migrated. Do not point this
at any tenant whose data you care about.

Safety:
  - Hard portal guard. Refuses anything but 148226118, and refuses Curtis
    Sloane production 143653372 unconditionally before that.
  - Dry run by default. Nothing changes without --apply.
  - Deletions gated again behind --confirm-deletes.
  - Idempotent. Safe to re-run after a partial failure.

Token comes from HS_DEV_TOKEN. Not HUBSPOT_TOKEN, which on this project has
held the production token.

Usage:
    export HS_DEV_TOKEN=...
    python migrate_dev_contacts.py                              # dry run
    python migrate_dev_contacts.py --apply --confirm-deletes
    python migrate_dev_contacts.py --verify-only
    python migrate_dev_contacts.py --verify-only \
        --dump 148226118_dev_contacts_schema.json
"""

from __future__ import annotations

import argparse
import sys
from typing import Dict, List, Optional, Set

import httpx

from contacts_schema import (
    CANONICAL_PROPERTIES,
    EXPECTED_FINAL_COUNT,
    LEGACY_DELETIONS,
)
from hubspot_migrate_lib import (
    TIMEOUT,
    assert_correct_tenant,
    create_property,
    delete_property,
    diff_property,
    get_property,
    patch_property,
    print_open_decisions,
    read_token,
    requires_recreate,
    verify,
)

TOKEN_ENV_VAR = "HS_DEV_TOKEN"
EXPECTED_PORTAL_ID = 148226118


def phase_delete(client: httpx.Client, token: str, apply: bool) -> Dict[str, List[str]]:
    print("\n" + "=" * 72)
    print(f"PHASE 1 - DELETE ({len(LEGACY_DELETIONS)} legacy properties)")
    print("=" * 72)

    done: List[str] = []
    absent: List[str] = []

    for name, reason in LEGACY_DELETIONS:
        if get_property(client, token, name) is None:
            absent.append(name)
            print(f"  skip     {name} (already gone)")
            continue
        if apply:
            delete_property(client, token, name)
            print(f"  DELETED  {name} - {reason}")
        else:
            print(f"  would    delete {name} - {reason}")
        done.append(name)

    print(f"\n  {len(done)} to delete, {len(absent)} already absent")
    return {"deleted": done, "absent": absent}


def phase_create(
    client: httpx.Client,
    token: str,
    apply: bool,
    pending_deletion: Optional[Set[str]] = None,
) -> Dict[str, List[str]]:
    """
    `pending_deletion` names properties phase 1 has removed, or would remove on
    a real run. `timeline` is in both lists: it is dropped as a checkbox and
    recreated as a select, because fieldType is immutable. Without this, a dry
    run would see the old checkbox still in place and wrongly report it blocked.
    """
    print("\n" + "=" * 72)
    print(f"PHASE 2 - CREATE / CONFORM ({len(CANONICAL_PROPERTIES)} properties)")
    print("=" * 72)

    pending_deletion = pending_deletion or set()
    created: List[str] = []
    patched: List[str] = []
    unchanged: List[str] = []

    for spec in CANONICAL_PROPERTIES:
        name = spec["name"]
        existing = None if name in pending_deletion else get_property(client, token, name)

        if existing is None:
            if apply:
                create_property(client, token, spec)
                print(f"  CREATED  {name}")
            else:
                print(f"  would    create {name}")
            created.append(name)
            continue

        diffs = diff_property(spec, existing)
        if not diffs:
            unchanged.append(name)
            print(f"  ok       {name} (already conformant)")
            continue

        # Property exists but differs. On a clean legacy tenant this should
        # not happen, since phase 1 removed everything being replaced. If it
        # does, something else created it and the difference matters.
        if requires_recreate(spec, existing):
            print(
                f"  BLOCKED  {name}: {'; '.join(diffs)}\n"
                f"           type/fieldType is immutable. Delete it by hand and re-run."
            )
            continue

        body = {k: spec[k] for k in ("label", "description", "options") if k in spec}
        if apply:
            patch_property(client, token, name, body)
            print(f"  PATCHED  {name}: {'; '.join(diffs)}")
        else:
            print(f"  would    patch {name}: {'; '.join(diffs)}")
        patched.append(name)

    print(f"\n  {len(created)} create, {len(patched)} patch, {len(unchanged)} unchanged")
    return {"created": created, "patched": patched, "unchanged": unchanged}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="make changes (default: dry run)")
    ap.add_argument("--confirm-deletes", action="store_true", help="required for deletions")
    ap.add_argument("--verify-only", action="store_true", help="check conformance, change nothing")
    ap.add_argument("--dump", metavar="PATH", help="write the full schema to PATH after verify")
    args = ap.parse_args()

    token = read_token(TOKEN_ENV_VAR)

    print("=" * 72)
    print("DEV CONTACTS SCHEMA MIGRATION")
    print("=" * 72)
    print(f"  Target portal : {EXPECTED_PORTAL_ID} (FutureSynch dev)")
    print(f"  Token from    : {TOKEN_ENV_VAR}")
    print(f"  Mode          : {'APPLY' if args.apply else 'DRY RUN'}")

    with httpx.Client(timeout=TIMEOUT) as client:
        assert_correct_tenant(client, token, EXPECTED_PORTAL_ID)

        if args.verify_only:
            ok = verify(client, token, args.dump)
            print_open_decisions()
            return 0 if ok else 1

        print(
            f"\n  Plan: {len(LEGACY_DELETIONS)} deletions, "
            f"{len(CANONICAL_PROPERTIES)} creations, "
            f"5 untouched -> {EXPECTED_FINAL_COUNT} final"
        )

        if args.apply and not args.confirm_deletes:
            print(
                "\nERROR: --apply requires --confirm-deletes.\n"
                f"       {len(LEGACY_DELETIONS)} properties will be permanently removed,\n"
                "       including any data they hold. Dev records are disposable per\n"
                "       FS-44, but confirm that you are on the tenant you think you are."
            )
            return 2

        deletion_result = phase_delete(client, token, args.apply)
        # Everything phase 1 removed, or would remove, is treated as absent by
        # phase 2. On a dry run nothing was actually deleted yet.
        phase_create(
            client, token, args.apply, pending_deletion=set(deletion_result["deleted"])
        )

        if args.apply:
            ok = verify(client, token, args.dump)
        else:
            print("\n  Dry run complete. Nothing changed.")
            print("  Re-run with --apply --confirm-deletes to execute.")
            ok = True

        print_open_decisions()

        if args.apply:
            print(
                "\n  MANUAL STEP STILL OUTSTANDING: lifecyclestage.\n"
                "  42106882 s1a decides 10 lifecycle stages. lifecyclestage is\n"
                "  hubspotDefined and the v3 API will not edit its options, so this\n"
                "  script cannot do it. Configure them in HubSpot Settings >\n"
                "  Properties > Lifecycle Stage, or amend the page to record R5."
            )

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
