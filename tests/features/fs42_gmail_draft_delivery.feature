Feature: FS-42 Gmail draft delivery
  As the orchestrator's draft step
  I want a composed message placed in the shared mailbox as a draft
  So that an agent can review, edit and send it by hand, and nothing is lost
  when Gmail cannot be reached

  # Written against the DraftTransport contract with a stub Google service, so
  # it is fully offline. The platform creates drafts; it never sends. Design
  # record: Gmail OAuth credential model (mailbox guard, reconnect-required).

  Background:
    Given a Gmail transport for the futuresynch_dev mailbox backed by a stub Google service

  Scenario: A composed message becomes a Gmail draft with a text part and an HTML part
    When the transport creates a draft for "applicant@example.com" with subject "Three properties to start your search"
    Then exactly one draft is created
    And the draft has a plain-text part and an HTML part
    And the draft is addressed to "applicant@example.com"
    And the draft subject is "Three properties to start your search"

  Scenario: The draft carries no From and no Bcc header
    When the transport creates a draft for "applicant@example.com" with subject "Welcome"
    Then the draft has no From header
    And the draft has no Bcc header

  Scenario: The platform never sends
    When the transport creates a draft for "applicant@example.com" with subject "Welcome"
    Then no send was attempted

  Scenario: The draft reference names the Gmail transport and the configured mailbox
    When the transport creates a draft for "applicant@example.com" with subject "Welcome"
    Then the draft reference has transport "gmail"
    And the draft reference has the draft id Gmail returned
    And the draft reference has the configured mailbox

  Scenario: The mailbox guard runs once, not once per draft
    When the transport creates two drafts for "applicant@example.com"
    Then exactly 2 drafts are created
    And the mailbox was checked exactly once

  Scenario: The mailbox guard stops a draft in the wrong mailbox
    Given the Google account behind the credentials is a different mailbox
    When the transport tries to create a draft for "applicant@example.com" with subject "Welcome"
    Then the draft is refused with a message that mentions the mailbox guard
    And exactly 0 drafts are created
    And the refusal does not say a reconnect is needed
    And a second attempt is refused without asking Gmail again

  Scenario: A revoked sign-in puts the transport in a reconnect-required state
    Given Gmail rejects the sign-in with "invalid_grant: Token has been expired or revoked."
    When the transport tries to create a draft for "applicant@example.com" with subject "Welcome"
    Then the draft is refused and a reconnect is required
    And a second attempt is refused without asking Gmail again

  Scenario: An administrator block is treated like a revoked sign-in
    Given Gmail rejects the sign-in with "admin_policy_enforced"
    When the transport tries to create a draft for "applicant@example.com" with subject "Welcome"
    Then the draft is refused and a reconnect is required

  Scenario: Any other Gmail error does not block later drafts
    Given Gmail fails once with HTTP status 503
    When the transport tries to create a draft for "applicant@example.com" with subject "Welcome"
    Then the draft is refused with a message that mentions "HTTP 503"
    And the refusal does not say a reconnect is needed
    And a later draft for "applicant@example.com" is created

  Scenario: A draft without a recipient is refused before Gmail is contacted
    When the transport tries to create a draft with no recipient
    Then the draft is refused with a message that mentions "recipient"
    And Gmail was not contacted

  Scenario: A recipient containing a line break is refused before Gmail is contacted
    When the transport tries to create a draft for "a@example.com\nBcc: other@example.com" with subject "Welcome"
    Then the draft is refused with a message that mentions "malformed"
    And Gmail was not contacted
