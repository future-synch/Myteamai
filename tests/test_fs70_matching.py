"""
FS-70 — Direction-1 matching engine tests (offline, deterministic).

All tests mock hubspot_service.get_all_listings so nothing hits live HubSpot.
"""
import pytest

import app.services.hubspot_service as hs
from app.services.matching import (
    find_matching_listings,
    _works_satisfies,
    _outside_space_satisfies,
    MATCH_WEIGHTS,
)


def _mock_get_all_listings(monkeypatch, listings):
    async def _fake(*args, **kwargs):
        return list(listings)
    monkeypatch.setattr(hs, "get_all_listings", _fake)


def _listing(id, price, beds, ltype="house", outside_space="", parking="false",
             works_required="", area=""):
    return {
        "id": id, "address": f"{id} Test St", "price_gbp": price, "bedrooms": beds,
        "listing_type": ltype, "outside_space": outside_space, "parking": parking,
        "works_required": works_required, "area": area, "listing_status": "available_for_sale",
    }


BUYER = {"budget": "up_to_3m", "beds_required": "3_plus", "property_types": ["house"]}


# ---------------------------------------------------------------------------
# weights sanity
# ---------------------------------------------------------------------------

def test_weights_sum_to_one():
    assert round(sum(MATCH_WEIGHTS.values()), 6) == 1.0


# ---------------------------------------------------------------------------
# (1) Stage-1 filter
# ---------------------------------------------------------------------------

async def test_filter_budget_beds_and_soft_type(monkeypatch):
    listings = [
        _listing("over", 3_300_000, 3, "house"),       # >5% over £3M ceiling -> excluded
        _listing("grace", 3_100_000, 3, "house"),      # within 5% grace -> kept
        _listing("fewbeds", 1_000_000, 2, "house"),    # < 3 beds -> excluded
        _listing("softtype", 1_500_000, 3, "apartment"),  # wrong type -> KEPT (soft)
    ]
    _mock_get_all_listings(monkeypatch, listings)
    out = await find_matching_listings(BUYER, limit=10)
    ids = {m["property_id"] for m in out}
    assert ids == {"grace", "softtype"}


async def test_filter_skipped_when_ceiling_and_beds_none(monkeypatch):
    # ten_plus -> ceiling None; no beds_required -> both filters skipped.
    _mock_get_all_listings(monkeypatch, [
        _listing("a", 9_000_000, 1, "house"),
        _listing("b", 500_000, 8, "flat"),
    ])
    out = await find_matching_listings({"budget": "ten_plus", "property_types": []}, limit=10)
    assert {m["property_id"] for m in out} == {"a", "b"}


# ---------------------------------------------------------------------------
# (2) Unranked path (survivors <= limit)
# ---------------------------------------------------------------------------

async def test_unranked_returns_all_with_none_score_price_ascending(monkeypatch):
    _mock_get_all_listings(monkeypatch, [
        _listing("A", 2_000_000, 3),
        _listing("B", 1_000_000, 3),
    ])
    out = await find_matching_listings(BUYER, limit=3)
    assert [m["property_id"] for m in out] == ["B", "A"]          # price ascending
    assert all(m["match_score"] is None for m in out)
    assert all(m["match_reason"] == "Meets your budget and bedroom criteria." for m in out)
    # shape
    m = out[0]
    assert set(m) == {"property_id", "address", "price_gbp", "bedrooms", "match_score", "match_reason"}
    assert m["price_gbp"] == 1_000_000.0 and m["bedrooms"] == 3


# ---------------------------------------------------------------------------
# (3) Ranked path (survivors > limit)
# ---------------------------------------------------------------------------

RANK_BUYER = {**BUYER, "outside_space": ["garden"], "parking": True}


def _rank_listings():
    return [
        _listing("best",    2_000_000, 3, "house",     outside_space="garden", parking="true"),
        _listing("partial", 2_900_000, 3, "house",     outside_space="garden", parking="false"),
        _listing("mid",     2_500_000, 4, "house",     outside_space="none",   parking="true"),
        _listing("low",     3_100_000, 3, "apartment", outside_space="none",   parking="false"),
    ]


