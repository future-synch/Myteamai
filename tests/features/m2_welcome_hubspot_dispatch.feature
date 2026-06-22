Feature: Welcome Message HubSpot Dispatch — Test 3
  As an estate agent at Curtis Sloane
  I want welcome messages dispatched to HubSpot automatically
  So that new clients are contacted without manual CRM entry

  Background:
    Given an authenticated agent in the Curtis Sloane workspace
    And the HubSpot sandbox account is connected
    And the Claude API is available

  # --- Test 3: Dispatch to HubSpot ---
  Scenario: Welcome message dispatched creates HubSpot contact
    When the agent submits a welcome request with:
      | field       | value          |
      | client_name | Sarah Chen     |
      | source      | Zoopla         |
      | budget_gbp  | 3000000        |
      | timeline    | wants to move August |
      | agent_name  | James          |
      | dispatch    | true           |
    Then the response status is "ok"
    And a HubSpot contact record is created for "Sarah Chen"
    And the contact is visible in HubSpot within 30 seconds
    And the welcome email is queued in HubSpot drafts

  Scenario: Dispatch creates contact with correct source property
    When the agent submits a welcome request with:
      | field       | value      |
      | client_name | James Hyde |
      | source      | Rightmove  |
      | agent_name  | James      |
      | dispatch    | true       |
    Then the response status is "ok"
    And a HubSpot contact record is created for "James Hyde"
    And the contact source property is "Rightmove"

  Scenario: Dispatch false returns draft without creating HubSpot record
    When the agent submits a welcome request with:
      | field       | value        |
      | client_name | Test Contact |
      | source      | Direct       |
      | agent_name  | James        |
      | dispatch    | false        |
    Then the response status is "ok"
    And a welcome message draft is returned
    And no HubSpot contact is created
    And the dispatched field is false