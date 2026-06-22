Feature: Welcome Message Generation — fn_generate_welcome
  As an estate agent at Curtis Sloane
  I want to generate a professional welcome message for new clients
  So that every client receives a timely, personalised response

  Background:
    Given an authenticated agent in the Curtis Sloane workspace
    And the Claude API is available

  # --- Test 1: Minimum input ---
  Scenario: Generate welcome message with minimum required input
    When the agent sends the request:
      """
      Welcome new client — James Hyde, came through Rightmove
      """
    Then the response status is "ok"
    And a welcome message draft is returned
    And the draft does not contain placeholder text
    And the draft appears within 8 seconds

  Scenario: Generate welcome with different source channels
    When the agent sends the request:
      """
      Welcome new client — Sarah Chen, came through Zoopla
      """
    Then the response status is "ok"
    And a welcome message draft is returned
    And the draft references "Zoopla" or acknowledges how the client found the agency

  Scenario: Generate welcome for referral client
    When the agent sends the request:
      """
      Welcome new client — Michael Brown, Referral
      """
    Then the response status is "ok"
    And a welcome message draft is returned
    And the draft tone is professional and warm

  # --- Test 2: Welcome with budget and timeline ---
  Scenario: Welcome message references budget and timeline naturally
    When the agent submits a welcome request with:
      | field       | value          |
      | client_name | Sarah Chen     |
      | source      | Zoopla         |
      | budget_gbp  | 3000000        |
      | timeline    | wants to move August |
      | agent_name  | James          |
      | dispatch    | false          |
    Then the response status is "ok"
    And the draft contains a reference to the budget
    And the draft contains a reference to the timeline
    And the draft does not contain hallucinated details

  Scenario: Welcome message with lower budget references it correctly
    When the agent submits a welcome request with:
      | field       | value        |
      | client_name | Tom Ahmed    |
      | source      | Direct       |
      | budget_gbp  | 1500000      |
      | timeline    | flexible     |
      | agent_name  | James        |
      | dispatch    | false        |
    Then the response status is "ok"
    And the draft contains a reference to the budget
    And the draft does not contain hallucinated details

  Scenario: Welcome message with property type preference
    When the agent submits a welcome request with:
      | field         | value           |
      | client_name   | Anna Williams   |
      | source        | Rightmove       |
      | property_type | 4-bed house     |
      | budget_gbp    | 2000000         |
      | agent_name    | James           |
      | dispatch      | false           |
    Then the response status is "ok"
    And the draft references the property preference
    And the draft does not contain hallucinated details