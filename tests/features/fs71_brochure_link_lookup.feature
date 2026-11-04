Feature: Brochure link lookup

  Scenario: A listing with a marked brochure note returns its url
    Given a listing with one note marked "brochure" carrying one attachment
    When the brochure link is requested
    Then the url from the files api is returned
    And no url is constructed in application code

  Scenario: A later floor plan does not displace the brochure
    Given a listing with a note marked "brochure" attached on Monday
    And a note marked "floor_plan" attached on Tuesday
    When the brochure link is requested
    Then the brochure's url is returned
    And the floor plan's url is not returned

  Scenario: Position in the attachment list is never relied on
    Given a listing with one note marked "brochure"
    And that note carries the floor plan id first and the brochure id second
    When the brochure link is requested
    Then the note is skipped as ambiguous
    And a warning is logged
    And nothing is returned

  Scenario: A re-published brochure supersedes the older one
    Given a listing with two notes marked "brochure"
    And the second has a later timestamp
    When the brochure link is requested
    Then the url of the second note's attachment is returned

  Scenario: The marker is found in an HTML note body
    Given a listing with a brochure note whose body lines are joined with <br>
    When the brochure link is requested
    Then the marker is matched
    And the url is returned

  Scenario: A swapped attachment is refused, not sent
    Given a listing with a note marked "brochure"
    And its attachment is named "88 Westbourne Park Road - Floor Plan.pdf"
    When the brochure link is requested
    Then nothing is returned
    And a warning is logged naming the file

  Scenario: The print variant is refused
    Given a listing with a note marked "brochure"
    And its attachment is named "88 Westbourne Park Road - Brochure (Print).pdf"
    When the brochure link is requested
    Then nothing is returned

  Scenario: An unmarked note is not a brochure
    Given a listing with one note carrying a pdf attachment and no marker
    When the brochure link is requested
    Then nothing is returned
    And nothing is logged above info level

  Scenario: Timestamps in different formats order correctly
    Given a listing with two notes marked "brochure"
    And their timestamps use different utc offset formats
    When the brochure link is requested
    Then the genuinely later note's attachment is returned

  Scenario: A listing with no notes returns nothing
    Given a listing with no notes
    When the brochure link is requested
    Then nothing is returned
    And no error is raised
    And nothing is logged above info level

  Scenario: Notes spanning more than one page of associations
    Given a listing with more associated notes than fit one page
    And only a note on the second page is marked "brochure"
    When the brochure link is requested
    Then that attachment's url is returned

  Scenario: A credential failure is not a missing brochure
    Given the HubSpot client returns 403
    When the brochure link is requested
    Then an error is raised
    And nothing is returned

  Scenario: A private file has no usable url
    Given a listing with a brochure note whose file access is PRIVATE
    When the brochure link is requested
    Then nothing is returned
    And the listing id is logged at info level

  Scenario: No Google client is ever constructed
    Given any listing
    When the brochure link is requested
    Then no Google Drive client is constructed
    And no Google credential is read
