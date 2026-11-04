Feature: Brochure links in the welcome email (FS-57, "Brochure buttons")
  Each matched listing may carry an optional brochure_url, resolved upstream by
  FS-71 and set on the match by the orchestrator (FS-55). Composition renders it
  and never looks it up: it makes no HubSpot, Drive or mail call. A listing with
  no brochure_url is the normal, deliberate state (a confidential listing) and
  renders exactly as it did before: no button, no placeholder, no sentence, no
  log line. The URL is rendered exactly as supplied.

  # -------------------------------------------------------------------------
  # Plain-text body
  # -------------------------------------------------------------------------

  Scenario: The plain text body carries the brochure link under its listing
    Given a matched listing "105 Pine Street" with the brochure link "https://files.example.test/105-pine-street-brochure.pdf"
    When the welcome email is rendered
    Then the text body shows "View brochure: https://files.example.test/105-pine-street-brochure.pdf" directly under listing 1
    And the text body still has exactly 1 numbered listing line

  Scenario: A listing without a brochure link adds nothing to the plain text
    Given a matched listing "105 Pine Street" without a brochure link
    When the welcome email is rendered
    Then the text body contains no brochure line
    And the text body still has exactly 1 numbered listing line

  Scenario: Each link stays with its own listing in the plain text
    Given three matched listings where the first and third have brochure links
    When the welcome email is rendered
    Then the text body shows each link under its own listing only
    And the text body still has exactly 3 numbered listing lines
