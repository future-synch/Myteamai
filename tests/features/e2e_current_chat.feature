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

  Scenario: TS Test 11 - an out-of-scope request shows the unknown-intent card
    Given I am signed in as the agent on the chat page
    When I type "What is the weather in London?" in the free-text box and send it
    Then an error card says "I couldn't understand that request. Here's what I can do:"
    And the error card lists the six capabilities

  Scenario: TS Test 12 - a blank client name is refused in the browser and nothing is sent
    Given I am signed in as the agent on the chat page
    And I open the "Welcome Client" form
    And I fill in the Welcome Client form with source "Rightmove" and agent name "Alex Agent"
    When I submit the Welcome Client form with the client name left blank
    Then the client name field shows the error "Client name is required"
    And no POST to "/bot/welcome" was sent

  Scenario: Control for Test 12 - a complete Welcome Client form does send POST /bot/welcome
    Given I am signed in as the agent on the chat page
    And I open the "Welcome Client" form
    And I fill in the Welcome Client form with source "Rightmove" and agent name "Alex Agent"
    When I submit the Welcome Client form with the client name "James Hyde"
    Then a POST to "/bot/welcome" was sent with dispatch set to false
    And a bot message greets "James Hyde"

  Scenario: Tabbing out of an empty required field shows Required
    Given I am signed in as the agent on the chat page
    And I open the "Welcome Client" form
    When I click into the client name field and tab out without typing
    Then the client name field shows the error "Required"

  Scenario: Free-text welcome is classified, extracted and drafted
    Given I am signed in as the agent on the chat page
    When I type "Welcome new client, James Hyde, came through Rightmove" in the free-text box and send it
    Then a success message mentions "James Hyde"
    And the success message has an "Extracted:" line naming "James Hyde" and "Rightmove"
    And the success message contains the draft greeting "Dear James Hyde,"
    And the browser sent POST "/classify" and then POST "/bot/welcome-from-text"
