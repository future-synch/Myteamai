"""
FS-67 unit tests — read-path / schema alignment (items B and C).

B: ensure_custom_properties() is a no-op and performs NO network I/O (zero POSTs),
   so a real app start against the dev tenant never (re)creates old-named props.
C: ValuationBriefRequest.property_type uses the new HubSpot vocabulary and
   rejects the retired "flat".
"""
import pytest
from pydantic import ValidationError

from app.services import hubspot_service
from app.models.schemas import ValuationBriefRequest


# ---------------------------------------------------------------------------
# B — bootstrap no-op
# ---------------------------------------------------------------------------

async def test_ensure_custom_properties_is_noop_no_network(monkeypatch):
    # Opening an HTTP client at all would mean a GET/POST to HubSpot — fail hard
    # so the test proves zero network I/O (and therefore zero property POSTs).
    def _boom(*args, **kwargs):
        raise AssertionError("ensure_custom_properties must perform no network I/O")
    monkeypatch.setattr(hubspot_service.httpx, "AsyncClient", _boom)

    result = await hubspot_service.ensure_custom_properties()

    assert result == {"created": 0, "existed": 0, "failed": 0}


def test_bootstrap_defines_no_legacy_properties():
    names = {p.get("name") for p in hubspot_service._CUSTOM_PROPERTIES}
    legacy = {
        "applicant_budget_gbp", "applicant_bedrooms_min", "applicant_bedrooms_max",
        "applicant_property_types", "applicant_financing", "applicant_preferred_channel",
        "applicant_source", "applicant_must_have", "applicant_timeline_weeks",
        "kyc_status", "kyc_documents_outstanding",
    }
    assert names.isdisjoint(legacy), f"bootstrap still defines legacy props: {names & legacy}"


# ---------------------------------------------------------------------------
# C — valuation property_type vocabulary
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pt", ["house", "townhouse", "apartment", "maisonette", "mews", "penthouse"])
def test_valuation_accepts_new_vocab(pt):
    req = ValuationBriefRequest(address="8 Portland Road", postcode="W11 4LA",
                                property_type=pt, bedrooms=3)
    assert req.property_type == pt


@pytest.mark.parametrize("bad", ["flat", "any", "bungalow"])
def test_valuation_rejects_retired_values(bad):
    with pytest.raises(ValidationError):
        ValuationBriefRequest(address="8 Portland Road", postcode="W11 4LA",
                              property_type=bad, bedrooms=3)
