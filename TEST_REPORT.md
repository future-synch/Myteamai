# My Team AI — M1 Test Report
Date: 16 April 2026
Tester: Manthan Bhanushali
TS version: v1.1
Milestone: M1
For: John Small (Technical Adviser)

---

## Overall: 97/97 PASS — 0.29s runtime

| Test | Name | Scenarios | Result |
|------|------|-----------|--------|
| 11 | Intent Classification | 52 | **PASS** |
| 12 | Input Validation | 45 | **PASS** |
| 1  | Welcome Message (Claude API) | — | **BLOCKED** — API account has no credits |

**Zero external services used.** Pure Python. Fully deterministic.

---

## Summary by test

### Test 11 — Intent Classification (52/52)
- 4 core unknown-intent behaviours
- 10 general-knowledge question rejections
- 7 property-adjacent out-of-scope rejections
- 4 boundary cases: greeting, thank-you, address, garbled input
- 16 valid-intent classifications across all 6 functions
- 2 determinism / history-independence checks
- 4 token / rate-limit / session-log checks
- 1 sequential-unknown-intents check
- 3 language / typo-tolerance checks (French, `valuaton brief` → VALUATION_BRIEF, severely garbled)

### Test 12 — Input Validation (45/45)
- 9 universal validation behaviours
- 9 `fn_generate_welcome` field rules
- 8 `fn_register_applicant` field rules (email, phone, enums)
- 3 `fn_match_applicants` field rules
- 3 `fn_valuation_brief` field rules
- 3 `fn_draft_outreach` field rules
- 2 `fn_kyc_status` field rules
- 7 type-safety / injection-prevention checks (non-numeric, negative, decimal, trim, XSS, SQLi, 10k-char)
- 1 error-response structure check

### Test 1 — BLOCKED
Anthropic API key is valid and connects successfully, but the account has zero credits.
Action: add credits at console.anthropic.com → Plans & Billing, then re-run.

---

## Classifier bugs fixed (CLAUDE.md documented)

| Bug | Fix |
|---|---|
| 1 | Removed bare `\bvaluation\b` — was wrongly matching "Book a valuation appointment for next Tuesday" |
| 2 | Added `\bcontact\b` to DRAFT_OUTREACH — TS Section 4.3 keyword |

---

## Schema enums corrected to spec (confirmed 16 April 2026)

| Field | Valid values |
|---|---|
| `source` (welcome) | Rightmove, Zoopla, Referral, Direct, Other |
| `financing` (applicant) | cash, mortgage_aip, mortgage_no_aip, unknown |
| `property_types` (applicant) | house, flat, maisonette, any |
| `preferred_channel` (applicant) | email, phone, whatsapp |
| `recipient_type` (outreach) | long_term_resident, recent_enquirer, warm_lead, lapsed |
| `channel` (outreach) | email, handwritten_note, letter |
| `property_type` (valuation) | house, flat, maisonette |
| `condition` (valuation) | excellent, good, fair, needs_work |
| `type` (kyc) | client, applicant |

---

## Full pytest output

