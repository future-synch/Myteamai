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

  Scenario: Opening the workspace without a token goes to the login page
    When I open the workspace with no stored session
    Then I am on the login page

  Scenario: Sign out from the account menu clears the session
    Given I am signed in as the agent on the workspace
    When I sign out from the account menu
    Then I am on the login page
    And the browser's local storage is empty

  Scenario: A 401 from the backend sends the user to the login page
    Given I am signed in as the agent on the workspace
    And the backend will answer POST "/bot/register-applicant" with the "unauthorised" response
    When I click the "Register applicant" chip
    And I fill in and submit the registration form for "Tom Baker"
    Then I am on the login page
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
