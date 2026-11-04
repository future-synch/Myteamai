"""
BDD step definitions — FS-57 brochure links in the welcome email.

Tests-first, all offline. The composer under test is the pure, deterministic
bot_functions._render_welcome_email: it is handed matches (dicts, as
find_matching_listings returns them, optionally carrying "brochure_url" set by the
FS-55 orchestrator) and returns {subject, html_body, text_body}. It makes no
network call, so these scenarios need no HubSpot, Gmail or HTTP fakes.

Pinned decisions (FS-57 ticket, "Brochure buttons"):
  - brochure_url is optional per match; None / missing / empty means no brochure
  - the plain-text body carries "View brochure: <url>" under that listing's
    numbered line, indented, so it is never itself a numbered listing line
  - the url is rendered exactly as supplied (no rewriting, no tracking params)
"""
import sys, os, re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

import app.functions.bot_functions as bot_functions

scenarios("../features/welcome_composition_brochure.feature")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _match(address, price=780_000, bedrooms=2, brochure_url=None):
    """A match dict as the orchestrator hands it to composition."""
    m = {"address": address, "price_gbp": price, "bedrooms": bedrooms}
    if brochure_url is not None:
        m["brochure_url"] = brochure_url
    return m


THREE_URLS = {
    0: "https://files.example.test/1-first-brochure.pdf",
    2: "https://files.example.test/3-third-brochure.pdf",
}


class Ctx:
    def __init__(self):
        self.matches = []
        self.rendered = None


@pytest.fixture
def ctx():
    return Ctx()


def _text(ctx):
    return ctx.rendered["text_body"]


def _numbered_lines(text):
    return re.findall(r"^\s*\d+\.\s+.+$", text, flags=re.MULTILINE)


def _line_after_listing(text, n):
    """The line directly after numbered listing line n (1-based), stripped."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.match(rf"^\s*{n}\.\s+", line):
            return lines[i + 1].strip() if i + 1 < len(lines) else ""
    raise AssertionError(f"no numbered listing line {n} in:\n{text}")


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------

@given(parsers.parse('a matched listing "{address}" with the brochure link "{url}"'))
def given_listing_with_link(ctx, address, url):
    ctx.matches = [_match(address, brochure_url=url)]


@given(parsers.parse('a matched listing "{address}" without a brochure link'))
def given_listing_without_link(ctx, address):
    ctx.matches = [_match(address)]


@given("three matched listings where the first and third have brochure links")
def given_three_mixed(ctx):
    addresses = ["105 Pine Street", "22 Oak Lane", "8 Birch Mews"]
    ctx.matches = [_match(a, brochure_url=THREE_URLS.get(i)) for i, a in enumerate(addresses)]


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------

@when("the welcome email is rendered")
def when_rendered(ctx):
    ctx.rendered = bot_functions._render_welcome_email(
        first_name="Sarah",
        search_parts=[],
        matches=[dict(m) for m in ctx.matches],
        agent_name="The Curtis Sloane team",
    )


# ---------------------------------------------------------------------------
# Then — plain text
# ---------------------------------------------------------------------------

@then(parsers.parse('the text body shows "{expected}" directly under listing {n:d}'))
def then_text_under_listing(ctx, expected, n):
    actual = _line_after_listing(_text(ctx), n)
    assert actual == expected, f"line under listing {n} was {actual!r}, expected {expected!r}"


@then("the text body contains no brochure line")
def then_text_no_brochure(ctx):
    assert "brochure" not in _text(ctx).lower(), f"unexpected brochure text:\n{_text(ctx)}"


@then(parsers.parse("the text body still has exactly {n:d} numbered listing line"))
@then(parsers.parse("the text body still has exactly {n:d} numbered listing lines"))
def then_text_numbered_count(ctx, n):
    lines = _numbered_lines(_text(ctx))
    assert len(lines) == n, f"expected {n} numbered lines, got {lines}"


@then("the text body shows each link under its own listing only")
def then_text_each_link_own_listing(ctx):
    for i, _ in enumerate(ctx.matches):
        under = _line_after_listing(_text(ctx), i + 1)
        url = THREE_URLS.get(i)
        if url:
            assert under == f"View brochure: {url}", f"listing {i + 1}: got {under!r}"
        else:
            assert "brochure" not in under.lower(), f"listing {i + 1} has a stray brochure line: {under!r}"
    # every link appears exactly once, nowhere else
    for url in THREE_URLS.values():
        assert _text(ctx).count(url) == 1, f"{url} should appear exactly once"
