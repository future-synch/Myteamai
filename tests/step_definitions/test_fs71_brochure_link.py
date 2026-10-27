"""
BDD step definitions — FS-71 brochure link lookup.

Offline throughout. Every scenario runs twice (association order ascending and
descending) because HubSpot documents no ordering and the lookup must not care.
"""
import logging
import os
import re
import sys
from collections.abc import MutableMapping

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import httpx
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from app.services import brochures
from app.services.brochures import (
    BrochureLinkSource,
    FakeBrochureLinkSource,
    HubSpotAuthError,
    HubSpotBrochureLinkSource,
    HubSpotRestReader,
    get_brochure_link_source,
    get_listing_document_link,
)
from app.services.brochures import hubspot as hubspot_module
from app.services.hubspot_service import HUBSPOT_BASE, HubSpotError
from tests.support.fake_hubspot import (
    ADDRESS, FakeHubSpot, RestTransport, default_filename, marker_body,
)

# HubSpot documents no association ordering: run every scenario both ways.
pytestmark = [
    pytest.mark.usefixtures("assoc_order"),
    pytest.mark.parametrize("assoc_order", ["asc", "desc"], ids=["assoc-asc", "assoc-desc"]),
]

scenarios("../features/fs71_brochure_link_lookup.feature")
scenarios("../features/fs71_brochure_link_lookup_additions.feature")

LISTING = "L-100"
MONDAY = "2026-10-19T09:00:00Z"
TUESDAY = "2026-10-20T09:00:00Z"
DAYS = {"Monday": MONDAY, "Tuesday": TUESDAY}


class Note:
    def __init__(self, note_id, file_id, kind):
        self.note_id, self.file_id, self.kind = note_id, file_id, kind


class Ctx:
    def __init__(self, order, caplog):
        self.fake = FakeHubSpot(order=order)
        self.reader = self.fake
        self.notes = []
        self.caplog = caplog
        self.result = None
        self.error = None
        self.expected_error = HubSpotError
        self.transport = None
        self.rest_kwargs = {}
        self.modules_before = set()
        self.modules_after = set()
        self.env_reads = None
        self.source = None
        self.build_error = None

    def add_note(self, kind, *, filename=None, timestamp=MONDAY, body=None):
        fid = self.fake.add_file(filename or default_filename(kind))
        nid = self.fake.add_note(
            LISTING, body if body is not None else marker_body(kind, filename or default_filename(kind)),
            [fid], timestamp)
        n = Note(nid, fid, kind)
        self.notes.append(n)
        return n

    def url(self, note):
        return self.fake.url_of(note.file_id)

    def note_of_kind(self, kind):
        return next(n for n in self.notes if n.kind == kind)


@pytest.fixture
def ctx(assoc_order, caplog):
    caplog.set_level(logging.DEBUG)
    return Ctx(assoc_order, caplog)


def _rest_reader(transport, **kw):
    client = httpx.Client(base_url=HUBSPOT_BASE, transport=httpx.MockTransport(transport))
    return HubSpotRestReader(token=RestTransport.TOKEN, client=client, sleep=lambda s: None, **kw)


def _run(ctx):
    ctx.modules_before = set(sys.modules)
    try:
        ctx.result = get_listing_document_link(ctx.reader, LISTING, "brochure")
    except Exception as exc:                       # noqa: BLE001 — the scenario asserts on it
        ctx.error = exc
        ctx.result = None
    ctx.modules_after = set(sys.modules)


# ---------------------------------------------------------------- Given: listings

@given(parsers.parse('a listing with one note marked "{kind}" carrying one attachment'))
def g_one_marked_with_attachment(ctx, kind):
    ctx.add_note(kind)


@given(parsers.parse('a listing with one note marked "{kind}"'))
@given(parsers.parse('a listing with a note marked "{kind}"'))
def g_one_marked(ctx, kind):
    ctx.add_note(kind)


