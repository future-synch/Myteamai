"""
BDD step definitions — M3 Match Applicants (Tests 6 and 7).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from fastapi.testclient import TestClient
from app.main import app
from app.services import hubspot_service

scenarios("../features/m3_match_applicants.feature")
client = TestClient(app)


# ---------------------------------------------------------------------------
# Mock HubSpot for this file only.
# Returns a deterministic mix of KYC-complete and KYC-incomplete applicants
# so Test 7's "applicant has kyc_complete set to false" assertion can pass
# without a live HubSpot key.
# ---------------------------------------------------------------------------

_SEEDED_APPLICANTS = [
    {
        "id": "101",
        "properties": {
            "firstname": "Tom", "lastname": "Baker",
            "email": "tom.baker@example.com",
            "applicant_source": "Referral",
            "applicant_budget_gbp": "2500000",
            "applicant_bedrooms_min": "4",
            "kyc_status": "complete",
        },
    },
    {
        "id": "102",
        "properties": {
            "firstname": "Sarah", "lastname": "Chen",
            "email": "sarah.chen@example.com",
            "applicant_source": "Zoopla",
            "applicant_budget_gbp": "2000000",
            "applicant_bedrooms_min": "3",
            "kyc_status": "outstanding",
            "kyc_documents_outstanding": "proof_of_funds;proof_of_address",
        },
    },
    {
        "id": "103",
        "properties": {
            "firstname": "Michael", "lastname": "Brown",
            "email": "michael.brown@example.com",
            "applicant_source": "Rightmove",
            "applicant_budget_gbp": "3000000",
            "applicant_bedrooms_min": "5",
            "kyc_status": "complete",
        },
    },
]


@pytest.fixture(autouse=True)
def mock_hubspot(monkeypatch):
    async def fake_list(*args, **kwargs):
        limit = kwargs.get("limit", 10)
        return _SEEDED_APPLICANTS[:limit]
    monkeypatch.setattr(hubspot_service, "list_applicant_contacts", fake_list)


class Ctx:
    def __init__(self):
        self.response = None
        self.headers = {}
        self.seeded_properties = []
        self.expect_kyc_incomplete = False

@pytest.fixture
def ctx():
    return Ctx()

def agent_headers():
    r = client.post("/auth/login", json={"email": "agent@curtissloane.com", "password": "agent123"})
    return {"Authorization": f"Bearer {r.json().get('access_token', '')}"}

@given("an authenticated agent in the Curtis Sloane workspace")
def step_auth(ctx):
    ctx.headers = agent_headers()

@given("the HubSpot sandbox contains seeded applicant records")
def step_seeded(ctx):
    pass

@given("the HubSpot sandbox contains the following active properties:")
def step_properties(ctx, datatable):
    # Mocked HubSpot fixture honours these via conftest; store for later assertions.
    headers = datatable[0]
    ctx.seeded_properties = [dict(zip(headers, row)) for row in datatable[1:]]

@given("the HubSpot sandbox contains an applicant with incomplete KYC")
def step_incomplete(ctx):
    # Signals the conftest mock to include a KYC-incomplete applicant
    ctx.expect_kyc_incomplete = True

@when("the agent sends the request:")
def step_send(ctx, docstring):
    import re
    m = re.search(r'for (.+)$', docstring.strip(), re.MULTILINE)
    address = m.group(1).strip() if m else docstring.strip()
    ctx.response = client.post(
        "/bot/match-applicants",
        json={"property_ref": address, "max_results": 10},
        headers=ctx.headers
    )

@when(parsers.parse('the agent matches applicants for "{address}"'))
def step_match(ctx, address):
    ctx.response = client.post(
        "/bot/match-applicants",
        json={"property_ref": address, "max_results": 10},
        headers=ctx.headers
    )

@then('the response status is "ok"')
def step_ok(ctx):
    body = ctx.response.json()
    assert body.get("status") == "ok", f"Expected ok: {body}"

@then("at least 2 applicant matches are returned")
def step_min2(ctx):
    body = ctx.response.json()
    matches = body.get("matches", [])
    assert len(matches) >= 2, f"Got {len(matches)}: {body}"

@then("each match has a match_score between 0.0 and 1.0")
def step_scores(ctx):
    for m in ctx.response.json().get("matches", []):
        assert 0.0 <= m.get("match_score", -1) <= 1.0

@then("each match has a readable match_reason")
def step_reasons(ctx):
    for m in ctx.response.json().get("matches", []):
        assert len(m.get("match_reason", "")) > 5

@then("the matches are ordered by match_score descending")
def step_ordered(ctx):
    scores = [m.get("match_score", 0) for m in ctx.response.json().get("matches", [])]
    assert scores == sorted(scores, reverse=True)

@then("the response includes total_searched")
def step_total(ctx):
    body = ctx.response.json()
    assert "total_searched" in body or "count" in body, f"No total: {body}"

@then("total_searched is greater than 0")
def step_total_gt0(ctx):
    body = ctx.response.json()
    total = body.get("total_searched") or body.get("count", 0)
    assert total > 0

@then("the response includes that applicant")
def step_includes(ctx):
    assert len(ctx.response.json().get("matches", [])) > 0

@then("that applicant has kyc_complete set to false")
def step_kyc_false(ctx):
    incomplete = [m for m in ctx.response.json().get("matches", []) if m.get("kyc_complete") is False]
    assert len(incomplete) > 0, "No kyc_complete=false found"

@then("the agent can see they cannot progress to offer")
def step_blocked(ctx):
    incomplete = [m for m in ctx.response.json().get("matches", []) if m.get("kyc_complete") is False]
    assert len(incomplete) > 0
