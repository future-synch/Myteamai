"""
BDD step definitions — M3 Valuation Brief (Test 8).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from fastapi.testclient import TestClient
from app.main import app

scenarios("../features/m3_valuation_brief.feature")
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
        k, v = row[0].strip(), row[1].strip()
        data[k] = int(v) if v.lstrip("-").isdigit() else v
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
    m = re.search(r'for (.+?)(\s+[A-Z]\d+.*)?$', docstring.strip())
    address = m.group(1).strip() if m else "8 Portland Road"
    postcode = "W11 4LA"
    pc = re.search(r'([A-Z]{1,2}\d+\s?\d[A-Z]{2})', docstring)
    if pc:
        postcode = pc.group(1)
    ctx.response = client.post(
        "/bot/valuation-brief",
        json={
            "property_address": address,
            "postcode": postcode,
            "property_type": "house",
            "bedrooms": 4
        },
        headers=ctx.headers
    )

@when("the agent submits a valuation brief request with:")
def step_submit(ctx, datatable):
    data = _parse_datatable(datatable)
    if "address" in data and "property_address" not in data:
        data["property_address"] = data.pop("address")
    ctx.response = client.post("/bot/valuation-brief", json=data, headers=ctx.headers)

@then('the response status is "ok"')
def step_ok(ctx):
    body = ctx.response.json()
    assert body.get("status") == "ok", f"Expected ok: {body}"

@then("the brief contains at least 3 comparables")
def step_comparables(ctx):
    body = ctx.response.json()
    brief = body.get("brief", body)
    total = len(brief.get("sold_comparables", [])) + len(brief.get("active_listings", []))
    assert total >= 3, f"Only {total} comparables: {body}"

@then("the price range contains both a low and high value")
def step_range(ctx):
    body = ctx.response.json()
    brief = body.get("brief", body)
    assert brief.get("price_range_low") is not None
    assert brief.get("price_range_high") is not None

@then("the price_range_high is greater than price_range_low")
def step_range_valid(ctx):
    body = ctx.response.json()
    brief = body.get("brief", body)
    assert brief.get("price_range_high", 0) > brief.get("price_range_low", 0)

@then("the AI commentary is at least 150 words")
def step_commentary(ctx):
    body = ctx.response.json()
    brief = body.get("brief", body)
    text = brief.get("ai_commentary", "") or brief.get("briefing", "")
    assert len(text.split()) >= 150, f"Only {len(text.split())} words"

@then("the brief contains a price_per_sqft value")
def step_ppsqft(ctx):
    body = ctx.response.json()
    brief = body.get("brief", body)
    assert brief.get("price_per_sqft") is not None

@then("the price_per_sqft is greater than 0")
def step_ppsqft_pos(ctx):
    body = ctx.response.json()
    brief = body.get("brief", body)
    assert brief.get("price_per_sqft", 0) > 0
