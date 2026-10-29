"""
FS-55 orchestration — step (c) brochure resolution.

Scenarios here test only the ORCHESTRATION: that the brochure delegate
is called the right number of times, with the right argument, in the
right order relative to composition, and that failure in one listing
does not cascade. The brochure function's own logic lives in FS-71's
suite; find_matching_listings' logic lives in FS-70's; composition's
in FS-57's.

The orchestrator takes an injected BrochureLinkSource (FS-71 seam) rather
than importing a brochure function by name, so tests install a fake source
via the function's `source=` parameter instead of monkey-patching.
Composition, matching and registration stay module-level functions and
are still swapped via monkeypatch.
"""
from __future__ import annotations

import ast
import asyncio
import inspect
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from app.functions import bot_functions as bf
from app.models.schemas import RegisterApplicantRequest
from app.services.brochures import BrochureLinkSource, FakeBrochureLinkSource
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


class _SpyingFakeBrochureSource(FakeBrochureLinkSource):
    """FakeBrochureLinkSource with ctx-wide call tracking + optional raises.

    Subclasses the real fake so the Background's statement — "a fake brochure
    source is installed" — is literally true. The orchestrator sees a
    BrochureLinkSource; `isinstance(..., FakeBrochureLinkSource)` holds.
    """

    def __init__(self, state: Dict[str, Any]) -> None:
        super().__init__()
        self._state = state

    def get_brochure_link(self, listing_id: str) -> Optional[str]:
        state = self._state
        state["brochure_calls"].append(
            CallRecord((str(listing_id),), {}, state["seq"].next())
        )
        if str(listing_id) in state["brochure_raises"]:
            raise RuntimeError(f"forced brochure failure for {listing_id}")
        return super().get_brochure_link(str(listing_id))


