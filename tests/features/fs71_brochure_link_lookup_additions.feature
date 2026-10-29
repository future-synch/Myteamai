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

  Scenario: A rate limit is retried once and then succeeds
    Given a listing with one note marked "brochure" carrying one attachment
    And HubSpot answers 429 to the first request
    When the brochure link is requested through the REST reader
    Then the url from the files api is returned

  Scenario: A server error that persists is raised, not flattened to nothing
    Given HubSpot answers 503 to every request
    When the brochure link is requested through the REST reader
    Then an error is raised
    And nothing is returned
    And 2 requests were attempted

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

  # --- Retry policy: FS-50 section 7, the "existing client policy" the ticket names ---

  Scenario: A 429 waits for Retry-After before its one retry
    Given a listing with one note marked "brochure" carrying one attachment
    And HubSpot answers 429 to the first request with a Retry-After of 3 seconds
    When the brochure link is requested through the REST reader
    Then the url from the files api is returned
    And the wait before the retry was 3s

  Scenario: A very long Retry-After is capped because this runs in a request path
    Given a listing with one note marked "brochure" carrying one attachment
    And HubSpot answers 429 to the first request with a Retry-After of 120 seconds
    When the brochure link is requested through the REST reader
    Then the url from the files api is returned
    And the wait before the retry was 10s

  Scenario: A 429 without Retry-After waits a default second
    Given a listing with one note marked "brochure" carrying one attachment
    And HubSpot answers 429 to the first request
    When the brochure link is requested through the REST reader
    Then the url from the files api is returned
    And the wait before the retry was 1s

  Scenario: A 5xx is retried once, straight away
    Given a listing with one note marked "brochure" carrying one attachment
    And HubSpot answers 503 to the first request
    When the brochure link is requested through the REST reader
    Then the url from the files api is returned
    And the retry came without a wait

  Scenario: A 429 that persists is raised after the one retry
    Given HubSpot answers 429 to every request
    When the brochure link is requested through the REST reader
    Then an error is raised
    And the error carries status 429
    And 2 requests were attempted

  Scenario: A client error other than 429 is not retried
    Given HubSpot answers 400 to every request
    When the brochure link is requested through the REST reader
    Then an error is raised
    And the error carries status 400
    And 1 request was attempted

  Scenario: A credential failure is not retried
    Given the HubSpot client returns 403
    When the brochure link is requested
    Then an error is raised
    And 1 request was attempted

  Scenario: A timeout is raised as a timeout and not retried
    Given HubSpot times out on every request
    When the brochure link is requested through the REST reader
    Then an error is raised
    And the error is a timeout
    And 1 request was attempted

  Scenario: A dropped connection is raised and not retried
    Given HubSpot drops the connection on every request
    When the brochure link is requested through the REST reader
    Then an error is raised
    And the error is not a timeout
    And the error carries status 0
    And 1 request was attempted

  # --- File access: fail closed. HubSpot's Files API has eight access values. ---

  Scenario Outline: Publicly reachable files return their url
    Given a listing with a brochure note whose file access is <access>
    When the brochure link is requested
    Then the url is returned
    And nothing is logged above info level

    Examples:
      | access               |
      | PUBLIC_NOT_INDEXABLE |
      | PUBLIC_INDEXABLE     |

  Scenario Outline: Any other access value is refused, with a warning
    Given a listing with a brochure note whose file access is <access>
    When the brochure link is requested
    Then nothing is returned
    And a warning is logged naming the access value <access>

    Examples:
      | access               |
      | SENSITIVE            |
      | HIDDEN_PRIVATE       |
      | HIDDEN_SENSITIVE     |
      | HIDDEN_INDEXABLE     |
      | HIDDEN_NOT_INDEXABLE |
      | SOME_FUTURE_VALUE    |

  Scenario: A file with no access value is refused
    Given a listing with a brochure note whose file has no access value
    When the brochure link is requested
    Then nothing is returned
    And a warning is logged

  Scenario: The allow-list names exactly the two public values
    Then the access check is a fail-closed allow-list

  # --- Async callers (FS-50 style) get the same behaviour ---

  Scenario: The async adapter returns the same url
    Given a listing with one note marked "brochure" carrying one attachment
    When the brochure link is requested asynchronously
    Then the url from the files api is returned

  Scenario: The async brochure alias returns the same url
    Given a listing with one note marked "brochure" carrying one attachment
    When the brochure link is requested asynchronously through the alias
    Then the url from the files api is returned

  Scenario: A credential failure propagates through the async adapter
    Given the HubSpot client returns 403
    When the brochure link is requested asynchronously
    Then an error is raised
    And nothing is returned

  # --- Probe: python -m app.services.brochures LISTING_ID ---

  Scenario: The probe prints only the url
    Given a listing with one note marked "brochure" carrying one attachment
    When the probe is run for the listing
    Then the probe exits 0 and prints only the url

  Scenario: The probe reports a missing brochure as a normal answer
    Given a listing with no notes
    When the probe is run for the listing
    Then the probe exits 1 and prints nothing on stdout

  Scenario: The probe reports a credential failure without echoing the token
    Given the HubSpot client returns 403
    When the probe is run for the listing
    Then the probe exits 2 and reports an auth error
    And the probe never prints the token

  Scenario: The probe reports HubSpot being down as an error
    Given HubSpot answers 503 to every request
    When the probe is run for the listing through the REST reader
    Then the probe exits 2 and reports an error
