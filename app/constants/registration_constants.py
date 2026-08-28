"""
FS-50 — Canonical enum constants for register_applicant_in_hubspot().

This is the SINGLE SOURCE OF TRUTH for every option value the registration
module accepts, validates against, and writes to HubSpot. When Olesya
answers Q5 (budget bands) or the option sets shift in future migrations,
only this file changes — the Gherkin scenarios, step definitions, and
function code all pick up the change without edits.

Casing rule (RESOLVED 2026-08-28 after FS-44 completion):
Internal HubSpot values are lowercase snake_case. Human-readable labels
carry the capitalisation on the HubSpot side. Every value below matches
the option set actually configured on HubSpot dev (portal 148226118)
after FS-44 ran successfully. Enum comparison is EXACT, not
case-insensitive — see §4 "Enum comparison is exact" scenario for the
guard. If Contacts and Listings ever disagree on casing, the join
silently returns nothing while both look correct in the HubSpot
interface.

Do NOT reference any of these values as string literals anywhere in
app/services/hubspot_registration.py — one Gherkin scenario asserts
the absence of literals directly.

Value source: scripts/contacts_schema.py (FS-44 canonical schema),
mirrored via GET /crm/v3/properties/contacts/* against HubSpot dev
after --apply --confirm-deletes on 2026-08-28.
"""

# ---------------------------------------------------------------------------
# Fields on the applicant payload
# ---------------------------------------------------------------------------

REQUIRED_FIELDS: list[str] = [
    "full_name",
    "email",
    "phone",
    "budget",
    "beds_required",
    "property_types",
    "financing_status",
    "preferred_channel",
    "source",
]

OPTIONAL_FIELDS: list[str] = [
    "beds_max",
    "must_have",
    "timeline_weeks",
]


# ---------------------------------------------------------------------------
# Enum option sets — lowercase snake_case matches HubSpot dev exactly
# ---------------------------------------------------------------------------

VALID_FINANCING_STATUS: list[str] = [
    "cash",
    "mortgage_aip",
    "mortgage_no_aip",
    "unknown",
]

VALID_PREFERRED_CHANNEL: list[str] = [
    "email",
    "phone",
    "whatsapp",
]

VALID_SOURCE: list[str] = [
    "rightmove",
    "zoopla",
    "referral",
    "direct",
    "other",
]

# Changed 2026-08-28: FS-44 dropped "any", added mews/penthouse/townhouse.
VALID_PROPERTY_TYPES: list[str] = [
    "house",
    "flat",
    "maisonette",
    "mews",
    "penthouse",
    "townhouse",
]

# Changed 2026-08-28: FS-44 uses "N_plus" format (not "N+") and adds 6_plus.
VALID_BEDS_REQUIRED: list[str] = [
    "1_plus",
    "2_plus",
    "3_plus",
    "4_plus",
    "5_plus",
    "6_plus",
]

# Aligned to HubSpot dev current state (11 cumulative-ceiling bands).
# Q5 (Olesya) still open: 42106882 decides 8 bands, dev holds 11.
# FS-44 deliberately left budget untouched pending Q5. When Q5 resolves,
# this list and the HubSpot dev property must update together.
VALID_BUDGET: list[str] = [
    "up_to_1m",
    "up_to_2m",
    "up_to_3m",
    "up_to_4m",
    "up_to_5m",
    "up_to_6m",
    "up_to_7m",
    "up_to_8m",
    "up_to_9m",
    "up_to_10m",
    "ten_plus",
]


# ---------------------------------------------------------------------------
# Multi-value fields — accept a list of values from their VALID_* set
# ---------------------------------------------------------------------------

MULTI_VALUE_FIELDS: set[str] = {"property_types"}


# ---------------------------------------------------------------------------
# Mapping from applicant-payload field name to configured VALID set
# Consumed by the registration validator and the enum tests.
# ---------------------------------------------------------------------------

ENUM_SETS: dict[str, list[str]] = {
    "budget":            VALID_BUDGET,
    "beds_required":     VALID_BEDS_REQUIRED,
    "property_types":    VALID_PROPERTY_TYPES,
    "financing_status":  VALID_FINANCING_STATUS,
    "preferred_channel": VALID_PREFERRED_CHANNEL,
    "source":            VALID_SOURCE,
}


# ---------------------------------------------------------------------------
# HubSpot portal IDs — tenant safety guard
# ---------------------------------------------------------------------------

DEV_PORTAL_ID: int = 148226118    # FutureSynch dev (writes allowed)
PROD_PORTAL_ID: int = 143653372   # Curtis Sloane production (FS-25, writes prohibited)


# ---------------------------------------------------------------------------
# HubSpot property names the registration code writes to.
# Kept here so §10's live check ("every property the code writes exists
# in the dev tenant") has a single list to iterate.
#
# NOTE 2026-08-28: beds_max, must_have, timeline_weeks are NOT in the
# post-FS-44 HubSpot schema. FS-44 replaced them with beds_required (floor
# only), outside_space (enum), and timeline (banded dropdown). Writing to
# these three from FS-50 will trigger a missing-property error against the
# real HubSpot dev tenant. Follow-up: either drop these from OPTIONAL_FIELDS,
# or map them to the FS-44 replacements. Tracked as FS-45 spec amendment.
# ---------------------------------------------------------------------------

HUBSPOT_PROPERTY_NAMES: list[str] = [
    "firstname",
    "lastname",
    "email",
    "phone",
    "budget",
    "beds_required",
    "property_types",
    "financing_status",
    "preferred_channel",
    "source",
    "registration_date",
    "beds_max",
    "must_have",
    "timeline_weeks",
]
