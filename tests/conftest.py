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


# ---------------------------------------------------------------------------
# FS-50 — Gherkin tag → pytest marker conversion
# ---------------------------------------------------------------------------
# pytest-bdd's default tag→marker mapping preserves hyphens, which pytest's
# marker filter can't select in `-m` expressions. Convert here so the
# addopts filter in pytest.ini works, and so @blocked-duplicate-policy
# scenarios skip by default rather than run.

def pytest_bdd_apply_tag(tag: str, function):
    if tag == "blocked-duplicate-policy":
        marker = pytest.mark.skip(reason="Blocked on duplicate-applicant policy decision (Q6)")
        marker(function)
        return True
    if tag == "integration":
        marker = pytest.mark.integration
        marker(function)
        return True
    return None


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
    """Canned listing per FS-16 spec — 22 Abbotsbury Road, £2.4M, 4-bed, house."""
    return {
        "id":             "listing-001",
        "name":           "22 Abbotsbury Road",
        "price_gbp":      "2400000",
        "bedrooms":       "4",
        "listing_type":   "house",
        "neighborhood":   "Holland Park",
        "postcode":       "W14 8EP",
        "outside_space":  "garden",
    }


@pytest.fixture
def mock_hubspot_applicants():
    """
    Three applicants per FS-16 spec against the £2.4M reference listing:
      1. Tom Baker    — cash,          £2.5M, beds_min 3, house, KYC complete
      2. Sarah Chen   — mortgage_aip,  £2.3M, beds_min 4, house, KYC in_progress
      3. James Hyde   — cash,          £1.8M — FILTERED OUT (below 95% threshold)

    Note: original FS-16 spec put Sarah at £2.2M, but the Stage 3 budget filter
    (budget < price * 0.95 = £2,280,000) would exclude her too — leaving only
    Tom, breaking the "≥2 matches" and "KYC-incomplete flagged" scenarios and
    orphaning the contact-002 entry in mock_claude_match_scores. Sarah bumped
    to £2.3M so she survives the filter and both scenarios exercise cleanly.
    Everything else follows the FS-16 spec verbatim.
    """
    return [
        {
            "id":                        "contact-001",
            "name":                      "Tom Baker",
            "email":                     "tom.baker@example.com",
            "budget_gbp":                "2500000",
            "bedrooms_min":              "3",
            "bedrooms_max":              None,
            "property_types":            "house",
            "financing":                 "cash",
            "must_have":                 "garden",
            "timeline_weeks":            "4",
            "kyc_status":                "complete",
            "kyc_documents_outstanding": "",
        },
        {
            "id":                        "contact-002",
            "name":                      "Sarah Chen",
            "email":                     "sarah.chen@example.com",
            "budget_gbp":                "2300000",
            "bedrooms_min":              "4",
            "bedrooms_max":              None,
            "property_types":            "house",
            "financing":                 "mortgage_aip",
            "must_have":                 "parking",
            "timeline_weeks":            "8",
            "kyc_status":                "in_progress",
            "kyc_documents_outstanding": "proof_of_id,proof_of_funds",
        },
        {
            "id":                        "contact-003",
            "name":                      "James Hyde",
            "email":                     "james.hyde@example.com",
            "budget_gbp":                "1800000",
            "bedrooms_min":              "4",
            "bedrooms_max":              None,
            "property_types":            "house",
            "financing":                 "cash",
            "must_have":                 "",
            "timeline_weeks":            "12",
            "kyc_status":                "complete",
            "kyc_documents_outstanding": "",
        },
    ]


@pytest.fixture
def mock_claude_scores():
    """
    Deterministic JSON scoring per FS-16 spec — scores contact-001 and
    contact-002 (contact-003/James Hyde is filtered out before scoring).
    Returned as the raw JSON string a Claude response would contain.
    """
    return json.dumps([
        {
            "applicant_id": "contact-001",
            "match_score":  0.92,
            "match_reason": "Cash buyer with strong budget headroom of £100,000 above asking price and garden requirement aligns with property outside space.",
        },
        {
            "applicant_id": "contact-002",
            "match_score":  0.74,
            "match_reason": "Mortgage AIP buyer with adequate budget but KYC incomplete — proof of ID and funds outstanding before offer stage.",
        },
    ])
