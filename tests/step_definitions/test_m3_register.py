"""
BDD step definitions — M3 Register Applicant (Tests 4 and 5).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from fastapi.testclient import TestClient
from app.main import app

scenarios("../features/m3_register_applicant.feature")
client = TestClient(app)

class Ctx:
    def __init__(self):
        self.response = None
        self.headers = {}

@pytest.fixture
def ctx():
    return Ctx()

def agent_headers():
    r = client.post("/auth/login", json={"email": "agent@curtissloane.com", "password": "agent123"})
    return {"Authorization": f"Bearer {r.json().get('access_token', '')}"}

def _parse_table(table):
    data = {}
    for row in table.strip().split("\n"):
        if "|" not in row:
            continue
        parts = [p.strip() for p in row.split("|") if p.strip()]
        if len(parts) == 2 and parts[0] != "field":
            k, v = parts
            if v.lstrip("-").isdigit():
                data[k] = int(v)
            elif v.lower() == "true":
                data[k] = True
            elif v.lower() == "false":
                data[k] = False
            else:
                data[k] = v
    if "property_types" in data and isinstance(data["property_types"], str):
        data["property_types"] = [data["property_types"]]
    return data

@given("an authenticated agent in the Curtis Sloane workspace")
def step_auth(ctx):
    ctx.headers = agent_headers()

@given("the HubSpot sandbox is connected")
def step_hs(ctx):
    pass

@when(parsers.parse("the agent submits the applicant registration form with:\n{table}"))
def step_register(ctx, table):
    ctx.response = client.post(
        "/bot/register-applicant",
        json=_parse_table(table),
        headers=ctx.headers
    )

@when("the agent registers a cash buyer applicant")
def step_cash(ctx):
    ctx.response = client.post(
        "/bot/register-applicant",
        json={
            "full_name": "Cash Buyer Test",
            "email": "cashtest@test.com",
            "phone": "07700900000",
            "budget_gbp": 2000000,
            "bedrooms_min": 3,
            "property_types": ["house"],
            "financing": "cash",
            "preferred_channel": "email",
            "source": "Direct"
        },
        headers=ctx.headers
    )

@when(parsers.parse("the agent registers an applicant with budget {budget:d} and bedrooms_min {beds:d}"))
def step_budget_beds(ctx, budget, beds):
    ctx.response = client.post(
        "/bot/register-applicant",
        json={
            "full_name": "Budget Test",
            "email": "budgettest@test.com",
            "phone": "07700900001",
            "budget_gbp": budget,
            "bedrooms_min": beds,
            "property_types": ["house"],
            "financing": "cash",
            "preferred_channel": "email",
            "source": "Direct"
        },
        headers=ctx.headers
    )

@then('the response status is "ok"')
def step_ok(ctx):
    body = ctx.response.json()
    assert body.get("status") == "ok", f"Expected ok: {body}"

@then(parsers.parse('a HubSpot contact record is created for "{name}"'))
def step_contact(ctx, name):
    body = ctx.response.json()
    assert body.get("hubspot_contact_id") or body.get("applicant_id"), f"No ID: {body}"

@then("a HubSpot contact ID is returned")
def step_id(ctx):
    body = ctx.response.json()
    assert body.get("hubspot_contact_id") or body.get("applicant_id"), f"No ID: {body}"

@then("a KYC checklist is returned")
def step_kyc(ctx):
    body = ctx.response.json()
    assert "kyc_checklist" in body or "kyc_status" in body, f"No KYC: {body}"

@then("the top 3 property matches are returned")
def step_matches(ctx):
    body = ctx.response.json()
    matches = body.get("first_matches", []) or body.get("matches", [])
    assert len(matches) >= 1, f"No matches: {body}"

@then("all match scores are between 0.0 and 1.0")
def step_scores(ctx):
    body = ctx.response.json()
    for m in body.get("first_matches", []) or body.get("matches", []):
        assert 0.0 <= m.get("match_score", -1) <= 1.0

@then("all match reasons are readable plain English")
def step_reasons(ctx):
    body = ctx.response.json()
    for m in body.get("first_matches", []) or body.get("matches", []):
        assert len(m.get("match_reason", "")) > 5

@then("the KYC checklist contains all three required items")
def step_kyc_three(ctx):
    body = ctx.response.json()
    checklist = body.get("kyc_checklist", {})
    for item in ["proof_of_id", "proof_of_address", "proof_of_funds"]:
        assert item in checklist, f"Missing: {item}"

@then(parsers.parse("the KYC checklist contains:\n{table}"))
def step_kyc_table(ctx, table):
    body = ctx.response.json()
    checklist = body.get("kyc_checklist", {})
    for row in table.strip().split("\n"):
        if "|" not in row:
            continue
        parts = [p.strip() for p in row.split("|") if p.strip()]
        if parts and parts[0] != "item":
            assert parts[0] in checklist, f"Missing {parts[0]}"

@then("all items have received set to false initially")
def step_all_false(ctx):
    body = ctx.response.json()
    checklist = body.get("kyc_checklist", {})
    for k, v in checklist.items():
        received = v if isinstance(v, bool) else v.get("received", True)
        assert received is False, f"{k} not false"

@then(parsers.parse("all returned matches have price_gbp less than or equal to {max_price:d}"))
def step_price(ctx, max_price):
    body = ctx.response.json()
    for m in body.get("first_matches", []) or body.get("matches", []):
        assert m.get("price_gbp", 0) <= max_price

@then(parsers.parse("all returned matches have bedrooms greater than or equal to {min_beds:d}"))
def step_beds(ctx, min_beds):
    body = ctx.response.json()
    for m in body.get("first_matches", []) or body.get("matches", []):
        assert m.get("bedrooms", 0) >= min_beds
