# PROPOSED ADDITIONS to FS-71 §7 — for John to ratify, amend or strike.
# None of these change the ticket's 14 scenarios (fs71_brochure_link_lookup.feature,
# verbatim). Each covers a row of the §4 table or a §6 acceptance criterion that §7
# does not exercise, and the ones marked "REST reader" drive the real HubSpotRestReader
# through a mock transport so paths, params, JSON shapes and status handling are tested.

Feature: Brochure link lookup — proposed additions

  Scenario: A 401 is a credential failure too
    Given the HubSpot client returns 401
    When the brochure link is requested
    Then an error is raised
    And nothing is returned

  Scenario: The REST reader returns the url end to end
    Given a listing with one note marked "brochure" carrying one attachment
    When the brochure link is requested through the REST reader
    Then the url from the files api is returned
    And no url is constructed in application code

  Scenario: The REST reader follows pagination
    Given a listing with more associated notes than fit one page
    And only a note on the second page is marked "brochure"
    When the brochure link is requested through the REST reader
    Then that attachment's url is returned

  Scenario: A rate limit is retried and then succeeds
    Given a listing with one note marked "brochure" carrying one attachment
    And HubSpot answers 429 to the first 2 requests
    When the brochure link is requested through the REST reader
    Then the url from the files api is returned

  Scenario: A server error that persists is raised, not flattened to nothing
    Given HubSpot answers 503 to every request
    When the brochure link is requested through the REST reader
    Then an error is raised
    And nothing is returned
    And 3 requests were attempted

  Scenario: A file that has gone from HubSpot returns nothing
    Given a listing with one note marked "brochure" carrying one attachment
    And the attachment's file no longer exists in HubSpot
    When the brochure link is requested
    Then nothing is returned
    And no error is raised
    And the listing id is logged at info level

  Scenario: A file that is not a document is refused
    Given a listing with a note marked "brochure"
    And its attachment is an image
    When the brochure link is requested
    Then nothing is returned
    And a warning is logged naming the file

  Scenario: The in-memory source returns what it was given
    Given an in-memory brochure source mapping listing "L-1" to "https://example.test/b1.pdf"
    Then listing "L-1" yields "https://example.test/b1.pdf"
    And listing "L-2" yields nothing
    And both brochure sources satisfy the BrochureLinkSource protocol

  Scenario: Configuration selects the in-memory source
    Given BROCHURE_LINK_SOURCE is "fake"
    When the brochure link source is built
    Then it is the in-memory source

  Scenario: Configuration selects the HubSpot source
    Given BROCHURE_LINK_SOURCE is "hubspot"
    When the brochure link source is built
    Then it is the HubSpot source

  Scenario: An unrecognised value does not quietly mean no brochures
    Given BROCHURE_LINK_SOURCE is "hubspt"
    When the brochure link source is built
    Then building it raises an error naming BROCHURE_LINK_SOURCE
