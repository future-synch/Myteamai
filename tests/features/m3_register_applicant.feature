Feature: Applicant Registration — fn_register_applicant (A-2 rev 5)
  As an estate agent at Curtis Sloane
  I want registration to orchestrate register → match → welcome → draft
  So that an applicant is registered and a welcome draft is composed every time

  Background:
    Given an authenticated agent in the Curtis Sloane workspace
    And the HubSpot sandbox is connected

  # --- Test 4: Full registration returns the A-2 rev 5 envelope ---
  Scenario: Register applicant returns id, welcome draft, and matches list
    When the agent submits the applicant registration form with:
      | field             | value               |
      | full_name         | Tom Baker           |
      | email             | tom.baker@email.com |
      | phone             | 07700 900123        |
      | budget_gbp        | 2500000             |
      | bedrooms_min      | 4                   |
      | property_types    | house               |
      | financing         | cash                |
      | preferred_channel | email               |
      | source            | Referral            |
    Then the response status is "ok"
    And an applicant ID is returned
    And a welcome draft is returned with subject, html_body and text_body
    And first_matches is a list
    And draft_ref is null
    And errors is empty

  # --- Test 5: dispatch=true creates a draft reference (step d) ---
  Scenario: Registering with dispatch true returns a draft reference
    When the agent registers an applicant with dispatch true
    Then the response status is "ok"
    And an applicant ID is returned
    And a welcome draft is returned with subject, html_body and text_body
    And draft_ref has transport, draft_id and mailbox

  # --- Matching is stubbed until FS-64 + FS-63 land ---
  Scenario: Matching returns no listings until the engine lands
    When the agent registers a cash buyer applicant
    Then the response status is "ok"
    And first_matches is empty
