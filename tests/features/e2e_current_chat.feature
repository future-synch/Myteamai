@e2e
Feature: The current chat page in a real browser (FS-75)
  The login page (/) and the chat page (/chat), driven through Chromium against
  the real app. Claude runs in mock mode, nothing talks to HubSpot, and the
  browser may reach only the local test server. These scenarios cover the
  CURRENT frontend; the new workspace design is FS-76.

  Background:
    Given the app is running offline with the mock Claude client

  Scenario: Visiting the chat page without a token redirects to the login page
    When I open the chat page with no stored session
    Then I am on the login page

  Scenario: A valid login lands on the chat page
    When I sign in through the login page as the agent
    Then I am on the chat page
    And a session token is stored in the browser

  Scenario: A wrong password stays on the login page and shows an error
    When I try to sign in through the login page with a wrong password
    Then I am on the login page
    And the login page shows the error "Invalid email or password."
    And no session token is stored in the browser

  Scenario: Signing out clears local storage and returns to the login page
    Given I am signed in as the agent on the chat page
    When I click "Sign out"
    Then I am on the login page
    And the browser's local storage is empty