@pytest.fixture
def ctx(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> Dict[str, Any]:
    caplog.set_level(logging.DEBUG, logger=bf.log.name)
    state: Dict[str, Any] = {
        "seq": _Seq(),
        "brochure_calls": [],      # list[CallRecord]
        "compose_calls": [],       # list[CallRecord]
        "match_calls": [],         # list[CallRecord]
        "register_calls": [],      # list[CallRecord]
        "brochure_raises": set(),  # listing_ids whose lookup raises
        "listings": [],            # returned by matching spy
        "sentinel_client": object(),
        "response": None,
        "raised": None,
        "caplog": caplog,
    }
    state["source"] = _SpyingFakeBrochureSource(state)

    async def _register_spy(criteria: dict, client: Any) -> RegistrationResult:
        state["register_calls"].append(CallRecord((criteria, client), {}, state["seq"].next()))
        return RegistrationResult(contact_id="contact-FS55-001", created=True)

    async def _match_spy(criteria: dict, limit: int = 3) -> List[dict]:
        state["match_calls"].append(CallRecord((criteria,), {"limit": limit}, state["seq"].next()))
        # Shallow copy so the orchestrator's in-place brochure_url mutation
        # does not leak back into the arranged fixture.
        return [dict(m) for m in state["listings"]]

    def _compose_spy(req: Any, matches: List[dict], agent_name: Optional[str] = None) -> Dict[str, str]:
        state["compose_calls"].append(
            CallRecord((req, matches), {"agent_name": agent_name}, state["seq"].next())
        )
        return {"subject": "Welcome", "html_body": "<p>ok</p>", "text_body": "ok"}

    def _build_client() -> Any:
        return state["sentinel_client"]

    monkeypatch.setattr(bf, "register_applicant_in_hubspot", _register_spy)
    monkeypatch.setattr(bf, "find_matching_listings", _match_spy)
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


@given("a fake brochure source is installed")
def _bg_fake_source_installed(ctx: Dict[str, Any]) -> None:
    # The ctx fixture built the spy; it satisfies the BrochureLinkSource
    # Protocol and subclasses FakeBrochureLinkSource.
    assert isinstance(ctx["source"], BrochureLinkSource)
    assert isinstance(ctx["source"], FakeBrochureLinkSource)


@given("composition is swapped for a spy")
def _bg_compose_swapped(ctx: Dict[str, Any]) -> None:
    assert bf._compose_welcome_draft.__name__ == "_compose_spy"


# ---------------------------------------------------------------------------
# Givens — scenario-specific arrangements
# ---------------------------------------------------------------------------


@given("an applicant registers successfully")
def given_register_ok(ctx: Dict[str, Any]) -> None:
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
        ctx["source"].set(listing["id"], f"https://cdn.example-hubfs.test/{listing['id']}.pdf")


@given("the second listing has no brochure in HubSpot")
def given_second_no_brochure(ctx: Dict[str, Any]) -> None:
    # First and third have URLs; second returns None (fake defaults to None
    # for any key not explicitly set, so just set the two with URLs).
    for i, listing in enumerate(ctx["listings"]):
        if i != 1:
            ctx["source"].set(listing["id"], f"https://cdn.example-hubfs.test/{listing['id']}.pdf")


@given("no listing has a brochure in HubSpot")
def given_none_have_brochure(ctx: Dict[str, Any]) -> None:
    # Fake returns None for unset keys; nothing to arrange.
    pass


@given("the brochure lookup raises an error for every listing")
def given_brochure_raises(ctx: Dict[str, Any]) -> None:
    for listing in ctx["listings"]:
        ctx["brochure_raises"].add(str(listing["id"]))


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------


@when("fn_register_applicant runs with dispatch false")
def when_run_dispatch_false(ctx: Dict[str, Any]) -> None:
    req = _valid_request()
    try:
        ctx["response"] = asyncio.run(
            bf.fn_register_applicant(req, agent_name="Agent", source=ctx["source"])
        )
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
    # The orchestrator module source has no google-shaped import.
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


@then("composition receives 2 brochure URLs and one absent value")
def then_two_urls_one_absent(ctx: Dict[str, Any]) -> None:
    assert len(ctx["compose_calls"]) == 1
    matches = ctx["compose_calls"][0].args[1]
    urls = [m.get("brochure_url") for m in matches]
    assert sum(1 for u in urls if u is not None) == 2
    assert sum(1 for u in urls if u is None) == 1


@then("no error is reported for the second listing")
def then_no_error_second(ctx: Dict[str, Any]) -> None:
    # The orchestrator uses WELCOME_FAILED / DRAFT_FAILED tags; a None from
    # the brochure source is NOT a failure.
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
    # Composition rendering is FS-57's concern; what this orchestration test
    # asserts is only that EVERY brochure URL passed to composition is None.
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


@then("an error is logged at error level for each failed listing")
def then_error_logged_per_failed(ctx: Dict[str, Any]) -> None:
    error_records = [
        r for r in ctx["caplog"].records
        if r.levelno == logging.ERROR and "brochure" in r.getMessage().lower()
    ]
    assert len(error_records) == len(ctx["brochure_raises"]), (
        f"expected {len(ctx['brochure_raises'])} error logs; got {len(error_records)}: "
        f"{[r.getMessage() for r in error_records]}"
    )
    for r in error_records:
        msg = r.getMessage()
        assert any(lid in msg for lid in ctx["brochure_raises"]), (
            f"error log did not name any raising listing: {msg!r}"
        )


@then("get_brochure_link is called before fn_generate_welcome")
def then_order(ctx: Dict[str, Any]) -> None:
    # Composition's spy stands in for fn_generate_welcome's role here.
    assert ctx["brochure_calls"], "expected at least one brochure call"
    assert ctx["compose_calls"], "expected a composition call"
    last_brochure = ctx["brochure_calls"][-1].seq
    first_compose = ctx["compose_calls"][0].seq
    assert last_brochure < first_compose, (
        f"brochure must finish before composition starts; "
        f"brochure seq {last_brochure} vs compose seq {first_compose}"
    )