@given(parsers.parse('a listing with a note marked "{kind}" attached on {day}'))
@given(parsers.parse('a note marked "{kind}" attached on {day}'))
def g_marked_on_day(ctx, kind, day):
    ctx.add_note(kind, timestamp=DAYS[day])


@given(parsers.parse('a listing with two notes marked "{kind}"'))
def g_two_marked(ctx, kind):
    ctx.add_note(kind, timestamp=MONDAY)
    ctx.add_note(kind, timestamp=TUESDAY)


@given("a listing with a brochure note whose body lines are joined with <br>")
def g_html_body(ctx):
    n = ctx.add_note("brochure")
    body = ctx.fake.notes[n.note_id]["hs_note_body"]
    assert "<br>" in body and "\n" not in body, "fixture must be one physical line"


@given("a listing with one note carrying a pdf attachment and no marker")
def g_unmarked(ctx):
    # Even a file called "Brochure" must not be picked: selection is by marker.
    fid = ctx.fake.add_file(default_filename("brochure"))
    ctx.fake.add_note(LISTING, "<div>Received from vendor</div>", [fid], MONDAY)


@given("a listing with no notes")
def g_no_notes(ctx):
    pass


@given("a listing with a brochure note whose file access is PRIVATE")
def g_private(ctx):
    n = ctx.add_note("brochure")
    ctx.fake.files[n.file_id]["access"] = "PRIVATE"


@given("any listing")
def g_any(ctx, monkeypatch):
    ctx.add_note("brochure")

    class RecordingEnviron(MutableMapping):
        """os.environ stand-in that records every key READ. Writes pass through
        (pytest itself sets PYTEST_CURRENT_TEST while this is installed)."""

        def __init__(self, real):
            self._real, self.read = real, []

        def __getitem__(self, key):
            self.read.append(key)
            return self._real[key]

        def __setitem__(self, key, value):
            self._real[key] = value

        def __delitem__(self, key):
            del self._real[key]

        def __iter__(self):
            return iter(self._real)

        def __len__(self):
            return len(self._real)

        def get(self, key, default=None):
            self.read.append(key)
            return self._real.get(key, default)

        def __contains__(self, key):
            self.read.append(key)
            return key in self._real

        def copy(self):
            return self._real.copy()

    ctx.env_reads = RecordingEnviron(os.environ)
    monkeypatch.setattr(os, "environ", ctx.env_reads)


@given("a listing with more associated notes than fit one page")
def g_many_notes(ctx):
    ctx.fake.page_size = 2
    ctx.noise = [ctx.add_note("brochure", filename=f"{ADDRESS} - Brochure.pdf", body=f"<div>noise {i}</div>")
                 for i in range(2)]


@given(parsers.parse('only a note on the second page is marked "{kind}"'))
def g_second_page(ctx, kind):
    marked = ctx.add_note(kind)
    ctx.marked = marked
    ctx.fake.set_assoc_order(LISTING, [n.note_id for n in ctx.noise] + [marked.note_id])
    page, nxt = ctx.fake.note_association_page(LISTING)
    assert marked.note_id not in page and nxt, "fixture: marked note must be on page 2"


# ---------------------------------------------------------------- Given: tweaks

@given("that note carries the floor plan id first and the brochure id second")
def g_two_attachments(ctx):
    n = ctx.notes[0]
    fp = ctx.fake.add_file(default_filename("floor_plan"))
    ctx.fake.notes[n.note_id]["hs_attachment_ids"] = f"{fp};{n.file_id}"


@given("the second has a later timestamp")
def g_second_later(ctx):
    ctx.fake.notes[ctx.notes[0].note_id]["hs_timestamp"] = "2026-10-19T09:00:00Z"
    ctx.fake.notes[ctx.notes[1].note_id]["hs_timestamp"] = "2026-10-20T09:00:00Z"


