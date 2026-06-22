Feature: Applicant Registration — fn_register_applicant
  As an estate agent at Curtis Sloane
  I want to register new applicants with full profile and KYC checklist
  So that every applicant is tracked from first contact

  Background:
    Given an authenticated agent in the Curtis Sloane workspace
    And the HubSpot sandbox is connected

  # --- Test 4: Full registration ---
  Scenario: Register applicant with full form creates HubSpot record
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
    And a HubSpot contact record is created for "Tom Baker"
    And a HubSpot contact ID is returned
    And a KYC checklist is returned
    And the top 3 property matches are returned
    And all match scores are between 0.0 and 1.0
    And all match reasons are readable plain English

  Scenario: KYC checklist contains all three required items
    When the agent registers a cash buyer applicant
    Then the KYC checklist contains:
      | item             |
      | proof_of_id      |
      | proof_of_address |
      | proof_of_funds   |
    And all items have received set to false initially

  Scenario: Matches returned are plausible for budget and bedrooms
    When the agent registers an applicant with budget 2500000 and bedrooms_min 4
    Then all returned matches have price_gbp less than or equal to 2625000
    And all returned matches have bedrooms greater than or equal to 4