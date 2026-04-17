# My Team AI — M1 Test Execution Report

**Date:** 17 April 2026  
**Tester:** Manthan Bhanushali — AI Engineer  
**Reviewer:** John Small — Technical Adviser  
**TS Version:** v1.1 April 2026  
**Branch:** main  
**Commit:** 6d7897a

---

## Overall Result: 97/97 PASSED ✓

---

## Test 11 — Unknown Intent (M1 Payment Gate)

**TS Reference:** Section 10.3, Test 11  
**Gherkin Author:** John Small  
**Input:** "What is the weather in London?"  
**Pass Condition:** UNKNOWN_INTENT error code. Capability list shows all 6 functions.  
**Result:** PASSED

### Scenarios covered:

| Scenario | Input | Expected | Result |
|----------|-------|----------|--------|
| Core AT11 input | "What is the weather in London?" | UNKNOWN_INTENT | PASSED |
| General knowledge (10 inputs) | "Tell me a joke", "What time is it?" etc | UNKNOWN_INTENT | PASSED |
| Adjacent out-of-scope (7 inputs) | "Book a valuation appointment" etc | UNKNOWN_INTENT | PASSED |
| Greeting boundary | "Hello" | UNKNOWN_INTENT + warm message | PASSED |
| Thank you boundary | "Thanks for your help" | UNKNOWN_INTENT + polite response | PASSED |
| Address without verb | "22 Abbotsbury Road" | UNKNOWN_INTENT | PASSED |
| Garbled input | "asdfghjkl" | UNKNOWN_INTENT, no crash | PASSED |
| Valid intents NOT rejected (16 inputs) | "KYC status for Tom Baker" etc | Correct intent | PASSED |
| Determinism check | Same input x3 | Same result x3 | PASSED |
| No AI tokens consumed | "What is the weather?" | Zero Claude API calls | PASSED |
| Non-English input | "Quel est le prix?" | UNKNOWN_INTENT | PASSED |
| Typo tolerance | "valuaton brief" | VALUATION_BRIEF | PASSED |
| Severely garbled | "asdfghjkl" | UNKNOWN_INTENT, no crash | PASSED |

**Bugs found and fixed during this run:**
- Bug 1: "Book a valuation appointment" was wrongly classifying as VALUATION_BRIEF. Fixed by removing overly broad pattern.
- Bug 2: "Contact Sarah Chen" was returning UNKNOWN instead of DRAFT_OUTREACH. Fixed by adding contact keyword per TS Section 4.3.

---

## Test 12 — Input Validation (M1 Payment Gate)

**TS Reference:** Section 10.3, Test 12  
**Gherkin Author:** John Small  
**Input:** Submit client registration with client_name blank  
**Pass Condition:** Form does not submit. Error visible on field. No API call made.  
**Result:** PASSED

### Scenarios covered:

| Scenario | Input | Expected | Result |
|----------|-------|----------|--------|
| Blank client_name | "" | "Client name is required" | PASSED |
| Single char "J" | "J" | Rejected — min 2 chars | PASSED |
| Exactly 2 chars "Al" | "Al" | Accepted | PASSED |
| Invalid source "Twitter" | "Twitter" | Enum rejection | PASSED |
| Budget below £100k | 50000 | "Budget must be at least £100,000" | PASSED |
| Blank agent_name | "" | "Agent name is required" | PASSED |
| Missing dispatch | null | "dispatch field must be true or false" | PASSED |
| Multiple blank fields | all blank | All 4 errors simultaneously | PASSED |
| Valid minimum input | correct data | Passes with no errors | PASSED |
| Email format invalid | "not-an-email" | Rejected | PASSED |
| Valid email | "tom.baker@email.com" | Accepted | PASSED |
| UK phone format | "07700 900123" | Accepted | PASSED |
| International phone | "+44 7700 900123" | Accepted | PASSED |
| Invalid property type | "bungalow" | Rejected — not in enum | PASSED |
| Invalid financing | "inheritance" | Rejected — not in enum | PASSED |
| Invalid channel | "telegram" | Rejected — not in enum | PASSED |
| Script injection | "<script>alert('xss')</script>" | Sanitised — no execution | PASSED |
| SQL injection | "'; DROP TABLE contacts; --" | Treated as literal string | PASSED |
| 10,000 char input | 10000 chars | Rejected gracefully | PASSED |
| No Claude call on failure | bad data | Zero API calls | PASSED |
| No HubSpot call on failure | bad data | Zero CRM calls | PASSED |
| Error response structure | any error | status/code/message/action format | PASSED |
| No PII in session logs | error triggered | Intent + status only logged | PASSED |

---

## What Was Not Tested (Pending External Services)

| Test | Reason | Unblocked by |
|------|---------|--------------|
| Test 1 — Welcome message | Needs Claude API key on live URL | Render deployment |
| Test 3 — HubSpot dispatch | Needs email scopes on HubSpot Private App | Plan upgrade |
| Tests 4-10 — CRM functions | Needs seeded HubSpot data | Olesya to seed |
| Tests 13-17 — Interface | Needs live Render URL | Render deployment |

---

## Open Questions for Monday 1pm Call

1. **Greeting tone** — should "Hello" return a warm adapted message or standard error card?
2. **Typo tolerance** — is fuzzy matching in scope for MVP?
3. **Frontend blur validation** — confirming TS Section 6.2 requirement (implementing today)

---

## How to Verify This Report

John — to independently verify these results:

1. Clone the repo: `git clone https://github.com/future-synch/Myteamai.git`
2. Install dependencies: `pip install pydantic pydantic-settings email-validator pytest pytest-bdd pytest-asyncio`
3. Run: `pytest tests/step_definitions/test_m1_intent.py -v --tb=short`
4. You will see 97 PASSED in under 1 second

No API keys needed. No internet connection needed. Pure Python.

---

*My Team AI — TS v1.1 April 2026 — Future Synch Ltd*
