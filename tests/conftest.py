"""
Shared pytest fixtures for My Team AI test suite.

Sets ANTHROPIC_MODE=mock at import time so any test that hits a Claude-backed
bot function gets deterministic templated responses without burning credits.
The mock client (app/clients/claude_client.py) intentionally echoes prompt
fields back, so tests can verify field propagation end-to-end.
"""
import json
import os
import pytest

# Force mock Claude before app modules are imported by step def files.
os.environ.setdefault("ANTHROPIC_MODE", "mock")


class StepContext:
    """Mutable context bag shared between BDD step functions."""
    def __init__(self):
        self.text = None
        self.result = None
        self.results = []
        self.validation_error = None
        self.request_data = {}


@pytest.fixture
def ctx():
    return StepContext()


# ---------------------------------------------------------------------------
# FS-16 fixtures — HubSpot Listing + applicant fetch + Claude scoring mocks
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_hubspot_listing():
    """Canned listing at £2,400,000 — the reference property used by m3_match tests."""
    return {
        "id":             "test-listing-1",
        "name":           "22 Abbotsbury Road",
        "price_gbp":      2400000,
        "bedrooms":       4,
        "listing_type":   "house",
        "neighborhood":   "Holland Park",
        "postcode":       "W14 8EP",
        "outside_space":  "garden",
        "works_required": "none",
    }


@pytest.fixture
def mock_hubspot_applicants():
    """
    Three applicants for the £2.4M / 4-bed / house reference listing:
      1. Cash buyer, £2.5M, 3-4 beds, house — passes filter, KYC complete
      2. Mortgage AIP, £2.3M, 4 beds, house — passes filter (2.3M > 2.28M threshold),
         KYC incomplete
      3. Cash buyer, £1.8M — FILTERED OUT (below 95% budget threshold of £2.28M)

    (Applicant 2's budget is £2.3M — deliberately just above the 95% floor to
    exercise "≥2 matches" and "KYC-incomplete flagged" scenarios together.
    Original FS-16 spec said £2.2M; that's below threshold and would fail both.)
    """
    return [
        {
            "id":                        "app-1",
            "name":                      "Sarah Chen",
            "email":                     "sarah@example.com",
            "budget_gbp":                "2500000",
            "bedrooms_min":              "3",
            "bedrooms_max":              "4",
            "property_types":            "house;flat",
            "financing":                 "cash",
            "must_have":                 "garden, period features",
            "timeline_weeks":            "4",
            "kyc_status":                "complete",
            "kyc_documents_outstanding": "",
        },
        {
            "id":                        "app-2",
            "name":                      "Tom Baker",
            "email":                     "tom@example.com",
            "budget_gbp":                "2300000",
            "bedrooms_min":              "4",
            "bedrooms_max":              "4",
            "property_types":            "house",
            "financing":                 "mortgage_aip",
            "must_have":                 "parking",
            "timeline_weeks":            "8",
            "kyc_status":                "outstanding",
            "kyc_documents_outstanding": "proof_of_funds, proof_of_address",
        },
        {
            "id":                        "app-3",
            "name":                      "David Okonkwo",
            "email":                     "david@example.com",
            "budget_gbp":                "1800000",
            "bedrooms_min":              "3",
            "bedrooms_max":              "5",
            "property_types":            "house",
            "financing":                 "cash",
            "must_have":                 "",
            "timeline_weeks":            "2",
            "kyc_status":                "complete",
            "kyc_documents_outstanding": "",
        },
    ]


@pytest.fixture
def mock_claude_scores():
    """
    Deterministic JSON scoring for applicants 1 and 2 (applicant 3 is filtered
    out before scoring). Returned as the raw JSON string a Claude response
    would contain.
    """
    return json.dumps([
        {
            "applicant_id": "app-1",
            "match_score":  0.95,
            "match_reason": "Cash buyer with strong budget headroom above the £2.4M asking, complete KYC, and short 4-week timeline; must-have features align with the garden and period features on this property.",
        },
        {
            "applicant_id": "app-2",
            "match_score":  0.75,
            "match_reason": "Mortgage-AIP buyer just above the 95% budget floor with an 8-week timeline; KYC outstanding will need to clear before offer, and must-have parking is not confirmed on the listing.",
        },
    ])
