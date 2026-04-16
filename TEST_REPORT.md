# My Team AI — M1 Test Report
Date: 16 April 2026
Tester: Manthan Bhanushali
TS version: v1.1
Milestone: M1

---

## Overall: 52/52 PASS

| Test | Name | Result | Count |
|------|------|--------|-------|
| 11 | Unknown Intent Classification | **PASS** | 42/42 |
| 12 | Input Validation (schema layer) | **PASS** | 10/10 |
| 1  | Welcome Message (Claude API) | **BLOCKED** | N/A |

---

## Test 11 — Unknown Intent Classification: 42/42 PASS

No external services required. Pure Python classifier.

Scenarios covered:
- Out-of-domain request returns UNKNOWN_INTENT ✓
- Error response includes all 6 capabilities ✓
- 10 general knowledge questions → UNKNOWN_INTENT ✓
- 7 property-adjacent out-of-scope requests → UNKNOWN_INTENT ✓
- Greeting ("Hello") → UNKNOWN_INTENT with warm message ✓
- "Thanks for your help" → UNKNOWN_INTENT ✓
- Address without verb → UNKNOWN_INTENT ✓
- Garbled input ("asdfghjkl") → UNKNOWN_INTENT, no crash ✓
- 16 valid intents correctly classified across all 6 functions ✓
- Determinism: same input always same output ✓
- Typo tolerance: "valuaton brief" → VALUATION_BRIEF ✓
- Zero tokens consumed for unknown intents ✓

Classifier bugs fixed (documented in CLAUDE.md):
- Bug 1: Removed bare `\bvaluation\b` — was wrongly matching "Book a valuation appointment"
- Bug 2: Added `\bcontact\b` to DRAFT_OUTREACH — TS Section 4.3 keyword

---

## Test 12 — Input Validation: 10/10 PASS

No external services required. Pydantic v2 schema validation.

Scenarios covered:
- Blank required field (client_name) triggers ValidationError ✓
- ValidationError targets the client_name field specifically ✓
- No Claude API call when validation fails ✓
- No HubSpot call when validation fails ✓
- Validation catches bad input before any backend processing ✓
- Valid client_name ("James Hyde") — no validation error ✓
- All required fields blank → multiple errors simultaneously ✓
- client_name "J" (1 char) → rejected (min 2) ✓
- client_name "Al" (2 chars) → accepted ✓
- source "Twitter" → rejected (not in enum) ✓

---

## Test 1 — Welcome Message (M2): BLOCKED

Reason: Anthropic API account has insufficient credits.
API key is valid and connected successfully.
Error: "Your credit balance is too low to access the Anthropic API"

Action required: Add credits to Anthropic account at console.anthropic.com → Plans & Billing.
Once credits added, re-run:

```
python3 -c "
import asyncio, os, sys
sys.path.insert(0, '.')
# load env. file
with open('env.') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()
from app.functions.bot_functions import fn_generate_welcome
from app.models.schemas import WelcomeRequest
async def test():
    req = WelcomeRequest(client_name='James Hyde', source='Rightmove', agent_name='James', dispatch=False)
    result = await fn_generate_welcome(req)
    print('STATUS:', result.status)
    print('DRAFT:', result.message_draft[:300] if result.message_draft else 'NONE')
    print('AGENT IN DRAFT:', 'James' in (result.message_draft or ''))
    print('NO PLACEHOLDER:', '[' not in (result.message_draft or ''))
asyncio.run(test())
"
```

---

## Full pytest output

