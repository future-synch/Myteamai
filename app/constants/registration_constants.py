"""
FS-50 — Canonical enum constants for register_applicant_in_hubspot().

This is the SINGLE SOURCE OF TRUTH for every option value the registration
module accepts, validates against, and writes to HubSpot. When Olesya
answers Q5 (budget bands), Q9 (tenure_acceptable), or the Title-Case-vs-
snake_case decision, only this file changes — the Gherkin scenarios,
step definitions, and function code all pick up the change without edits.

Casing rule (recommended, pending Olesya sign-off on page 48693249):
Title Case for internal HubSpot values. This must exactly match the
option values configured on the HubSpot Contacts object properties —
enum comparison is EXACT, not case-insensitive. If Contacts and
Listings disagree on casing, the join silently returns nothing while
both look correct in the HubSpot interface. See §4 "Enum comparison is
exact" scenario for the guard.

Do NOT reference any of these values as string literals anywhere in
app/services/hubspot_registration.py — one Gherkin scenario asserts
the absence of literals directly.
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
# Enum option sets
# ---------------------------------------------------------------------------

VALID_FINANCING_STATUS: list[str] = [
    "Cash",
    "Mortgage AIP",
    "Mortgage No AIP",
    "Unknown",
]

VALID_PREFERRED_CHANNEL: list[str] = [
    "Email",
    "Phone",
    "WhatsApp",
]

VALID_SOURCE: list[str] = [
    "Rightmove",
    "Zoopla",
    "Referral",
    "Direct",
    "Other",
]

VALID_PROPERTY_TYPES: list[str] = [
    "House",
    "Flat",
    "Maisonette",
    "Any",
]

VALID_BEDS_REQUIRED: list[str] = [
    "1+",
    "2+",
    "3+",
    "4+",
    "5+",
]

# Placeholder until Q5 (Olesya). Change only this line when decided.
VALID_BUDGET: list[str] = [
    "Under £500k",
    "£500k–£1M",
    "£1M–£2M",
    "£2M–£3M",
    "£3M–£5M",
    "£5M+",
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
