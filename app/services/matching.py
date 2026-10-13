"""
FS-70 — Direction-1 deterministic matching: listings -> one buyer.

Given ONE buyer's criteria, rank available listings by COMPATIBILITY only
(value, beds, type, features). Buyer-intrinsic traits (financing, timeline,
KYC) are constant for one buyer, so they do not vary across listings and are
deliberately NOT used here. Contrast fn_match_applicants (Direction 2), which
this module does not touch. No Claude/LLM call anywhere — explanations are
templated from the sub-scores.

Spec extension: the TS specifies Direction 2's rubric, not Direction 1. Weights
are hardcoded per owner instruction (re-tunable; ranking only fires when there
are more survivors than `limit`). Logged on the drift register.

Verified against Confluence "Listings schema - definitive 2026-10-06" and the
Contacts schema; NOT yet verified against the demo portal.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services import hubspot_service
from app.services.hubspot_service import _budget_ceiling, _beds_minimum, _split_multi

# Compatibility-only weights (sum to 1.0). Hardcoded per owner instruction.
MATCH_WEIGHTS = {
    "value_headroom":      0.35,
    "feature_alignment":   0.25,
    "bedroom_fit":         0.20,
    "property_type_match": 0.20,
}

_GRACE = 0.95  # TS grace band: allow listings up to ceiling / 0.95 (5% over)

# works_required is an ORDERED ceiling: a buyer accepting level X also accepts
# anything below it, so a listing satisfies when listing_level <= buyer_level.
_WORKS_ORDER = [
    "none", "minimal_works", "cosmetic", "modernisation",
    "complete_refurbishment", "development_potential",
]

# outside_space buyer -> listing vocabulary map (PENDING owner confirmation, C7).
# Buyer value -> set of listing values that satisfy it. Buyer "none" = no requirement.
_OUTSIDE_SPACE_MAP = {
    "garden":       {"garden", "private_garden", "communal_garden"},
    "communal":     {"communal_garden"},
    "terrace":      {"terrace"},
    "balcony":      {"balcony"},
    "roof_terrace": {"roof_terrace"},
    "patio":        {"patio"},
}


# ---------------------------------------------------------------------------
# small coercion helpers
# ---------------------------------------------------------------------------

def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _num(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _int(v: Any) -> Optional[int]:
    f = _num(v)
    return int(f) if f is not None else None


def _split_multi_any(v: Any) -> List[str]:
    """Normalise a multi-value field (list OR semicolon string OR None) to a list."""
    if v is None or v == "":
        return []
    if isinstance(v, (list, tuple)):
        return [str(x) for x in v]
    return _split_multi(str(v))


# ---------------------------------------------------------------------------
# sub-scores (each 0.0-1.0, deterministic)
# ---------------------------------------------------------------------------

def _value_headroom(ceiling: Optional[float], price: Optional[float]) -> float:
    # PENDING owner confirmation (C5): with no ceiling (budget ten_plus/unset)
    # there is no measurable headroom -> 0.0 for all such listings, so it does
    # not differentiate (matches "the fixed side drops out").
    if not ceiling or price is None:
        return 0.0
    return _clamp((ceiling - price) / ceiling)


def _bedroom_fit(beds_required: Optional[int], beds: Optional[int]) -> float:
    if beds_required is None:
        return 1.0  # PENDING (P3): no bedroom preference -> neutral
    if beds is None:
        return 0.5
    if beds == beds_required:
        return 1.0
    return max(0.5, 1.0 - 0.15 * (beds - beds_required))


def _property_type_match(wanted_types: List[str], listing_type: Any) -> float:
    if not wanted_types:
        return 1.0
    return 1.0 if listing_type in wanted_types else 0.3


def _works_satisfies(buyer_level: Any, listing_level: Any) -> bool:
    try:
        bi = _WORKS_ORDER.index(str(buyer_level).strip().lower())
        li = _WORKS_ORDER.index(str(listing_level).strip().lower())
    except ValueError:
        return False
    return li <= bi


def _outside_space_satisfies(buyer_vals: List[str], listing_vals: List[str]) -> bool:
    listing_set = {v.strip().lower() for v in listing_vals}
    for b in buyer_vals:
        b = b.strip().lower()
        if b == "none":
            continue
        if _OUTSIDE_SPACE_MAP.get(b, {b}) & listing_set:
            return True
    return False


def _feature_alignment(criteria: Dict[str, Any], listing: Dict[str, Any]) -> float:
    """Fraction of the features the buyer ACTUALLY specified that the listing
    satisfies. None specified -> 1.0. (In the register flow today no feature
    wants reach criteria, so this is the neutral 1.0 case — see FS-70 note.)"""
    specified = 0
    satisfied = 0

    bos = [v for v in _split_multi_any(criteria.get("outside_space")) if v.strip().lower() != "none"]
    if bos:
        specified += 1
        if _outside_space_satisfies(bos, _split_multi_any(listing.get("outside_space"))):
            satisfied += 1

    bp = criteria.get("parking")
    if bp not in (None, "", []) and hubspot_service._parse_bool(bp):
        specified += 1
        if hubspot_service._parse_bool(listing.get("parking")):
            satisfied += 1

    bw = criteria.get("works_required")
    if bw not in (None, "", []) and str(bw).strip().lower() != "none":
        specified += 1
        if _works_satisfies(bw, listing.get("works_required")):
            satisfied += 1

    bareas = [v.strip().lower() for v in _split_multi_any(criteria.get("area"))]
    if bareas:
        specified += 1
        if str(listing.get("area") or "").strip().lower() in bareas:
            satisfied += 1

    return 1.0 if specified == 0 else satisfied / specified


# ---------------------------------------------------------------------------
# templated explanation
# ---------------------------------------------------------------------------

def _money(n: float) -> str:
    n = int(round(n))
    return f"{round(n / 1000)}k" if n >= 1000 else str(n)


def _join_and(items: List[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _satisfied_feature_labels(criteria: Dict[str, Any], listing: Dict[str, Any]) -> List[str]:
    labels: List[str] = []
    bos = [v for v in _split_multi_any(criteria.get("outside_space")) if v.strip().lower() != "none"]
    if bos and _outside_space_satisfies(bos, _split_multi_any(listing.get("outside_space"))):
        labels.append("garden" if any(b.strip().lower() == "garden" for b in bos) else "outside space")
    bp = criteria.get("parking")
    if bp not in (None, "", []) and hubspot_service._parse_bool(bp) and hubspot_service._parse_bool(listing.get("parking")):
        labels.append("parking")
    return labels


def _match_reason(criteria, listing, ceiling, subs) -> str:
    clauses: List[tuple] = []  # (sub_score, text)

    price = _num(listing.get("price_gbp"))
    if ceiling and price is not None and price < ceiling:
        clauses.append((subs["value_headroom"], f"£{_money(ceiling - price)} under budget"))

    beds = _int(listing.get("bedrooms"))
    lt = listing.get("listing_type")
    if beds is not None:
        clauses.append((subs["bedroom_fit"], f"{beds}-bed{(' ' + str(lt)) if lt else ''}"))
    elif lt:
        clauses.append((subs["property_type_match"], str(lt)))

    feats = _satisfied_feature_labels(criteria, listing)
    if feats:
        clauses.append((subs["feature_alignment"], "has " + _join_and(feats)))

    clauses.sort(key=lambda c: c[0], reverse=True)
    picked = [c[1] for c in clauses[:3] if c[1]]
    return " · ".join(picked) if picked else "Meets your budget and bedroom criteria."


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

async def find_matching_listings(criteria: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
    """
    Return a buyer's best-fitting available listings as PropertyMatch dicts
    (TS §5.2): {property_id, address, price_gbp, bedrooms, match_score, match_reason}.
    match_score is None on the unranked path (survivors <= limit).
    """
    listings = await hubspot_service.get_all_listings()

    ceiling = _budget_ceiling(criteria.get("budget"))
    beds_required = _beds_minimum(criteria.get("beds_required"))
    wanted_types = criteria.get("property_types") or []
    if isinstance(wanted_types, str):
        wanted_types = _split_multi(wanted_types)

    # Stage 1 — inclusive filter (property type is soft; it feeds the score).
    filtered: List[Dict[str, Any]] = []
    for lst in listings:
        price = _num(lst.get("price_gbp"))
        beds = _int(lst.get("bedrooms"))
        if ceiling is not None and price is not None and price > ceiling / _GRACE:
            continue
        if beds_required is not None and (beds is None or beds < beds_required):
            continue
        filtered.append(lst)

    def _price_key(l):
        p = _num(l.get("price_gbp"))
        return (p if p is not None else float("inf"), str(l.get("id")))

    filtered.sort(key=_price_key)  # natural order: price ascending

    def _shape(l, score, reason):
        return {
            "property_id": l.get("id"),
            "address":     l.get("address"),
            "price_gbp":   _num(l.get("price_gbp")),
            "bedrooms":    _int(l.get("bedrooms")),
            "match_score": score,
            "match_reason": reason,
        }

    # Stage 2 — count-gated ranking.
    if len(filtered) <= limit:
        return [_shape(l, None, "Meets your budget and bedroom criteria.") for l in filtered]

    scored = []
    for l in filtered:
        subs = {
            "value_headroom":      _value_headroom(ceiling, _num(l.get("price_gbp"))),
            "feature_alignment":   _feature_alignment(criteria, l),
            "bedroom_fit":         _bedroom_fit(beds_required, _int(l.get("bedrooms"))),
            "property_type_match": _property_type_match(wanted_types, l.get("listing_type")),
        }
        score = round(sum(MATCH_WEIGHTS[k] * subs[k] for k in MATCH_WEIGHTS), 2)
        scored.append((score, l, subs))

    # Sort desc by score; deterministic tie-break by price asc then id.
    scored.sort(key=lambda t: (-t[0], _price_key(t[1])))
    return [_shape(l, score, _match_reason(criteria, l, ceiling, subs)) for (score, l, subs) in scored[:limit]]
