Feature: Draft Outreach — fn_draft_outreach
  As an estate agent at Curtis Sloane
  I want to generate personalised outreach messages
  So that I can maintain relationships with database contacts

  Background:
    Given an authenticated agent in the Curtis Sloane workspace
    And the Claude API is available

  # --- Test 9: Handwritten note ---
  Scenario: Draft handwritten note is short and personal
    When the agent sends the request:
      """
      Draft a handwritten note to Mrs Patterson, 
      30-year resident, spring market
      """
    Then the response status is "ok"
    And the draft is returned
    And the draft word count is less than 120
    And the draft does not contain corporate language
    And the draft does not contain placeholder text

  Scenario: Draft email outreach is appropriately longer
    When the agent submits an outreach request with:
      | field          | value             |
      | recipient_name | Mr Thompson       |
      | recipient_type | warm_lead         |
      | channel        | email             |
      | context        | spring market     |
      | agent_name     | James             |
    Then the response status is "ok"
    And the draft is returned
    And the tone_notes explain the tone chosen

  Scenario: Draft letter for long term resident
    When the agent submits an outreach request with:
      | field          | value               |
      | recipient_name | Mrs Patterson       |
      | recipient_type | long_term_resident  |
      | channel        | letter              |
      | context        | anniversary of purchase |
      | agent_name     | James               |
    Then the response status is "ok"
    And the draft is returned
    And the draft does not contain placeholder text