#!/usr/bin/env python3
"""
Verify the HUBSPOT_API_KEY resolves to the expected DEV_PORTAL_ID (and never the
Curtis Sloane production portal). Run before trusting a demo/deploy:

    HUBSPOT_API_KEY=... DEV_PORTAL_ID=149441587 python scripts/check_portal.py
"""
import os, sys, httpx

key = os.environ["HUBSPOT_API_KEY"]
expected = os.getenv("DEV_PORTAL_ID")

r = httpx.get(
    "https://api.hubapi.com/account-info/v3/details",
    headers={"Authorization": f"Bearer {key}"},
    timeout=10,
)
r.raise_for_status()
actual = str(r.json()["portalId"])

print(f"resolved portalId: {actual}")
if expected and actual != expected:
    sys.exit(f"MISMATCH — DEV_PORTAL_ID={expected}, every write will be refused")
if actual == "143653372":
    sys.exit("REFUSING — that is the production portal")
print("ok")
