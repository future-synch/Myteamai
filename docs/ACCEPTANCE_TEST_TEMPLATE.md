# Acceptance Test Runbook — TEMPLATE

> Copy this file to `docs/M{n}_ACCEPTANCE_RUNBOOK.md` and replace every `{placeholder}` token.
> Delete this banner before signing.

**Milestone:** M{n}
**Tests covered:** {N1}, {N2}, …
**Ticket:** FS-{nn}
**Created:** {YYYY-MM-DD} by {author}
**TS reference:** Section {x.y} of `MyTeamAI_TZ_v1.1.docx`

---

## Roles

The Tester runs every test input themselves. The Observer does not type, click, or assist. The Reviewer signs off after the run.

| Role | Person | Responsibility |
|---|---|---|
| **Tester** | {name} | Runs every test input themselves. No coaching from observer. |
| **Observer** | {name} | Watches silently. Does not type, click, or assist. |
| **Reviewer** | {name} | Countersigns the result. |

---

## Environment

| Item | Value |
|---|---|
| URL | {https://…} |
| Login | {user / pass} |
| Backend HubSpot | {FutureSynch sandbox / Curtis Sloane prod} |
| Backend Claude | {real / mock / record} |
| Date of run | {YYYY-MM-DD} |
| Git commit under test | {hash} |
| Render deploy event ID | {from dashboard} |

---

## Pre-conditions (must be true before starting)

- [ ] {e.g. Anthropic credits topped up at console.anthropic.com}
- [ ] {e.g. HubSpot Private App scopes include emails.read/write}
- [ ] {e.g. Render service shows last deploy = {commit hash}}
- [ ] Tester has reviewed input rules — minimum 3 varied inputs per test, 9 of 10 must pass
- [ ] Observer has NOT pre-shared any test data with the tester

---

## Test {N} — {short title}

| Field | Detail |
|---|---|
| What to type | `{exact template, e.g. "Welcome new client — [name], came through [source]"}` |
| Varied inputs needed | At least 3 different {names / sources / budgets / …} |
| Expected output | {what should appear} |
| Pass conditions | {timing + content + side-effect criteria} |
| Spec reference | TS §{x.y} |

| Input # | {var 1} | {var 2} | {check 1} | {check 2} | {check 3} | PASS/FAIL |
|---|---|---|---|---|---|---|
| 1 |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |

*(Duplicate the entire Test block — heading, fields table, results table — for every test in the milestone.)*

---

## Tester verification (tester completes — countersign required)

I, **{tester name}**, confirm that:

- [ ] I personally typed every input above. The observer did not assist.
- [ ] I used data the observer had not seen in advance.
- [ ] I waited for each response and recorded the outcome honestly.
- [ ] I screenshotted any failing scenario and attached below.
- [ ] I did not retry a failed input without recording the original failure.

**Signature (typed name + date):** _______________________

**Screenshots / evidence:**

```
(paste links or filenames here)
```

---

## Observer countersign

I, **{observer name}**, confirm that:

- [ ] I observed the tester throughout. I did not type, click, or coach.
- [ ] The inputs used match what the tester wrote in the input columns above.
- [ ] The PASS/FAIL outcomes match what I saw on screen.
- [ ] I attest the tester ran every scenario themselves.

**Signature (typed name + date):** _______________________

---

## Reviewer sign-off

| Test | Tester result | Observer agrees | Final verdict |
|---|---|---|---|
| Test {N1} | PASS / FAIL | YES / NO | ☐ PASS  ☐ FAIL |
| Test {N2} | PASS / FAIL | YES / NO | ☐ PASS  ☐ FAIL |
| Test {N3} | PASS / FAIL | YES / NO | ☐ PASS  ☐ FAIL |

**Overall M{n} decision:** ☐ ACCEPT — release payment · ☐ REJECT — issues below

**Issues found / notes:**

```
(reviewer writes here)
```

**Reviewer signature + date:** _______________________

---

*Template version: 1.0 — Future Synch Ltd*
