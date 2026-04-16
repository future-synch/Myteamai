# My Team AI — M1 Test Report
Date: 16 April 2026
Tester: Manthan Bhanushali
TS version: v1.1
Milestone: M1

---

## Overall: 97/97 PASS

| Test | Name | Scenarios | Result |
|------|------|-----------|--------|
| 11 | Intent Classification | 52 | **PASS** |
| 12 | Input Validation | 45 | **PASS** |
| 1  | Welcome Message (Claude API) | — | **BLOCKED** — no API credits |

Zero external services used. Pure Python. Runs in 0.29s.

---

## Test 11 — Intent Classification: 52/52 PASS

### Core unknown intent behaviour (4 scenarios)
- Out-of-domain request returns UNKNOWN_INTENT ✓
- Error response includes all 6 capabilities ✓
- Error response status is "error" not "ok" ✓
- Error message contains rephrasing guidance ✓

### General knowledge questions (10 scenarios)
All 10 out-of-domain questions → UNKNOWN_INTENT with capability list ✓

### Property-adjacent out-of-scope requests (7 scenarios)
All 7 adjacent requests → UNKNOWN_INTENT ✓
Includes: "Book a valuation appointment for next Tuesday" (Bug 1 fix verified)

### Boundary cases — close to valid intents (4 scenarios)
- "Hello" → UNKNOWN_INTENT with welcoming message ✓
- "Thanks for your help" → UNKNOWN_INTENT with polite message ✓
- "22 Abbotsbury Road" (address without verb) → UNKNOWN_INTENT with address acknowledgement ✓
- "asdfghjkl" (garbled) → UNKNOWN_INTENT, no crash ✓

### Valid intent classification (16 scenarios)
All 16 valid intent phrases correctly classified across all 6 functions ✓

### Determinism and history independence (2 scenarios)
- Same input × 3 → always UNKNOWN_INTENT ✓
- Prior successful classification does not influence current result ✓

### Token / rate limit accounting (4 scenarios)
- Zero tokens consumed for unknown intents ✓
- Unknown intents do not count toward per-hour rate limit ✓
- Unknown intents DO count toward daily request counter ✓
- Admin session log records UNKNOWN_INTENT without AI function or token usage ✓

### Sequential unknown intents (1 scenario)
- 3 sequential unknowns → all return full capability list ✓

### Language and typo tolerance (3 scenarios)
- French input → UNKNOWN_INTENT with English capability list ✓
- "valuaton brief" (typo) → VALUATION_BRIEF (Bug 2 fix context: typo handled by regex `valuat(?:i)?on`) ✓
- Severely garbled input → UNKNOWN_INTENT, no crash ✓

### Classifier bugs fixed (documented in CLAUDE.md)
- Bug 1: Removed bare `\bvaluation\b` — was matching "Book a valuation appointment for next Tuesday" → now correctly UNKNOWN_INTENT
- Bug 2: Added `\bcontact\b` to DRAFT_OUTREACH — "Contact Sarah Chen about her search" now correctly DRAFT_OUTREACH

---

## Test 12 — Input Validation: 45/45 PASS

### Universal validation behaviour (9 scenarios)
- Required field blank → ValidationError raised before any external call ✓
- Validation error targets the specific field ✓
- No Claude API call on validation failure ✓
- No HubSpot call on validation failure ✓
- Validation caught before backend processing ✓
- Valid input clears validation error ✓
- Multiple blank fields → multiple errors simultaneously ✓
- Submit behaviour (backend validates regardless) ✓
- Required field marking (frontend concern, backend validates) ✓

### fn_generate_welcome validation (9 scenarios)
- client_name blank → ValidationError ✓
- client_name "A" (1 char) → ValidationError ✓
- client_name "Al" (2 chars) → accepted ✓
- source "Twitter" → ValidationError ✓
- source field has exactly 5 valid options (Rightmove, Zoopla, Referral, Direct, Other) ✓
- budget_gbp 50000 → ValidationError ✓
- budget_gbp blank → accepted (optional field) ✓
- agent_name blank → ValidationError ✓
- dispatch blank → ValidationError ✓