async def test_ranked_returns_limit_sorted_desc(monkeypatch):
    _mock_get_all_listings(monkeypatch, _rank_listings())
    out = await find_matching_listings(RANK_BUYER, limit=3)

    assert len(out) == 3                                  # exactly limit
    assert out[0]["property_id"] == "best"                # all features + best headroom ranks first
    scores = [m["match_score"] for m in out]
    assert all(s is not None for s in scores)
    assert scores == sorted(scores, reverse=True)         # descending
    assert "low" not in {m["property_id"] for m in out}   # weakest dropped
    # best outranks the partial-feature match
    by_id = {m["property_id"]: m for m in out}
    assert by_id["best"]["match_score"] > by_id["partial"]["match_score"]
    # templated reason mentions headroom + features
    reason = by_id["best"]["match_reason"]
    assert "under budget" in reason and "garden" in reason and "parking" in reason


async def test_ranked_scores_are_in_unit_interval(monkeypatch):
    _mock_get_all_listings(monkeypatch, _rank_listings())
    out = await find_matching_listings(RANK_BUYER, limit=3)
    for m in out:
        assert 0.0 <= m["match_score"] <= 1.0


# ---------------------------------------------------------------------------
# (4) Determinism
# ---------------------------------------------------------------------------

async def test_deterministic_same_inputs_same_output(monkeypatch):
    _mock_get_all_listings(monkeypatch, _rank_listings())
    out1 = await find_matching_listings(RANK_BUYER, limit=3)
    _mock_get_all_listings(monkeypatch, _rank_listings())
    out2 = await find_matching_listings(RANK_BUYER, limit=3)
    assert out1 == out2


# ---------------------------------------------------------------------------
# feature sub-score helpers (works ceiling C6, outside_space mapping C7)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("buyer,listing,ok", [
    ("modernisation", "cosmetic", True),              # below ceiling
    ("modernisation", "modernisation", True),         # at ceiling
    ("modernisation", "complete_refurbishment", False),  # above ceiling
    ("none", "none", True),
    ("development_potential", "none", True),           # accepts everything below
    ("cosmetic", "bogus", False),
])
def test_works_required_ceiling(buyer, listing, ok):
    assert _works_satisfies(buyer, listing) is ok


@pytest.mark.parametrize("buyer_vals,listing_vals,ok", [
    (["garden"], ["private_garden"], True),    # P2 mapping
    (["garden"], ["communal_garden"], True),
    (["communal"], ["communal_garden"], True),
    (["garden"], ["terrace"], False),
    (["balcony"], ["balcony"], True),
])
def test_outside_space_mapping(buyer_vals, listing_vals, ok):
    assert _outside_space_satisfies(buyer_vals, listing_vals) is ok


async def test_area_membership_feeds_score(monkeypatch):
    # Buyer wants chelsea OR holland_park; listing in chelsea satisfies the area feature.
    _mock_get_all_listings(monkeypatch, [
        _listing("in",  2_000_000, 3, "house", area="chelsea"),
        _listing("out", 2_000_000, 3, "house", area="bayswater"),
        _listing("x",   2_100_000, 3, "house", area="other"),
        _listing("y",   2_200_000, 3, "house", area="other"),
    ])
    buyer = {**BUYER, "area": ["chelsea", "holland_park"]}
    out = await find_matching_listings(buyer, limit=3)
    by_id = {m["property_id"]: m for m in out}
    # 'in' (area satisfied, feature_alignment 1.0) outranks 'out' (0.0) at equal price.
    assert by_id["in"]["match_score"] > by_id["out"]["match_score"]


# ---------------------------------------------------------------------------
# get_all_listings: available_for_sale filter (C1) + Python off_market parse (C3)
# ---------------------------------------------------------------------------

