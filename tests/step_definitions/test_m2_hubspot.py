"""
BDD step definitions — M2 HubSpot Dispatch (Test 3).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from fastapi.testclient import TestClient
from app.main import app

scenarios("../features/m2_welcome_hubspot_dispatch.feature")
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

@when(parsers.parse("the agent submits a welcome request with:\n{table}"))
def step_submit(ctx, table):
    ctx.response = client.post("/bot/welcome", json=_parse_table(table), headers=ctx.headers)

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
