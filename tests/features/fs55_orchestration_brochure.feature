Feature: FS-55 orchestration — brochure step (c)
  As the orchestrator fn_register_applicant()
  I want to resolve a brochure URL for every matched listing
  So that composition receives the URLs as data, without ever being
  the thing that reaches out to HubSpot or (never) Google Drive

  # Adapted from §"New Gherkin — orchestration of the brochure step" of
  # the FS-55 ticket (revised 20 October 2026). The orchestrator now takes
  # an injected BrochureLinkSource (FS-71 seam) rather than importing the
  # brochure function by name, so the Background installs a fake source
  # instead of monkey-patching a module attribute. The last scenario looks
  # pedantic and is not: if composition is ever called first, someone has
  # moved link resolution inside it, which breaks FS-57's offline
  # guarantee.

  Background:
    Given registration succeeds for the submitted applicant
    And a fake brochure source is installed
    And composition is swapped for a spy

  Scenario: Brochure links are resolved for every matched listing
    Given an applicant registers successfully
    And matching returns 3 listings
    And every listing has a brochure in HubSpot
    When fn_register_applicant runs with dispatch false
    Then get_brochure_link is called exactly 3 times
    And composition receives 3 brochure URLs
    And no Google Drive client is constructed

  Scenario: A listing without a brochure does not affect the others
    Given an applicant registers successfully
    And matching returns 3 listings
    And the second listing has no brochure in HubSpot
    When fn_register_applicant runs with dispatch false
    Then composition receives 2 brochure URLs and one absent value
    And no error is reported for the second listing
    And the composed message is returned successfully

  Scenario: No listing has a brochure
    Given an applicant registers successfully
    And matching returns 3 listings
    And no listing has a brochure in HubSpot
    When fn_register_applicant runs with dispatch false
    Then the composed message is returned successfully
    And the composed message contains no brochure button

  Scenario: Brochure lookup failure does not discard the registration
    Given an applicant registers successfully
    And matching returns 3 listings
    And the brochure lookup raises an error for every listing
    When fn_register_applicant runs with dispatch false
    Then the applicant id is returned
    And the matches are returned
    And the composed message is returned successfully
    And an error is logged at error level for each failed listing

  Scenario: Brochure links are resolved before composition is called
    Given an applicant registers successfully
    And matching returns 1 listing
    When fn_register_applicant runs with dispatch false
    Then get_brochure_link is called before fn_generate_welcome
