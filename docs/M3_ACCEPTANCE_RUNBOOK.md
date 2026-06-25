# M3 Acceptance Runbook — Tests 4, 6, 7, 8, 9, 10

> **STATUS: SHELL — needs population by John Small.**
> Per-test pass conditions and expected outputs are placeholders below.

**Milestone:** M3
**Tests covered:** 4, 6, 7, 8, 9, 10 *(Test 5 is folded into Test 4's register flow — no separate entry)*
**Ticket:** FS-{populate}
**Created:** 2026-06-25 (shell)
**TS reference:** Section 10.3 of `MyTeamAI_TZ_v1.1.docx`

---

## Roles

| Role | Person | Responsibility |
|---|---|---|
| **Tester** | Olesya Kovalskaya | Runs every test input themselves. No coaching from observer. |
| **Observer** | Manthan Bhanushali | Watches silently. Does not type, click, or assist. |
| **Reviewer** | John Small | Countersigns the result. |

---

## Environment

| Item | Value |
|---|---|
| URL | https://myteamai.onrender.com |
| Login | `agent@curtissloane.com` / `agent123` |
| Backend HubSpot | FutureSynch sandbox — **seeded with 10 applicants + 5 properties** (CLAUDE.md milestone map) |
| Backend Claude | real (live `claude-sonnet-4-6`) |
| Date of run | _____________ |
| Git commit under test | _____________ |
| Render deploy event ID | _____________ |

---

## Pre-conditions

- [ ] Anthropic API credits topped up
- [ ] HubSpot sandbox contains the **10 seeded applicants** required by Tests 6, 7, 10
- [ ] HubSpot sandbox contains the **5 seeded properties** required by Tests 6, 8
- [ ] Seeded contacts span: at least 1 with complete KYC, at least 1 with incomplete KYC, mixed budgets, mixed bedroom requirements
- [ ] Render service shows last deploy is the commit being tested
- [ ] Tester has reviewed input rules — minimum 3 varied inputs per test, 9 of 10 must pass
- [ ] Observer has NOT pre-shared any test data with the tester
- [ ] *(blocker as of 2026-06-25)* `fn_match_applicants` returns scored matches (currently returns unscored list — FS-{tbd}). Do not run Test 6/7 until fixed.

---

## Test 4 — Register applicant (full form)

| Field | Detail |
|---|---|
| What to type | Use **Register Applicant** form with full profile: name, email, phone, budget, bedrooms, property types, financing, channel, source |
| Varied inputs needed | At least 3 different applicants varying budget, bedrooms, financing, source |
| Expected output | HubSpot contact created, contact ID returned, KYC checklist initialised, top property matches returned |
| Pass conditions | _**TBD — populate per TS §5.2**_ |
| Spec reference | TS §4.3 (REGISTER_APPLICANT), §5.2 |

| Input # | Name | Budget | Beds | Contact created? | KYC checklist returned? | Top matches returned? | PASS/FAIL |
|---|---|---|---|---|---|---|---|
| 1 |  |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |  |

---

## Test 6 — Match applicants for known property

| Field | Detail |
|---|---|
| What to type | `Match applicants for [property_ref]` — use a seeded property address |
| Varied inputs needed | At least 3 different seeded properties |
| Expected output | Ranked list of applicants with match_score (0.0-1.0) and readable match_reason |
| Pass conditions | _**TBD — populate per TS §5.3**_ |
| Spec reference | TS §4.3 (MATCH_APPLICANTS), §5.3 |

| Input # | Property ref | Matches returned (count) | Scored 0.0-1.0? | Reasons readable? | PASS/FAIL |
|---|---|---|---|---|---|
| 1 |  |  |  |  |  |
| 2 |  |  |  |  |  |
| 3 |  |  |  |  |  |

---

## Test 7 — Match flags KYC-incomplete applicants

| Field | Detail |
|---|---|
| What to type | Same as Test 6, but use a seeded property that matches the KYC-incomplete applicant |
| Varied inputs needed | At least 3 inputs that include the KYC-incomplete applicant in results |
| Expected output | KYC-incomplete applicant appears in results with `kyc_complete: false`, and a clear indicator they cannot progress |
| Pass conditions | _**TBD — populate per TS §5.3**_ |
| Spec reference | TS §5.3 + §5.6 (KYC) |

| Input # | Property ref | KYC-incomplete shown? | Flagged as can't-progress? | PASS/FAIL |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |

---

## Test 8 — Valuation brief

| Field | Detail |
|---|---|
| What to type | `Valuation briefing for [address] [postcode]` OR use the Valuation form |
| Varied inputs needed | At least 3 different properties of differing types (house / flat / maisonette) |
| Expected output | Structured brief with comparables, price range, positioning notes, time-on-market estimate |
| Pass conditions | _**TBD — populate per TS §5.4**_ |
| Spec reference | TS §4.3 (VALUATION_BRIEF), §5.4 |

| Input # | Address | Type | Comparables count | Price range present? | PASS/FAIL |
|---|---|---|---|---|---|
| 1 |  |  |  |  |  |
| 2 |  |  |  |  |  |
| 3 |  |  |  |  |  |

---

## Test 9 — Draft outreach

| Field | Detail |
|---|---|
| What to type | `Draft a [channel] to [name], [context]` — vary channel across handwritten_note, email, letter |
| Varied inputs needed | At least 3 inputs covering all 3 channels and at least 2 recipient types |
| Expected output | Channel-appropriate draft, addressed to the named recipient, signed by agent, no placeholders |
| Pass conditions | _**TBD — populate per TS §5.5**_ |
| Spec reference | TS §4.3 (DRAFT_OUTREACH), §5.5 |

| Input # | Recipient | Channel | Length appropriate? | Tone correct? | No placeholders? | PASS/FAIL |
|---|---|---|---|---|---|---|
| 1 |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |

---

## Test 10 — KYC status check

| Field | Detail |
|---|---|
| What to type | `KYC status for [name]` — vary across known-complete, known-incomplete, and unknown contacts |
| Varied inputs needed | At least 3 inputs covering all 3 cases (complete / incomplete / unknown) |
| Expected output | For complete: `can_progress: true`, empty outstanding list. For incomplete: outstanding items listed. For unknown: clear "not found" error. |
| Pass conditions | _**TBD — populate per TS §5.6**_ |
| Spec reference | TS §4.3 (KYC_STATUS), §5.6 |

| Input # | Name queried | Case (complete/incomplete/unknown) | Status returned matches case? | PASS/FAIL |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |

---

## Tester verification (Olesya completes — countersign required)

I, **Olesya Kovalskaya**, confirm that:

- [ ] I personally typed every input above. Manthan did not assist.
- [ ] I used data Manthan had not seen in advance.
- [ ] I waited for each response and recorded the outcome honestly.
- [ ] I screenshotted any failing scenario and attached below.
- [ ] I did not retry a failed input without recording the original failure.

**Signature (typed name + date):** _______________________

**Screenshots / evidence:**

```
(paste links or filenames here)
```

---

## Observer countersign (Manthan)

I, **Manthan Bhanushali**, confirm that:

- [ ] I observed Olesya throughout. I did not type, click, or coach.
- [ ] The inputs Olesya used match what is written in the input columns above.
- [ ] The PASS/FAIL outcomes match what I saw on screen.
- [ ] I attest that Olesya ran every scenario herself.

**Signature (typed name + date):** _______________________

---

## Reviewer sign-off (John Small)

| Test | Tester result | Observer agrees | Final verdict |
|---|---|---|---|
| Test 4 | PASS / FAIL | YES / NO | ☐ PASS  ☐ FAIL |
| Test 6 | PASS / FAIL | YES / NO | ☐ PASS  ☐ FAIL |
| Test 7 | PASS / FAIL | YES / NO | ☐ PASS  ☐ FAIL |
| Test 8 | PASS / FAIL | YES / NO | ☐ PASS  ☐ FAIL |
| Test 9 | PASS / FAIL | YES / NO | ☐ PASS  ☐ FAIL |
| Test 10 | PASS / FAIL | YES / NO | ☐ PASS  ☐ FAIL |

**Overall M3 decision:** ☐ ACCEPT — release M3 payment · ☐ REJECT — issues below

**Issues found / notes:**

```
(reviewer writes here)
```

**Reviewer signature + date:** _______________________

---

*Future Synch Ltd*
