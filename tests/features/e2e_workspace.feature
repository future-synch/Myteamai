@e2e
Feature: The new workspace page in a real browser (FS-76)
  The workspace design at /workspace, driven through Chromium. Only four calls
  are wired: POST /classify, /bot/welcome-from-text, /bot/welcome and
  /bot/register-applicant. Everything else is the design with its client-side
  behaviour. Claude runs in mock mode, HubSpot is faked at the same seams as
  tests/step_definitions/test_m3_register.py, and the browser may reach only the
  local test server (the FS-75 network guard is active in every scenario).

  Two layers. Scenarios that say "the backend will answer ..." stub one endpoint
  with page.route to test the UI contract without HubSpot. Scenarios that say
  "HubSpot is faked" go through the real app.

  Background:
    Given the app is running offline with the mock Claude client

  # ---- session ------------------------------------------------------------

  Scenario: Opening the workspace without a token goes to the login page with next=/workspace
    When I open the workspace with no stored session
    Then the current URL path and query are "/?next=/workspace"

  Scenario: Sign out from the account menu clears the session
    Given I am signed in as the agent on the workspace
    When I sign out from the account menu
    Then I am on the login page
    And the browser's local storage is empty

  Scenario: A 401 from the backend preserves next=/workspace when sending the user to the login page
    Given I am signed in as the agent on the workspace
    And the backend will answer POST "/bot/register-applicant" with the "unauthorised" response
    When I click the "Register applicant" chip
    And I fill in and submit the registration form for "Tom Baker"
    Then the current URL path and query are "/?next=/workspace"
    And the browser's local storage is empty

  # ---- agent input and thread --------------------------------------------

  Scenario: The thread opens with the greeting only
    Given I am signed in as the agent on the workspace
    Then the thread holds one message, "Ready. Type a command or use the chips above to run a flow."
    And the thread mentions none of "Sarah Chen", "James Hyde", "Tom Baker", "Patterson", "Ladbroke"

  Scenario: Pressing Enter sends the command
    Given I am signed in as the agent on the workspace
    When I type "What is the weather in London?" in the agent box and press Enter
    Then the agent shows the capability card

  Scenario: Shift+Enter adds a line and sends nothing
    Given I am signed in as the agent on the workspace
    When I type "first line" then Shift+Enter then "second line" in the agent box
    Then the agent box holds two lines
    And no POST to "/classify" was sent

  Scenario: Running an empty command does nothing
    Given I am signed in as the agent on the workspace
    When I click Run with the agent box empty
    Then no POST to "/classify" was sent
    And the thread holds one message, "Ready. Type a command or use the chips above to run a flow."

  Scenario: TS Test 11 - an out-of-scope request shows the capability card
    Given I am signed in as the agent on the workspace
    When I type "What is the weather in London?" in the agent box and click Run
    Then the agent shows the capability card

  Scenario: The typing indicator shows while the request is in flight and is removed after
    Given I am signed in as the agent on the workspace
    And the backend holds POST "/classify" until I let it through
    When I type "What is the weather in London?" in the agent box and click Run
    Then the typing indicator is shown
    When I let the held request through
    Then the typing indicator is gone
    And the agent shows the capability card

  Scenario: Clear puts the greeting back
    Given I am signed in as the agent on the workspace
    And I have sent "What is the weather in London?" from the agent box
    When I click Clear
    Then the thread holds one message, "Ready. Type a command or use the chips above to run a flow."

  # ---- welcome ------------------------------------------------------------

  Scenario: Free-text welcome renders a result card with the client name and no placeholder
    Given I am signed in as the agent on the workspace
    When I type "Welcome new client, James Hyde, came through Rightmove" in the agent box and click Run
    Then a result card says "Dear James Hyde,"
    And the result card has an "Extracted:" line naming "James Hyde" and "Rightmove"
    And the result card has no "[" placeholder
    And the browser sent POST "/classify" and then POST "/bot/welcome-from-text"

  Scenario: Run flow on Generate welcome opens the form and sends dispatch false
    Given I am signed in as the agent on the workspace
    When I run the "welcome" flow from Action Flows
    Then the welcome form is shown in the Command Centre
    And the welcome form has no dispatch field
    When I submit the welcome form for "James Hyde"
    Then a result card says "Dear James Hyde,"
    And a POST to "/bot/welcome" was sent with dispatch set to false
    And the welcome form has collapsed

  Scenario: A blank client name is refused in the browser and nothing is sent
    Given I am signed in as the agent on the workspace
    When I run the "welcome" flow from Action Flows
    And I submit the welcome form with the client name left blank
    Then the "client_name" field shows the error "Client name is required"
    And no POST to "/bot/welcome" was sent

  # ---- register applicant -------------------------------------------------

  Scenario: The Register applicant chip shows the registration form
    Given I am signed in as the agent on the workspace
    When I click the "Register applicant" chip
    Then the registration form is shown in the Command Centre
    And the browser sent only POST "/classify"

  Scenario: TS Test 12 equivalent - a blank registration is refused in the browser and nothing is sent
    Given I am signed in as the agent on the workspace
    When I click the "Register applicant" chip
    And I submit the registration form with nothing filled in
    Then the registration form shows the inline error "Full name is required" under "full_name"
    And the registration form shows the inline error "Pick at least one" under "property_types"
    And no POST to "/bot/register-applicant" was sent

  Scenario: Tabbing out of an empty required field shows Required
    Given I am signed in as the agent on the workspace
    When I click the "Register applicant" chip
    And I click into the "full_name" field and tab out without typing
    Then the registration form shows the inline error "Required" under "full_name"

  Scenario: Registering a new applicant through the real app
    Given HubSpot is faked: registering creates a new contact and one listing matches
    And I am signed in as the agent on the workspace
    When I click the "Register applicant" chip
    And I fill in and submit the registration form for "Tom Baker"
    Then the confirmation says "New applicant registered in HubSpot" with ID "7001" and "1 suggested match"
    And the welcome email preview is collapsed
    And a POST to "/bot/register-applicant" was sent with dispatch set to false
    And the registration form has collapsed

  Scenario: Registering an applicant who already exists through the real app
    Given HubSpot is faked: the applicant already exists and their budget differs
    And I am signed in as the agent on the workspace
    When I click the "Register applicant" chip
    And I fill in and submit the registration form for "Tom Baker"
    Then the info card says the applicant already exists and the record was left unchanged
    And the info card has a row for "budget_gbp" saying "we hold “2000000”, you entered “3500000”"

  Scenario: Created response - confirmation with ID and match count, collapsed preview
    Given I am signed in as the agent on the workspace
    And the backend will answer POST "/bot/register-applicant" with the "created" response
    When I click the "Register applicant" chip
    And I fill in and submit the registration form for "Tom Baker"
    Then the confirmation says "New applicant registered in HubSpot" with ID "7001" and "2 suggested matches"
    And the welcome email preview is collapsed
    When I open the welcome email preview
    Then the preview shows the subject "Welcome to Curtis Sloane, Tom" and the text "Dear Tom,"

  Scenario: Existing response - info card with one row per differing field
    Given I am signed in as the agent on the workspace
    And the backend will answer POST "/bot/register-applicant" with the "existing" response
    When I click the "Register applicant" chip
    And I fill in and submit the registration form for "Tom Baker"
    Then the info card says the applicant already exists and the record was left unchanged
    And the info card has a row for "budget_gbp" saying "we hold “2000000”, you entered “3500000”"
    And the info card has a row for "property_types" saying "we hold “house”, you entered “flat; house”"

  Scenario: An errors list is shown as an error card with the reason and a next step
    Given I am signed in as the agent on the workspace
    And the backend will answer POST "/bot/register-applicant" with the "errors" response
    When I click the "Register applicant" chip
    And I fill in and submit the registration form for "Tom Baker"
    Then an error card says "HUBSPOT_SYNC_FAIL"
    And the error card says what to do next
    And the registration form is still open

  Scenario: A 422 is shown as an error card with the reason
    Given I am signed in as the agent on the workspace
    And the backend will answer POST "/bot/register-applicant" with the "unprocessable" response
    When I click the "Register applicant" chip
    And I fill in and submit the registration form for "Tom Baker"
    Then an error card says "value is not a valid email address"
    And the error card says what to do next

  Scenario: The submit button is disabled while the request runs
    Given HubSpot is faked: registering creates a new contact and one listing matches
    And I am signed in as the agent on the workspace
    And the backend holds POST "/bot/register-applicant" until I let it through
    When I click the "Register applicant" chip
    And I fill in and submit the registration form for "Tom Baker"
    Then the registration form's submit button is disabled
    When I let the held request through
    Then the registration form has collapsed

  Scenario: XSS - markup in a name is shown as literal text and never runs
    Given I am signed in as the agent on the workspace
    And the backend will answer POST "/bot/register-applicant" with the "markup" response
    When I click the "Register applicant" chip
    And I fill in and submit the registration form for "<img src=x onerror=window.__xss=1>"
    Then the confirmation shows the text "<img src=x onerror=window.__xss=1>" literally
    When I open the welcome email preview
    Then the preview shows the text "<img src=x onerror=window.__xss=1>" literally
    And the thread contains no active elements that can run code in the top frame
    And window.__xss is undefined

  # ---- everything not wired ----------------------------------------------

  Scenario Outline: An unwired chip says "not connected yet" and sends nothing but /classify
    Given I am signed in as the agent on the workspace
    When I click the "<chip>" chip
    Then the agent says the flow the classifier chose for "<chip>" isn't connected yet
    And the browser sent only POST "/classify"

    Examples:
      | chip             |
      | Match applicants |
      | Valuation brief  |
      | KYC status       |
      | Draft outreach   |
      | Social draft     |

  Scenario Outline: Run flow on a flow card opens its form or says it is not connected
    Given I am signed in as the agent on the workspace
    When I run the "<flow>" flow from Action Flows
    Then <outcome>
    And no POST was sent

    Examples:
      | flow      | outcome                                                  |
      | welcome   | the welcome form is shown in the Command Centre          |
      | applicant | the registration form is shown in the Command Centre     |
      | match     | the agent says "Match applicants" isn't connected yet    |
      | val       | the agent says "Valuation briefing" isn't connected yet  |
      | social    | the agent says "Social content draft" isn't connected yet |
      | outreach  | the agent says "Draft outreach" isn't connected yet      |
      | kyc       | the agent says "KYC / AML status" isn't connected yet    |

  Scenario Outline: Each topbar tab activates its page
    Given I am signed in as the agent on the workspace
    When I click the "<tab>" tab
    Then the "<tab>" tab and the "<page>" page are active and no other is
    And no POST was sent

    Examples:
      | tab             | page |
      | Command Centre  | cc   |
      | Action Flows    | af   |
      | Knowledge Base  | kb   |
      | Social          | sm   |
      | Apps Hub        | ah   |

  Scenario Outline: The model dropdown opens, selects and updates the labels
    Given I am signed in as the agent on the workspace
    When I open the model dropdown
    And I choose the "<model>" model
    Then the model label reads "<model>"
    And the agent header tag reads "<model> · KB loaded"
    And the model dropdown is closed
    And no POST was sent

    Examples:
      | model         |
      | Claude Opus   |
      | Claude Haiku  |
      | GPT-4o        |
      | Claude Sonnet |

  Scenario Outline: The user panel opens on each tab and closes
    Given I am signed in as the agent on the workspace
    When I open the account menu
    And I choose "<item>" from the account menu
    Then the user panel is open and titled "<item>"
    When I close the user panel
    Then the user panel is closed
    And no POST was sent

    Examples:
      | item          |
      | Dashboard     |
      | Documentation |
      | Team          |
      | Profile       |
      | Settings      |

  Scenario: Settings has a Stripe mount point and no card inputs
    Given I am signed in as the agent on the workspace
    When I open the account menu
    And I choose "Settings" from the account menu
    And I click "+ Add card"
    Then the Stripe card element is empty
    And there is no card number, expiry or CVC input anywhere in the page
    And no POST was sent

  # ---- mobile -------------------------------------------------------------

  Scenario: Mobile - the agent input runs a free-text welcome and the page does not scroll sideways
    Given the viewport is 390 by 844
    And I am signed in as the agent on the workspace
    When I type "Welcome new client, James Hyde, came through Rightmove" in the mobile agent box and tap send
    Then the mobile thread shows a result card saying "Dear James Hyde,"
    And the page has no horizontal scroll

  Scenario: Mobile - the registration form fits the screen
    Given the viewport is 390 by 844
    And I am signed in as the agent on the workspace
    When I type "register new applicant" in the mobile agent box and tap send
    Then the registration form is shown in the mobile thread
    And the page has no horizontal scroll

  # =========================================================================
  # FS-76 John comment 11514: demo blockers A (auth return-to) and B (Gmail
  # draft on /workspace), and the remaining register-form fixes.
  # =========================================================================

  # ---- A. Return-to allowlist and auth gate on /workspace -----------------

  Scenario: Signing in from /?next=/workspace lands on /workspace
    When I open the login page at "/?next=/workspace"
    And I fill in and submit the login form as the agent
    Then I am on the workspace page

  Scenario: Signing in from / with no next still lands on /chat
    When I open the login page at "/"
    And I fill in and submit the login form as the agent
    Then I am on the chat page

  Scenario: Signing in from /?next=/chat lands on /chat
    When I open the login page at "/?next=/chat"
    And I fill in and submit the login form as the agent
    Then I am on the chat page

  Scenario: Signing in with an off-allowlist next falls back to /chat
    When I open the login page at "/?next=/admin"
    And I fill in and submit the login form as the agent
    Then I am on the chat page

  Scenario: Signing in with a cross-origin next falls back to /chat
    When I open the login page at "/?next=https://evil.example.com/"
    And I fill in and submit the login form as the agent
    Then I am on the chat page

  Scenario: An invalid token on /workspace clears and redirects to login with next=/workspace
    Given I have the token "not-a-real-jwt" stored
    When I open the workspace
    Then the current URL path and query are "/?next=/workspace"
    And the browser's local storage is empty

  Scenario: A 401 while registering preserves the return-to-/workspace after sign-in
    Given I am signed in as the agent on the workspace
    And the backend will answer POST "/bot/register-applicant" with the "unauthorised" response
    When I click the "Register applicant" chip
    And I fill in and submit the registration form for "Tom Baker"
    Then the current URL path and query are "/?next=/workspace"
    When I fill in and submit the login form as the agent
    Then I am on the workspace page

  # ---- B. Gmail draft checkbox on /workspace register form ----------------

  Scenario: The registration form has an unticked Gmail draft checkbox
    Given I am signed in as the agent on the workspace
    When I click the "Register applicant" chip
    Then the registration form has an unticked "Also create a Gmail draft of the welcome email" checkbox

  Scenario: Registering with the Gmail draft checkbox left unticked sends dispatch:false and shows no draft outcome
    Given HubSpot is faked: registering creates a new contact and one listing matches
    And I am signed in as the agent on the workspace
    When I click the "Register applicant" chip
    And I fill in and submit the registration form for "Tom Baker"
    Then the last POST to "/bot/register-applicant" sent dispatch set to false
    And no draft outcome note is shown

  Scenario: Ticking the Gmail draft checkbox sends dispatch:true and renders the draft outcome
    Given I am signed in as the agent on the workspace
    And the backend will answer POST "/bot/register-applicant" with the "created_fake_draft" response
    When I click the "Register applicant" chip
    And I tick the Gmail draft checkbox and fill in and submit the registration form for "Tom Baker"
    Then the last POST to "/bot/register-applicant" sent dispatch set to true
    And a draft outcome note mentions the "fake" transport

  # ---- John's remaining points on the register form -----------------------

  Scenario: Source on the registration form is a dropdown with the fixed options
    Given I am signed in as the agent on the workspace
    When I click the "Register applicant" chip
    Then the "source" field on the registration form is a select
    And the "source" options are exactly "Rightmove", "Zoopla", "Referral", "Direct", "Other"

  Scenario: Property types on the registration form use the new multiselect with no "Any"
    Given I am signed in as the agent on the workspace
    When I click the "Register applicant" chip
    Then the registration form's property type values are exactly "house", "apartment", "maisonette", "mews", "penthouse", "townhouse"
    And the registration form has no property type labelled "Any"
    And the label "Apartment" appears exactly once in the registration form

  Scenario: The registration form has no Max bedrooms field
    Given I am signed in as the agent on the workspace
    When I click the "Register applicant" chip
    Then the registration form has no "bedrooms_max" field

  Scenario: The welcome email preview is rendered as HTML in a sandboxed iframe with no allow-scripts
    Given I am signed in as the agent on the workspace
    And the backend will answer POST "/bot/register-applicant" with the "created_brochure" response
    When I click the "Register applicant" chip
    And I fill in and submit the registration form for "Tom Baker"
    And I open the welcome email preview
    Then the welcome email preview renders the html body in an iframe whose sandbox does not allow scripts
    And the iframe's body contains the text "View brochure"