### fn_register_applicant validation (8 scenarios)
- email "not-an-email" → ValidationError ✓
- email "tom.baker@email.com" → accepted ✓
- phone "07700 900123" (UK) → accepted ✓
- phone "+44 7700 900123" (international) → accepted ✓
- property_types "bungalow" → ValidationError (valid: house/flat/maisonette/any) ✓
- financing "inheritance" → ValidationError (valid: cash/mortgage_aip/mortgage_no_aip/unknown) ✓
- preferred_channel "telegram" → ValidationError (valid: email/phone/whatsapp) ✓
- Optional fields (bedrooms_max, must_have, timeline_weeks) blank → accepted ✓

### fn_match_applicants validation (3 scenarios)
- property_ref blank → ValidationError ✓
- max_results not specified → defaults to 5 ✓
- max_results 25 → ValidationError (max 20) ✓

### fn_valuation_brief validation (3 scenarios)
- property_type "bungalow" → ValidationError (valid: house/flat/maisonette) ✓
- condition "terrible" → ValidationError (valid: excellent/good/fair/needs_work) ✓
- sqft blank → accepted (optional) ✓

### fn_draft_outreach validation (3 scenarios)
- recipient_type "vendor" → ValidationError (valid: long_term_resident/recent_enquirer/warm_lead/lapsed) ✓
- channel "telegram" → ValidationError (valid: email/handwritten_note/letter) ✓
- Optional fields (context_notes, property_mention) blank → accepted ✓

### fn_kyc_status validation (2 scenarios)
- name_or_id blank → ValidationError ✓
- type "vendor" → ValidationError (valid: client/applicant) ✓

### Type safety and injection prevention (7 scenarios)
- budget_gbp "two million" (string) → ValidationError ✓
- budget_gbp -500000 (negative) → ValidationError ✓
- budget_gbp 2500000.50 (decimal) → ValidationError ✓
- "  James Hyde  " → stored as "James Hyde" (trimmed) ✓
- "<script>alert('xss')</script>" → HTML tags stripped, no script stored ✓
- SQL injection "'; DROP TABLE contacts; --" → treated as literal string, no crash ✓
- 10,000 character client_name → ValidationError ✓

### Error response structure (1 scenario)
- Validation error has structured response with loc/msg/type fields ✓

---

## Test 1 — Welcome Message (M2): BLOCKED

Reason: Anthropic API account has insufficient credits.
API key is valid and connected successfully (HTTP 400 received — not a connection error).

Action required: Add credits at console.anthropic.com → Plans & Billing.
Test 1 will be run immediately once credits are available.

---

## Full pytest output

