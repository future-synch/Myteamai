Feature: Register an applicant in HubSpot
  As the registration half of fn_register_applicant()
  I want to validate an applicant payload and create the HubSpot contact
  So that registration can be verified independently of match finding,
    email dispatch, and any AI call

  Background:
    Given a fake HubSpot client with no network access
    And the fake client is bound to portal 148226118
    And the canonical enum constants module is loaded
    And a valid applicant payload

  # =====================================================
  # SECTION 1: Contract boundaries
  # =====================================================

  Scenario: Registration performs no match finding
    When the applicant is registered
    Then no listings are fetched from HubSpot
    And the return value contains no property matches

  Scenario: Registration sends no email and creates no draft
    When the applicant is registered
    Then no request is made to any mail provider
    And no Gmail draft is created
    And no welcome message is generated

  Scenario: Registration generates no KYC checklist
    When the applicant is registered
    Then the return value contains no KYC structure
    And no KYC-related property is written to the contact

  Scenario: Registration makes no AI call
    When the applicant is registered
    Then no request is made to the Claude API
    And no tokens are recorded against the workspace budget

  Scenario: Registration returns the HubSpot contact ID and nothing else
    When the applicant is registered
    Then the return value is the HubSpot contact ID
    And the return value is a non-empty string

  # =====================================================
  # SECTION 2: Required field validation
  # =====================================================

  Scenario Outline: A missing required field is rejected before any HubSpot call
    When the applicant is registered with "<field>" absent
    Then the registration is rejected
    And the error names the field "<field>"
    And no contact is created in HubSpot
    And no HubSpot API call is made at all

    Examples:
      | field             |
      | full_name         |
      | email             |
      | phone             |
      | budget            |
      | beds_required     |
      | property_types    |
      | financing_status  |
      | preferred_channel |
      | source            |

  Scenario Outline: An empty required field is rejected the same as an absent one
    When the applicant is registered with "<field>" set to an empty string
    Then the registration is rejected
    And the error names the field "<field>"
    And no contact is created in HubSpot

    Examples:
      | field     |
      | full_name |
      | email     |
      | phone     |

  Scenario: All validation errors are reported together, not one at a time
    When the applicant is registered with full_name, email and phone all absent
    Then the registration is rejected
    And the error names all three fields
    And the agent is not required to resubmit three times

  Scenario: An optional field may be absent
    When the applicant is registered with no optional fields supplied
    Then the registration succeeds
    And the contact is created

  Scenario: An unrecognised field in the payload is rejected
    When the applicant is registered with an unrecognised field "budget_gbp"
    Then the registration is rejected
    And the error names the unrecognised field
    And no contact is created in HubSpot

  # =====================================================
  # SECTION 3: Email and phone validation
  # =====================================================

  Scenario Outline: A malformed email address is rejected
    When the applicant is registered with email "<value>"
    Then the registration is rejected
    And the error names the field "email"
    And no contact is created in HubSpot

    Examples:
      | value                  |
      | sarah.chen@            |
      | sarah.chen             |
      | @example.com           |
      | sarah chen@example.com |

  Scenario: A valid email address is accepted and stored unchanged
    When the applicant is registered with email "Sarah.Chen@Example.com"
    Then the registration succeeds
    And the email property on the contact holds exactly "Sarah.Chen@Example.com"
    And the address is not lower-cased, trimmed or otherwise altered

  # =====================================================
  # SECTION 4: Enum handling, vocabulary-agnostic
  # =====================================================

  Scenario Outline: A value outside the configured set is rejected
    Given the configured option set for "<field>" is loaded from the constants module
    When the applicant is registered with a "<field>" value not in that set
    Then the registration is rejected
    And the error names the field "<field>"
    And the error lists the permitted values
    And no contact is created in HubSpot

    Examples:
      | field             |
      | budget            |
      | beds_required     |
      | property_types    |
      | financing_status  |
      | preferred_channel |
      | source            |

  Scenario Outline: A value inside the configured set is written through unchanged
    Given the configured option set for "<field>" is loaded from the constants module
    When the applicant is registered with the first value from that set
    Then the registration succeeds
    And the "<field>" property on the contact holds that value byte-for-byte
    And no casing change, trimming or substitution is applied

    Examples:
      | field             |
      | budget            |
      | beds_required     |
      | property_types    |
      | financing_status  |
      | preferred_channel |
      | source            |

  Scenario: Enum comparison is exact, not case-insensitive
    Given the configured option set for "property_types" contains "flat"
    When the applicant is registered with property_types "Flat"
    Then the registration is rejected
    And no contact is created in HubSpot

  Scenario: Enum values come from one canonical module
    When the registration module is inspected
    Then no option value appears as a string literal in the module
    And every option value is referenced from the canonical constants module

  Scenario: A multi-value field accepts several values
    Given "property_types" is configured as a multi-value field
    When the applicant is registered with two values from the configured set
    Then the registration succeeds
    And both values are present on the contact property

  Scenario: An absent multi-value field is stored as no selection, not as an error
    When the applicant is registered with property_types absent
    Then the registration succeeds
    And the property_types property on the contact holds no value

  # =====================================================
  # SECTION 5: Field mapping
  # =====================================================

  Scenario: full_name is split across the native HubSpot name properties
    When the applicant is registered with full_name "Sarah Chen"
    Then the firstname property holds "Sarah"
    And the lastname property holds "Chen"

  Scenario: A single-word name populates lastname and leaves firstname empty
    When the applicant is registered with full_name "Cher"
    Then the lastname property holds "Cher"
    And the firstname property is empty

  Scenario: A multi-part surname is preserved
    When the applicant is registered with full_name "Maria del Carmen Rodriguez"
    Then the firstname property holds "Maria"
    And the lastname property holds "del Carmen Rodriguez"

  Scenario: email and phone map to the native HubSpot properties
    When the applicant is registered
    Then the email address is written to the native email property
    And the phone number is written to the native phone property
    And neither is written to a custom property

  Scenario: Every supplied applicant criterion reaches a HubSpot property
    When the applicant is registered with every supported field populated
    Then every supplied field appears in the HubSpot create payload
    And no supplied field is silently discarded

  Scenario: registration_date is set by the system, not by the caller
    When the applicant is registered
    Then the registration_date property is set to the current date
    And a registration_date supplied in the payload is ignored

  # =====================================================
  # SECTION 6: Duplicate handling                [BLOCKED]
  # =====================================================
  # Excluded from default run via @blocked-duplicate-policy tag.

  @blocked-duplicate-policy
  Scenario: Registering an existing email address does not create a duplicate
    Given a contact already exists with email "sarah.chen@example.com"
    When the applicant is registered with that email address
    Then no duplicate contact is created
    And the existing contact ID is returned

  @blocked-duplicate-policy
  Scenario: The caller is told the contact already existed
    Given a contact already exists with email "sarah.chen@example.com"
    When the applicant is registered with that email address
    Then the return value indicates the contact was pre-existing
    And the agent can be told, rather than being shown a silent success

  @blocked-duplicate-policy
  Scenario: Registering an existing applicant does not overwrite their criteria
    Given a contact already exists with email "sarah.chen@example.com" and a budget already recorded
    When the applicant is registered with a different budget
    Then the existing budget is not overwritten
    And the difference is reported to the caller

  # =====================================================
  # SECTION 7: HubSpot failure handling
  # =====================================================

  Scenario: A 5xx from HubSpot is retried once
    Given HubSpot returns 503 on the first attempt and succeeds on the second
    When the applicant is registered
    Then the contact is created via the second attempt
    And the caller sees a normal success

  Scenario: A persistent 5xx fails cleanly with the payload preserved
    Given HubSpot returns 503 on every attempt
    When the applicant is registered
    Then the registration reports failure
    And the error code is HUBSPOT_SYNC_FAIL
    And the submitted payload is returned to the caller so nothing is retyped
    And no partial contact is left in HubSpot

  Scenario: A 4xx is not retried
    Given HubSpot returns 400
    When the applicant is registered
    Then no retry is attempted
    And the registration reports failure immediately

  Scenario: A 429 is retried after the interval HubSpot specifies
    Given HubSpot returns 429 with a Retry-After header
    When the applicant is registered
    Then the retry waits for the interval given in the header
    And the retry is not immediate

  Scenario: A network timeout is handled as a failure, not a crash
    Given the HubSpot client raises a timeout
    When the applicant is registered
    Then the registration reports failure
    And the exception does not propagate to the caller

  Scenario: A HubSpot property that does not exist is reported by name
    Given HubSpot rejects the create because a property does not exist
    When the applicant is registered
    Then the error names the offending property
    And the error distinguishes a missing property from a bad value

  # =====================================================
  # SECTION 8: Tenant safety
  # =====================================================

  Scenario: The portal is verified before any write
    When the applicant is registered
    Then the portal ID is verified before the create call is made
    And the create call is not made if verification fails

  Scenario: A write to the production portal is refused
    Given the client is bound to portal 143653372
    When the applicant is registered
    Then the registration is refused
    And no create call is made
    And the error states that writes to the production tenant are prohibited

  Scenario: A write to an unrecognised portal is refused
    Given the client is bound to a portal that is neither 148226118 nor 143653372
    When the applicant is registered
    Then the registration is refused
    And no create call is made

  Scenario: The unit suite makes no live HubSpot calls
    When the untagged suite is run
    Then every HubSpot interaction is served by the fake client
    And no outbound network request is made

  # =====================================================
  # SECTION 9: Test data hygiene
  # =====================================================

  Scenario: Records created by the suite are identifiable
    When the suite creates an applicant against the dev tenant
    Then the record carries the TEST- prefix convention
    And the record can be found and removed by that prefix
