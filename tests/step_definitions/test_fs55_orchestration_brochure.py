"""
FS-55 orchestration — step (c) brochure resolution.

Scenarios here test only the ORCHESTRATION: that the brochure delegate
is called the right number of times, with the right arguments, in the
right order relative to composition, and that failure in one listing
does not cascade. The brochure function's own logic lives in FS-71's
suite; find_matching_listings' logic lives in FS-70's; composition's
in FS-57's. All three are swapped for spies in Background.

The orchestrator in app.functions.bot_functions imports its delegates
by name, so monkeypatching those module-level attributes replaces them
for the duration of a scenario without touching the delegates themselves.
"""
from __future__ import annotations

import ast
import asyncio
import inspect
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from app.functions import bot_functions as bf
from app.models.schemas import RegisterApplicantRequest
from app.services.hubspot_registration import RegistrationResult


scenarios("../features/fs55_orchestration_brochure.feature")


# ---------------------------------------------------------------------------
# Spies — plain callables with a .calls list; shared via the ctx fixture.
# ---------------------------------------------------------------------------


@dataclass
class CallRecord:
    args: tuple
    kwargs: dict
    seq: int  # global ordering counter


class _Seq:
    """Monotonic counter so we can assert call ordering across spies."""

    def __init__(self) -> None:
        self.n = 0

    def next(self) -> int:
        self.n += 1
        return self.n


