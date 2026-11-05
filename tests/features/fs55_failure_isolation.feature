Feature: FS-55 orchestration — failure isolation between the five steps
  As the orchestrator fn_register_applicant()
  I want each step to fail on its own
  So that a later failure never discards an earlier success, and nothing
  downstream runs once there is no applicant to act on

  # One scenario per row of the failure table in the FS-55 ticket
  # ("Failure isolation — the part worth care"). The brochure rows are covered
  # in fs55_orchestration_brochure.feature. Once a HubSpot contact exists it
  # exists, so every failure after registration must still report the applicant
  # as registered. All offline: the five delegates are replaced by spies.

  Background:
    Given the five delegates are replaced by recording spies

  Scenario: Validation failure calls no delegate beyond the validation itself
    Given registration rejects the payload as invalid
    When fn_register_applicant runs with dispatch true
    Then the response status is error
    And the error code is VALIDATION_ERROR
    And no applicant id is returned
    And matching was not called
    And the brochure source was not asked
    And composition was not called
    And draft creation was not called

  Scenario: Registration failure stops the chain
    Given registration fails with an unexpected error
    When fn_register_applicant runs with dispatch true
    Then the response status is error
    And the error code is HUBSPOT_SYNC_FAIL
    And no applicant id is returned
    And matching was not called
    And the brochure source was not asked
    And composition was not called
    And draft creation was not called

  Scenario: Matching failure does not discard the registration
    Given matching raises an error
    When fn_register_applicant runs with dispatch true
    Then the response status is ok
    And the applicant id is returned
    And no matches are returned
    And the first error starts with MATCH_FAILED
    And the brochure source was not asked
    And the welcome draft is returned

  Scenario: Composition failure keeps the registration and the matches
    Given matching returns 3 listings
    And composition raises an error
    When fn_register_applicant runs with dispatch true
    Then the response status is ok
    And the applicant id is returned
    And the matches are returned
    And the first error starts with WELCOME_FAILED
    And no welcome draft is returned
    And draft creation was not called

  Scenario: Gmail draft failure keeps the registration, the matches and the composed text
    Given matching returns 3 listings
    And draft creation raises an error
    When fn_register_applicant runs with dispatch true
    Then the response status is ok
    And the applicant id is returned
    And the matches are returned
    And the welcome draft is returned
    And the first error starts with DRAFT_FAILED
    And no draft reference is returned

  Scenario: No draft is created when dispatch is false
    Given matching returns 3 listings
    When fn_register_applicant runs with dispatch false
    Then the response status is ok
    And the welcome draft is returned
    And draft creation was not called
    And no draft reference is returned

  Scenario: A draft is created exactly once when dispatch is true
    Given matching returns 3 listings
    When fn_register_applicant runs with dispatch true
    Then the response status is ok
    And draft creation was called once
    And a draft reference is returned
