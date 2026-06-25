"""
BDD step definitions — M3 Draft Outreach (Test 9).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from fastapi.testclient import TestClient
from app.main import app

scenarios("../features/m3_draft_outreach.feature")
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

def _parse_datatable(rows):
    data = {}
    for row in rows[1:]:
        if len(row) < 2:
            continue
        data[row[0].strip()] = row[1].strip()
    return data

@given("an authenticated agent in the Curtis Sloane workspace")
def step_auth(ctx):
    ctx.headers = agent_headers()

@given("the Claude API is available")
def step_claude(ctx):
    pass

@when("the agent sends the request:")
def step_send(ctx, docstring):
    import re
    name_m = re.search(r'to (Mrs?\.?\s+\w+)', docstring)
    name = name_m.group(1) if name_m else "Mrs Patterson"
    ctx.response = client.post(
        "/bot/draft-outreach",
        json={
            "recipient_name": name,
            "recipient_type": "long_term_resident",
            "channel": "handwritten_note",
            "agent_name": "James",
            "context_notes": docstring.strip()
        },
        headers=ctx.headers
    )

@when("the agent submits an outreach request with:")
def step_submit(ctx, datatable):
    data = _parse_datatable(datatable)
    if "context" in data:
        data["context_notes"] = data.pop("context")
    ctx.response = client.post("/bot/draft-outreach", json=data, headers=ctx.headers)

@then('the response status is "ok"')
def step_ok(ctx):
    body = ctx.response.json()
    assert body.get("status") == "ok", f"Expected ok: {body}"

@then("the draft is returned")
def step_draft(ctx):
    body = ctx.response.json()
    assert body.get("draft") and len(body["draft"]) > 10

@then("the draft word count is less than 120")
def step_words(ctx):
    body = ctx.response.json()
    draft = body.get("draft", "")
    count = body.get("word_count") or len(draft.split())
    assert count < 120, f"Too long: {count} words"

@then("the draft does not contain corporate language")
def step_no_corp(ctx):
    draft = ctx.response.json().get("draft", "").lower()
    for w in ["synergy", "leverage", "pursuant", "aforementioned"]:
        assert w not in draft

@then("the draft does not contain placeholder text")
def step_no_placeholder(ctx):
    draft = ctx.response.json().get("draft", "")
    for p in ["[", "]", "INSERT", "TODO"]:
        assert p not in draft

@then("the tone_notes explain the tone chosen")
def step_tone(ctx):
    notes = ctx.response.json().get("tone_notes", "")
    assert notes and len(notes) > 5
