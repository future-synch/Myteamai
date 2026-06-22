Feature: KYC Status — fn_kyc_status
  As an estate agent at Curtis Sloane
  I want to check KYC status for any client or applicant
  So that I know exactly what documents are outstanding

  Background:
    Given an authenticated agent in the Curtis Sloane workspace
    And the HubSpot sandbox contains seeded contact records

  # --- Test 10: KYC status check ---
  Scenario: KYC status returns checklist with outstanding items
    When the agent sends the request:
      """
      KYC status for Tom Baker
      """
    Then the response status is "ok"
    And the KYC checklist is returned
    And outstanding items are listed in plain English
    And can_progress is false if any item is missing

  Scenario: KYC complete contact shows can_progress true
    Given the HubSpot sandbox contains a contact with complete KYC
    When the agent checks KYC status for that contact
    Then the response status is "ok"
    And can_progress is true
    And the outstanding list is empty

  Scenario: Unknown contact returns not found error
    When the agent checks KYC status for "Unknown Person XYZ"
    Then the response status is "error"
    And the error references contact not found