@given("their timestamps use different utc offset formats")
def g_offsets(ctx):
    # First is genuinely later (23:30Z vs 23:15Z) yet sorts EARLIER as a string.
    ctx.fake.notes[ctx.notes[0].note_id]["hs_timestamp"] = "2026-10-19T23:30:00+00:00"
    ctx.fake.notes[ctx.notes[1].note_id]["hs_timestamp"] = "2026-10-20T00:15:00+01:00"
    assert "2026-10-20T00:15:00+01:00" > "2026-10-19T23:30:00+00:00"


@given(parsers.parse('its attachment is named "{name}"'))
def g_rename(ctx, name):
    ctx.fake.files[ctx.notes[0].file_id]["name"] = name


@given("its attachment is an image")
def g_image(ctx):
    ctx.fake.files[ctx.notes[0].file_id]["type"] = "IMG"


@given("the attachment's file no longer exists in HubSpot")
def g_gone(ctx):
    del ctx.fake.files[ctx.notes[0].file_id]


@given(parsers.parse("the HubSpot client returns {status:d}"))
def g_status(ctx, status):
    ctx.reader = _rest_reader(RestTransport(always=status))
    ctx.expected_error = HubSpotAuthError if status in (401, 403) else HubSpotError


@given(parsers.parse("HubSpot answers {status:d} to the first {n:d} requests"))
def g_fail_first(ctx, status, n):
    ctx.transport = RestTransport(ctx.fake, fail_first=(status, n))


@given(parsers.parse("HubSpot answers {status:d} to every request"))
def g_always(ctx, status):
    ctx.transport = RestTransport(ctx.fake, always=status)


# ---------------------------------------------------------------- When

@when("the brochure link is requested")
def w_request(ctx):
    _run(ctx)


@when("the brochure link is requested through the REST reader")
def w_request_rest(ctx):
    ctx.transport = ctx.transport or RestTransport(ctx.fake)
    ctx.reader = _rest_reader(ctx.transport)
    _run(ctx)


# ---------------------------------------------------------------- Then: results

@then("the url from the files api is returned")
def t_files_url(ctx):
    assert ctx.error is None, ctx.error
    assert ctx.result == ctx.url(ctx.notes[0])


@then("no url is constructed in application code")
def t_no_constructed_url(ctx):
    n = ctx.notes[0]
    assert n.file_id not in ctx.result and n.note_id not in ctx.result, "url looks assembled from ids"
    src = open(hubspot_module.__file__, encoding="utf-8").read()
    assert not re.search(r"""f?["']https?://""", src), "a url literal/template exists in application code"


@then("the brochure's url is returned")
def t_brochure_url(ctx):
    assert ctx.result == ctx.url(ctx.note_of_kind("brochure"))


@then("the floor plan's url is not returned")
def t_not_floor_plan(ctx):
    assert ctx.result != ctx.url(ctx.note_of_kind("floor_plan"))


@then("the url of the second note's attachment is returned")
def t_second_url(ctx):
    assert ctx.result == ctx.url(ctx.notes[1])


@then("the genuinely later note's attachment is returned")
def t_later_url(ctx):
    assert ctx.result == ctx.url(ctx.notes[0])


@then("the marker is matched")
def t_marker(ctx):
    assert ctx.result is not None, "marker not matched in a <br>-joined HTML body"


@then("the url is returned")
def t_url(ctx):
    assert ctx.result == ctx.url(ctx.notes[0])


@then("that attachment's url is returned")
def t_that_url(ctx):
    assert ctx.error is None, ctx.error
    assert ctx.result == ctx.url(ctx.marked)


@then("nothing is returned")
def t_nothing(ctx):
    assert ctx.result is None


@then("no error is raised")
def t_no_error(ctx):
    assert ctx.error is None, repr(ctx.error)


@then("an error is raised")
def t_error(ctx):
    assert isinstance(ctx.error, ctx.expected_error), repr(ctx.error)
    assert ctx.result is None


# ---------------------------------------------------------------- Then: logging