class _FakeResp:
    status_code = 200

    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class _FakeClient:
    """Stands in for httpx.AsyncClient as an async context manager."""
    last_payload = None

    def __init__(self, data):
        self._data = data

    def __call__(self, *a, **k):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, headers=None, json=None):
        _FakeClient.last_payload = json
        return _FakeResp(self._data)


async def test_get_all_listings_filter_and_offmarket(monkeypatch):
    canned = {"results": [
        {"id": "L1", "properties": {"hs_price": "2000000", "hs_bedrooms": "3",
         "hs_listing_type": "house", "hs_address_1": "1 A St",
         "listing_status": "available_for_sale", "off_market": "false", "area": "chelsea"}},
        {"id": "L2", "properties": {"hs_price": "2500000", "hs_bedrooms": "4",
         "hs_address_1": "2 B St", "listing_status": "available_for_sale",
         "off_market": "true"}},   # off-market -> excluded in Python
        {"id": "L3", "properties": {"hs_price": "1800000", "hs_bedrooms": "2",
         "hs_address_1": "3 C St", "listing_status": "available_for_sale",
         "off_market": ""}},       # empty off_market -> kept
    ]}
    fake = _FakeClient(canned)
    monkeypatch.setattr(hs.httpx, "AsyncClient", fake)

    out = await hs.get_all_listings(token="dummy-dev-token")

    assert {r["id"] for r in out} == {"L1", "L3"}                 # L2 off-market dropped
    # server-side filter is the available_for_sale internal value (C1)
    flt = _FakeClient.last_payload["filterGroups"][0]["filters"][0]
    assert flt == {"propertyName": "listing_status", "operator": "EQ", "value": "available_for_sale"}
    # normalised shape: neighborhood comes from area (C2)
    l1 = next(r for r in out if r["id"] == "L1")
    assert l1["price_gbp"] == "2000000" and l1["address"] == "1 A St" and l1["neighborhood"] == "chelsea"


class _PagingClient:
    """Fake httpx.AsyncClient that returns a sequence of pages across posts and
    records every request payload."""

    def __init__(self, pages):
        self._pages = pages
        self._i = 0
        self.payloads = []

    def __call__(self, *a, **k):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, headers=None, json=None):
        self.payloads.append(json)
        body = self._pages[self._i]
        self._i += 1
        return _FakeResp(body)


def _prop(hs_price, off_market, addr):
    return {"hs_price": hs_price, "hs_bedrooms": "3", "hs_listing_type": "house",
            "hs_address_1": addr, "listing_status": "available_for_sale",
            "off_market": off_market, "area": "chelsea"}


async def test_get_all_listings_paginates_and_merges_pages(monkeypatch):
    # Page 1 hands back a next cursor; page 2 has none (stop). off_market records
    # appear on BOTH pages and must be skipped on both.
    page1 = {
        "results": [
            {"id": "P1a", "properties": _prop("2000000", "false", "1 A")},   # keep
            {"id": "P1b", "properties": _prop("2100000", "true", "2 B")},    # off-market -> skip
        ],
        "paging": {"next": {"after": "CURSOR-123"}},
    }
    page2 = {
        "results": [
            {"id": "P2a", "properties": _prop("2200000", "", "3 C")},        # keep (empty off_market)
            {"id": "P2b", "properties": _prop("2300000", "true", "4 D")},    # off-market -> skip
        ],
        # no "paging" -> loop stops after this page
    }
    client = _PagingClient([page1, page2])
    monkeypatch.setattr(hs.httpx, "AsyncClient", client)

    out = await hs.get_all_listings(token="dummy-dev-token")

    # both pages merged; off_market skipped on page 1 AND page 2
    assert {r["id"] for r in out} == {"P1a", "P2a"}
    # exactly two requests were made
    assert len(client.payloads) == 2
    # first request has no cursor; second carries the page-1 `after`
    assert "after" not in client.payloads[0]
    assert client.payloads[1].get("after") == "CURSOR-123"