```
============================= test session starts ==============================
platform darwin -- Python 3.13.5, pytest-9.0.2, pluggy-1.5.0
plugins: anyio-4.12.1, asyncio-1.3.0, bdd-8.1.0, cov-7.0.0
collected 52 items

tests/step_definitions/test_m1_intent.py::test_outofdomain_request_returns_unknown_intent PASSED [  1%]
tests/step_definitions/test_m1_intent.py::test_error_response_includes_all_6_capabilities PASSED [  3%]
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[What is the weather in London?] PASSED [  5%]
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[Who won the Premier League last season?] PASSED [  7%]
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[What is the capital of France?] PASSED [  9%]
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[Tell me a joke] PASSED [ 11%]
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[What time is it?] PASSED [ 13%]
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[Write me a poem about houses] PASSED [ 15%]
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[How do I make a cup of tea?] PASSED [ 17%]
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[What is the meaning of life?] PASSED [ 19%]
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[Translate this to French: hello] PASSED [ 21%]
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[Summarise the news today] PASSED [ 23%]
tests/step_definitions/test_m1_intent.py::test_propertyadjacent_outofscope_requests_return_unknown_intent[What is the average house price in Kensington?] PASSED [ 25%]
tests/step_definitions/test_m1_intent.py::test_propertyadjacent_outofscope_requests_return_unknown_intent[Schedule a viewing for Tom Baker on Thursday] PASSED [ 26%]
tests/step_definitions/test_m1_intent.py::test_propertyadjacent_outofscope_requests_return_unknown_intent[Send a reminder to all applicants about the open day] PASSED [ 28%]
tests/step_definitions/test_m1_intent.py::test_propertyadjacent_outofscope_requests_return_unknown_intent[Generate a monthly sales report] PASSED [ 30%]
tests/step_definitions/test_m1_intent.py::test_propertyadjacent_outofscope_requests_return_unknown_intent[Create a new property listing for 10 Holland Park] PASSED [ 32%]
tests/step_definitions/test_m1_intent.py::test_propertyadjacent_outofscope_requests_return_unknown_intent[Book a valuation appointment for next Tuesday] PASSED [ 34%]
tests/step_definitions/test_m1_intent.py::test_propertyadjacent_outofscope_requests_return_unknown_intent[How many properties did we sell last quarter?] PASSED [ 36%]
tests/step_definitions/test_m1_intent.py::test_greeting_returns_unknown_intent_with_warm_message PASSED [ 38%]
tests/step_definitions/test_m1_intent.py::test_thank_you_returns_unknown_intent PASSED [ 40%]
tests/step_definitions/test_m1_intent.py::test_address_without_verb_returns_unknown_intent PASSED [ 42%]
tests/step_definitions/test_m1_intent.py::test_garbled_input_returns_unknown_intent_gracefully PASSED [ 44%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Welcome new client Sarah Jones from Rightmove-WELCOME_CLIENT] PASSED [ 46%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Register a new applicant-REGISTER_APPLICANT] PASSED [ 48%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[New applicant Tom Baker 2.5M 4bed-REGISTER_APPLICANT] PASSED [ 50%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Match applicants for 22 Abbotsbury Road-MATCH_APPLICANTS] PASSED [ 51%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Who fits 14 Ladbroke Road?-MATCH_APPLICANTS] PASSED [ 53%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Find suitable applicants for the Portland Road house-MATCH_APPLICANTS] PASSED [ 55%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Valuation briefing for 8 Portland Road W11-VALUATION_BRIEF] PASSED [ 57%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Prepare valuation 22 Abbotsbury Road-VALUATION_BRIEF] PASSED [ 59%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Comparables for W11 4LA-VALUATION_BRIEF] PASSED [ 61%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Draft a handwritten note to Mrs Patterson-DRAFT_OUTREACH] PASSED [ 63%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Write to Tom Baker about the new listing-DRAFT_OUTREACH] PASSED [ 65%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Contact Sarah Chen about her search-DRAFT_OUTREACH] PASSED [ 67%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[KYC status for Tom Baker-KYC_STATUS] PASSED [ 69%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[AML check for Mrs Patterson-KYC_STATUS] PASSED [ 71%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Documents outstanding for David Okonkwo-KYC_STATUS] PASSED [ 73%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Compliance check James Hyde-KYC_STATUS] PASSED [ 75%]
tests/step_definitions/test_m1_intent.py::test_determinism__same_input_always_produces_same_output PASSED [ 76%]
tests/step_definitions/test_m1_intent.py::test_typo_tolerance__valuaton_brief_classified_as_valuation_brief PASSED [ 78%]
tests/step_definitions/test_m1_intent.py::test_unknown_intent_does_not_consume_ai_tokens PASSED [ 80%]
tests/step_definitions/test_m1_intent.py::test_required_field_blank_triggers_validation_error PASSED [ 82%]
tests/step_definitions/test_m1_intent.py::test_validation_error_targets_the_client_name_field PASSED [ 84%]
tests/step_definitions/test_m1_intent.py::test_no_claude_api_call_when_validation_fails PASSED [ 86%]
tests/step_definitions/test_m1_intent.py::test_no_hubspot_call_when_validation_fails PASSED [ 88%]
tests/step_definitions/test_m1_intent.py::test_validation_catches_bad_input_before_backend_processing PASSED [ 90%]
tests/step_definitions/test_m1_intent.py::test_valid_client_name_clears_validation_error PASSED [ 92%]
tests/step_definitions/test_m1_intent.py::test_multiple_blank_required_fields_produce_multiple_validation_errors PASSED [ 94%]
tests/step_definitions/test_m1_intent.py::test_client_name_shorter_than_2_characters_is_rejected PASSED [ 96%]
tests/step_definitions/test_m1_intent.py::test_client_name_of_exactly_2_characters_is_accepted PASSED [ 98%]
tests/step_definitions/test_m1_intent.py::test_invalid_source_value_is_rejected PASSED [100%]

============================== 52 passed in 0.22s ==============================
```
