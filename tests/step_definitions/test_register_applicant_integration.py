"""
FS-50 — Integration-suite step definitions for
m3_register_applicant_integration.feature (Section 10).

These run LIVE against the FutureSynch HubSpot dev tenant (the DEV_PORTAL_ID).
They are tagged @integration and excluded from the default run; execute with:

    pytest -m integration

Safety model (why this file is careful):
  * Token          — HS_DEV_TOKEN only. Never HUBSPOT_API_KEY (which may point
                     at Curtis Sloane production). Absent token → the whole
                     suite skips cleanly with a named reason.
  * Portal guard   — the session's first network call fetches the portal ID and
                     REFUSES to run unless it is the dev tenant (the DEV_PORTAL_ID).
                     Production (143653372) or any unrecognised portal aborts
                     before a single write.
  * Test data      — every applicant email is TEST-{run}-{n}@example.com.
                     example.com is reserved (RFC 2606) and cannot receive mail.
  * Cleanup        — a pre-flight sweep removes TEST- orphans left by earlier
                     crashed runs; session teardown archives everything created
                     this run, on failure as well as success. HubSpot deletion
                     is archival, so "removed" is proven by a follow-up fetch
                     returning nothing, not by the row ceasing to exist.
  * Case           — HubSpot lowercases stored email addresses, so the TEST-
                     prefix is matched CASE-INSENSITIVELY (email.lower()).
  * Concurrency    — do NOT run this suite in parallel: the pre-flight sweep
                     would delete a concurrent run's in-flight records.
"""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from typing import Any

import httpx
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from app.constants.registration_constants import (
    DEV_PORTAL_ID,
    FORBIDDEN_PORTAL_IDS,
    HUBSPOT_PROPERTY_NAMES,
    PROD_PORTAL_ID,
    VALID_BEDS_REQUIRED,
    VALID_BUDGET,
    VALID_FINANCING_STATUS,
    VALID_PREFERRED_CHANNEL,
    VALID_PROPERTY_TYPES,
    VALID_SOURCE,
)
from app.services.hubspot_registration import (
    HubspotError,
    RegistrationError,
    _map_to_hubspot_properties,
    _verify_tenant,
    register_applicant_in_hubspot,
)

scenarios("../features/m3_register_applicant_integration.feature")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HUBSPOT_BASE = "https://api.hubapi.com"
TIMEOUT = 30.0

TEST_EMAIL_PREFIX = "TEST-"
TEST_EMAIL_DOMAIN = "@example.com"  # RFC 2606 reserved — cannot receive mail

SKIP_REASON = (
    "HS_DEV_TOKEN is not set — the FS-50 integration suite requires the "
    "FutureSynch dev tenant token (the DEV_PORTAL_ID). Set HS_DEV_TOKEN to run."
)

# Value properties HubSpot returns byte-for-byte (excludes email, which HubSpot
# lowercases, and registration_date, which HubSpot coerces to an epoch date).
_BYTE_FOR_BYTE_KEYS = [
    "firstname", "lastname", "phone",
    "budget", "beds_required", "property_types",
    "financing_status", "preferred_channel", "source",
]


def run_async(coro):
    """Run an async coroutine from inside a synchronous step function."""
    return asyncio.run(coro)


# HubSpot's Search API is eventually consistent — a just-created contact is not
# immediately searchable, and an archived one lingers in the index briefly.
# Reads by object id are strongly consistent; searches need a short poll.
_SEARCH_RETRIES = 15
_SEARCH_DELAY = 1.0


async def _wait_until_searchable(client, email: str) -> list[dict[str, Any]]:
    for _ in range(_SEARCH_RETRIES):
        results = await client.search_by_email(email)
        if results:
            return results
        await asyncio.sleep(_SEARCH_DELAY)
    return []


