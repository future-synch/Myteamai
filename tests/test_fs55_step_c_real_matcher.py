"""
FS-55 step (c) against the REAL FS-70 matcher.

The orchestration suite swaps find_matching_listings for a spy that returns
{"id": ...}. The real function returns the TS section 5.2 PropertyMatch shape,
whose identifier key is "property_id". These tests keep the real matcher in
the loop (only the HubSpot listings fetch is faked) so the key the matcher
emits and the key step (c) reads cannot drift apart unnoticed.
"""
from __future__ import annotations

from typing import Any, Dict, List

import pytest

import app.services.hubspot_service as hs
from app.functions import bot_functions as bf
from app.models.schemas import RegisterApplicantRequest
from app.services.brochures import FakeBrochureLinkSource
from app.services.hubspot_registration import RegistrationResult

LINK_1 = "https://cdn.example-hubfs.test/1393968357613-brochure.pdf"


def _listing(listing_id: str, price: int) -> Dict[str, Any]:
    return {
        "id": listing_id,
        "address": f"{listing_id} Test Street",
        "price_gbp": price,
        "bedrooms": 3,
        "listing_type": "house",
        "outside_space": "",
        "parking": "false",
        "works_required": "",
        "area": "",
        "listing_status": "available_for_sale",
    }


def _request() -> RegisterApplicantRequest:
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


@pytest.fixture
def real_matcher(monkeypatch: pytest.MonkeyPatch) -> List[Dict[str, Any]]:
    """Fake only what leaves the process: the HubSpot reads and the registration write."""
    listings = [
        _listing("1393968357613", 1_100_000),
        _listing("1393968357614", 1_200_000),
        _listing("1393968357615", 1_300_000),
    ]

    async def _fake_listings(*args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
        return [dict(l) for l in listings]

    async def _fake_register(criteria: dict, client: Any) -> RegistrationResult:
        return RegistrationResult(contact_id="contact-FS55-REAL", created=True)

    monkeypatch.setattr(hs, "get_all_listings", _fake_listings)
    monkeypatch.setattr(bf, "register_applicant_in_hubspot", _fake_register)
    monkeypatch.setattr(bf, "build_hubspot_client", lambda: object())
    return listings


async def test_step_c_asks_the_source_about_the_ids_the_real_matcher_returns(real_matcher):
    source = FakeBrochureLinkSource()

    await bf.fn_register_applicant(_request(), agent_name="Agent", source=source)

    assert source.requested == [l["id"] for l in real_matcher], (
        "step (c) must pass each match's listing id to the brochure source; "
        f"it asked about {source.requested!r}"
    )


async def test_a_brochure_link_reaches_the_welcome_draft_via_the_real_matcher(real_matcher):
    source = FakeBrochureLinkSource({"1393968357613": LINK_1})

    response = await bf.fn_register_applicant(_request(), agent_name="Agent", source=source)

    by_id = {m["property_id"]: m for m in response.first_matches}
    assert by_id["1393968357613"]["brochure_url"] == LINK_1
    assert by_id["1393968357614"]["brochure_url"] is None
    assert LINK_1 in response.welcome_draft.html_body
    assert LINK_1 in response.welcome_draft.text_body
    assert response.welcome_draft.html_body.count(LINK_1) == 1      # one button, one href
    assert response.welcome_draft.text_body.count("View brochure:") == 1


async def test_a_match_without_any_listing_id_is_not_looked_up(real_matcher, monkeypatch, caplog):
    async def _match_without_id(criteria: dict, limit: int = 3) -> List[dict]:
        return [{"address": "No Id Road", "price_gbp": 1_000_000}]

    monkeypatch.setattr(bf, "find_matching_listings", _match_without_id)
    source = FakeBrochureLinkSource()

    response = await bf.fn_register_applicant(_request(), agent_name="Agent", source=source)

    assert source.requested == []
    assert response.first_matches[0]["brochure_url"] is None
    assert response.status != "error"