@pytest.fixture
def ctx(monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    state: Dict[str, Any] = {
        "seq": _Seq(),
        "brochure_calls": [],      # list[CallRecord]
        "compose_calls": [],       # list[CallRecord]
        "match_calls": [],         # list[CallRecord]
        "register_calls": [],      # list[CallRecord]
        "brochure_returns": {},    # listing_id -> url | None
        "brochure_raises": set(),  # listing_ids whose lookup raises
        "listings": [],            # returned by matching spy
        "sentinel_client": object(),  # identity-asserted
        "response": None,
        "raised": None,
    }

    async def _register_spy(criteria: dict, client: Any) -> RegistrationResult:
        state["register_calls"].append(CallRecord((criteria, client), {}, state["seq"].next()))
        return RegistrationResult(contact_id="contact-FS55-001", created=True)

    async def _match_spy(criteria: dict, limit: int = 3) -> List[dict]:
        state["match_calls"].append(CallRecord((criteria,), {"limit": limit}, state["seq"].next()))
        # Return a shallow copy so the orchestrator's in-place brochure_url
        # mutation does not leak back into the arranged fixture.
        return [dict(m) for m in state["listings"]]

    async def _brochure_spy(client: Any, listing_id: str, doc_type: str = "brochure") -> Optional[str]:
        state["brochure_calls"].append(
            CallRecord((client, listing_id), {"doc_type": doc_type}, state["seq"].next())
        )
        if listing_id in state["brochure_raises"]:
            raise RuntimeError(f"forced brochure failure for {listing_id}")
        return state["brochure_returns"].get(listing_id)

    def _compose_spy(req: Any, matches: List[dict], agent_name: Optional[str] = None) -> Dict[str, str]:
        state["compose_calls"].append(
            CallRecord((req, matches), {"agent_name": agent_name}, state["seq"].next())
        )
        return {"subject": "Welcome", "html_body": "<p>ok</p>", "text_body": "ok"}

    def _build_client() -> Any:
        return state["sentinel_client"]

    monkeypatch.setattr(bf, "register_applicant_in_hubspot", _register_spy)
    monkeypatch.setattr(bf, "find_matching_listings", _match_spy)
    monkeypatch.setattr(bf, "get_brochure_link", _brochure_spy)
    monkeypatch.setattr(bf, "_compose_welcome_draft", _compose_spy)
    monkeypatch.setattr(bf, "build_hubspot_client", _build_client)

    return state


def _valid_request() -> RegisterApplicantRequest:
    """Minimal payload that passes RegisterApplicantRequest validation."""
    return RegisterApplicantRequest(
        full_name="Test Applicant",
        email="test.applicant@example.com",
        phone="+447700900000",
        budget_gbp=2_000_000,
        bedrooms_min=2,
        property_types=["house"],
        financing="cash",
        preferred_channel="email",
        source="direct",
        dispatch=False,
    )


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------


@given("registration succeeds for the submitted applicant")
def _bg_registration_succeeds(ctx: Dict[str, Any]) -> None:
    # The register spy already returns a success RegistrationResult.
    pass


@given("brochure resolution is swapped for a spy")
def _bg_brochure_swapped(ctx: Dict[str, Any]) -> None:
    # Patched in the ctx fixture; this step is here as a readable anchor.
    assert bf.get_brochure_link.__name__ == "_brochure_spy"


@given("composition is swapped for a spy")
def _bg_compose_swapped(ctx: Dict[str, Any]) -> None:
    assert bf._compose_welcome_draft.__name__ == "_compose_spy"


# ---------------------------------------------------------------------------
# Givens — scenario-specific arrangements
# ---------------------------------------------------------------------------


@given("an applicant registers successfully")
def given_register_ok(ctx: Dict[str, Any]) -> None:
    # No-op: the spy returns a successful RegistrationResult.
    pass


def _arrange_listings(ctx: Dict[str, Any], count: int) -> None:
    ctx["listings"] = [
        {"id": f"listing-{i+1}", "address": f"{i+1} Example Rd", "price_gbp": 2_000_000}
        for i in range(count)
    ]


@given("matching returns 3 listings")
def given_three_listings(ctx: Dict[str, Any]) -> None:
    _arrange_listings(ctx, 3)


@given("matching returns 1 listing")
def given_one_listing(ctx: Dict[str, Any]) -> None:
    _arrange_listings(ctx, 1)


@given("every listing has a brochure in HubSpot")
def given_every_has_brochure(ctx: Dict[str, Any]) -> None:
    for listing in ctx["listings"]:
        ctx["brochure_returns"][listing["id"]] = f"https://files.hubspot.com/{listing['id']}.pdf"


@given("the second listing has no brochure in HubSpot")
def given_second_no_brochure(ctx: Dict[str, Any]) -> None:
    # First and third have URLs; second is explicitly None.
    for i, listing in enumerate(ctx["listings"]):
        ctx["brochure_returns"][listing["id"]] = (
            None if i == 1 else f"https://files.hubspot.com/{listing['id']}.pdf"
        )


@given("no listing has a brochure in HubSpot")
def given_none_have_brochure(ctx: Dict[str, Any]) -> None:
    for listing in ctx["listings"]:
        ctx["brochure_returns"][listing["id"]] = None


@given("the brochure lookup raises an error for every listing")
def given_brochure_raises(ctx: Dict[str, Any]) -> None:
    for listing in ctx["listings"]:
        ctx["brochure_raises"].add(listing["id"])


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------


@when("fn_register_applicant runs with dispatch false")
def when_run_dispatch_false(ctx: Dict[str, Any]) -> None:
    req = _valid_request()
    try:
        ctx["response"] = asyncio.run(bf.fn_register_applicant(req, agent_name="Agent"))
    except Exception as exc:
        ctx["raised"] = exc


# ---------------------------------------------------------------------------
# Thens
# ---------------------------------------------------------------------------


@then("get_brochure_link is called exactly 3 times")
def then_called_three_times(ctx: Dict[str, Any]) -> None:
    assert len(ctx["brochure_calls"]) == 3, (
        f"expected 3 brochure calls; got {len(ctx['brochure_calls'])}"
    )


@then("composition receives 3 brochure URLs")
def then_compose_receives_three_urls(ctx: Dict[str, Any]) -> None:
    assert len(ctx["compose_calls"]) == 1
    matches = ctx["compose_calls"][0].args[1]
    urls = [m.get("brochure_url") for m in matches]
    assert urls.count(None) == 0, f"expected 0 Nones; got {urls}"
    assert len(urls) == 3


@then("no Google Drive client is constructed")
def then_no_google_client(ctx: Dict[str, Any]) -> None:
    # 1. The orchestrator module source has no google-shaped import.
    tree = ast.parse(inspect.getsource(bf))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            assert root != "google", f"orchestrator imports {node.module!r}"
            assert root != "googleapiclient"
        elif isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                assert root != "google"
                assert root != "googleapiclient"
    # 2. The brochure delegate was called with our sentinel HubSpot client —
    # proof the orchestrator passes the HubSpot client through, not a Drive
    # one it secretly constructed.
    for call in ctx["brochure_calls"]:
        assert call.args[0] is ctx["sentinel_client"]


@then("composition receives 2 brochure URLs and one absent value")
def then_two_urls_one_absent(ctx: Dict[str, Any]) -> None:
    assert len(ctx["compose_calls"]) == 1
    matches = ctx["compose_calls"][0].args[1]
    urls = [m.get("brochure_url") for m in matches]
    assert sum(1 for u in urls if u is not None) == 2
    assert sum(1 for u in urls if u is None) == 1


@then("no error is reported for the second listing")
def then_no_error_second(ctx: Dict[str, Any]) -> None:
    # The orchestrator uses the WELCOME_FAILED / DRAFT_FAILED tags; a None
    # from the brochure delegate is NOT a failure — the Gherkin wants
    # confirmation that nothing was logged into the errors envelope for it.
    assert ctx["response"] is not None
    for err in ctx["response"].errors:
        assert "brochure" not in err.lower()
        assert "BROCHURE" not in err


@then("the composed message is returned successfully")
def then_composed_ok(ctx: Dict[str, Any]) -> None:
    assert ctx["response"] is not None
    assert ctx["response"].welcome_draft is not None


@then("the composed message contains no brochure button")
def then_no_button(ctx: Dict[str, Any]) -> None:
    # Composition rendering is FS-57's concern; what the orchestration test
    # asserts here is only that EVERY brochure URL passed to composition is
    # None, so nothing could be rendered as a button downstream.
    matches = ctx["compose_calls"][0].args[1]
    assert all(m.get("brochure_url") is None for m in matches), (
        f"expected all brochure_url None; got {[m.get('brochure_url') for m in matches]}"
    )


@then("the applicant id is returned")
def then_applicant_id_returned(ctx: Dict[str, Any]) -> None:
    assert ctx["response"] is not None
    assert ctx["response"].applicant_id == "contact-FS55-001"


@then("the matches are returned")
def then_matches_returned(ctx: Dict[str, Any]) -> None:
    assert ctx["response"] is not None
    assert len(ctx["response"].first_matches) == 3


@then("get_brochure_link is called before fn_generate_welcome")
def then_order(ctx: Dict[str, Any]) -> None:
    # Composition's spy name stands in for fn_generate_welcome's role here.
    assert ctx["brochure_calls"], "expected at least one brochure call"
    assert ctx["compose_calls"], "expected a composition call"
    last_brochure = ctx["brochure_calls"][-1].seq
    first_compose = ctx["compose_calls"][0].seq
    assert last_brochure < first_compose, (
        f"brochure must finish before composition starts; "
        f"brochure seq {last_brochure} vs compose seq {first_compose}"
    )
