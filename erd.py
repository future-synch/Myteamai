"""
extract_hubspot_erd.py

Read-only extraction of HubSpot data structure for ERD generation.
Pulls: object types, custom properties, associations between objects.
Output: hubspot_erd_<account>.json + hubspot_erd_<account>.mmd (Mermaid)
Usage: python extract_hubspot_erd.py <account_label>
       (set HUBSPOT_API_KEY in .env to the target account's token)

Account labels: 'futuresynch' or 'curtissloane' (just for filename)
"""

import json
import os
import sys
from datetime import datetime
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("HUBSPOT_API_KEY")
if not API_KEY:
    sys.exit("ERROR: HUBSPOT_API_KEY not found in .env")

if len(sys.argv) < 2:
    print("Usage: python extract_hubspot_erd.py <account_label>")
    print("Example: python extract_hubspot_erd.py futuresynch")
    sys.exit(1)

ACCOUNT_LABEL = sys.argv[1].lower().replace(" ", "_")

BASE = "https://api.hubapi.com"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

STANDARD_OBJECTS = [
    "contacts",
    "companies",
    "deals",
    "tickets",
    "products",
    "line_items",
    "quotes",
    "tasks",
    "calls",
    "emails",
    "meetings",
    "notes",
]


def fetch(url: str) -> dict | None:
    """GET wrapper with error handling."""
    try:
        r = httpx.get(url, headers=HEADERS, timeout=30.0)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 403:
            print(f"  403 Forbidden (missing scope?): {url}")
            return None
        if r.status_code == 404:
            print(f"  404 Not Found: {url}")
            return None
        print(f"  {r.status_code} error: {url}")
        return None
    except httpx.RequestError as e:
        print(f"  Request error: {e}")
        return None


def fetch_object_schemas() -> list[dict]:
    """Fetch all object schemas (standard + custom)."""
    print("Fetching all object schemas...")
    data = fetch(f"{BASE}/crm/v3/schemas")
    if not data:
        return []
    schemas = data.get("results", [])
    print(f"  Found {len(schemas)} object schemas\n")
    return schemas


def fetch_properties(object_type: str) -> list[dict]:
    """Fetch all properties for a given object type."""
    data = fetch(f"{BASE}/crm/v3/properties/{object_type}")
    if not data:
        return []
    return data.get("results", [])


def fetch_associations(from_object: str, to_object: str) -> list[dict]:
    """Fetch association labels between two object types."""
    url = f"{BASE}/crm/v4/associations/{from_object}/{to_object}/labels"
    data = fetch(url)
    if not data:
        return []
    return data.get("results", [])


def build_erd_data() -> dict:
    """Build a structured dict of objects, properties, and associations."""
    erd: dict[str, Any] = {
        "account_label": ACCOUNT_LABEL,
        "generated_at": datetime.now().isoformat(),
        "objects": {},
        "associations": [],
    }

    schemas = fetch_object_schemas()
    object_types = STANDARD_OBJECTS + [
        s["name"] for s in schemas if s.get("name") not in STANDARD_OBJECTS
    ]
    object_types = list(dict.fromkeys(object_types))

    print(f"Inspecting {len(object_types)} object types...\n")

    for obj_type in object_types:
        print(f"  {obj_type}")
        props = fetch_properties(obj_type)
        if not props:
            continue

        custom_props = [p for p in props if not p.get("hubspotDefined", False)]
        erd["objects"][obj_type] = {
            "total_properties": len(props),
            "custom_properties": len(custom_props),
            "custom_property_names": [p["name"] for p in custom_props],
            "custom_property_details": [
                {
                    "name": p["name"],
                    "label": p.get("label", ""),
                    "type": p.get("type", ""),
                    "field_type": p.get("fieldType", ""),
                }
                for p in custom_props
            ],
        }
        print(f"    {len(props)} total, {len(custom_props)} custom")

    print("\nProbing associations between objects...")
    major = ["contacts", "companies", "deals", "tickets", "tasks"]
    for from_obj in major:
        if from_obj not in erd["objects"]:
            continue
        for to_obj in major:
            if from_obj == to_obj or to_obj not in erd["objects"]:
                continue
            assocs = fetch_associations(from_obj, to_obj)
            if assocs:
                erd["associations"].append({
                    "from": from_obj,
                    "to": to_obj,
                    "labels": [a.get("label", "default") for a in assocs],
                })
                print(f"  {from_obj} -> {to_obj}: {len(assocs)} association(s)")

    return erd


def render_mermaid(erd: dict) -> str:
    """Generate Mermaid erDiagram syntax from the ERD data."""
    lines = ["erDiagram"]

    for obj_name, obj_data in erd["objects"].items():
        if obj_data["custom_properties"] == 0 and obj_data["total_properties"] == 0:
            continue
        entity = obj_name.upper().replace("-", "_")
        lines.append(f'    {entity} {{')
        for prop in obj_data["custom_property_details"][:8]:
            ftype = prop["field_type"] or prop["type"] or "string"
            ftype_clean = ftype.replace(" ", "_")
            name_clean = prop["name"].replace("-", "_")
            lines.append(f'        {ftype_clean} {name_clean}')
        if obj_data["custom_properties"] > 8:
            lines.append(f'        string _and_{obj_data["custom_properties"] - 8}_more')
        lines.append("    }")

    for assoc in erd["associations"]:
        from_e = assoc["from"].upper()
        to_e = assoc["to"].upper()
        label = assoc["labels"][0].replace(" ", "_")[:20] if assoc["labels"] else "associated"
        lines.append(f'    {from_e} ||--o{{ {to_e} : {label}')

    return "\n".join(lines)


def main() -> None:
    erd = build_erd_data()

    json_path = f"hubspot_erd_{ACCOUNT_LABEL}.json"
    with open(json_path, "w") as f:
        json.dump(erd, f, indent=2)
    print(f"\nJSON written to: {json_path}")

    mmd_path = f"hubspot_erd_{ACCOUNT_LABEL}.mmd"
    with open(mmd_path, "w") as f:
        f.write(render_mermaid(erd))
    print(f"Mermaid ERD written to: {mmd_path}")
    print()
    print("To render the ERD visually:")
    print(f"  1. Open {mmd_path} contents")
    print(f"  2. Paste into https://mermaid.live")
    print(f"  3. Or: npx -p @mermaid-js/mermaid-cli mmdc -i {mmd_path} -o erd.png")
    print()
    print("Summary:")
    print(f"  Objects with properties: {len(erd['objects'])}")
    print(f"  Associations mapped: {len(erd['associations'])}")


if __name__ == "__main__":
    main()