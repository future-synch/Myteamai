#!/usr/bin/env python3
"""
Smoke test: register an applicant end-to-end against a running My Team AI API.

Credentials are read from the environment — NEVER hardcoded:
  SMOKE_EMAIL     login email      (required)
  SMOKE_PASSWORD  login password   (required)
  SMOKE_BASE_URL  API base URL     (optional; default http://localhost:8000)

Exits non-zero with a clear message if either credential is unset, or if any
step (login / register) fails.

NOTE (FS-67 follow-up): this file was (re)created — the original was missing
from the repo. The register payload below is a SAMPLE; adjust it to your
canonical smoke applicant if the smoke test needs a specific record.
"""
from __future__ import annotations

import os
import sys

import httpx


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.exit(
            f"ERROR: {name} is not set. The smoke test reads credentials from the "
            f"environment and never hardcodes them.\n"
            f"Set SMOKE_EMAIL and SMOKE_PASSWORD (and optionally SMOKE_BASE_URL) "
            f"before running, e.g.:\n"
            f"  SMOKE_EMAIL=you@example.com SMOKE_PASSWORD=... python scripts/smoke_register.py"
        )
    return value


def main() -> int:
    email = _require_env("SMOKE_EMAIL")
    password = _require_env("SMOKE_PASSWORD")
    base_url = os.getenv("SMOKE_BASE_URL", "http://localhost:8000").rstrip("/")

    with httpx.Client(timeout=30.0) as client:
        # 1) Log in with the env-provided credentials.
        r = client.post(f"{base_url}/auth/login", json={"email": email, "password": password})
        if r.status_code != 200:
            sys.exit(f"ERROR: login failed ({r.status_code}): {r.text}")
        token = r.json().get("access_token")
        if not token:
            sys.exit(f"ERROR: login returned no access_token: {r.text}")
        headers = {"Authorization": f"Bearer {token}"}

        # 2) Register a sample applicant (SAMPLE payload — adjust as needed).
        applicant = {
            "full_name": "Smoke Test Applicant",
            "email": "smoke-test@example.com",
            "phone": "07700900000",
            "budget_gbp": 1_000_000,
            "bedrooms_min": 2,
            "property_types": ["house"],
            "financing": "cash",
            "preferred_channel": "email",
            "source": "direct",
        }
        r = client.post(f"{base_url}/bot/register-applicant", json=applicant, headers=headers)
        if r.status_code != 200:
            sys.exit(f"ERROR: register-applicant failed ({r.status_code}): {r.text}")
        body = r.json()
        if body.get("status") != "ok":
            sys.exit(f"ERROR: register-applicant returned status={body.get('status')}: {body}")

    print(
        f"SMOKE OK: logged in as {email} and registered an applicant "
        f"(applicant_id={body.get('applicant_id')})."
    )

    matches = body.get("first_matches") or []
    print(f"first_matches: {len(matches)}")
    for i, m in enumerate(matches, start=1):
        print(
            f"  {i}. {m.get('address')} — £{m.get('price_gbp')}, "
            f"{m.get('bedrooms')} bed — {m.get('match_reason')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
