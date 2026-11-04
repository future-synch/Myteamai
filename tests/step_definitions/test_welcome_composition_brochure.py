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
import sys, os, re, html, logging
from html.parser import HTMLParser

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


HOSTILE_URL = "https://files.example.test/b.pdf?x=\"1\"&y=<2>&z='3'"
HOSTILE_ADDRESS = "5 <Script> & \"Co\" Mews"
BUTTON_TEXT = "View brochure"
_VOID = {"br", "img", "hr", "meta", "input", "link"}


class _Doc(HTMLParser):
    """Minimal well-formedness-tolerant parse of the html body: records every
    anchor with its attributes, visible text and enclosing elements, and counts
    the cells of each table so 'single-cell table' can be asserted."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.anchors = []
        self._cur = None

    def handle_starttag(self, tag, attrs):
        el = {"tag": tag, "attrs": dict(attrs), "cells": 0}
        if tag == "td":
            for parent in reversed(self.stack):
                if parent["tag"] == "table":
                    parent["cells"] += 1
                    break
        if tag == "a":
            self._cur = {"attrs": dict(attrs), "text": "", "ancestors": list(self.stack)}
            self.anchors.append(self._cur)
        if tag not in _VOID:
            self.stack.append(el)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                del self.stack[i:]
                break
        if tag == "a":
            self._cur = None

    def handle_data(self, data):
        if self._cur is not None:
            self._cur["text"] += data


def _doc(ctx):
    d = _Doc()
    d.feed(ctx.rendered["html_body"])
    d.close()
    return d


def _buttons(ctx):
    return [a for a in _doc(ctx).anchors if a["text"].strip() == BUTTON_TEXT]


def _nearest(anchor, tag):
    for el in reversed(anchor["ancestors"]):
        if el["tag"] == tag:
            return el
    raise AssertionError(f"button has no enclosing <{tag}>")


def _raw_html(ctx):
    return ctx.rendered["html_body"]


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


@given(parsers.parse('a matched listing "{address}" whose brochure link is empty'))
def given_listing_empty_link(ctx, address):
    ctx.matches = [_match(address, brochure_url="   ")]


@given(parsers.parse('a matched listing "{address}" with a brochure link containing quotes, an ampersand and angle brackets'))
def given_listing_hostile_link(ctx, address):
    ctx.matches = [_match(address, brochure_url=HOSTILE_URL)]


@given("a matched listing with a hostile address and a brochure link")
def given_hostile_address(ctx):
    ctx.matches = [_match(HOSTILE_ADDRESS, brochure_url="https://files.example.test/h.pdf")]


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


@when("the welcome email is rendered with logging captured")
def when_rendered_logged(ctx, caplog):
    caplog.set_level(logging.DEBUG)
    when_rendered(ctx)
    ctx.log_records = list(caplog.records)


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


@then(parsers.parse('the text body contains the supplied link unchanged'))
def then_text_link_unchanged(ctx):
    assert ctx.matches[0]["brochure_url"] in _text(ctx), "supplied link not found verbatim in the text body"


# ---------------------------------------------------------------------------
# Then — html button
# ---------------------------------------------------------------------------

@then(parsers.parse("the html body contains exactly {n:d} brochure button"))
@then(parsers.parse("the html body contains exactly {n:d} brochure buttons"))
def then_button_count(ctx, n):
    found = _buttons(ctx)
    assert len(found) == n, f"expected {n} brochure buttons, got {len(found)}:\n{_raw_html(ctx)}"


@then(parsers.parse('the button text is "{text}"'))
def then_button_text(ctx, text):
    assert _buttons(ctx)[0]["text"].strip() == text


@then("the button href equals the supplied link")
def then_button_href(ctx):
    assert _buttons(ctx)[0]["attrs"].get("href") == ctx.matches[0]["brochure_url"]


@then("the button sits in a single-cell presentation table")
def then_button_table(ctx):
    table = _nearest(_buttons(ctx)[0], "table")
    assert table["attrs"].get("role") == "presentation", table["attrs"]
    assert table["cells"] == 1, f"button table has {table['cells']} cells, expected 1"


@then("the button cell carries a bgcolor attribute")
def then_button_bgcolor(ctx):
    td = _nearest(_buttons(ctx)[0], "td")
    assert td["attrs"].get("bgcolor"), f"button td has no bgcolor attribute: {td['attrs']}"


@then("the button cell has a visible border")
def then_button_border(ctx):
    td = _nearest(_buttons(ctx)[0], "td")
    assert "border" in (td["attrs"].get("style") or "").lower(), f"no border on the button cell: {td['attrs']}"


@then("the button's aria-label names the listing address")
def then_button_aria(ctx):
    address = ctx.matches[0]["address"]
    assert _buttons(ctx)[0]["attrs"].get("aria-label") == f"{BUTTON_TEXT} for {address}"


@then("each button href equals its own listing's link")
def then_each_button_href(ctx):
    hrefs = [b["attrs"].get("href") for b in _buttons(ctx)]
    assert hrefs == [THREE_URLS[0], THREE_URLS[2]], hrefs


@then("the html body contains no text about a brochure")
def then_html_no_brochure_text(ctx):
    assert "brochure" not in _raw_html(ctx).lower(), f"unexpected brochure text:\n{_raw_html(ctx)}"


@then("the listing address still appears in the html body")
def then_html_address(ctx):
    assert html.escape(ctx.matches[0]["address"]) in _raw_html(ctx)


@then("every listing address still appears in the html body")
def then_html_every_address(ctx):
    for m in ctx.matches:
        assert html.escape(m["address"]) in _raw_html(ctx), f"{m['address']!r} missing"


@then("the html body contains no link other than the brochure buttons")
def then_html_no_other_links(ctx):
    anchors = _doc(ctx).anchors
    others = [a for a in anchors if a["text"].strip() != BUTTON_TEXT]
    assert others == [], f"unexpected links: {others}"


@then("the raw html body does not contain the unescaped link")
def then_raw_no_unescaped_link(ctx):
    assert ctx.matches[0]["brochure_url"] not in _raw_html(ctx)


@then("the raw html body contains the escaped link")
def then_raw_escaped_link(ctx):
    assert html.escape(ctx.matches[0]["brochure_url"], quote=True) in _raw_html(ctx)


@then("the raw html body does not contain the unescaped hostile address")
def then_raw_no_hostile_address(ctx):
    assert HOSTILE_ADDRESS not in _raw_html(ctx)
    assert "<Script>" not in _raw_html(ctx)


@then("nothing was logged")
def then_nothing_logged(ctx):
    assert ctx.log_records == [], f"unexpected log records: {[r.getMessage() for r in ctx.log_records]}"
