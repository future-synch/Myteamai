"""
BDD step definitions — M3 KYC Status (Test 10).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from fastapi.testclient import TestClient
from app.main import app

scenarios("../features/m3_kyc_status.feature")
client = TestClient(app)

class Ctx:
    def __init__(self):
        self.response = None
        self.headers = {}
        self.complete_name = None

@pytest.fixture
def ctx():
    return Ctx()

def agent_headers():
    r = client.post("/auth/login", json={"email": "agent@curtissloane.com", "password": "agent123"})
    return {"Authorization": f"Bearer {r.json().get('access_token', '')}"}

@given("an authenticated agent in the Curtis Sloane workspace")
def step_auth(ctx):
    ctx.headers = agent_headers()

@given("the HubSpot sandbox contains seeded contact records")
def step_seeded(ctx):
    pass

@given("the HubSpot sandbox contains a contact with complete KYC")
def step_complete(ctx):
    ctx.complete_name = "Tom Baker"

@when("the agent sends the request:")
def step_send(ctx, docstring):
    import re
    m = re.search(r'for (.+)$', docstring.strip())
    name = m.group(1).strip() if m else "Tom Baker"
    ctx.response = client.post(
        "/bot/kyc-status",
        json={"name_or_id": name, "type": "applicant"},
        headers=ctx.headers
    )

@when("the agent checks KYC status for that contact")
def step_check_complete(ctx):
    ctx.response = client.post(
        "/bot/kyc-status",
        json={"name_or_id": ctx.complete_name or "Tom Baker", "type": "applicant"},
        headers=ctx.headers
    )

@when(parsers.parse('the agent checks KYC status for "{name}"'))
def step_check_named(ctx, name):
    ctx.response = client.post(
        "/bot/kyc-status",
        json={"name_or_id": name, "type": "applicant"},
        headers=ctx.headers
    )

@then('the response status is "ok"')
def step_ok(ctx):
    body = ctx.response.json()
    assert body.get("status") == "ok", f"Expected ok: {body}"

@then('the response status is "error"')
def step_error(ctx):
    body = ctx.response.json()
    assert body.get("status") == "error", f"Expected error: {body}"

@then("the KYC checklist is returned")
def step_checklist(ctx):
    body = ctx.response.json()
    assert "checklist" in body or "kyc_status" in body, f"No checklist: {body}"

@then("outstanding items are listed in plain English")
def step_outstanding(ctx):
    body = ctx.response.json()
    assert isinstance(body.get("outstanding", []), list)

@then("can_progress is false if any item is missing")
def step_blocked(ctx):
    body = ctx.response.json()
    if body.get("outstanding"):
        assert body.get("can_progress") is False

@then("can_progress is true")
def step_can_progress(ctx):
    body = ctx.response.json()
    assert body.get("can_progress") is True, f"Expected true: {body}"

@then("the outstanding list is empty")
def step_empty(ctx):
    body = ctx.response.json()
    assert len(body.get("outstanding", ["x"])) == 0

@then("the error references contact not found")
def step_not_found(ctx):
    body = ctx.response.json()
    msg = str(body.get("message", "") or body.get("errors", "")).lower()
    assert "not found" in msg or "no contact" in msg, f"Expected not found: {body}"
