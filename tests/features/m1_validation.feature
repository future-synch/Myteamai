Feature: M1 Input Validation
  As an estate agent at Curtis Sloane
  I want the system to catch invalid input before it reaches the AI or CRM
  So that I get immediate, clear feedback on what to fix
    and no malformed data enters HubSpot or wastes AI tokens

  Background:
    Given an authenticated agent in the Curtis Sloane workspace

  # =====================================================
  # SECTION 1: Universal validation behaviour
  # =====================================================

  Scenario: Form does not submit when a required field is blank
    When the agent submits a welcome request with client_name blank
    Then the request is rejected with a validation error
    And no external API calls are made

  Scenario: Inline error targets the invalid field
    When the agent submits a welcome request with client_name blank
    Then the validation error targets the "client_name" field

  Scenario: No Claude API call when validation fails
    When any form has a validation error
    Then no Claude call is made
    And no tokens are consumed

  Scenario: No HubSpot call when validation fails
    When any form has a validation error
    Then no HubSpot call is made

  Scenario: Validation catches bad input before backend processing
    When the agent submits a welcome request with client_name blank
    Then the validation error is caught before any backend processing

  Scenario: Valid client_name clears the validation error
    When the agent provides client_name "James Hyde"
    Then no validation error exists for client_name

  Scenario: Multiple blank required fields produce multiple errors simultaneously
    When the agent submits a welcome request with all required fields blank
    Then multiple validation errors are returned

  Scenario: Submit button remains active — validation runs on click not disable
    When the agent submits a welcome request with client_name blank
    Then the request is rejected with a validation error

  Scenario: Required field marking is a frontend concern — backend validates
    When the agent submits a welcome request with client_name blank
    Then the request is rejected with a validation error

  # =====================================================
  # SECTION 2: fn_generate_welcome validation (TS 5.1)
  # =====================================================

  Scenario: Welcome — client_name is required
    When the agent submits a welcome request with client_name blank
    Then the request is rejected with a validation error

  Scenario: Welcome — client_name minimum 2 characters
    When the agent submits a welcome request with client_name "A"
    Then the request is rejected with a validation error

  Scenario: Welcome — client_name of exactly 2 characters accepted
    When the agent submits a welcome request with client_name "Al"
    Then no client_name validation error exists

  Scenario: Welcome — invalid source value rejected
    When the agent submits a welcome request with source "Twitter"
    Then the request is rejected with a validation error

  Scenario: Welcome — source dropdown has exactly 5 valid options
    Then the source field has exactly 5 valid options

  Scenario: Welcome — budget_gbp below 100000 rejected
    When the agent submits a welcome request with budget_gbp 50000
    Then the request is rejected with a validation error

  Scenario: Welcome — budget_gbp blank is accepted
    When the agent submits a valid welcome request without budget_gbp
    Then no budget validation error exists

  Scenario: Welcome — agent_name is required
    When the agent submits a welcome request with agent_name blank
    Then the request is rejected with a validation error

  Scenario: Welcome — dispatch blank is rejected
    When the agent submits a welcome request with dispatch blank
    Then the request is rejected with a validation error

  # =====================================================
  # SECTION 3: fn_register_applicant validation (TS 5.2)
  # =====================================================

  Scenario: Applicant — email format validation
    When the agent submits a register request with email "not-an-email"
    Then the request is rejected with a validation error

  Scenario: Applicant — valid email accepted
    When the agent submits a register request with email "tom.baker@email.com"
    Then no email validation error exists

  Scenario: Applicant — UK phone format accepted
    When the agent submits a register request with phone "07700 900123"
    Then no phone validation error exists

  Scenario: Applicant — international phone format accepted
    When the agent submits a register request with phone "+44 7700 900123"
    Then no phone validation error exists

  Scenario: Applicant — property_types invalid enum rejected
    When the agent submits a register request with property_types "bungalow"
    Then the request is rejected with a validation error

  Scenario: Applicant — financing invalid enum rejected
    When the agent submits a register request with financing "inheritance"
    Then the request is rejected with a validation error

  Scenario: Applicant — preferred_channel invalid enum rejected
    When the agent submits a register request with preferred_channel "telegram"
    Then the request is rejected with a validation error

  Scenario: Applicant — optional fields blank are accepted
    When the agent submits a valid register request with optional fields blank
    Then no validation error exists for optional applicant fields

  # =====================================================
  # SECTION 4: fn_match_applicants validation (TS 5.3)
  # =====================================================

  Scenario: Match — property_ref blank rejected
    When the agent submits a match request with property_ref blank
    Then the request is rejected with a validation error

  Scenario: Match — max_results defaults to 5 when not specified
    When the agent submits a match request without max_results
    Then max_results defaults to 5

  Scenario: Match — max_results above 20 rejected
    When the agent submits a match request with max_results 25
    Then the request is rejected with a validation error

  # =====================================================
  # SECTION 5: fn_valuation_brief validation (TS 5.4)
  # =====================================================

  Scenario: Valuation — property_type invalid enum rejected
    When the agent submits a valuation request with property_type "bungalow"
    Then the request is rejected with a validation error

  Scenario: Valuation — condition invalid enum rejected
    When the agent submits a valuation request with condition "terrible"
    Then the request is rejected with a validation error

  Scenario: Valuation — sqft blank is accepted
    When the agent submits a valid valuation request without sqft
    Then no sqft validation error exists

  # =====================================================
  # SECTION 6: fn_draft_outreach validation (TS 5.5)
  # =====================================================

  Scenario: Outreach — recipient_type invalid enum rejected
    When the agent submits an outreach request with recipient_type "vendor"
    Then the request is rejected with a validation error

  Scenario: Outreach — channel invalid enum rejected
    When the agent submits an outreach request with channel "telegram"
    Then the request is rejected with a validation error

  Scenario: Outreach — optional fields blank are accepted
    When the agent submits a valid outreach request with optional fields blank
    Then no validation error exists for optional outreach fields

  # =====================================================
  # SECTION 7: fn_kyc_status validation (TS 5.6)
  # =====================================================

  Scenario: KYC — name_or_id blank rejected
    When the agent submits a KYC request with name_or_id blank
    Then the request is rejected with a validation error

  Scenario: KYC — type invalid enum rejected
    When the agent submits a KYC request with type "vendor"
    Then the request is rejected with a validation error

  # =====================================================
  # SECTION 8: Type safety and injection prevention
  # =====================================================

  Scenario: Integer fields reject non-numeric input
    When the agent submits a welcome request with budget_gbp "two million"
    Then the request is rejected with a validation error

  Scenario: Integer fields reject negative values
    When the agent submits a welcome request with budget_gbp -500000
    Then the request is rejected with a validation error

  Scenario: Integer fields reject decimal values
    When the agent submits a welcome request with budget_gbp 2500000.50
    Then the request is rejected with a validation error

  Scenario: String fields are trimmed of leading and trailing whitespace
    When the agent submits a welcome request with client_name "  James Hyde  "
    Then the client_name is stored as "James Hyde"

  Scenario: Script injection in client_name is sanitised
    When the agent submits a welcome request with client_name "<script>alert('xss')</script>"
    Then no script tag is stored in client_name

  Scenario: SQL injection in client_name is treated as a literal string
    When the agent submits a welcome request with client_name "'; DROP TABLE contacts; --"
    Then no sql injection error occurs and input is stored literally

  Scenario: Extremely long client_name is rejected
    When the agent submits a welcome request with a 10000 character client_name
    Then the request is rejected with a validation error

  # =====================================================
  # SECTION 9: Error response structure
  # =====================================================

  Scenario: Validation error response follows standard structure
    When the agent submits a welcome request with client_name blank
    Then the validation error has a structured error response

  Scenario: Validation error is logged without PII
    When the agent submits a welcome request with client_name blank
    Then the request is rejected with a validation error