def _records(ctx, level):
    return [r for r in ctx.caplog.records if r.levelno == level]


@then("a warning is logged")
def t_warning(ctx):
    assert _records(ctx, logging.WARNING)


@then("the note is skipped as ambiguous")
def t_ambiguous(ctx):
    assert any("ambiguous" in r.getMessage() for r in _records(ctx, logging.WARNING))


@then("a warning is logged naming the file")
def t_warning_names_file(ctx):
    name = ctx.fake.files[ctx.notes[0].file_id]["name"]
    assert any(name in r.getMessage() for r in _records(ctx, logging.WARNING)), \
        [r.getMessage() for r in ctx.caplog.records]


@then("nothing is logged above info level")
def t_quiet(ctx):
    loud = [r.getMessage() for r in ctx.caplog.records if r.levelno > logging.INFO]
    assert not loud, loud


@then("the listing id is logged at info level")
def t_info_listing(ctx):
    assert any(LISTING in r.getMessage() for r in _records(ctx, logging.INFO))
    assert not [r for r in ctx.caplog.records if r.levelno > logging.INFO], "absence must not warn"


@then(parsers.parse("{n:d} requests were attempted"))
def t_attempts(ctx, n):
    assert len(ctx.transport.requests) == n


# ---------------------------------------------------------------- Then: no Google

@then("no Google Drive client is constructed")
def t_no_google_client(ctx):
    new = {m for m in ctx.modules_after - ctx.modules_before if m.split(".")[0] in ("google", "googleapiclient", "oauth2client")}
    assert not new, new
    pkg_dir = os.path.dirname(brochures.__file__)
    for fn in os.listdir(pkg_dir):
        if fn.endswith(".py"):
            text = open(os.path.join(pkg_dir, fn), encoding="utf-8").read()
            assert not re.search(r"^\s*(import|from)\s+(google|googleapiclient|oauth2client)", text, re.M), fn


@then("no Google credential is read")
def t_no_google_credential(ctx):
    google = [k for k in ctx.env_reads.read if str(k).upper().startswith(("GOOGLE", "GCP", "GCLOUD"))]
    assert not google, google


# ---------------------------------------------------------------- additions: sources

@given(parsers.parse('an in-memory brochure source mapping listing "{lid}" to "{url}"'))
def g_fake_source(ctx, lid, url):
    ctx.source = FakeBrochureLinkSource({lid: url})


@then(parsers.parse('listing "{lid}" yields "{url}"'))
def t_yields(ctx, lid, url):
    assert ctx.source.get_brochure_link(lid) == url


@then(parsers.parse('listing "{lid}" yields nothing'))
def t_yields_nothing(ctx, lid):
    assert ctx.source.get_brochure_link(lid) is None


@then("both brochure sources satisfy the BrochureLinkSource protocol")
def t_protocol(ctx):
    assert isinstance(ctx.source, BrochureLinkSource)
    assert isinstance(HubSpotBrochureLinkSource(FakeHubSpot()), BrochureLinkSource)


@given(parsers.parse('BROCHURE_LINK_SOURCE is "{value}"'))
def g_env(ctx, monkeypatch, value):
    monkeypatch.setenv("BROCHURE_LINK_SOURCE", value)


@when("the brochure link source is built")
def w_build(ctx):
    try:
        ctx.source = get_brochure_link_source()
    except Exception as exc:                       # noqa: BLE001
        ctx.build_error = exc


@then("it is the in-memory source")
def t_is_fake(ctx):
    assert isinstance(ctx.source, FakeBrochureLinkSource)


@then("it is the HubSpot source")
def t_is_hubspot(ctx):
    assert isinstance(ctx.source, HubSpotBrochureLinkSource)


@then("building it raises an error naming BROCHURE_LINK_SOURCE")
def t_build_error(ctx):
    assert isinstance(ctx.build_error, ValueError) and "BROCHURE_LINK_SOURCE" in str(ctx.build_error)
