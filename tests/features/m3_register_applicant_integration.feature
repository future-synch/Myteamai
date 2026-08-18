Feature: Register an applicant against the live dev tenant
  As the integration half of the register_applicant_in_hubspot() test suite
  I want the same behaviour verified against FutureSynch dev portal 148226118
  So that a property renamed during the FS-44 migration, an option
    HubSpot itself won't accept, or a value HubSpot coerces on the way in
    is caught in test rather than in production

  # =====================================================
  # SECTION 10: Live dev tenant integration      [@integration]
  # =====================================================
  # Run: pytest -m integration
  # Requires HS_DEV_TOKEN authenticating to portal 148226118.
  # Never against production — see the refusal scenarios below.
  # NOTE: integration step definitions are added in a later commit
  # per the PM's execution order — this file lands with the feature
  # scaffold but is currently un-implemented.

  @integration
  Scenario: The suite skips cleanly when no dev token is present
    Given the environment variable HS_DEV_TOKEN is not set
    When the integration suite is run
    Then every integration scenario is skipped
    And the skip reason names the missing variable
    And the run does not report failure

  @integration
  Scenario: The tenant is verified before the first write
    Given HS_DEV_TOKEN is set
    When the integration suite starts
    Then the portal ID is fetched from the account information endpoint
    And the run continues only if it is 148226118
    And the verified portal ID is printed in the run output

  @integration
  Scenario: The suite refuses to run against Curtis Sloane production
    Given the supplied token belongs to portal 143653372
    When the integration suite starts
    Then the run aborts before any write
    And the failure states that writes to the production tenant are prohibited
    And no contact is created

  @integration
  Scenario: The suite refuses to run against any unrecognised portal
    Given the supplied token belongs to a portal that is not 148226118
    When the integration suite starts
    Then the run aborts before any write

  @integration
  Scenario: A run cleans up records left behind by earlier runs
    Given the dev tenant contains contacts carrying the TEST- prefix from a previous run
    When the integration suite starts
    Then those contacts are removed before the first scenario executes
    And the count removed is reported in the run output

  @integration
  Scenario: Each run uses email addresses unique to that run
    When the integration suite generates a test applicant
    Then the email address carries the TEST- prefix and a per-run identifier
    And the domain is one that cannot receive mail
    And running the suite twice in succession produces no duplicate-email error

  @integration
  Scenario: A real contact is created in the dev tenant
    When a valid applicant is registered against the live dev tenant
    Then HubSpot returns a contact ID
    And fetching that ID returns a contact record
    And the record is visible in portal 148226118

  @integration
  Scenario: Every property the code writes exists in the dev tenant
    Given the canonical constants module lists every property the code writes
    When the property definitions are fetched from the live dev tenant
    Then every property the code writes exists on the Contacts object
    And any missing property is reported by name

  @integration
  Scenario: Written values are returned byte-for-byte
    When a valid applicant is registered against the live dev tenant
    And the created contact is fetched back from HubSpot
    Then every supplied value is returned exactly as it was sent
    And no value has been case-changed, trimmed or substituted

  @integration
  Scenario: HubSpot itself rejects an option value outside the configured set
    When a registration is attempted with an option value HubSpot does not define
    Then HubSpot returns an error
    And the error is surfaced with the property name and the offending value
    And no contact is created

  @integration
  Scenario: The created contact is findable by its email address
    Given an applicant has been registered against the live dev tenant
    When the dev tenant is searched by that email address
    Then exactly one contact is returned
    And it is the contact that was just created

  @integration
  Scenario: Every record created by a scenario is removed afterwards
    When an integration scenario completes
    Then the contact it created is deleted from the dev tenant
    And no TEST- prefixed contact remains from that scenario

  @integration
  Scenario: Cleanup runs even when the scenario fails
    Given an integration scenario fails partway through
    When the run finishes
    Then any contact it created is still removed
    And the original failure is the one reported

  @integration
  Scenario: The suite touches nothing outside its own records
    Given the dev tenant contains contacts without the TEST- prefix
    When the integration suite runs and completes its cleanup
    Then those contacts are unchanged
    And no non-prefixed record has been created, modified or deleted
