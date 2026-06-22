Feature: Valuation Brief — fn_valuation_brief
  As an estate agent at Curtis Sloane
  I want a structured valuation brief for any property
  So that I am prepared for client valuation meetings

  Background:
    Given an authenticated agent in the Curtis Sloane workspace
    And the Claude API is available

  # --- Test 8: Valuation brief ---
  Scenario: Valuation brief returns structured brief with comparables
    When the agent sends the request:
      """
      Valuation briefing for 8 Portland Road W11
      """
    Then the response status is "ok"
    And the brief contains at least 3 comparables
    And the price range contains both a low and high value
    And the price_range_high is greater than price_range_low
    And the AI commentary is at least 150 words

  Scenario: Valuation brief for different property types
    When the agent submits a valuation brief request with:
      | field            | value           |
      | property_address | 14 Ladbroke Road |
      | postcode         | W11 3NR         |
      | property_type    | flat            |
      | bedrooms         | 2               |
    Then the response status is "ok"
    And the brief contains at least 3 comparables
    And the AI commentary is at least 150 words

  Scenario: Valuation brief with sqft returns price per sqft
    When the agent submits a valuation brief request with:
      | field            | value            |
      | property_address | 22 Abbotsbury Road |
      | postcode         | W14 8EP          |
      | property_type    | house            |
      | bedrooms         | 4                |
      | sqft             | 2200             |
    Then the response status is "ok"
    And the brief contains a price_per_sqft value
    And the price_per_sqft is greater than 0