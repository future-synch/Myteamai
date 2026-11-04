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

  # -------------------------------------------------------------------------
  # HTML body — the button
  # -------------------------------------------------------------------------

  Scenario: A listing with a brochure link renders one button
    Given a matched listing "105 Pine Street" with the brochure link "https://files.example.test/105-pine-street-brochure.pdf"
    When the welcome email is rendered
    Then the html body contains exactly 1 brochure button
    And the button text is "View brochure"
    And the button href equals the supplied link
    And the button sits in a single-cell presentation table
    And the button cell carries a bgcolor attribute
    And the button cell has a visible border
    And the button's aria-label names the listing address

  Scenario: A listing without a brochure link renders no button and no substitute text
    Given a matched listing "105 Pine Street" without a brochure link
    When the welcome email is rendered
    Then the html body contains exactly 0 brochure buttons
    And the html body contains no text about a brochure
    And the listing address still appears in the html body

  Scenario: Mixed listings render one button each where available
    Given three matched listings where the first and third have brochure links
    When the welcome email is rendered
    Then the html body contains exactly 2 brochure buttons
    And each button href equals its own listing's link
    And every listing address still appears in the html body

  Scenario: An empty brochure link is treated as no brochure
    Given a matched listing "105 Pine Street" whose brochure link is empty
    When the welcome email is rendered
    Then the html body contains exactly 0 brochure buttons
    And the html body contains no text about a brochure
    And the text body contains no brochure line

  Scenario: Addresses are never turned into links
    Given three matched listings where the first and third have brochure links
    When the welcome email is rendered
    Then the html body contains no link other than the brochure buttons

  # -------------------------------------------------------------------------
  # Escaping and fidelity
  # -------------------------------------------------------------------------

  Scenario: The brochure link is escaped in the href, not trusted
    Given a matched listing "105 Pine Street" with a brochure link containing quotes, an ampersand and angle brackets
    When the welcome email is rendered
    Then the raw html body does not contain the unescaped link
    And the raw html body contains the escaped link
    And the button href equals the supplied link
    And the html body contains exactly 1 brochure button

  Scenario: The brochure link is rendered exactly as supplied
    Given a matched listing "105 Pine Street" with the brochure link "https://files.example.test/b.pdf?download=1&utm=a%20b"
    When the welcome email is rendered
    Then the button href equals the supplied link
    And the text body contains the supplied link unchanged

  Scenario: The address in the aria-label is escaped too
    Given a matched listing with a hostile address and a brochure link
    When the welcome email is rendered
    Then the raw html body does not contain the unescaped hostile address
    And the button's aria-label names the listing address

  Scenario: Nothing is logged for a listing without a brochure
    Given a matched listing "105 Pine Street" without a brochure link
    When the welcome email is rendered with logging captured
    Then nothing was logged

  # -------------------------------------------------------------------------
  # Layout — as in the sample email: details on the left, the button on the right
  # -------------------------------------------------------------------------

  Scenario: A listing with a brochure link is a row with its details on the left and the button on the right
    Given a matched listing "105 Pine Street" with the brochure link "https://files.example.test/105-pine-street-brochure.pdf"
    When the welcome email is rendered
    Then the listing is a full-width presentation row of exactly two cells
    And the left cell holds the listing details and no button
    And the right cell is right-aligned and holds the button

  Scenario: Each listing with a link is its own row carrying its own details
    Given three matched listings where the first and third have brochure links
    When the welcome email is rendered
    Then there are exactly 2 listing rows
    And each row's left cell holds its own listing's details

  Scenario: A listing without a link stays a plain list item with no table
    Given a matched listing "105 Pine Street" without a brochure link
    When the welcome email is rendered
    Then the html body contains no table

  # -------------------------------------------------------------------------
  # The seam: a link set on a match by the orchestrator reaches the draft
  # -------------------------------------------------------------------------

  Scenario: A link set on a match reaches the welcome draft through the register endpoint
    Given the register endpoint is served by offline fakes
    And matching returns three listings, the first with a brochure link and all carrying internal fields
    When the applicant is registered through the endpoint
    Then the welcome draft html has exactly 1 brochure button for that link
    And the welcome draft text body shows that link under listing 1
    And no internal match field appears in the welcome draft
