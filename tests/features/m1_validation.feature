Feature: M1 Input Validation
  As an estate agent at Curtis Sloane
  I want the system to catch invalid input before it reaches the AI or CRM

  Background:
    Given an authenticated agent in the Curtis Sloane workspace

  Scenario: Required field blank triggers validation error
    When the agent submits a welcome request with client_name blank
    Then the request is rejected with a validation error
    And no external API calls are made

  Scenario: Validation error targets the client_name field
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

  Scenario: Valid client_name clears validation error
    When the agent provides client_name "James Hyde"
    Then no validation error exists for client_name

  Scenario: Multiple blank required fields produce multiple validation errors
    When the agent submits a welcome request with all required fields blank
    Then multiple validation errors are returned

  Scenario: client_name shorter than 2 characters is rejected
    When the agent submits a welcome request with client_name "J"
    Then the request is rejected with a validation error

  Scenario: client_name of exactly 2 characters is accepted
    When the agent submits a welcome request with client_name "Al"
    Then no client_name validation error exists

  Scenario: Invalid source value is rejected
    When the agent submits a welcome request with source "Twitter"
    Then the request is rejected with a validation error