```
============================= test session starts ==============================
platform darwin -- Python 3.13.5, pytest-9.0.2, pluggy-1.5.0 -- /opt/miniconda3/bin/python
cachedir: .pytest_cache
rootdir: /Users/manthanbhanushali/Myteamai
plugins: anyio-4.12.1, asyncio-1.3.0, bdd-8.1.0, cov-7.0.0
collected 97 items

tests/step_definitions/test_m1_intent.py::test_outofdomain_request_returns_unknown_intent_error PASSED
tests/step_definitions/test_m1_intent.py::test_error_response_includes_all_6_capabilities PASSED
tests/step_definitions/test_m1_intent.py::test_error_response_is_an_error_status_not_ok PASSED
tests/step_definitions/test_m1_intent.py::test_error_message_includes_guidance_on_rephrasing PASSED
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[What is the weather in London?] PASSED
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[Who won the Premier League last season?] PASSED
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[What is the capital of France?] PASSED
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[Tell me a joke] PASSED
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[What time is it?] PASSED
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[Write me a poem about houses] PASSED
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[How do I make a cup of tea?] PASSED
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[What is the meaning of life?] PASSED
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[Translate this to French: hello] PASSED
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[Summarise the news today] PASSED
tests/step_definitions/test_m1_intent.py::test_propertyadjacent_outofscope_requests_return_unknown_intent[What is the average house price in Kensington?] PASSED
tests/step_definitions/test_m1_intent.py::test_propertyadjacent_outofscope_requests_return_unknown_intent[Schedule a viewing for Tom Baker on Thursday] PASSED
tests/step_definitions/test_m1_intent.py::test_propertyadjacent_outofscope_requests_return_unknown_intent[Send a reminder to all applicants about the open day] PASSED
tests/step_definitions/test_m1_intent.py::test_propertyadjacent_outofscope_requests_return_unknown_intent[Generate a monthly sales report] PASSED
tests/step_definitions/test_m1_intent.py::test_propertyadjacent_outofscope_requests_return_unknown_intent[Create a new property listing for 10 Holland Park] PASSED
tests/step_definitions/test_m1_intent.py::test_propertyadjacent_outofscope_requests_return_unknown_intent[Book a valuation appointment for next Tuesday] PASSED
tests/step_definitions/test_m1_intent.py::test_propertyadjacent_outofscope_requests_return_unknown_intent[How many properties did we sell last quarter?] PASSED
tests/step_definitions/test_m1_intent.py::test_greeting_returns_unknown_intent_with_warm_message PASSED
tests/step_definitions/test_m1_intent.py::test_thank_you_returns_unknown_intent_with_polite_message PASSED
tests/step_definitions/test_m1_intent.py::test_property_address_without_action_verb_returns_unknown_intent PASSED
tests/step_definitions/test_m1_intent.py::test_garbled_input_returns_unknown_intent_gracefully PASSED
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Welcome new client Sarah Jones from Rightmove-WELCOME_CLIENT] PASSED
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Register a new applicant-REGISTER_APPLICANT] PASSED
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[New applicant Tom Baker 2.5M 4bed-REGISTER_APPLICANT] PASSED
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Match applicants for 22 Abbotsbury Road-MATCH_APPLICANTS] PASSED
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Who fits 14 Ladbroke Road?-MATCH_APPLICANTS] PASSED
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Find suitable applicants for the Portland Road house-MATCH_APPLICANTS] PASSED
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Valuation briefing for 8 Portland Road W11-VALUATION_BRIEF] PASSED
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Prepare valuation 22 Abbotsbury Road-VALUATION_BRIEF] PASSED
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Comparables for W11 4LA-VALUATION_BRIEF] PASSED
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Draft a handwritten note to Mrs Patterson-DRAFT_OUTREACH] PASSED
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Write to Tom Baker about the new listing-DRAFT_OUTREACH] PASSED
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Contact Sarah Chen about her search-DRAFT_OUTREACH] PASSED
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[KYC status for Tom Baker-KYC_STATUS] PASSED
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[AML check for Mrs Patterson-KYC_STATUS] PASSED
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Documents outstanding for David Okonkwo-KYC_STATUS] PASSED
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Compliance check James Hyde-KYC_STATUS] PASSED
tests/step_definitions/test_m1_intent.py::test_same_input_always_produces_same_classification PASSED
tests/step_definitions/test_m1_intent.py::test_classification_is_independent_of_prior_successful_requests PASSED
tests/step_definitions/test_m1_intent.py::test_unknown_intent_does_not_consume_ai_tokens PASSED
tests/step_definitions/test_m1_intent.py::test_unknown_intent_does_not_count_toward_perhour_rate_limit PASSED
tests/step_definitions/test_m1_intent.py::test_unknown_intent_still_counts_toward_daily_request_counter PASSED
tests/step_definitions/test_m1_intent.py::test_admin_session_log_records_unknown_intent_without_ai_metadata PASSED
tests/step_definitions/test_m1_intent.py::test_repeated_unknown_intents_all_show_capability_list PASSED
tests/step_definitions/test_m1_intent.py::test_nonenglish_input_returns_unknown_intent_with_english_capabilities PASSED
tests/step_definitions/test_m1_intent.py::test_typo_tolerance__valuaton_brief_classified_as_valuation_brief PASSED
tests/step_definitions/test_m1_intent.py::test_severely_garbled_input_returns_unknown_intent_gracefully PASSED
tests/step_definitions/test_m1_intent.py::test_form_does_not_submit_when_a_required_field_is_blank PASSED
tests/step_definitions/test_m1_intent.py::test_inline_error_targets_the_invalid_field PASSED
tests/step_definitions/test_m1_intent.py::test_no_claude_api_call_when_validation_fails PASSED
tests/step_definitions/test_m1_intent.py::test_no_hubspot_call_when_validation_fails PASSED
tests/step_definitions/test_m1_intent.py::test_validation_catches_bad_input_before_backend_processing PASSED
tests/step_definitions/test_m1_intent.py::test_valid_client_name_clears_the_validation_error PASSED
tests/step_definitions/test_m1_intent.py::test_multiple_blank_required_fields_produce_multiple_errors_simultaneously PASSED
tests/step_definitions/test_m1_intent.py::test_submit_button_remains_active__validation_runs_on_click_not_disable PASSED
tests/step_definitions/test_m1_intent.py::test_required_field_marking_is_a_frontend_concern__backend_validates PASSED
tests/step_definitions/test_m1_intent.py::test_welcome__client_name_is_required PASSED
tests/step_definitions/test_m1_intent.py::test_welcome__client_name_minimum_2_characters PASSED
tests/step_definitions/test_m1_intent.py::test_welcome__client_name_of_exactly_2_characters_accepted PASSED
tests/step_definitions/test_m1_intent.py::test_welcome__invalid_source_value_rejected PASSED
tests/step_definitions/test_m1_intent.py::test_welcome__source_dropdown_has_exactly_5_valid_options PASSED
tests/step_definitions/test_m1_intent.py::test_welcome__budget_gbp_below_100000_rejected PASSED
tests/step_definitions/test_m1_intent.py::test_welcome__budget_gbp_blank_is_accepted PASSED
tests/step_definitions/test_m1_intent.py::test_welcome__agent_name_is_required PASSED
tests/step_definitions/test_m1_intent.py::test_welcome__dispatch_blank_is_rejected PASSED
tests/step_definitions/test_m1_intent.py::test_applicant__email_format_validation PASSED
tests/step_definitions/test_m1_intent.py::test_applicant__valid_email_accepted PASSED
tests/step_definitions/test_m1_intent.py::test_applicant__uk_phone_format_accepted PASSED
tests/step_definitions/test_m1_intent.py::test_applicant__international_phone_format_accepted PASSED
tests/step_definitions/test_m1_intent.py::test_applicant__property_types_invalid_enum_rejected PASSED
tests/step_definitions/test_m1_intent.py::test_applicant__financing_invalid_enum_rejected PASSED
tests/step_definitions/test_m1_intent.py::test_applicant__preferred_channel_invalid_enum_rejected PASSED
tests/step_definitions/test_m1_intent.py::test_applicant__optional_fields_blank_are_accepted PASSED
tests/step_definitions/test_m1_intent.py::test_match__property_ref_blank_rejected PASSED
tests/step_definitions/test_m1_intent.py::test_match__max_results_defaults_to_5_when_not_specified PASSED
tests/step_definitions/test_m1_intent.py::test_match__max_results_above_20_rejected PASSED
tests/step_definitions/test_m1_intent.py::test_valuation__property_type_invalid_enum_rejected PASSED
tests/step_definitions/test_m1_intent.py::test_valuation__condition_invalid_enum_rejected PASSED
tests/step_definitions/test_m1_intent.py::test_valuation__sqft_blank_is_accepted PASSED
tests/step_definitions/test_m1_intent.py::test_outreach__recipient_type_invalid_enum_rejected PASSED
tests/step_definitions/test_m1_intent.py::test_outreach__channel_invalid_enum_rejected PASSED
tests/step_definitions/test_m1_intent.py::test_outreach__optional_fields_blank_are_accepted PASSED
tests/step_definitions/test_m1_intent.py::test_kyc__name_or_id_blank_rejected PASSED
tests/step_definitions/test_m1_intent.py::test_kyc__type_invalid_enum_rejected PASSED
tests/step_definitions/test_m1_intent.py::test_integer_fields_reject_nonnumeric_input PASSED
tests/step_definitions/test_m1_intent.py::test_integer_fields_reject_negative_values PASSED
tests/step_definitions/test_m1_intent.py::test_integer_fields_reject_decimal_values PASSED
tests/step_definitions/test_m1_intent.py::test_string_fields_are_trimmed_of_leading_and_trailing_whitespace PASSED
tests/step_definitions/test_m1_intent.py::test_script_injection_in_client_name_is_sanitised PASSED
tests/step_definitions/test_m1_intent.py::test_sql_injection_in_client_name_is_treated_as_a_literal_string PASSED
tests/step_definitions/test_m1_intent.py::test_extremely_long_client_name_is_rejected PASSED
tests/step_definitions/test_m1_intent.py::test_validation_error_response_follows_standard_structure PASSED
tests/step_definitions/test_m1_intent.py::test_validation_error_is_logged_without_pii PASSED

============================== 97 passed in 0.29s ==============================
```
