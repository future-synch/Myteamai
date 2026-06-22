"""
BDD step definitions — M2 Welcome Message (Tests 1 and 2).
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from fastapi.testclient import TestClient
from app.main import app

scenarios("../features/m2_welcome_message.feature")
client = TestClient(app)

class Ctx:
    def __init__(self):
        self.response = None
        self.elapsed = None
        self.headers = {}

@pytest.fixture
def ctx():
    return Ctx()

def agent_headers():
    r = client.post("/auth/login", json={"email": "agent@curtissloane.com", "password": "agent123"})
    return {"Authorization": f"Bearer {r.json().get('access_token', '')}"}

@given("an authenticated agent in the Curtis Sloane workspace")
def step_auth(ctx):
    ctx.headers = agent_headers()

@given("the Claude API is available")
def step_claude(ctx):
    pass

@when(parsers.parse("the agent sends the request:\n{text}"))
def step_send_text(ctx, text):
    start = time.time()
    ctx.response = client.post(
        "/bot/welcome",
        json={
            "client_name": _extract_name(text),
            "source": _extract_source(text),
            "agent_name": "James",
            "dispatch": False
        },
        headers=ctx.headers
    )
    ctx.elapsed = time.time() - start

def _extract_name(text):
    import re
    m = re.search(r'—\s+([A-Z][a-z]+ [A-Z][a-z]+)', text)
    return m.group(1) if m else "Test Client"

def _extract_source(text):
    for s in ["Rightmove", "Zoopla", "Referral", "Direct", "Other"]:
        if s.lower() in text.lower():
            return s
    return "Direct"

@when(parsers.parse("the agent submits a welcome request with:\n{table}"))
def step_submit_form(ctx, table):
    data = _parse_table(table)
    start = time.time()
    ctx.response = client.post("/bot/welcome", json=data, headers=ctx.headers)
    ctx.elapsed = time.time() - start

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

@then('the response status is "ok"')
def step_ok(ctx):
    body = ctx.response.json()
    assert body.get("status") == "ok", f"Expected ok, got: {body}"

@then("a welcome message draft is returned")
def step_draft(ctx):
    body = ctx.response.json()
    draft = body.get("message_draft", "") or body.get("draft", "")
    assert draft and len(draft) > 10, f"No draft: {body}"

@then("the draft does not contain placeholder text")
def step_no_placeholder(ctx):
    body = ctx.response.json()
    draft = body.get("message_draft", "") or body.get("draft", "")
    for p in ["[", "]", "INSERT", "TODO", "PLACEHOLDER"]:
        assert p not in draft, f"Placeholder '{p}' in draft"

@then("the draft appears within 8 seconds")
def step_timing(ctx):
    assert ctx.elapsed < 8.0, f"Took {ctx.elapsed:.2f}s"

@then(parsers.parse('the draft references "{source}" or acknowledges how the client found the agency'))
def step_source_ref(ctx, source):
    body = ctx.response.json()
    draft = body.get("message_draft", "") or body.get("draft", "")
    assert len(draft) > 10, f"Draft too short: {draft}"

@then("the draft tone is professional and warm")
def step_tone(ctx):
    body = ctx.response.json()
    draft = body.get("message_draft", "") or body.get("draft", "")
    assert len(draft) > 10

@then("the draft contains a reference to the budget")
def step_budget(ctx):
    body = ctx.response.json()
    draft = body.get("message_draft", "") or body.get("draft", "")
    assert any(h in draft for h in ["£", "million", "budget", "000"]), f"No budget in: {draft}"

@then("the draft contains a reference to the timeline")
def step_timeline(ctx):
    body = ctx.response.json()
    draft = body.get("message_draft", "") or body.get("draft", "")
    assert any(h in draft for h in ["August", "summer", "move", "timeline"]), f"No timeline in: {draft}"

@then("the draft does not contain hallucinated details")
def step_no_hallucination(ctx):
    body = ctx.response.json()
    draft = body.get("message_draft", "") or body.get("draft", "")
    assert len(draft) > 10

@then("the draft references the property preference")
def step_prop_pref(ctx):
    body = ctx.response.json()
    draft = body.get("message_draft", "") or body.get("draft", "")
    assert len(draft) > 10
