"""
FS-67 item 1 — read-path parser/normaliser unit tests.

_budget_ceiling / _beds_minimum / _split_multi are importable from
hubspot_service (FS-70 will reuse the parsers). They must never raise.
"""
import pytest

from app.services.hubspot_service import _budget_ceiling, _beds_minimum, _split_multi


# ---- _budget_ceiling: up_to_Nm -> N*1e6, ten_plus -> None, bad -> None -------

@pytest.mark.parametrize("band,expected", [
    ("up_to_1m", 1_000_000),
    ("up_to_2m", 2_000_000),
    ("up_to_3m", 3_000_000),
    ("up_to_4m", 4_000_000),
    ("up_to_5m", 5_000_000),
    ("up_to_6m", 6_000_000),
    ("up_to_10m", 10_000_000),
    ("UP_TO_3M", 3_000_000),   # case-insensitive
])
def test_budget_ceiling_bands(band, expected):
    assert _budget_ceiling(band) == expected


def test_budget_ceiling_ten_plus_is_none():
    # PENDING owner confirmation: ten_plus has no numeric ceiling.
    assert _budget_ceiling("ten_plus") is None


@pytest.mark.parametrize("bad", [None, "", "   ", "unknown", "up_to_", "3m", "up_toXm", "garbage"])
def test_budget_ceiling_bad_returns_none(bad):
    assert _budget_ceiling(bad) is None


# ---- _beds_minimum: N_plus -> N (floor), bad -> None -------------------------

@pytest.mark.parametrize("band,expected", [
    ("1_plus", 1), ("2_plus", 2), ("3_plus", 3),
    ("4_plus", 4), ("5_plus", 5), ("6_plus", 6),
    ("3_PLUS", 3),
])
def test_beds_minimum_bands(band, expected):
    assert _beds_minimum(band) == expected


@pytest.mark.parametrize("bad", [None, "", "   ", "unknown", "plus", "3", "_plus", "3plus"])
def test_beds_minimum_bad_returns_none(bad):
    assert _beds_minimum(bad) is None


# ---- _split_multi: semicolon string -> list, empty -> [] ---------------------

@pytest.mark.parametrize("raw,expected", [
    ("house;apartment", ["house", "apartment"]),
    ("house", ["house"]),
    ("", []),
    (None, []),
    ("house; apartment ;maisonette", ["house", "apartment", "maisonette"]),
    (";;house;;", ["house"]),
])
def test_split_multi(raw, expected):
    assert _split_multi(raw) == expected
