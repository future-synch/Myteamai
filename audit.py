"""
audit_futuresynch_properties.py

Read-only audit of all Contact properties in FutureSynch dev HubSpot.
Output: properties_audit.csv with creator, type, group, options.
Usage: python audit_futuresynch_properties.py
Requires: HUBSPOT_API_KEY in .env (FutureSynch token)
"""

import csv
import os
import sys
from datetime import datetime

import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("HUBSPOT_API_KEY")
if not API_KEY:
    sys.exit("ERROR: HUBSPOT_API_KEY not found in .env")

BASE_URL = "https://api.hubapi.com/crm/v3/properties/contacts"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def fetch_all_properties() -> list[dict]:
    """Fetch every contact property in the account."""
    print("Fetching all contact properties from FutureSynch HubSpot...")
    response = httpx.get(BASE_URL, headers=HEADERS, timeout=30.0)
    response.raise_for_status()
    data = response.json()
    properties = data.get("results", [])
    print(f"Retrieved {len(properties)} properties.\n")
    return properties


def classify_creator(prop: dict) -> str:
    """Categorise who created this property."""
    if prop.get("hubspotDefined", False):
        return "HubSpot (default)"
    created_user_id = prop.get("createdUserId")
    if not created_user_id:
        return "Unknown"
    return f"User ID: {created_user_id}"


def summarise(properties: list[dict]) -> None:
    """Print a quick breakdown by creator and group."""
    by_creator: dict[str, int] = {}
    by_group: dict[str, int] = {}
    custom_count = 0

    for prop in properties:
        creator = classify_creator(prop)
        by_creator[creator] = by_creator.get(creator, 0) + 1
        group = prop.get("groupName", "(no group)")
        by_group[group] = by_group.get(group, 0) + 1
        if not prop.get("hubspotDefined", False):
            custom_count += 1

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total properties: {len(properties)}")
    print(f"Custom (non-HubSpot) properties: {custom_count}")
    print()
    print("By creator:")
    for creator, count in sorted(by_creator.items(), key=lambda x: -x[1]):
        print(f"  {creator}: {count}")
    print()
    print("Top groups:")
    top_groups = sorted(by_group.items(), key=lambda x: -x[1])[:10]
    for group, count in top_groups:
        print(f"  {group}: {count}")
    print()


def write_csv(properties: list[dict], filepath: str) -> None:
    """Dump everything useful to CSV for sorting/filtering."""
    fieldnames = [
        "internal_name",
        "label",
        "type",
        "field_type",
        "group",
        "is_hubspot_default",
        "created_user_id",
        "created_at",
        "updated_at",
        "options_count",
        "options_preview",
        "description",
    ]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for prop in properties:
            options = prop.get("options", []) or []
            options_preview = " | ".join(
                opt.get("label", "") for opt in options[:5]
            )
            if len(options) > 5:
                options_preview += f" | ... (+{len(options) - 5} more)"
            writer.writerow({
                "internal_name": prop.get("name", ""),
                "label": prop.get("label", ""),
                "type": prop.get("type", ""),
                "field_type": prop.get("fieldType", ""),
                "group": prop.get("groupName", ""),
                "is_hubspot_default": prop.get("hubspotDefined", False),
                "created_user_id": prop.get("createdUserId", ""),
                "created_at": prop.get("createdAt", ""),
                "updated_at": prop.get("updatedAt", ""),
                "options_count": len(options),
                "options_preview": options_preview,
                "description": prop.get("description", "")[:200],
            })
    print(f"Full CSV written to: {filepath}")


def write_custom_only_csv(properties: list[dict], filepath: str) -> None:
    """Smaller CSV with just the custom properties (the interesting ones)."""
    custom = [p for p in properties if not p.get("hubspotDefined", False)]
    custom.sort(key=lambda p: (p.get("createdUserId") or "", p.get("name", "")))

    fieldnames = [
        "created_user_id",
        "internal_name",
        "label",
        "type",
        "field_type",
        "group",
        "created_at",
        "options_count",
        "options_preview",
    ]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for prop in custom:
            options = prop.get("options", []) or []
            options_preview = " | ".join(
                opt.get("label", "") for opt in options[:5]
            )
            if len(options) > 5:
                options_preview += f" | ... (+{len(options) - 5} more)"
            writer.writerow({
                "created_user_id": prop.get("createdUserId", ""),
                "internal_name": prop.get("name", ""),
                "label": prop.get("label", ""),
                "type": prop.get("type", ""),
                "field_type": prop.get("fieldType", ""),
                "group": prop.get("groupName", ""),
                "created_at": prop.get("createdAt", ""),
                "options_count": len(options),
                "options_preview": options_preview,
            })
    print(f"Custom-only CSV written to: {filepath}")
    print(f"  ({len(custom)} custom properties)")


def print_custom_table(properties: list[dict]) -> None:
    """Print custom properties grouped by creator for quick scan."""
    custom = [p for p in properties if not p.get("hubspotDefined", False)]
    by_user: dict[str, list[dict]] = {}
    for prop in custom:
        uid = str(prop.get("createdUserId") or "Unknown")
        by_user.setdefault(uid, []).append(prop)

    print("=" * 60)
    print("CUSTOM PROPERTIES BY CREATOR")
    print("=" * 60)
    for uid, props in sorted(by_user.items(), key=lambda x: -len(x[1])):
        props.sort(key=lambda p: p.get("name", ""))
        print(f"\nUser ID {uid}: {len(props)} properties")
        print("-" * 60)
        for prop in props:
            name = prop.get("name", "")
            label = prop.get("label", "")
            ftype = prop.get("fieldType", "")
            group = prop.get("groupName", "")
            print(f"  {name:35s} | {ftype:18s} | {group:25s} | {label}")
    print()


def main() -> None:
    properties = fetch_all_properties()
    summarise(properties)
    print_custom_table(properties)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    write_csv(properties, f"properties_audit_full_{timestamp}.csv")
    write_custom_only_csv(properties, f"properties_audit_custom_{timestamp}.csv")
    print()
    print("Done. Open the custom CSV in Numbers or Excel.")
    print("Sort by 'created_user_id' to see who built what.")


if __name__ == "__main__":
    main()