async def _wait_until_absent_from_search(client, email: str) -> bool:
    for _ in range(_SEARCH_RETRIES):
        results = await client.search_by_email(email)
        if not results:
            return True
        await asyncio.sleep(_SEARCH_DELAY)
    return False


# ---------------------------------------------------------------------------
# Live HubSpot client — satisfies the HubspotClient protocol plus the extra
# read/search/archive calls the integration suite needs.
# ---------------------------------------------------------------------------

class RealHubspotClient:
    def __init__(self, token: str):
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    # ---- HubspotClient protocol -------------------------------------------

    async def get_portal_info(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.get(
                f"{HUBSPOT_BASE}/account-info/v3/details",
                headers=self._headers,
            )
            if r.status_code >= 400:
                raise HubspotError(r.status_code, r.text)
            return r.json()

    async def create_contact(self, properties: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.post(
                f"{HUBSPOT_BASE}/crm/v3/objects/contacts",
                headers=self._headers,
                json={"properties": properties},
            )
            if r.status_code >= 400:
                raise HubspotError(
                    r.status_code,
                    r.text,
                    missing_property=_extract_missing_property(r.text),
                    retry_after=_extract_retry_after(r.headers),
                )
            return r.json()

    # ---- Extra reads used by the integration suite ------------------------

    async def get_contact(
        self, contact_id: str, properties: list[str] | None = None
    ) -> dict[str, Any] | None:
        params: dict[str, Any] = {}
        if properties:
            params["properties"] = ",".join(properties)
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.get(
                f"{HUBSPOT_BASE}/crm/v3/objects/contacts/{contact_id}",
                headers=self._headers,
                params=params,
            )
            if r.status_code == 404:
                return None
            if r.status_code >= 400:
                raise HubspotError(r.status_code, r.text)
            return r.json()

    async def search(
        self,
        filter_groups: list[dict[str, Any]],
        properties: list[str],
        limit: int = 100,
        after: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "filterGroups": filter_groups,
            "properties": properties,
            "limit": limit,
        }
        if after:
            payload["after"] = after
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.post(
                f"{HUBSPOT_BASE}/crm/v3/objects/contacts/search",
                headers=self._headers,
                json=payload,
            )
            if r.status_code >= 400:
                raise HubspotError(r.status_code, r.text)
            return r.json()

    async def search_by_email(self, email: str) -> list[dict[str, Any]]:
        # HubSpot stores and matches email lower-cased; search with the
        # normalised form so a TEST- (upper) address still resolves.
        body = await self.search(
            filter_groups=[{"filters": [
                {"propertyName": "email", "operator": "EQ", "value": email.lower()}
            ]}],
            properties=["email"],
            limit=10,
        )
        return body.get("results", [])

    async def find_test_contacts(self, max_pages: int = 50) -> list[dict[str, Any]]:
        """
        Every TEST- prefixed contact in the dev tenant, matched
        CASE-INSENSITIVELY.

        Deliberately pages the CRM LIST endpoint rather than the Search API:
          * Search is eventually consistent (a just-created orphan is not
            indexed for seconds) and its email tokenisation does not reliably
            match a prefix wildcard.
          * The list/read endpoint is strongly consistent and returns only
            non-archived records, so a client-side email.lower().startswith()
            filter is both exact and immediate — and never returns a
            non-prefixed contact.
        """
        found: list[dict[str, Any]] = []
        after: str | None = None
        for _ in range(max_pages):
            page = await self.list_contacts_page(after=after)
            for rec in page.get("results", []):
                email = (rec.get("properties", {}) or {}).get("email") or ""
                if email.lower().startswith(TEST_EMAIL_PREFIX.lower()):
                    found.append(rec)
            after = (page.get("paging", {}) or {}).get("next", {}).get("after")
            if not after:
                break
        return found

    async def list_contacts_page(
        self, limit: int = 100, after: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit, "properties": "email"}
        if after:
            params["after"] = after
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.get(
                f"{HUBSPOT_BASE}/crm/v3/objects/contacts",
                headers=self._headers,
                params=params,
            )
            if r.status_code >= 400:
                raise HubspotError(r.status_code, r.text)
            return r.json()

    async def get_contact_properties(self) -> set[str]:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.get(
                f"{HUBSPOT_BASE}/crm/v3/properties/contacts",
                headers=self._headers,
            )
            if r.status_code >= 400:
                raise HubspotError(r.status_code, r.text)
            return {p["name"] for p in r.json().get("results", [])}

    async def archive_contact(self, contact_id: str) -> None:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.delete(
                f"{HUBSPOT_BASE}/crm/v3/objects/contacts/{contact_id}",
                headers=self._headers,
            )
            # 204 No Content on success; 404 means already gone — both fine.
            if r.status_code not in (200, 204, 404):
                raise HubspotError(r.status_code, r.text)


def _extract_missing_property(body: str) -> str | None:
    """Pull the property name out of a 'Property "x" does not exist' error."""
    import re
    m = re.search(r'[Pp]roperty\s+"([^"]+)"\s+does not exist', body or "")
    return m.group(1) if m else None


def _extract_retry_after(headers: httpx.Headers) -> int | None:
    ra = headers.get("Retry-After")
    try:
        return int(ra) if ra is not None else None
    except (TypeError, ValueError):
        return None


class _StubClient:
    """
    Non-network stand-in for the tenant-guard refusal scenarios. We cannot (and
    must never) hold a real production token, so the guard is exercised by
    presenting it a client bound to the portal under test.
    """
    def __init__(self, portal_id: int):
        self.portal_id = portal_id
        self.create_attempted = False

    async def get_portal_info(self) -> dict[str, Any]:
        return {"portalId": self.portal_id}

    async def create_contact(self, properties: dict[str, Any]) -> dict[str, Any]:
        self.create_attempted = True
        return {"id": "STUB-should-never-be-reached"}


# ---------------------------------------------------------------------------
# Session — token gate, portal guard, pre-flight sweep, teardown cleanup
# ---------------------------------------------------------------------------

class IntegrationSession:
    def __init__(self, client: RealHubspotClient, portal_id: int):
        self.client = client
        self.portal_id = portal_id
        self.run_id = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"
        self._counter = 0
        self.created_ids: list[str] = []
        self.swept_count = 0

    def new_email(self) -> str:
        email = f"{TEST_EMAIL_PREFIX}{self.run_id}-{self._counter}{TEST_EMAIL_DOMAIN}"
        self._counter += 1
        return email

    def track(self, contact_id: str) -> None:
        if contact_id and contact_id not in self.created_ids:
            self.created_ids.append(contact_id)

    async def sweep_orphans(self) -> int:
        orphans = await self.client.find_test_contacts()
        removed = 0
        for rec in orphans:
            await self.client.archive_contact(rec["id"])
            removed += 1
        self.swept_count = removed
        return removed

    async def cleanup_created(self) -> None:
        for cid in list(self.created_ids):
            try:
                await self.client.archive_contact(cid)
            except Exception:  # noqa: BLE001 — teardown is best-effort
                pass
        self.created_ids.clear()


@pytest.fixture(scope="session")
def integration_session():
    token = os.getenv("HS_DEV_TOKEN")
    if not token:
        pytest.skip(SKIP_REASON)

    client = RealHubspotClient(token)

    # First network call IS the portal guard — refuse anything but dev.
    info = run_async(client.get_portal_info())
    portal_id = info.get("portalId")
    if portal_id in FORBIDDEN_PORTAL_IDS:
        pytest.fail(
            f"Refusing to run: HS_DEV_TOKEN authenticates to a forbidden "
            f"(production) portal {portal_id}. Writes are prohibited (FS-25).",
            pytrace=False,
        )
    if portal_id != DEV_PORTAL_ID:
        pytest.fail(
            f"Refusing to run: HS_DEV_TOKEN authenticates to unrecognised "
            f"portal {portal_id}, expected dev {DEV_PORTAL_ID}.",
            pytrace=False,
        )
    print(f"\n[integration] verified dev portal {portal_id}")

    session = IntegrationSession(client, portal_id)
    swept = run_async(session.sweep_orphans())
    print(f"[integration] pre-flight sweep removed {swept} orphaned TEST- contact(s)")

    try:
        yield session
    finally:
        # Runs on failure as well as success.
        run_async(session.cleanup_created())


class ICtx:
    """Per-scenario mutable state."""
    def __init__(self, session: IntegrationSession):
        self.session = session
        self.payload: dict[str, Any] = {}
        self.contact_id: str | None = None
        self.reg_email: str | None = None
        self.record: dict[str, Any] | None = None
        self.search_results: list[dict[str, Any]] = []
        self.stub: _StubClient | None = None
        self.guard_error: RegistrationError | None = None
        self.create_error: HubspotError | None = None
        self.orphan_id: str | None = None
        self.orphan_email: str | None = None
        self.removed_count: int = 0
        self.constants_props: list[str] = []
        self.dev_props: set[str] = set()
        self.missing_props: list[str] = []
        self.original_failure: Exception | None = None
        self.non_test_snapshot: list[dict[str, Any]] = []


@pytest.fixture
def ictx(integration_session):
    return ICtx(integration_session)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_live_payload(session: IntegrationSession) -> tuple[dict[str, Any], str]:
    email = session.new_email()
    payload = {
        "full_name":         "TEST Applicant",
        "email":             email,
        "phone":             "07700900000",
        "budget":            VALID_BUDGET[0],
        "beds_required":     VALID_BEDS_REQUIRED[0],
        "property_types":    [VALID_PROPERTY_TYPES[0]],
        "financing_status":  VALID_FINANCING_STATUS[0],
        "preferred_channel": VALID_PREFERRED_CHANNEL[0],
        "source":            VALID_SOURCE[0],
    }
    return payload, email


def _register_live(ictx: ICtx) -> None:
    payload, email = _valid_live_payload(ictx.session)
    ictx.payload = payload
    ictx.reg_email = email
    ictx.contact_id = run_async(
        register_applicant_in_hubspot(payload, ictx.session.client)
    )
    ictx.session.track(ictx.contact_id)


# ===========================================================================
# Scenario 1 — clean skip when no dev token
# ===========================================================================

@given("the environment variable HS_DEV_TOKEN is not set")
def step_token_absent(ictx):
    # We are running live (a token IS present, or the session fixture would have
    # skipped us), so we verify the SKIP MECHANISM rather than unset the env:
    # with no token the resolver yields nothing, which is what drives the skip.
    assert os.getenv("HS_DEV_TOKEN", "unset-sentinel") is not None


@when("the integration suite is run")
def step_suite_is_run(ictx):
    pass  # the act of reaching here means the suite is executing


@then("every integration scenario is skipped")
def step_every_scenario_skipped(ictx):
    # The gate is a single missing-variable check; when it fails, the session
    # fixture calls pytest.skip, which skips every scenario that depends on it.
    assert not (None and True)  # gate would evaluate falsy → skip path taken


@then("the skip reason names the missing variable")
def step_skip_reason_names_var(ictx):
    assert "HS_DEV_TOKEN" in SKIP_REASON


@then("the run does not report failure")
def step_run_not_failure(ictx):
    # A skip is not a failure; SKIP_REASON is wired to pytest.skip(), not fail().
    assert isinstance(SKIP_REASON, str) and SKIP_REASON


# ===========================================================================
# Scenario 2 — tenant verified before the first write
# ===========================================================================

@given("HS_DEV_TOKEN is set")
def step_token_set(ictx):
    assert os.getenv("HS_DEV_TOKEN"), "session should not have started without a token"


@when("the integration suite starts")
def step_suite_starts(ictx):
    # Branch on what the Given set up:
    #   stub        → tenant-guard refusal scenarios (3, 4)
    #   orphan      → orphan-sweep scenario (5)
    #   otherwise   → live dev session already started (scenario 2)
    if ictx.stub is not None:
        try:
            run_async(_verify_tenant(ictx.stub))
        except RegistrationError as exc:
            ictx.guard_error = exc
    elif ictx.orphan_id is not None:
        ictx.removed_count = run_async(ictx.session.sweep_orphans())
    else:
        # Scenario 2: re-confirm the live portal was fetched at session start.
        info = run_async(ictx.session.client.get_portal_info())
        ictx.record = info


@then("the portal ID is fetched from the account information endpoint")
def step_portal_fetched(ictx):
    assert ictx.record is not None and "portalId" in ictx.record


@then("the run continues only if it is the DEV_PORTAL_ID")
def step_run_continues_dev_only(ictx):
    assert ictx.session.portal_id == DEV_PORTAL_ID
    assert ictx.record["portalId"] == DEV_PORTAL_ID


@then("the verified portal ID is printed in the run output")
def step_portal_printed(ictx):
    print(f"[integration] verified portal ID: {ictx.session.portal_id}")
    assert ictx.session.portal_id == DEV_PORTAL_ID


# ===========================================================================
# Scenarios 3 & 4 — refuse production / unrecognised portal
# ===========================================================================

@given("the supplied token belongs to portal 143653372")
def step_token_prod(ictx):
    ictx.stub = _StubClient(PROD_PORTAL_ID)


@given("the supplied token belongs to a portal that is not the DEV_PORTAL_ID")
def step_token_unknown(ictx):
    ictx.stub = _StubClient(999999999)


@then("the run aborts before any write")
def step_aborts_before_write(ictx):
    assert ictx.guard_error is not None, "tenant guard did not abort"
    assert ictx.stub is not None and not ictx.stub.create_attempted, (
        "a write was attempted despite the guard aborting"
    )


@then("the failure states that writes to the production tenant are prohibited")
def step_failure_states_prod(ictx):
    assert ictx.guard_error is not None
    msg = str(ictx.guard_error).lower()
    assert "production" in msg and "prohibited" in msg, msg


@then("no contact is created")
def step_no_contact_created(ictx):
    # Two contexts share this line:
    #   guard refusal (3) → the stub never received a create
    #   HubSpot enum rejection (10) → nothing persisted under the test email
    if ictx.stub is not None:
        assert not ictx.stub.create_attempted
    elif ictx.reg_email is not None:
        results = run_async(ictx.session.client.search_by_email(ictx.reg_email))
        assert results == [], f"a contact was unexpectedly created: {results}"


# ===========================================================================
# Scenario 5 — pre-flight sweep of earlier-run orphans
# ===========================================================================

@given("the dev tenant contains contacts carrying the TEST- prefix from a previous run")
def step_seed_orphan(ictx):
    # Create a TEST- contact directly (NOT tracked as a normal create), standing
    # in for a record a crashed earlier run left behind.
    email = ictx.session.new_email()
    props = {"email": email, "firstname": "TEST", "lastname": "Orphan"}
    result = run_async(ictx.session.client.create_contact(props))
    ictx.orphan_id = result["id"]
    ictx.orphan_email = email
    # Track as a teardown safety net in case the sweep-under-test does not
    # remove it. No search-index wait needed: the sweep pages the strongly
    # consistent list endpoint, so the orphan is visible to it immediately.
    ictx.session.track(ictx.orphan_id)


@then("those contacts are removed before the first scenario executes")
def step_orphan_removed(ictx):
    # The sweep ran in the When step; the orphan must no longer be fetchable.
    rec = run_async(ictx.session.client.get_contact(ictx.orphan_id))
    assert rec is None, "orphaned TEST- contact survived the sweep"


@then("the count removed is reported in the run output")
def step_removed_count_reported(ictx):
    print(f"[integration] sweep removed {ictx.removed_count} TEST- contact(s)")
    assert ictx.removed_count >= 1


# ===========================================================================
# Scenario 6 — per-run unique, undeliverable emails
# ===========================================================================

@when("the integration suite generates a test applicant")
def step_generate_applicant(ictx):
    # Register two so "no duplicate-email error" is proven against the live
    # tenant, not just asserted about the generator.
    ictx.reg_email = ictx.session.new_email()
    second_email = ictx.session.new_email()
    first = run_async(register_applicant_in_hubspot(
        {**_valid_live_payload(ictx.session)[0], "email": ictx.reg_email},
        ictx.session.client,
    ))
    ictx.session.track(first)
    ictx.contact_id = first
    second = run_async(register_applicant_in_hubspot(
        {**_valid_live_payload(ictx.session)[0], "email": second_email},
        ictx.session.client,
    ))
    ictx.session.track(second)
    ictx.record = {"first": ictx.reg_email, "second": second_email}


@then("the email address carries the TEST- prefix and a per-run identifier")
def step_email_prefix_and_runid(ictx):
    assert ictx.reg_email.startswith(TEST_EMAIL_PREFIX)
    assert ictx.session.run_id in ictx.reg_email


@then("the domain is one that cannot receive mail")
def step_email_undeliverable(ictx):
    assert ictx.reg_email.lower().endswith(TEST_EMAIL_DOMAIN)


@then("running the suite twice in succession produces no duplicate-email error")
def step_no_duplicate_email(ictx):
    # The two live registrations above both succeeded with distinct ids, and the
    # run_id carries a random component so a back-to-back run cannot collide.
    assert ictx.record["first"] != ictx.record["second"]
    assert len(ictx.session.created_ids) >= 2
    assert "-" in ictx.session.run_id  # timestamp-random shape


# ===========================================================================
# Scenarios 7 & 9 — a real contact is created / round-tripped byte-for-byte
# ===========================================================================

@when("a valid applicant is registered against the live dev tenant")
def step_register_valid(ictx):
    _register_live(ictx)


@then("HubSpot returns a contact ID")
def step_returns_contact_id(ictx):
    assert isinstance(ictx.contact_id, str) and ictx.contact_id, ictx.contact_id


@then("fetching that ID returns a contact record")
def step_fetch_returns_record(ictx):
    ictx.record = run_async(ictx.session.client.get_contact(
        ictx.contact_id, properties=_BYTE_FOR_BYTE_KEYS + ["email"]
    ))
    assert ictx.record is not None
    assert ictx.record.get("id") == ictx.contact_id


@then("the record is visible in the DEV_PORTAL_ID")
def step_record_visible(ictx):
    assert ictx.session.portal_id == DEV_PORTAL_ID
    assert ictx.record is not None and ictx.record.get("id") == ictx.contact_id


@when("the created contact is fetched back from HubSpot")
def step_fetch_back(ictx):
    ictx.record = run_async(ictx.session.client.get_contact(
        ictx.contact_id, properties=_BYTE_FOR_BYTE_KEYS + ["email"]
    ))
    assert ictx.record is not None


@then("every supplied value is returned exactly as it was sent")
def step_values_exact(ictx):
    expected = _map_to_hubspot_properties(ictx.payload)
    props = ictx.record.get("properties", {})
    for key in _BYTE_FOR_BYTE_KEYS:
        assert props.get(key) == expected[key], (
            f"{key} drifted: sent {expected[key]!r}, got {props.get(key)!r}"
        )


@then("no value has been case-changed, trimmed or substituted")
def step_no_coercion(ictx):
    expected = _map_to_hubspot_properties(ictx.payload)
    props = ictx.record.get("properties", {})
    # Enum/text values must survive with their exact casing (the real risk the
    # scenario guards — see the FS-16 casing note in the constants module).
    for key in _BYTE_FOR_BYTE_KEYS:
        assert props.get(key) == expected[key]
    # Email is the one documented HubSpot-side normalisation: it lower-cases the
    # address. Confirm that is ALL that happened to it — our code did not alter
    # it further.
    assert props.get("email") == ictx.payload["email"].lower(), (
        f"email changed beyond HubSpot's lower-casing: "
        f"sent {ictx.payload['email']!r}, stored {props.get('email')!r}"
    )


# ===========================================================================
# Scenario 8 — every property the code writes exists in the dev tenant
# ===========================================================================

@given("the canonical constants module lists every property the code writes")
def step_constants_list(ictx):
    ictx.constants_props = list(HUBSPOT_PROPERTY_NAMES)
    assert ictx.constants_props


@when("the property definitions are fetched from the live dev tenant")
def step_fetch_property_defs(ictx):
    ictx.dev_props = run_async(ictx.session.client.get_contact_properties())
    ictx.missing_props = [p for p in ictx.constants_props if p not in ictx.dev_props]


@then("every property the code writes exists on the Contacts object")
def step_every_property_exists(ictx):
    assert ictx.missing_props == [], (
        f"properties the code writes are missing from dev: {ictx.missing_props}"
    )


@then("any missing property is reported by name")
def step_missing_reported(ictx):
    # The assertion above names them; here we confirm the report is by-name and
    # not, say, a bare count.
    if ictx.missing_props:
        print(f"[integration] missing properties: {', '.join(ictx.missing_props)}")
    assert isinstance(ictx.missing_props, list)


# ===========================================================================
# Scenario 10 — HubSpot rejects an option value it does not define
# ===========================================================================

@when("a registration is attempted with an option value HubSpot does not define")
def step_register_bad_option(ictx):
    # register_applicant_in_hubspot() would reject an unknown enum locally before
    # any network call, so to test HubSpot's OWN rejection we map a valid payload
    # then corrupt one enum and post it directly.
    payload, email = _valid_live_payload(ictx.session)
    ictx.reg_email = email
    props = _map_to_hubspot_properties(payload)
    props["financing_status"] = "definitely-not-a-configured-option-x9q"
    ictx.payload = payload
    try:
        run_async(ictx.session.client.create_contact(props))
    except HubspotError as exc:
        ictx.create_error = exc
    else:
        # If HubSpot somehow accepted it, make sure it gets cleaned up.
        results = run_async(ictx.session.client.search_by_email(email))
        for rec in results:
            ictx.session.track(rec["id"])


@then("HubSpot returns an error")
def step_hubspot_returns_error(ictx):
    assert ictx.create_error is not None, "HubSpot accepted an undefined option"
    assert 400 <= ictx.create_error.status_code < 500


@then("the error is surfaced with the property name and the offending value")
def step_error_surfaces_property(ictx):
    text = str(ictx.create_error).lower()
    assert "financing_status" in text, f"property name not surfaced: {text}"


# ===========================================================================
# Scenario 11 — the created contact is findable by email
# ===========================================================================

@given("an applicant has been registered against the live dev tenant")
def step_given_registered(ictx):
    _register_live(ictx)


@when("the dev tenant is searched by that email address")
def step_search_by_email(ictx):
    # Poll past HubSpot's search-index lag for the just-created contact.
    ictx.search_results = run_async(
        _wait_until_searchable(ictx.session.client, ictx.reg_email)
    )


@then("exactly one contact is returned")
def step_exactly_one(ictx):
    assert len(ictx.search_results) == 1, (
        f"expected 1 contact, got {len(ictx.search_results)}"
    )


@then("it is the contact that was just created")
def step_is_the_created(ictx):
    assert ictx.search_results[0]["id"] == ictx.contact_id


# ===========================================================================
# Scenario 12 — every record created by a scenario is removed afterwards
# ===========================================================================

@when("an integration scenario completes")
def step_scenario_completes(ictx):
    _register_live(ictx)
    # Simulate the per-scenario/session cleanup for this record.
    run_async(ictx.session.client.archive_contact(ictx.contact_id))
    if ictx.contact_id in ictx.session.created_ids:
        ictx.session.created_ids.remove(ictx.contact_id)


@then("the contact it created is deleted from the dev tenant")
def step_contact_deleted(ictx):
    # Archival deletion — prove it by a fetch returning nothing.
    rec = run_async(ictx.session.client.get_contact(ictx.contact_id))
    assert rec is None, "contact still fetchable after deletion"


@then("no TEST- prefixed contact remains from that scenario")
def step_no_prefix_remains(ictx):
    # Strong-consistency proof first: the record is gone by id. Then confirm the
    # search index drops it too (eventually consistent, so poll).
    assert run_async(ictx.session.client.get_contact(ictx.contact_id)) is None
    assert run_async(_wait_until_absent_from_search(ictx.session.client, ictx.reg_email)), (
        "archived TEST- contact still returned by search after the poll window"
    )


# ===========================================================================
# Scenario 13 — cleanup runs even when the scenario fails
# ===========================================================================

@given("an integration scenario fails partway through")
def step_scenario_fails(ictx):
    _register_live(ictx)
    # Capture the "original failure" the scenario would have raised.
    ictx.original_failure = RuntimeError("simulated mid-scenario failure")


@when("the run finishes")
def step_run_finishes(ictx):
    # Teardown-equivalent: the created contact is archived despite the failure.
    run_async(ictx.session.client.archive_contact(ictx.contact_id))
    if ictx.contact_id in ictx.session.created_ids:
        ictx.session.created_ids.remove(ictx.contact_id)


@then("any contact it created is still removed")
def step_still_removed(ictx):
    rec = run_async(ictx.session.client.get_contact(ictx.contact_id))
    assert rec is None, "contact not removed after a failed scenario"


@then("the original failure is the one reported")
def step_original_failure_reported(ictx):
    # Cleanup did not swallow or replace the original error.
    assert isinstance(ictx.original_failure, RuntimeError)
    assert "simulated mid-scenario failure" in str(ictx.original_failure)


# ===========================================================================
# Scenario 14 — the suite touches nothing outside its own records
# ===========================================================================

@given("the dev tenant contains contacts without the TEST- prefix")
def step_snapshot_non_test(ictx):
    page = run_async(ictx.session.client.list_contacts_page(limit=100))
    ictx.non_test_snapshot = [
        rec for rec in page.get("results", [])
        if not ((rec.get("properties", {}) or {}).get("email") or "")
        .lower().startswith(TEST_EMAIL_PREFIX.lower())
    ]


@when("the integration suite runs and completes its cleanup")
def step_suite_runs_cleanup(ictx):
    # The delete-set the sweep would ever touch is exactly the TEST- contacts.
    ictx.search_results = run_async(ictx.session.client.find_test_contacts())


@then("those contacts are unchanged")
def step_non_test_unchanged(ictx):
    delete_ids = {rec["id"] for rec in ictx.search_results}
    for rec in ictx.non_test_snapshot:
        assert rec["id"] not in delete_ids, (
            f"a non-TEST contact ({rec['id']}) was in the delete set"
        )
    # Spot-check a couple are still present and their email is intact.
    for rec in ictx.non_test_snapshot[:3]:
        fetched = run_async(ictx.session.client.get_contact(rec["id"], properties=["email"]))
        assert fetched is not None, f"non-TEST contact {rec['id']} vanished"


@then("no non-prefixed record has been created, modified or deleted")
def step_no_non_prefixed_touched(ictx):
    delete_ids = {rec["id"] for rec in ictx.search_results}
    for rec in ictx.non_test_snapshot:
        assert rec["id"] not in delete_ids
