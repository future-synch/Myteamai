"""
contacts_schema.py — canonical Contact property schema for My Team AI.

SINGLE SOURCE OF TRUTH for both migration scripts. Neither script defines a
property name or an option value of its own. If a decision changes, it changes
here once and both tenants converge on the next run.

That is deliberate. The dev/production value drift this project has been
chasing (`full_refurb` in one tenant, `Full Refurb` in the other) exists
because two schemas were maintained separately. Two migration scripts with
their own copies of the option lists would reproduce it.

--------------------------------------------------------------------------
DECISION PROVENANCE
--------------------------------------------------------------------------
Base:       Confluence 42106882 "Final decision on contact fields", v18.
Overrides:  Confluence 50823188 "TS v1.2 proposed amendments", 17 Aug 2026,
            carrying Olesya's Decision Record answers.

Where the two disagree, 50823188 wins: it is ten days newer and records
answers given directly by Olesya. One field is affected.

  works_required   42106882 : None / Cosmetic / Modernisation / Full Refurb /
                              Development Potential
                   50823188 §1.7 (Q8), 17 Aug 2026, CURRENT :
                              None / Minimal Works / Cosmetic /
                              Modernisation / Complete Refurbishment

Every other property below matches 42106882 v18 unchanged.

--------------------------------------------------------------------------
NAMING AND VALUE CONVENTION
--------------------------------------------------------------------------
Internal `value` is lower snake_case. Human-readable `label` carries the
capitalisation. Per 42106882 section 10.

Note this is the OPPOSITE of Curtis Sloane production 143653372, which stores
Title Case in the value itself. Any code writing enum values remains tenant
sensitive until production is re-optioned. FS-50's round-trip assertion is the
guard against that drift going unnoticed.

--------------------------------------------------------------------------
DECISIONS NOT ENCODED HERE, BECAUSE THEY ARE STILL OPEN
--------------------------------------------------------------------------
These are listed in OPEN_DECISIONS and printed by both scripts on every run.
None of them is guessed at. Where a decision is missing, the current state is
left alone rather than being replaced with an invention.

  budget bands          42106882 decides 8 bands (Up to 1M .. Up to 8M).
                        Both tenants hold 11 (.. up_to_10m, ten_plus).
                        50823188 §3.3 shows the boundaries are still being
                        confirmed with Olesya. `budget` is NOT touched.

  bedrooms upper bound  50823188 §3.4 (Q6) answered "Amend" with no amendment
                        given. beds_required stays a floor-only dropdown.

  lifecycle_stage       42106882 section 1 decides a custom `lifecycle_stage`
                        with 10 stages (section 1a). R5 on FS-44 overrides to
                        HubSpot's built-in `lifecyclestage`, which is
                        hubspotDefined and cannot be edited via the v3
                        Properties API. Configuring the 10 stages is a MANUAL
                        step in Settings > Properties > Lifecycle Stage.
                        NOT DONE in any tenant as at 24 Aug 2026.

  kyc_documents_outstanding
                        Deleted by these scripts, but 42106882 left the cell
                        blank. The deletion is INFERRED from R1 (compliance
                        moves to the Deal object). It is the only irreversible
                        action taken on an inference. Remove it from
                        LEGACY_DELETIONS if Olesya wants the field kept.

  buyer_fee_agreed date 42106882 section 8 requires the fee to be ticked AND
                        dated, but specifies a checkbox. No companion date
                        field is created. The commercial gate is not
                        enforceable as specified.

  legacy works mapping  50823188 §3.5 (Q8 follow-up) — how existing "Yes" and
                        blank values map to the new scale is undecided.
                        Only relevant to production, which these scripts do
                        not touch.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

GROUP = "contactinformation"

# Curtis Sloane production. Never a migration target, under any flag.
# FS-25 standing rule.
FORBIDDEN_PORTAL_IDS = {143653372}


def _opts(*pairs: Tuple[str, str]) -> List[Dict[str, Any]]:
    """Build a HubSpot options list from (label, value) pairs."""
    return [
        {"label": label, "value": value, "displayOrder": i, "hidden": False}
        for i, (label, value) in enumerate(pairs)
    ]


# ---------------------------------------------------------------------------
# The 20 custom properties these scripts own.
# ---------------------------------------------------------------------------
CANONICAL_PROPERTIES: List[Dict[str, Any]] = [
    # --- Identity and classification -------------------------------------
    {
        "name": "source",
        "label": "Source",
        "type": "enumeration",
        "fieldType": "select",
        "groupName": GROUP,
        "description": "Lead origin. 42106882 s1. Replaces free-text applicant_source.",
        "options": _opts(
            ("Rightmove", "rightmove"),
            ("Zoopla", "zoopla"),
            ("Referral", "referral"),
            ("Direct", "direct"),
            ("Other", "other"),
        ),
    },
    {
        "name": "applicant_status",
        "label": "Applicant Status",
        "type": "enumeration",
        "fieldType": "select",
        "groupName": GROUP,
        "description": "Buyer motivation. 42106882 s1. Renamed from buyer_status.",
        "options": _opts(
            ("Passive Buyer", "passive_buyer"),
            ("Motivated Buyer", "motivated_buyer"),
            ("Priority Buyer", "priority_buyer"),
        ),
    },
    {
        "name": "client_type",
        "label": "Client Type",
        "type": "enumeration",
        "fieldType": "checkbox",
        "groupName": GROUP,
        "description": "42106882 s1. Multi-select; a contact may be both buyer and seller.",
        "options": _opts(
            ("Buyer", "buyer"),
            ("Seller", "seller"),
            ("Investor", "investor"),
        ),
    },
    {
        "name": "priority_level",
        "label": "Priority Level",
        "type": "enumeration",
        "fieldType": "select",
        "groupName": GROUP,
        "description": "42106882 s1. Production calls this contact_priority_level.",
        "options": _opts(("High", "high"), ("Medium", "medium"), ("Low", "low")),
    },
    # --- Budget and financing --------------------------------------------
    {
        "name": "financing_status",
        "label": "Financing Status",
        "type": "enumeration",
        "fieldType": "select",
        "groupName": GROUP,
        "description": "42106882 s2. Values preserve the TS enum; labels are Olesya's.",
        "options": _opts(
            ("Cash Buyer", "cash"),
            ("AIP Obtained", "mortgage_aip"),
            ("Mortgage Required", "mortgage_no_aip"),
            ("Unconfirmed", "unknown"),
        ),
    },
    {
        "name": "proof_of_funds",
        "label": "Proof of Funds Received",
        "type": "bool",
        "fieldType": "booleancheckbox",
        "groupName": GROUP,
        "description": "42106882 s2. Gate before introductions.",
        "options": _opts(("Yes", "true"), ("No", "false")),
    },
    {
        "name": "buyer_fee_agreed",
        "label": "Buyer Fee Agreed (0.5%)",
        "type": "bool",
        "fieldType": "booleancheckbox",
        "groupName": GROUP,
        "description": (
            "42106882 s8, R6. Checkbox only. The Google Doc also requires a date; "
            "no date field is decided, so the gate is not fully enforceable."
        ),
        "options": _opts(("Yes", "true"), ("No", "false")),
    },
    # --- Property search criteria ----------------------------------------
    {
        "name": "beds_required",
        "label": "Beds Required",
        "type": "enumeration",
        "fieldType": "select",
        "groupName": GROUP,
        "description": (
            "42106882 s3. Floor only. Upper bound unresolved: 50823188 s3.4 (Q6) "
            "answered 'Amend' without giving the amendment."
        ),
        "options": _opts(
            ("1+", "1_plus"),
            ("2+", "2_plus"),
            ("3+", "3_plus"),
            ("4+", "4_plus"),
            ("5+", "5_plus"),
            ("6+", "6_plus"),
        ),
    },
    {
        "name": "property_types",
        "label": "Property Types",
        "type": "enumeration",
        "fieldType": "checkbox",
        "groupName": GROUP,
        "description": "42106882 s3. Multi-select. No 'any' value; empty means not yet defined (Q7).",
        "options": _opts(
            ("House", "house"),
            ("Flat", "flat"),
            ("Maisonette", "maisonette"),
            ("Mews", "mews"),
            ("Penthouse", "penthouse"),
            ("Townhouse", "townhouse"),
        ),
    },
    {
        "name": "area",
        "label": "Area",
        "type": "enumeration",
        "fieldType": "checkbox",
        "groupName": GROUP,
        "description": (
            "42106882 s3. Closes the geographic gap TS v1.1 had in both matching "
            "directions. Listings has no Area property yet; see FS-45."
        ),
        "options": _opts(
            ("Holland Park", "holland_park"),
            ("Notting Hill", "notting_hill"),
            ("Kensington", "kensington"),
            ("Chelsea", "chelsea"),
            ("Other", "other"),
        ),
    },
    {
        "name": "outside_space",
        "label": "Outside Space",
        "type": "enumeration",
        "fieldType": "checkbox",
        "groupName": GROUP,
        "description": (
            "42106882 s3. Narrowing of free-text applicant_must_have. Parking is NOT "
            "here: Q19 puts it on Listings."
        ),
        "options": _opts(
            ("Garden", "garden"),
            ("Terrace", "terrace"),
            ("Balcony", "balcony"),
            ("Roof Terrace", "roof_terrace"),
            ("Patio", "patio"),
            ("Communal", "communal"),
            ("None", "none"),
        ),
    },
    {
        "name": "sqft",
        "label": "Minimum Size (sqft)",
        "type": "number",
        "fieldType": "number",
        "groupName": GROUP,
        "description": "42106882 s3. Minimum floor area. Renamed from minimum_size_sqft.",
    },
    {
        # ---------------------------------------------------------------
        # THE ONE FIELD THAT CHANGED SINCE THE FS-44 SCRIPT.
        # 50823188 s1.7 (Q8), 17 Aug 2026, supersedes 42106882.
        # Retired: full_refurb, development_potential
        # Added:   minimal_works, complete_refurbishment
        # ---------------------------------------------------------------
        "name": "works_required",
        "label": "Works Required",
        "type": "enumeration",
        "fieldType": "select",
        "groupName": GROUP,
        "description": (
            "Work the applicant will accept. Ceiling, not equality: someone accepting "
            "Complete Refurbishment must also see properties needing nothing. "
            "Five-point scale per Olesya Q8, 50823188 s1.7, 17 Aug 2026."
        ),
        "options": _opts(
            ("None", "none"),
            ("Minimal Works", "minimal_works"),
            ("Cosmetic", "cosmetic"),
            ("Modernisation", "modernisation"),
            ("Complete Refurbishment", "complete_refurbishment"),
        ),
    },
    # --- Timeline and chain ----------------------------------------------
    {
        "name": "timeline",
        "label": "Timeline",
        "type": "enumeration",
        "fieldType": "select",
        "groupName": GROUP,
        "description": (
            "42106882 s4. Single dropdown replacing three overlapping timeline fields. "
            "fieldType is select, not checkbox: one timeline per applicant."
        ),
        "options": _opts(
            ("As soon as possible", "as_soon_as_possible"),
            ("Within 3 months", "within_3_months"),
            ("3-6 months", "3_6_months"),
            ("6-12 months", "6_12_months"),
            ("Still Dreaming", "still_dreaming"),
        ),
    },
    {
        "name": "chain_status",
        "label": "Chain Status",
        "type": "enumeration",
        "fieldType": "select",
        "groupName": GROUP,
        "description": "42106882 s5. From the Google Doc; no equivalent in either tenant.",
        "options": _opts(
            ("Chain Free", "chain_free"),
            ("Selling", "selling"),
            ("Sold STC", "sold_stc"),
            ("Renting", "renting"),
            ("First Purchase", "first_purchase"),
        ),
    },
    {
        "name": "property_to_sell",
        "label": "Property to Sell?",
        "type": "bool",
        "fieldType": "booleancheckbox",
        "groupName": GROUP,
        "description": "42106882 s5. Clears the trailing-underscore defect in property_to_sell_.",
        "options": _opts(("Yes", "true"), ("No", "false")),
    },
    # --- Communications ---------------------------------------------------
    {
        "name": "preferred_channel",
        "label": "Preferred Channel",
        "type": "enumeration",
        "fieldType": "select",
        "groupName": GROUP,
        "description": "42106882 s7. Matches the TS enum exactly. No 'any' value.",
        "options": _opts(
            ("Email", "email"),
            ("Phone", "phone"),
            ("WhatsApp", "whatsapp"),
        ),
    },
    {
        "name": "communication_frequency",
        "label": "Communication Frequency",
        "type": "enumeration",
        "fieldType": "select",
        "groupName": GROUP,
        "description": (
            "42106882 s7. NOTE: no writer. Q2 puts the frequency promise on office "
            "procedures, not the platform. Field exists for manual agent use only."
        ),
        "options": _opts(
            ("Immediately on match", "immediately_on_match"),
            ("Weekly", "weekly"),
            ("Fortnightly", "fortnightly"),
            ("Monthly", "monthly"),
        ),
    },
    # --- Operational tracking --------------------------------------------
    {
        "name": "last_match_sent",
        "label": "Last Match Sent",
        "type": "date",
        "fieldType": "date",
        "groupName": GROUP,
        "description": (
            "42106882 s8. NOTE: no writer. Gmail is the sole record of client email "
            "and the platform does not track sends. Manual agent use only."
        ),
    },
    {
        "name": "registration_date",
        "label": "Registration Date",
        "type": "date",
        "fieldType": "date",
        "groupName": GROUP,
        "description": "42106882 s8. Distinct from HubSpot createdate.",
    },
]


# ---------------------------------------------------------------------------
# Properties the canonical schema requires but these scripts do not create.
# They already exist in both tenants with correct configuration, and are left
# untouched so no live option set is rewritten without a decision.
# ---------------------------------------------------------------------------
ASSUMED_PRESENT: Dict[str, str] = {
    "budget": "Band set unresolved (8 decided vs 11 present). 50823188 s3.3. NOT touched.",
    "contact_status": "42106882 s1. Existing option set already matches.",
    "pipeline_status": "42106882 s1. Existing set matches, including the 'Suppresed' typo.",
    "type_of_customer": "42106882 s1. Existing set matches. Row still marked PROPOSED.",
    "notes": "42106882 s7. Free text, no options.",
}


# ---------------------------------------------------------------------------
# Legacy properties to remove. Only relevant to a tenant still in the
# pre-FS-44 state. Script 2 will find none of these.
# ---------------------------------------------------------------------------
LEGACY_DELETIONS: List[Tuple[str, str]] = [
    ("applicant_bedrooms_min", "R2. Superseded by beds_required."),
    ("applicant_bedrooms_max", "R2. Superseded by beds_required."),
    ("applicant_budget_gbp", "R2. Superseded by banded budget."),
    ("applicant_source", "Renamed to source; free text becomes a dropdown."),
    ("applicant_financing", "Renamed to financing_status."),
    ("applicant_property_types", "Renamed to property_types."),
    ("applicant_preferred_channel", "Renamed to preferred_channel."),
    ("applicant_timeline_weeks", "Replaced by banded timeline."),
    ("applicant_must_have", "Replaced by outside_space. NARROWING: free text to closed enum."),
    ("minimum_size_sqft", "Renamed to sqft."),
    ("willing_to_do_works", "Renamed to works_required; new option set."),
    ("buyer_status", "Renamed to applicant_status."),
    ("property_to_sell_", "Renamed to property_to_sell; clears trailing underscore."),
    ("timeline", "fieldType checkbox to select. Must be dropped before recreation."),
    ("when_are_you_thinking_of_moving_", "No need. Also clears the wrong-options defect."),
    ("dream_home_notes", "No need. Overlapped must_have."),
    ("looking_to_sell", "No need. Overlapped property_to_sell."),
    ("kyc_status", "R1. Compliance moves to the Deal object."),
    ("kyc_documents_outstanding", "INFERRED from R1, not explicitly decided. See module docstring."),
]


# ---------------------------------------------------------------------------
# Option values retired by a decision, mapped to their replacement where one
# exists. Used to detect records holding a value the schema no longer offers.
# None means no automatic mapping is possible and a human must decide.
# ---------------------------------------------------------------------------
RETIRED_OPTION_VALUES: Dict[str, Dict[str, str | None]] = {
    "works_required": {
        # Q8, 50823188 s1.7. Direct successor: a full refurbishment is the
        # same concept renamed, so this one maps cleanly.
        "full_refurb": "complete_refurbishment",
        # No successor. "Development Potential" describes planning upside, not
        # a level of work, and Olesya's five-point scale drops it. A-2's open
        # items already question whether it belonged on the scale at all.
        "development_potential": None,
    },
}


OPEN_DECISIONS: List[str] = [
    "budget band set: 42106882 decides 8, both tenants hold 11. 50823188 s3.3 unconfirmed.",
    "beds_required upper bound: 50823188 s3.4 (Q6) answered 'Amend' with no amendment.",
    "lifecycle_stage: 42106882 s1a decides 10 custom stages. R5 uses HubSpot's built-in "
    "instead. Configuring the stages is a MANUAL step and has not been done.",
    "kyc_documents_outstanding deletion is INFERRED from R1, not decided by Olesya.",
    "buyer_fee_agreed has no companion date field; the commercial gate is unenforceable.",
    "works_required legacy value mapping (Yes / blank) undecided. 50823188 s3.5.",
]


EXPECTED_FINAL_COUNT = len(CANONICAL_PROPERTIES) + len(ASSUMED_PRESENT)  # 25
