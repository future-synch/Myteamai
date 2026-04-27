# Progress Log

> Updated: 2026-04-26

## Current focus
M3 prep — HubSpot properties mirrored into FutureSynch dev account.
Awaiting Olesya to seed test contacts (TS Section 10.2: 10 applicants + 5 properties).

## Done ✅
- M1 code: 97/97 BDD scenarios passing locally
- M1 deployed to Render: https://myteamai.onrender.com (commit 1f674ce)
- M1 runbook for John + Olesya: ACCEPTANCE_TESTS_M1.md (commit 84ccecd)
- Inspected Curtis Sloane HubSpot manually (browser, no API key swap)
- Captured 13 custom Contact properties with full options spec
- Mirrored properties into FutureSynch HubSpot via mirror_hubspot_structure.py
- minimum_size collapsed into contactinformation group (see DECISIONS.md)
- "Suppresed" typo preserved verbatim to match Curtis Sloane source

## In progress 🔄
- Olesya: seeding test contacts in FutureSynch HubSpot
- Path A/B/C decision on TS-vs-Curtis-Sloane structure mismatch

## Blocked 🚫
- M3 Tests 4–10 — blocked on test contact seeding
- M2 Test 3 — needs crm.objects.emails.read/write scope, gated by
  FutureSynch HubSpot plan tier

## Next session
- [ ] Confirm with Olesya that test contacts are seeded
- [ ] Run M3 Tests 4–10 against seeded data
- [ ] Confirm John on Path A/B/C for TS-vs-reality structure
- [ ] Plan M2 Test 3 once emails scope is unblocked

## Open questions
- What are Tickets used for in Curtis Sloane's HubSpot?
  (3,353 records, not in TS)
- Listings custom object is deactivated — confirm with Olesya whether
  MyTeamAI needs property listings tracking at all
- Does Olesya want to mirror Curtis Sloane's "Budget" semantics
  (property price tier) or pivot to TS-spec "buyer budget"?

## Live URLs
- App: https://myteamai.onrender.com
- Health: https://myteamai.onrender.com/health
- Login: agent@curtissloane.com / agent123 (test agent)
