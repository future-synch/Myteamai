# M2 Acceptance Runbook — Tests 1, 2, 3

**Milestone:** M2
**Tests covered:** 1, 2, 3
**Ticket:** FS-13
**Created:** 2026-06-22 by John Small (Claude Web PM)
**TS reference:** Section 10.3 of `MyTeamAI_TZ_v1.1.docx`

---

## Roles

| Role | Person | Responsibility |
|---|---|---|
| **Tester** | Olesya Kovalskaya (client) | Runs every test input themselves. No coaching from observer. |
| **Observer** | Manthan Bhanushali | Watches silently. Does not type, click, or assist. |
| **Reviewer** | John Small | Countersigns the result. |

---

## Environment

| Item | Value |
|---|---|
| URL | https://myteamai.onrender.com |
| Login | `agent@curtissloane.com` / `agent123` |
| Backend HubSpot | FutureSynch sandbox (app-eu1.hubspot.com, ID 148226118) |
| Backend Claude | real (live `claude-sonnet-4-6`) |
| Date of run | _____________ |
| Git commit under test | _____________ (read from Render dashboard → Events) |
| Render deploy event ID | _____________ |

---

## Pre-conditions (must be true before starting)

- [ ] Anthropic API credits topped up at console.anthropic.com (Tests 1+2 fail immediately without)
- [ ] HubSpot Private App scopes include `crm.objects.contacts.read` + `crm.objects.contacts.write`
- [ ] **For Test 3 only:** HubSpot Private App also has `crm.objects.emails.read` + `crm.objects.emails.write` (plan-tier dependent)
- [ ] Render service shows last deploy is the commit being tested
- [ ] Tester has reviewed input rules — minimum 3 varied inputs per test, 9 of 10 must pass
- [ ] Observer has NOT pre-shared any test data with the tester
- [ ] Render service has been pinged once in the last 5 minutes (avoids cold-start affecting timings)

---

## Test 1 — Welcome message, minimum input

| Field | Detail |
|---|---|
| What to type | `Welcome new client — [name], came through [source]` |
| Varied inputs needed | At least 3 different names AND sources (from: Rightmove, Zoopla, Referral, Direct, Other) |
| Expected output | Draft welcome message addressed to the named client, signed by the agent, professional tone |
| Pass conditions | Draft appears in under 8 seconds. No placeholder text (`[name]`, `INSERT`, `TODO`) visible. Agent name correct. |
| Spec reference | TS §4.3 (WELCOME_CLIENT), §5.1 (validation) |

| Input # | Name used | Source used | Under 8s? | No placeholders? | Agent name correct? | PASS/FAIL |
|---|---|---|---|---|---|---|
| 1 |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |

---

## Test 2 — Welcome message with budget and timeline

| Field | Detail |
|---|---|
| What to type | `Welcome [name], [source], budget [amount], wants to move [timeline]` |
| Varied inputs needed | At least 3 different budgets AND timelines |
| Expected output | Draft references budget AND timeline naturally in body — not as bullet list |
| Pass conditions | Budget present in draft. Timeline present in draft. No hallucinated details (no fictional addresses, viewings, etc.) |
| Spec reference | TS §4.3, §5.1 (budget min £100k) |

| Input # | Name | Budget | Timeline | Budget in draft? | Timeline in draft? | No hallucination? | PASS/FAIL |
|---|---|---|---|---|---|---|---|
| 1 |  |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |  |

---

## Test 3 — Welcome dispatch to HubSpot

| Field | Detail |
|---|---|
| What to type | Same input as Test 2 — use the **Welcome Client form** in the chat UI, toggle **dispatch ON** |
| Varied inputs needed | At least 3 different names |
| Expected output | HubSpot contact created in the FutureSynch sandbox. Welcome email queued in HubSpot drafts. |
| Pass conditions | Contact visible in FutureSynch sandbox within 30 seconds. Email visible in HubSpot drafts. **CHECK FUTURESYNCH SANDBOX — NOT CURTIS SLOANE PRODUCTION.** |
| Spec reference | TS §4.3, §6 (dispatch flow) |

| Input # | Name used | Contact in HubSpot within 30s? | Email in HubSpot drafts? | PASS/FAIL |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |

---

## Tester verification (Olesya completes — countersign required)

I, **Olesya Kovalskaya**, confirm that:

- [ ] I personally typed every input above. Manthan did not assist.
- [ ] I used names and budgets Manthan had not seen in advance.
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
| Test 1 | PASS / FAIL | YES / NO | ☐ PASS  ☐ FAIL |
| Test 2 | PASS / FAIL | YES / NO | ☐ PASS  ☐ FAIL |
| Test 3 | PASS / FAIL | YES / NO | ☐ PASS  ☐ FAIL |

**Overall M2 decision:** ☐ ACCEPT — release M2 payment · ☐ REJECT — issues below

**Issues found / notes:**

```
(reviewer writes here)
```

**Reviewer signature + date:** _______________________

---

*Based on FS-13 (22 June 2026) — Future Synch Ltd*
