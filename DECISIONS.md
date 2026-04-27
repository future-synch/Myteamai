# Decision Log

Newest first. Each entry: date, decision, why, alternatives considered.

---

## 2026-04-26 — Preserved "Suppresed" typo verbatim

**Decision:** When mirroring Curtis Sloane HubSpot properties, copied the
misspelled option label "Suppresed" exactly as-is into FutureSynch.

**Why:** Field values must match Curtis Sloane's source data byte-for-byte.
At M5 we point HUBSPOT_API_KEY at Curtis Sloane's account — any
"corrected" label would silently fail to match real records and break
filtering, matching, and reporting.

**Alternative considered:** Fix to "Suppressed" in FutureSynch and add a
normalisation layer. Rejected — adds code complexity for a cosmetic gain
and creates dev-vs-prod schema drift.

---

## 2026-04-26 — Collapsed minimum_size into contactinformation group

**Decision:** Mirror script places the `minimum_size` property under the
existing `contactinformation` group rather than creating a dedicated
`minimum_size` group.

**Why:** Curtis Sloane HubSpot has it ungrouped in practice; HubSpot
requires every property to live in a group. `contactinformation` is the
default catch-all and keeps the FutureSynch UI uncluttered. No semantic
loss — the property name itself carries the meaning.

**Alternative considered:** Create a one-off `minimum_size` group to
match a literal reading of the schema export. Rejected — single-property
groups are noise in the HubSpot sidebar and Olesya flagged them as
confusing during inspection.

---

## 2026-04-26 — Manual HubSpot inspection vs API token swap

**Decision:** Inspected Curtis Sloane HubSpot via browser UI rather than
provisioning an API token and running schema_inspector.py against their
account.

**Why:** Avoided needing a Curtis Sloane API token + .env key swap.
Read-only browser inspection has zero risk to their production account.
Captured the same data via HubSpot's "Copy option labels and internal
names" feature, then transcribed into mirror_hubspot_structure.py.

**Alternative considered:** Create a read-only Private App in Curtis
Sloane HubSpot and run schema_inspector.py. Rejected — manual approach
gave the same info without any credential handling, audit trail, or
risk of accidental writes.

---

## 2026-04-XX — [next decision]