```
============================= test session starts ==============================
platform darwin -- Python 3.13.5, pytest-8.3.0, pluggy-1.5.0 -- /opt/miniconda3/bin/python
cachedir: .pytest_cache
rootdir: /Users/manthanbhanushali/Myteamai
plugins: anyio-4.12.1, asyncio-0.24.0, bdd-8.1.0, cov-7.0.0
collected 97 items

tests/step_definitions/test_m1_intent.py::test_outofdomain_request_returns_unknown_intent_error PASSED [  1%]
tests/step_definitions/test_m1_intent.py::test_error_response_includes_all_6_capabilities PASSED [  2%]
tests/step_definitions/test_m1_intent.py::test_error_response_is_an_error_status_not_ok PASSED [  3%]
tests/step_definitions/test_m1_intent.py::test_error_message_includes_guidance_on_rephrasing PASSED [  4%]
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[What is the weather in London?] PASSED [  5%]
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[Who won the Premier League last season?] PASSED [  6%]
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[What is the capital of France?] PASSED [  7%]
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[Tell me a joke] PASSED [  8%]
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[What time is it?] PASSED [  9%]
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[Write me a poem about houses] PASSED [ 10%]
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[How do I make a cup of tea?] PASSED [ 11%]
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[What is the meaning of life?] PASSED [ 12%]
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[Translate this to French: hello] PASSED [ 13%]
tests/step_definitions/test_m1_intent.py::test_general_knowledge_questions_return_unknown_intent[Summarise the news today] PASSED [ 14%]
tests/step_definitions/test_m1_intent.py::test_propertyadjacent_outofscope_requests_return_unknown_intent[What is the average house price in Kensington?] PASSED [ 15%]
tests/step_definitions/test_m1_intent.py::test_propertyadjacent_outofscope_requests_return_unknown_intent[Schedule a viewing for Tom Baker on Thursday] PASSED [ 16%]
tests/step_definitions/test_m1_intent.py::test_propertyadjacent_outofscope_requests_return_unknown_intent[Send a reminder to all applicants about the open day] PASSED [ 17%]
tests/step_definitions/test_m1_intent.py::test_propertyadjacent_outofscope_requests_return_unknown_intent[Generate a monthly sales report] PASSED [ 18%]
tests/step_definitions/test_m1_intent.py::test_propertyadjacent_outofscope_requests_return_unknown_intent[Create a new property listing for 10 Holland Park] PASSED [ 19%]
tests/step_definitions/test_m1_intent.py::test_propertyadjacent_outofscope_requests_return_unknown_intent[Book a valuation appointment for next Tuesday] PASSED [ 20%]
tests/step_definitions/test_m1_intent.py::test_propertyadjacent_outofscope_requests_return_unknown_intent[How many properties did we sell last quarter?] PASSED [ 21%]
tests/step_definitions/test_m1_intent.py::test_greeting_returns_unknown_intent_with_warm_message PASSED [ 22%]
tests/step_definitions/test_m1_intent.py::test_thank_you_returns_unknown_intent_with_polite_message PASSED [ 23%]
tests/step_definitions/test_m1_intent.py::test_property_address_without_action_verb_returns_unknown_intent PASSED [ 24%]
tests/step_definitions/test_m1_intent.py::test_garbled_input_returns_unknown_intent_gracefully PASSED [ 25%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Welcome new client Sarah Jones from Rightmove-WELCOME_CLIENT] PASSED [ 26%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Register a new applicant-REGISTER_APPLICANT] PASSED [ 27%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[New applicant Tom Baker 2.5M 4bed-REGISTER_APPLICANT] PASSED [ 28%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Match applicants for 22 Abbotsbury Road-MATCH_APPLICANTS] PASSED [ 29%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Who fits 14 Ladbroke Road?-MATCH_APPLICANTS] PASSED [ 30%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Find suitable applicants for the Portland Road house-MATCH_APPLICANTS] PASSED [ 31%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Valuation briefing for 8 Portland Road W11-VALUATION_BRIEF] PASSED [ 32%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Prepare valuation 22 Abbotsbury Road-VALUATION_BRIEF] PASSED [ 34%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Comparables for W11 4LA-VALUATION_BRIEF] PASSED [ 35%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Draft a handwritten note to Mrs Patterson-DRAFT_OUTREACH] PASSED [ 36%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Write to Tom Baker about the new listing-DRAFT_OUTREACH] PASSED [ 37%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Contact Sarah Chen about her search-DRAFT_OUTREACH] PASSED [ 38%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[KYC status for Tom Baker-KYC_STATUS] PASSED [ 39%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[AML check for Mrs Patterson-KYC_STATUS] PASSED [ 40%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Documents outstanding for David Okonkwo-KYC_STATUS] PASSED [ 41%]
tests/step_definitions/test_m1_intent.py::test_valid_property_management_intents_are_classified_correctly[Compliance check James Hyde-KYC_STATUS] PASSED [ 42%]
tests/step_definitions/test_m1_intent.py::test_same_input_always_produces_same_classification PASSED [ 43%]
tests/step_definitions/test_m1_intent.py::test_classification_is_independent_of_prior_successful_requests PASSED [ 44%]
tests/step_definitions/test_m1_intent.py::test_unknown_intent_does_not_consume_ai_tokens PASSED [ 45%]
tests/step_definitions/test_m1_intent.py::test_unknown_intent_does_not_count_toward_perhour_rate_limit PASSED [ 46%]
tests/step_definitions/test_m1_intent.py::test_unknown_intent_still_counts_toward_daily_request_counter PASSED [ 47%]
tests/step_definitions/test_m1_intent.py::test_admin_session_log_records_unknown_intent_without_ai_metadata PASSED [ 48%]
tests/step_definitions/test_m1_intent.py::test_repeated_unknown_intents_all_show_capability_list PASSED [ 49%]
tests/step_definitions/test_m1_intent.py::test_nonenglish_input_returns_unknown_intent_with_english_capabilities PASSED [ 50%]
tests/step_definitions/test_m1_intent.py::test_typo_tolerance__valuaton_brief_classified_as_valuation_brief PASSED [ 51%]
tests/step_definitions/test_m1_intent.py::test_severely_garbled_input_returns_unknown_intent_gracefully PASSED [ 52%]
tests/step_definitions/test_m1_intent.py::test_form_does_not_submit_when_a_required_field_is_blank PASSED [ 53%]
tests/step_definitions/test_m1_intent.py::test_inline_error_targets_the_invalid_field PASSED [ 54%]
tests/step_definitions/test_m1_intent.py::test_no_claude_api_call_when_validation_fails PASSED [ 55%]
tests/step_definitions/test_m1_intent.py::test_no_hubspot_call_when_validation_fails PASSED [ 56%]
tests/step_definitions/test_m1_intent.py::test_validation_catches_bad_input_before_backend_processing PASSED [ 57%]
tests/step_definitions/test_m1_intent.py::test_valid_client_name_clears_the_validation_error PASSED [ 58%]
tests/step_definitions/test_m1_intent.py::test_multiple_blank_required_fields_produce_multiple_errors_simultaneously PASSED [ 59%]
tests/step_definitions/test_m1_intent.py::test_submit_button_remains_active__validation_runs_on_click_not_disable PASSED [ 60%]
tests/step_definitions/test_m1_intent.py::test_required_field_marking_is_a_frontend_concern__backend_validates PASSED [ 61%]
tests/step_definitions/test_m1_intent.py::test_welcome__client_name_is_required PASSED [ 62%]
tests/step_definitions/test_m1_intent.py::test_welcome__client_name_minimum_2_characters PASSED [ 63%]
tests/step_definitions/test_m1_intent.py::test_welcome__client_name_of_exactly_2_characters_accepted PASSED [ 64%]
tests/step_definitions/test_m1_intent.py::test_welcome__invalid_source_value_rejected PASSED [ 65%]
tests/step_definitions/test_m1_intent.py::test_welcome__source_dropdown_has_exactly_5_valid_options PASSED [ 67%]
tests/step_definitions/test_m1_intent.py::test_welcome__budget_gbp_below_100000_rejected PASSED [ 68%]
tests/step_definitions/test_m1_intent.py::test_welcome__budget_gbp_blank_is_accepted PASSED [ 69%]
tests/step_definitions/test_m1_intent.py::test_welcome__agent_name_is_required PASSED [ 70%]
tests/step_definitions/test_m1_intent.py::test_welcome__dispatch_blank_is_rejected PASSED [ 71%]
tests/step_definitions/test_m1_intent.py::test_applicant__email_format_validation PASSED [ 72%]
tests/step_definitions/test_m1_intent.py::test_applicant__valid_email_accepted PASSED [ 73%]
tests/step_definitions/test_m1_intent.py::test_applicant__uk_phone_format_accepted PASSED [ 74%]
tests/step_definitions/test_m1_intent.py::test_applicant__international_phone_format_accepted PASSED [ 75%]
tests/step_definitions/test_m1_intent.py::test_applicant__property_types_invalid_enum_rejected PASSED [ 76%]
tests/step_definitions/test_m1_intent.py::test_applicant__financing_invalid_enum_rejected PASSED [ 77%]
tests/step_definitions/test_m1_intent.py::test_applicant__preferred_channel_invalid_enum_rejected PASSED [ 78%]
tests/step_definitions/test_m1_intent.py::test_applicant__optional_fields_blank_are_accepted PASSED [ 79%]
tests/step_definitions/test_m1_intent.py::test_match__property_ref_blank_rejected PASSED [ 80%]
tests/step_definitions/test_m1_intent.py::test_match__max_results_defaults_to_5_when_not_specified PASSED [ 81%]
tests/step_definitions/test_m1_intent.py::test_match__max_results_above_20_rejected PASSED [ 82%]
tests/step_definitions/test_m1_intent.py::test_valuation__property_type_invalid_enum_rejected PASSED [ 83%]
tests/step_definitions/test_m1_intent.py::test_valuation__condition_invalid_enum_rejected PASSED [ 84%]
tests/step_definitions/test_m1_intent.py::test_valuation__sqft_blank_is_accepted PASSED [ 85%]
tests/step_definitions/test_m1_intent.py::test_outreach__recipient_type_invalid_enum_rejected PASSED [ 86%]
tests/step_definitions/test_m1_intent.py::test_outreach__channel_invalid_enum_rejected PASSED [ 87%]
tests/step_definitions/test_m1_intent.py::test_outreach__optional_fields_blank_are_accepted PASSED [ 88%]
tests/step_definitions/test_m1_intent.py::test_kyc__name_or_id_blank_rejected PASSED [ 89%]
tests/step_definitions/test_m1_intent.py::test_kyc__type_invalid_enum_rejected PASSED [ 90%]
tests/step_definitions/test_m1_intent.py::test_integer_fields_reject_nonnumeric_input PASSED [ 91%]
tests/step_definitions/test_m1_intent.py::test_integer_fields_reject_negative_values PASSED [ 92%]
tests/step_definitions/test_m1_intent.py::test_integer_fields_reject_decimal_values PASSED [ 93%]
tests/step_definitions/test_m1_intent.py::test_string_fields_are_trimmed_of_leading_and_trailing_whitespace PASSED [ 94%]
tests/step_definitions/test_m1_intent.py::test_script_injection_in_client_name_is_sanitised PASSED [ 95%]
tests/step_definitions/test_m1_intent.py::test_sql_injection_in_client_name_is_treated_as_a_literal_string PASSED [ 96%]
tests/step_definitions/test_m1_intent.py::test_extremely_long_client_name_is_rejected PASSED [ 97%]
tests/step_definitions/test_m1_intent.py::test_validation_error_response_follows_standard_structure PASSED [ 98%]
tests/step_definitions/test_m1_intent.py::test_validation_error_is_logged_without_pii PASSED [100%]

============================== 97 passed in 0.29s ==============================
```
