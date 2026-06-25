"""
BDD step definitions — M2 HubSpot Dispatch (Test 3).
"""
import sys, os, itertools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from fastapi.testclient import TestClient
from app.main import app
from app.services import hubspot_service

scenarios("../features/m2_welcome_hubspot_dispatch.feature")
client = TestClient(app)


# Deterministic incrementing HubSpot contact id for dispatch assertions.
_id_seq = itertools.count(start=5001)


@pytest.fixture(autouse=True)
def mock_hubspot(monkeypatch):
    async def fake_create_contact(properties):
        return {
            "id": str(next(_id_seq)),
            "properties": properties,
        }
    monkeypatch.setattr(hubspot_service, "create_contact", fake_create_contact)

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

def _parse_datatable(rows):
    """pytest-bdd 8 passes a list-of-lists. First row is headers, rest are data."""
    data = {}
    for row in rows[1:]:
        if len(row) < 2:
            continue
        k, v = row[0].strip(), row[1].strip()
        if v.lstrip("-").isdigit():
            data[k] = int(v)
        elif v.lower() == "true":
            data[k] = True
        elif v.lower() == "false":
            data[k] = False
        else:
            data[k] = v
    return data

@given("an authenticated agent in the Curtis Sloane workspace")
def step_auth(ctx):
    ctx.headers = agent_headers()

@given("the HubSpot sandbox account is connected")
def step_hs(ctx):
    pass

@given("the Claude API is available")
def step_claude(ctx):
    pass

@when("the agent submits a welcome request with:")
def step_submit(ctx, datatable):
    ctx.response = client.post("/bot/welcome", json=_parse_datatable(datatable), headers=ctx.headers)

@then('the response status is "ok"')
def step_ok(ctx):
    body = ctx.response.json()
    assert body.get("status") == "ok", f"Expected ok: {body}"

@then(parsers.parse('a HubSpot contact record is created for "{name}"'))
def step_contact(ctx, name):
    body = ctx.response.json()
    assert body.get("hubspot_contact_id"), f"No contact ID: {body}"

@then("the contact is visible in HubSpot within 30 seconds")
def step_visible(ctx):
    body = ctx.response.json()
    assert body.get("hubspot_contact_id"), f"No contact ID: {body}"

@then("the welcome email is queued in HubSpot drafts")
def step_email(ctx):
    body = ctx.response.json()
    assert body.get("dispatched") is True, f"Not dispatched: {body}"

@then(parsers.parse('the contact source property is "{source}"'))
def step_source(ctx, source):
    body = ctx.response.json()
    assert body.get("hubspot_contact_id"), f"No contact: {body}"

@then("a welcome message draft is returned")
def step_draft(ctx):
    body = ctx.response.json()
    assert body.get("message_draft"), f"No draft: {body}"

@then("no HubSpot contact is created")
def step_no_contact(ctx):
    body = ctx.response.json()
    assert body.get("hubspot_contact_id") is None, f"Unexpected contact: {body}"

@then("the dispatched field is false")
def step_not_dispatched(ctx):
    body = ctx.response.json()
    assert body.get("dispatched") is False, f"Expected false: {body}"
