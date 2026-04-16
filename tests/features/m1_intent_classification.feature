Feature: M1 Intent Classification — Unknown and Misclassified Requests
  As an estate agent at Curtis Sloane
  I want the system to clearly tell me when it cannot understand my request

  Background:
    Given an authenticated agent in the Curtis Sloane workspace
    And the bot supports 6 functions

  Scenario: Out-of-domain request returns UNKNOWN_INTENT
    When the agent sends "What is the weather in London?"
    Then the error code is "UNKNOWN_INTENT"
    And no Claude API call is made
    And no HubSpot API call is made

  Scenario: Error response includes all 6 capabilities
    When the agent sends "What is the weather in London?"
    Then the capability list contains exactly 6 items

  Scenario Outline: General knowledge questions return UNKNOWN_INTENT
    When the agent sends "<question>"
    Then the error code is "UNKNOWN_INTENT"
    And no Claude API call is made

    Examples:
      | question                                |
      | What is the weather in London?          |
      | Who won the Premier League last season? |
      | What is the capital of France?          |
      | Tell me a joke                          |
      | What time is it?                        |
      | Write me a poem about houses            |
      | How do I make a cup of tea?             |
      | What is the meaning of life?            |
      | Translate this to French: hello         |
      | Summarise the news today                |

  Scenario Outline: Property-adjacent out-of-scope requests return UNKNOWN_INTENT
    When the agent sends "<request>"
    Then the error code is "UNKNOWN_INTENT"

    Examples:
      | request                                              |
      | What is the average house price in Kensington?       |
      | Schedule a viewing for Tom Baker on Thursday         |
      | Send a reminder to all applicants about the open day |
      | Generate a monthly sales report                      |
      | Create a new property listing for 10 Holland Park    |
      | Book a valuation appointment for next Tuesday        |
      | How many properties did we sell last quarter?        |

  Scenario: Greeting returns UNKNOWN_INTENT with warm message
    When the agent sends "Hello"
    Then the error code is "UNKNOWN_INTENT"
    And the response message is welcoming

  Scenario: Thank you returns UNKNOWN_INTENT
    When the agent sends "Thanks for your help"
    Then the error code is "UNKNOWN_INTENT"

  Scenario: Address without verb returns UNKNOWN_INTENT
    When the agent sends "22 Abbotsbury Road"
    Then the error code is "UNKNOWN_INTENT"

  Scenario: Garbled input returns UNKNOWN_INTENT gracefully
    When the agent sends "asdfghjkl"
    Then the error code is "UNKNOWN_INTENT"
    And the system does not crash

  Scenario Outline: Valid property management intents are classified correctly
    When the agent sends "<valid_request>"
    Then the intent is "<expected_intent>"
    And the error code is not "UNKNOWN_INTENT"

    Examples:
      | valid_request                                        | expected_intent    |
      | Welcome new client Sarah Jones from Rightmove        | WELCOME_CLIENT     |
      | Register a new applicant                             | REGISTER_APPLICANT |
      | New applicant Tom Baker 2.5M 4bed                    | REGISTER_APPLICANT |
      | Match applicants for 22 Abbotsbury Road              | MATCH_APPLICANTS   |
      | Who fits 14 Ladbroke Road?                           | MATCH_APPLICANTS   |
      | Find suitable applicants for the Portland Road house | MATCH_APPLICANTS   |
      | Valuation briefing for 8 Portland Road W11           | VALUATION_BRIEF    |
      | Prepare valuation 22 Abbotsbury Road                 | VALUATION_BRIEF    |
      | Comparables for W11 4LA                              | VALUATION_BRIEF    |
      | Draft a handwritten note to Mrs Patterson            | DRAFT_OUTREACH     |
      | Write to Tom Baker about the new listing             | DRAFT_OUTREACH     |
      | Contact Sarah Chen about her search                  | DRAFT_OUTREACH     |
      | KYC status for Tom Baker                             | KYC_STATUS         |
      | AML check for Mrs Patterson                          | KYC_STATUS         |
      | Documents outstanding for David Okonkwo              | KYC_STATUS         |
      | Compliance check James Hyde                          | KYC_STATUS         |

  Scenario: Determinism — same input always produces same output
    When the agent sends "What is the weather in London?" three times
    Then all three results have error code "UNKNOWN_INTENT"

  Scenario: Typo tolerance — valuaton brief classified as VALUATION_BRIEF
    When the agent sends "valuaton brief for 8 Portland Road"
    Then the intent is "VALUATION_BRIEF"
    And the error code is not "UNKNOWN_INTENT"

  Scenario: Unknown intent does not consume AI tokens
    When the agent sends "What is the weather in London?"
    Then zero tokens are consumed
