Feature: Deterministic welcome email with matched listings (FS-57)
  The welcome_draft composed on /bot/register-applicant is built from a fixed
  plain-text template — no Claude call for the body. It lists the applicant's
  first_matches as numbered lines (address, price, bedrooms only), drawn from an
  explicit allowlist so no score, property id, match reason or other field can
  leak. The search line shows only the parts the agent supplied, never the
  HubSpot budget band. The HTML body escapes every inserted value. The count of
  matches (0 / 1 / 2-3) drives the subject and the lead-in line.

  Background:
    Given an authenticated agent in the Curtis Sloane workspace
    And HubSpot registration is served by an offline fake
    And matching is served by an offline fake

  # -------------------------------------------------------------------------
  # Listings come from first_matches only, via the allowlist
  # -------------------------------------------------------------------------

  Scenario: Every listing detail in the email comes from first_matches and nothing else does
    Given the applicant has three matched listings
    When the applicant is registered
    Then the email lists exactly the three matched listings, numbered
    And every address, price and bedroom count in the email is one from first_matches

  Scenario: Fields outside the allowlist never reach the email
    Given the applicant has three matched listings carrying internal fields
    When the applicant is registered
    Then no match score, property id, match reason or note appears in the email

  Scenario: A one-bedroom listing uses the singular
    Given a matched listing with one bedroom
    When the applicant is registered
    Then the listing line reads "1. 3 Maple Court, £650,000, 1 bedroom"

  Scenario: A listing with no bedroom count drops that part
    Given a matched listing with no bedroom count
    When the applicant is registered
    Then the listing line reads "1. 7 Cedar Rise, £680,000"

  # -------------------------------------------------------------------------
  # Search line — supplied parts only, pinned budget wording, never the band
  # -------------------------------------------------------------------------

  Scenario: The search line omits parts that were not supplied
    Given the applicant supplied a flat and a 1000000 budget but no timeline
    And the applicant has one matched listing
    When the applicant is registered
    Then the search line reads "Flat · around £1m"
    And the HubSpot budget band does not appear in the email

  Scenario: A sub-million budget rounds to whole thousands
    Given the applicant supplied a flat and a 750000 budget but no timeline
    And the applicant has one matched listing
    When the applicant is registered
    Then the search line reads "Flat · around £750k"

  Scenario: A budget with a half-million trims to one decimal
    Given the applicant supplied a flat and a 1500000 budget but no timeline
    And the applicant has one matched listing
    When the applicant is registered
    Then the search line reads "Flat · around £1.5m"

  Scenario: A budget with a quarter-million keeps two decimals
    Given the applicant supplied a flat and a 1250000 budget but no timeline
    And the applicant has one matched listing
    When the applicant is registered
    Then the search line reads "Flat · around £1.25m"

  Scenario: The search line includes the timeline when supplied
    Given the applicant supplied a flat, a 1000000 budget and a 12 week timeline
    And the applicant has one matched listing
    When the applicant is registered
    Then the search line reads "Flat · around £1m · within 12 weeks"

  Scenario: An empty search line omits the sentence and the line
    When the welcome email is rendered with no supplied search criteria
    Then the email omits the search sentence and line

  # -------------------------------------------------------------------------
  # HTML escaping
  # -------------------------------------------------------------------------

  Scenario: An address with special characters is HTML-escaped in the html body
    Given a matched listing whose address contains "<" "&" and ">"
    When the applicant is registered
    Then the html body contains the escaped address
    And the html body does not contain the raw unescaped address
    And the text body contains the raw address

  # -------------------------------------------------------------------------
  # 0 / 1 / 2 / 3 match variants
  # -------------------------------------------------------------------------

  Scenario: Zero matches produce a holding message, not a list
    Given the applicant has no matched listings
    When the applicant is registered
    Then the subject is "Thank you for registering with Curtis Sloane"
    And the email says no close match yet
    And the email contains no numbered listing line

  Scenario: One match uses the singular lead-in
    Given the applicant has one matched listing
    When the applicant is registered
    Then the subject is "One property to start your search"
    And the email contains "To start, this one stands out:"
    And the email contains exactly one numbered listing line

  Scenario: Two matches use the plural lead-in
    Given the applicant has two matched listings
    When the applicant is registered
    Then the subject is "Two properties to start your search"
    And the email contains "To start, these are the two that fit best:"
    And the email contains exactly two numbered listing lines

  Scenario: Three matches use the plural lead-in
    Given the applicant has three matched listings
    When the applicant is registered
    Then the subject is "Three properties to start your search"
    And the email contains "To start, these are the three that fit best:"
    And the email contains exactly three numbered listing lines

  # -------------------------------------------------------------------------
  # Greeting
  # -------------------------------------------------------------------------

  Scenario: A single-word name falls back to a nameless greeting
    Given the applicant's name is a single word
    And the applicant has one matched listing
    When the applicant is registered
    Then the email contains "Hello,"
    And the email does not contain "Hi Cher,"

  # -------------------------------------------------------------------------
  # Sign-off — display name injected by test; fallback otherwise
  # -------------------------------------------------------------------------

  Scenario: The sign-off uses the agent's configured display name
    Given the agent has a configured display name "Nadia Rahman"
    And the applicant has one matched listing
    When the applicant is registered
    Then the email is signed off with "Nadia Rahman"
    And the sign-off is not the agent's email local-part

  Scenario: The sign-off falls back to the team name when no display name is configured
    Given the agent has no configured display name
    And the applicant has one matched listing
    When the applicant is registered
    Then the email is signed off as "The Curtis Sloane team"
