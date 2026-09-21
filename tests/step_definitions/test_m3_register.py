"""
BDD step definitions — M3 Register Applicant (Tests 4 and 5), A-2 rev 5.

FS-55: the endpoint now orchestrates register -> match -> welcome -> draft.
The mock intercepts register_applicant_in_hubspot() (step a) so no network is
touched; step c (welcome) runs through the mock Claude client (ANTHROPIC_MODE
=mock, set in conftest); step b/d run their real stub/fake collaborators.
"""
import sys, os, itertools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from fastapi.testclient import TestClient
from app.main import app
import app.functions.bot_functions as bot_functions

scenarios("../features/m3_register_applicant.feature")
client = TestClient(app)

_id_seq = itertools.count(start=7001)


@pytest.fixture(autouse=True)
def mock_register(monkeypatch):
    # Intercept step a — no HubSpot network, deterministic applicant id.
    async def fake_register(criteria, hs_client):
        return str(next(_id_seq))
    monkeypatch.setattr(bot_functions, "register_applicant_in_hubspot", fake_register)


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
        if v.lstrip("-").isdigit():
            data[k] = int(v)
        elif v.lower() in ("true", "false"):
            data[k] = v.lower() == "true"
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


@when("the agent submits the applicant registration form with:")
def step_register(ctx, datatable):
    ctx.response = client.post("/bot/register-applicant",
                               json=_parse_datatable(datatable), headers=ctx.headers)


@when("the agent registers an applicant with dispatch true")
def step_dispatch(ctx):
    ctx.response = client.post("/bot/register-applicant", json={
        "full_name": "Dispatch Test", "email": "dispatch@test.com", "phone": "07700900002",
        "budget_gbp": 2000000, "bedrooms_min": 3, "property_types": ["house"],
        "financing": "cash", "preferred_channel": "email", "source": "Direct",
        "dispatch": True,
    }, headers=ctx.headers)


@when("the agent registers a cash buyer applicant")
def step_cash(ctx):
    ctx.response = client.post("/bot/register-applicant", json={
        "full_name": "Cash Buyer Test", "email": "cashtest@test.com", "phone": "07700900000",
        "budget_gbp": 2000000, "bedrooms_min": 3, "property_types": ["house"],
        "financing": "cash", "preferred_channel": "email", "source": "Direct",
    }, headers=ctx.headers)


@then('the response status is "ok"')
def step_ok(ctx):
    body = ctx.response.json()
    assert body.get("status") == "ok", f"Expected ok: {body}"


@then("an applicant ID is returned")
def step_id(ctx):
    body = ctx.response.json()
    assert body.get("applicant_id"), f"No applicant_id: {body}"


@then("a welcome draft is returned with subject, html_body and text_body")
def step_welcome(ctx):
    wd = ctx.response.json().get("welcome_draft")
    assert wd and all(k in wd for k in ("subject", "html_body", "text_body")), f"Bad welcome_draft: {wd}"


@then("first_matches is a list")
def step_matches_list(ctx):
    assert isinstance(ctx.response.json().get("first_matches"), list)


@then("first_matches is empty")
def step_matches_empty(ctx):
    assert ctx.response.json().get("first_matches") == []


@then("draft_ref is null")
def step_draft_null(ctx):
    assert ctx.response.json().get("draft_ref") is None


@then("draft_ref has transport, draft_id and mailbox")
def step_draft_ref(ctx):
    dr = ctx.response.json().get("draft_ref")
    assert dr and all(k in dr for k in ("transport", "draft_id", "mailbox")), f"Bad draft_ref: {dr}"
    assert dr["transport"] in ("gmail", "fake")


@then("errors is empty")
def step_errors_empty(ctx):
    assert ctx.response.json().get("errors") == []
