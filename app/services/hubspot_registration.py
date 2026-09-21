"""
FS-50 — register_applicant_in_hubspot()

Registration half of fn_register_applicant() per TS Amendment A-2 rev 3.

What this function does:
  1. Validates the applicant payload
  2. Verifies the HubSpot portal is safe to write to (FS-25 tenant guard)
  3. Creates the HubSpot contact with retry/backoff on transient errors
  4. Returns the HubSpot contact ID as a non-empty string

What this function DOES NOT do (asserted by §1 contract-boundary scenarios):
  - Match finding (no listings fetched) — belongs to find_matching_listings()
  - Email dispatch or draft creation — belongs to fn_generate_welcome() (FS-42)
  - KYC checklist generation — removed from this function entirely
  - AI calls (no Claude API call) — registration is deterministic
  - Response assembly — belongs to fn_register_applicant() caller

Constants rule (§4): every option value used for validation or written to
HubSpot comes from app/constants/registration_constants — this module
contains NO string literals for any enum value.
"""
from __future__ import annotations

import asyncio
import re
from datetime import date
from typing import Any, Protocol

from app.constants.registration_constants import (
    DEV_PORTAL_ID,
    ENUM_SETS,
    MULTI_VALUE_FIELDS,
    OPTIONAL_FIELDS,
    PROD_PORTAL_ID,
    REQUIRED_FIELDS,
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class RegistrationError(Exception):
    """
    Raised when the registration cannot complete. Carries structured info:
      - fields: list of offending field names (may be empty)
      - code:   short machine-readable code
      - payload: the original criteria dict so the caller does not have
        to retype anything (spec §7 "the submitted payload is returned")
      - permitted: for enum errors, the set of allowed values
    """

    def __init__(
        self,
        message: str,
        *,
        fields: list[str] | None = None,
        code: str | None = None,
        payload: dict[str, Any] | None = None,
        permitted: dict[str, list[str]] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.fields = fields or []
        self.code = code
        self.payload = payload
        self.permitted = permitted or {}


class HubspotError(Exception):
    """
    Raised by a HubspotClient implementation on a non-2xx response.
    Attributes:
      - status_code:      HTTP status
      - retry_after:      integer seconds if HubSpot supplied Retry-After
      - missing_property: property name if the failure was a schema mismatch
    """

    def __init__(
        self,
        status_code: int,
        message: str = "",
        *,
        retry_after: int | None = None,
        missing_property: str | None = None,
    ):
        super().__init__(message or f"HubSpot HTTP {status_code}")
        self.status_code = status_code
        self.retry_after = retry_after
        self.missing_property = missing_property


class HubspotTimeoutError(HubspotError):
    """A HubSpot call timed out. Handled as a failure, never propagated bare."""

    def __init__(self, message: str = "HubSpot request timed out"):
        super().__init__(status_code=0, message=message)


# ---------------------------------------------------------------------------
# Client protocol — real and fake clients both satisfy this
# ---------------------------------------------------------------------------

class HubspotClient(Protocol):
    async def get_portal_info(self) -> dict[str, Any]: ...
    async def create_contact(self, properties: dict[str, Any]) -> dict[str, Any]: ...


# ---------------------------------------------------------------------------
# Payload validation (§2, §3, §4)
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

_SYSTEM_ONLY_FIELDS: set[str] = {"registration_date"}


def _validate_payload(criteria: dict[str, Any]) -> None:
    """
    Collect every validation error before raising, so the caller sees all
    problems at once (§2 "All validation errors are reported together").
    """
    errors: list[tuple[str, str]] = []
    permitted: dict[str, list[str]] = {}

    known_fields = set(REQUIRED_FIELDS) | set(OPTIONAL_FIELDS) | _SYSTEM_ONLY_FIELDS

    # §2: Unrecognised fields
    for field in criteria:
        if field not in known_fields:
            errors.append((field, "unrecognised"))

    # §2: Required-field presence + empty-string equivalence
    missing_or_empty: set[str] = set()
    for field in REQUIRED_FIELDS:
        if field not in criteria:
            errors.append((field, "missing"))
            missing_or_empty.add(field)
            continue
        value = criteria[field]
        if value is None:
            errors.append((field, "missing"))
            missing_or_empty.add(field)
            continue
        if isinstance(value, str) and value == "":
            errors.append((field, "empty"))
            missing_or_empty.add(field)
            continue
        if isinstance(value, list) and len(value) == 0 and field not in MULTI_VALUE_FIELDS:
            errors.append((field, "empty"))
            missing_or_empty.add(field)

    # §3: Email format — only if email is present and non-empty
    email = criteria.get("email")
    if email and "email" not in missing_or_empty:
        if not _EMAIL_RE.match(str(email)):
            errors.append(("email", "malformed"))

    # §4: Enum validation (case-sensitive, exact)
    for field, valid_set in ENUM_SETS.items():
        if field not in criteria or field in missing_or_empty:
            continue
        value = criteria[field]
        if value is None or value == "":
            continue

        if field in MULTI_VALUE_FIELDS:
            values_to_check = value if isinstance(value, list) else [value]
            for v in values_to_check:
                if v not in valid_set:
                    errors.append((field, f"invalid_value:{v}"))
                    permitted[field] = list(valid_set)
        else:
            if value not in valid_set:
                errors.append((field, f"invalid_value:{value}"))
                permitted[field] = list(valid_set)

    if errors:
        field_names = list(dict.fromkeys(f for f, _ in errors))
        raise RegistrationError(
            f"Registration validation failed: fields={field_names} reasons={errors}",
            fields=field_names,
            code="VALIDATION",
            payload=dict(criteria),
            permitted=permitted,
        )


# ---------------------------------------------------------------------------
# Field mapping (§5)
# ---------------------------------------------------------------------------

def _split_full_name(full_name: str) -> tuple[str, str]:
    """
    §5: full_name split — first word -> firstname, remainder -> lastname.
    Single-word name -> firstname empty, lastname holds the word.
    Multi-part surnames preserved intact.
    """
    parts = str(full_name).strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return "", parts[0]
    return parts[0], " ".join(parts[1:])


def _map_to_hubspot_properties(criteria: dict[str, Any]) -> dict[str, Any]:
    """
    Map validated payload to HubSpot contact properties.

    §4 critical: every value in ENUM_SETS-managed fields is written
    byte-for-byte, no casing/trimming/substitution.
    §5 critical: every supplied criterion reaches a property.
    §5 critical: registration_date is set by the system, not the caller.
    """
    firstname, lastname = _split_full_name(criteria["full_name"])

    props: dict[str, Any] = {
        "firstname":         firstname,
        "lastname":          lastname,
        "email":             criteria["email"],
        "phone":             criteria["phone"],
        "budget":            criteria["budget"],
        "beds_required":     criteria["beds_required"],
        "financing_status":  criteria["financing_status"],
        "preferred_channel": criteria["preferred_channel"],
        "source":            criteria["source"],
        "registration_date": date.today().isoformat(),
    }

    # Multi-value: property_types. HubSpot represents multi-value checkbox
    # enumerations as a semicolon-separated string on the wire.
    prop_types = criteria.get("property_types")
    if prop_types is None:
        props["property_types"] = ""
    elif isinstance(prop_types, list):
        props["property_types"] = ";".join(prop_types)
    else:
        props["property_types"] = prop_types

    # Optional fields
    for opt in OPTIONAL_FIELDS:
        if opt in criteria and criteria[opt] is not None:
            props[opt] = criteria[opt]

    return props


# ---------------------------------------------------------------------------
# Tenant guard (§8)
# ---------------------------------------------------------------------------

async def _verify_tenant(client: HubspotClient) -> int:
    """
    §8: verify the client is bound to the dev portal BEFORE any write.
    Refuse writes to production or any unrecognised portal.
    """
    try:
        info = await client.get_portal_info()
    except Exception as exc:
        raise RegistrationError(
            f"Portal verification failed: {exc}",
            code="TENANT_UNVERIFIED",
        )

    portal_id = info.get("portalId")
    if portal_id == DEV_PORTAL_ID:
        return portal_id
    if portal_id == PROD_PORTAL_ID:
        raise RegistrationError(
            f"Writes to Curtis Sloane production tenant ({PROD_PORTAL_ID}) "
            f"are prohibited under FS-25.",
            code="TENANT_PRODUCTION_REFUSED",
        )
    raise RegistrationError(
        f"Writes to unrecognised portal {portal_id} are refused. "
        f"Only dev portal {DEV_PORTAL_ID} is allowed.",
        code="TENANT_UNRECOGNISED",
    )


# ---------------------------------------------------------------------------
# HubSpot create with retry (§7)
# ---------------------------------------------------------------------------

async def _create_with_retry(
    client: HubspotClient,
    properties: dict[str, Any],
    original_criteria: dict[str, Any],
) -> str:
    """
    §7 retry policy:
      - 5xx           -> retry once, then HUBSPOT_SYNC_FAIL
      - 429           -> wait Retry-After seconds, retry once, then fail
      - 4xx (non-429) -> no retry, fail immediately
      - timeout       -> fail cleanly, exception does not propagate
      - missing prop  -> report by name, distinguish from bad value
    """
    max_attempts = 2  # 1 initial + 1 retry
    attempts = 0

    while attempts < max_attempts:
        attempts += 1
        try:
            result = await client.create_contact(properties)
        except HubspotTimeoutError as exc:
            if attempts >= max_attempts:
                raise RegistrationError(
                    f"HubSpot timed out after {max_attempts} attempts: {exc}",
                    code="HUBSPOT_SYNC_FAIL",
                    payload=original_criteria,
                )
            continue
        except HubspotError as exc:
            # Missing property — name it, no retry
            if exc.missing_property:
                raise RegistrationError(
                    f"HubSpot rejected the create: property "
                    f"'{exc.missing_property}' does not exist on Contacts. "
                    f"(This is a missing-property error, not a bad-value error.)",
                    fields=[exc.missing_property],
                    code="HUBSPOT_MISSING_PROPERTY",
                    payload=original_criteria,
                )
            # 4xx (non-429) — no retry
            if 400 <= exc.status_code < 500 and exc.status_code != 429:
                raise RegistrationError(
                    f"HubSpot rejected the create ({exc.status_code}): {exc}",
                    code="HUBSPOT_REJECTED",
                    payload=original_criteria,
                )
            # 429 — wait, then retry
            if exc.status_code == 429:
                if attempts >= max_attempts:
                    raise RegistrationError(
                        f"HubSpot rate-limited after {max_attempts} attempts",
                        code="HUBSPOT_SYNC_FAIL",
                        payload=original_criteria,
                    )
                if exc.retry_after:
                    await asyncio.sleep(exc.retry_after)
                continue
            # 5xx — retry once
            if 500 <= exc.status_code < 600:
                if attempts >= max_attempts:
                    raise RegistrationError(
                        f"HubSpot persistent 5xx ({exc.status_code}) "
                        f"after {max_attempts} attempts",
                        code="HUBSPOT_SYNC_FAIL",
                        payload=original_criteria,
                    )
                continue
            # Anything else — fail
            raise RegistrationError(
                f"HubSpot error ({exc.status_code}): {exc}",
                code="HUBSPOT_SYNC_FAIL",
                payload=original_criteria,
            )

        # Success path — extract the contact ID
        contact_id = str(result.get("id", "")) if isinstance(result, dict) else ""
        if not contact_id:
            raise RegistrationError(
                "HubSpot returned no contact id",
                code="HUBSPOT_SYNC_FAIL",
                payload=original_criteria,
            )
        return contact_id

    # Defensive — the loop should always return or raise inside
    raise RegistrationError(
        "Retry loop exhausted without result",
        code="HUBSPOT_SYNC_FAIL",
        payload=original_criteria,
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def register_applicant_in_hubspot(
    criteria: dict[str, Any],
    client: HubspotClient,
) -> str:
    """
    Registration half of fn_register_applicant() per TS Amendment A-2 rev 3.

    Args:
      criteria: applicant payload dict
      client:   HubSpot client (fake in unit tests, real in production /
                integration suite)

    Returns:
      HubSpot contact ID as a non-empty string.

    Raises:
      RegistrationError with .code, .fields, and .payload attributes on
      any validation, tenant, or HubSpot failure.
    """
    # §5 "registration_date is set by the system": strip any caller-supplied
    # value before validation so it doesn't trip the "unrecognised field"
    # branch, and let the mapper set today's date.
    criteria = {k: v for k, v in criteria.items() if k != "registration_date"}

    # §2/§3/§4: validate (fails fast before any network call)
    _validate_payload(criteria)

    # §8: tenant guard BEFORE any write
    await _verify_tenant(client)

    # §5: map payload to HubSpot properties (byte-for-byte, no coercion)
    properties = _map_to_hubspot_properties(criteria)

    # §7: create with retry policy
    contact_id = await _create_with_retry(client, properties, dict(criteria))

    return contact_id
