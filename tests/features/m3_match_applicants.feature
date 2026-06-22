Feature: Applicant Matching — fn_match_applicants
  As an estate agent at Curtis Sloane
  I want to find ranked applicants for a given property
  So that I can identify the best buyers immediately

  Background:
    Given an authenticated agent in the Curtis Sloane workspace
    And the HubSpot sandbox contains seeded applicant records
    And the HubSpot sandbox contains the following active properties:
      | address            | price_gbp | bedrooms | property_type |
      | 22 Abbotsbury Road | 2400000   | 4        | house         |

  # --- Test 6: Known property matching ---
  Scenario: Match applicants for a known property returns ranked list
    When the agent sends the request:
      """
      Match applicants for 22 Abbotsbury Road
      """
    Then the response status is "ok"
    And at least 2 applicant matches are returned
    And each match has a match_score between 0.0 and 1.0
    And each match has a readable match_reason
    And the matches are ordered by match_score descending

  Scenario: Match returns total count of applicants searched
    When the agent matches applicants for "22 Abbotsbury Road"
    Then the response includes total_searched
    And total_searched is greater than 0

  # --- Test 7: KYC incomplete flag ---
  Scenario: Applicant with incomplete KYC is included but flagged
    Given the HubSpot sandbox contains an applicant with incomplete KYC
    When the agent matches applicants for "22 Abbotsbury Road"
    Then the response includes that applicant
    And that applicant has kyc_complete set to false
    And the agent can see they cannot progress to offer