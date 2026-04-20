# M1 Acceptance Test Runbook

**For:** John Small (Technical Adviser) + Olesya Kovalskaya (Client)
**Tester runs the tests. Developer observes.** (TS Section 10.1)
**Date prepared:** 20 April 2026
**Milestone:** M1 — First Payment Gate

---

## What's being tested

Per **TS Section 10.3**, two acceptance tests gate the M1 payment:

| # | Test | Spec pass condition |
|---|---|---|
| 11 | Unknown intent | `UNKNOWN_INTENT` error code. Capability list shows all 6 functions. |
| 12 | Validation error | Form does not submit. Error visible on field. No API call made. |

Neither test requires HubSpot data, Claude API credits, or any external service. **M1 is deliberately designed to run on pure Python logic only** — so it is verifiable by anyone, anywhere, anytime.

---

## How to run the tests

### Environment

**Live URL:** https://myteamai.onrender.com
*(Alternative URL, same code: https://myteamai-8l20.onrender.com)*

**Login credentials (MVP hardcoded, replaced before M5 go-live):**

| Role | Email | Password |
|---|---|---|
| Agent | `agent@curtissloane.com` | `agent123` |
| Admin | `admin@curtissloane.com` | `admin123` |

---

## Test 11 — Unknown Intent

### Protocol

1. Open the live URL → sign in with the agent credentials
2. You'll land on the chat screen. At the bottom there's a text box labelled *"Or type your request here…"*
3. Paste each input below one at a time, press **Send**, record the outcome

### Required scenarios (pass condition per TS §10.3)

| # | Input | Expected | Pass/Fail |
|---|---|---|---|
| 1 | `What is the weather in London?` | Red error card with 6-item capability list | ☐ |

✅ **Spec pass condition:** UNKNOWN_INTENT error code + capability list showing all 6 functions.

### Additional scenarios (broader Gherkin coverage — optional)

| # | Input | Expected behaviour | Pass/Fail |
|---|---|---|---|
| 2 | `Hello` | Error card with warm greeting: *"Hello! Here's what I can help you with:"* | ☐ |
| 3 | `Thanks for your help` | Error card with polite response: *"You're welcome! Let me know if you need anything else."* | ☐ |
| 4 | `22 Abbotsbury Road` | Error card: *"I recognise that as a property address, but I'm not sure what you'd like me to do."* | ☐ |
| 5 | `Schedule a viewing for Tom Baker on Thursday` | Error card — **not** classified as DRAFT_OUTREACH | ☐ |
| 6 | `Book a valuation appointment for next Tuesday` | Error card — **not** classified as VALUATION_BRIEF *(Bug 1 fix)* | ☐ |
| 7 | `Tell me a joke` | Error card with generic: *"I couldn't understand that request."* | ☐ |
| 8 | `KYC status for Tom Baker` | Bot response: *"Classified as KYC_STATUS"* (NOT an error) | ☐ |
| 9 | `valuaton brief for 8 Portland Road` | Bot response: *"Classified as VALUATION_BRIEF"* (typo tolerated) | ☐ |
| 10 | `Contact Sarah Chen about her search` | Bot response: *"Classified as DRAFT_OUTREACH"* *(Bug 2 fix)* | ☐ |

---

## Test 12 — Input Validation

### Protocol

Still signed in as the agent. Left sidebar shows the 6 function buttons.

### 12A — Required field blank triggers inline error

1. Click **Welcome Client** in left sidebar
2. Form slides in at the bottom with Client Name, Source, Agent Name, Budget, Dispatch
3. **Do not fill any fields.** Click **Generate Welcome** button
4. **Expected:**
   - Red border on Client Name, Source, Agent Name
   - Red error text under each:
     - *"Client name is required"*
     - *"Source is required"*
     - *"Agent name is required"*
   - Form does NOT submit (no new message in chat)

| | Pass/Fail |
|---|---|
| Form blocked from submitting | ☐ |
| 3 inline errors visible on required fields | ☐ |
| No network request made *(check DevTools Network tab if needed)* | ☐ |

### 12B — Blur validation (TS Section 6.2 explicit requirement)

1. Refresh page, click **Welcome Client** again
2. Click **inside** the Client Name field (do nothing)
3. Click **inside** the Source dropdown (switch focus)
4. **Expected:** Red error appears under Client Name *immediately*, before you click submit

| | Pass/Fail |
|---|---|
| Error fires on blur, not just submit | ☐ |

### 12C — Error clears on correction

1. With the 12A errors showing, start typing `James Hyde` into Client Name
2. **Expected:** Red error under Client Name disappears as you type

| | Pass/Fail |
|---|---|
| Error clears when field is valid | ☐ |

### 12D — Length validation

1. Clear any input. In Client Name, type just `J`
2. Set Source = Rightmove, Agent Name = James
3. Click Generate Welcome
4. **Expected:** Error under Client Name: *"must be at least 2 characters"*

| | Pass/Fail |
|---|---|
| Minimum length rule enforced | ☐ |

### 12E — Register Applicant form validation

1. Click **Register Applicant** in left sidebar
2. Without filling anything, click **Register Applicant** button
3. **Expected:** ~9 red errors across all required fields (Full Name, Email, Phone, Budget, Bedrooms Min, Financing, Preferred Channel, Source, Property Types)

| | Pass/Fail |
|---|---|
| All required fields flagged | ☐ |
| No backend request sent | ☐ |

---

## Automated test evidence

In addition to manual verification, 97 automated BDD tests run against the same classifier and validation layer. These cover 52 Test 11 scenarios and 45 Test 12 scenarios.

### How to run them yourself

```bash
git clone https://github.com/future-synch/Myteamai.git
cd Myteamai
pip install pydantic pydantic-settings email-validator pytest pytest-bdd pytest-asyncio
pytest tests/step_definitions/test_m1_intent.py -v
```

**Expected:** `97 passed in 0.29s` — no internet required, no API keys needed.

The test runner output is recorded in [TEST_REPORT.md](TEST_REPORT.md).

---

## M1 Pass/Fail Sign-Off

| Test | Manual pass | Automated pass | Verdict |
|---|---|---|---|
| Test 11 | ☐ | ☐ | ☐ PASS · ☐ FAIL |
| Test 12 | ☐ | ☐ | ☐ PASS · ☐ FAIL |

**Overall M1 verdict:** ☐ PASSED — release M1 payment · ☐ FAILED — document issues below

**Issues found (if any):**

```
(tester writes here)
```

---

## Signed

| | Name | Date |
|---|---|---|
| Tester | | |
| Observer | Manthan Bhanushali | |
| Reviewer | John Small | |
