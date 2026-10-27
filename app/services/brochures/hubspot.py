"""
HubSpot-backed brochure lookup (FS-71).

    get_listing_document_link(hs, listing_id, kind="brochure") -> str | None

READ-ONLY. No Google Drive call, no Drive credential, nothing written to HubSpot.

How a document is found
-----------------------
A document is a HubSpot Note associated with the Listing (0-420), carrying
`hs_attachment_ids`. Every note this platform attaches begins its body with

    MyTeamAI document: <kind>          e.g. "MyTeamAI document: brochure"

Selection is by that MARKER, never by recency across all notes and never by
position in `hs_attachment_ids` (HubSpot documents no ordering for that list).
Among notes of the requested kind only, the newest wins, so a re-published
brochure supersedes the old one and a later floor plan cannot displace it.

Behaviour that matters more than the code
-----------------------------------------
* None is a normal answer (confidential listings deliberately have no brochure).
  Not an error, not logged above INFO, no retry, no placeholder.
* Divergence is a WARNING, not a repair: a marked note whose file does not look
  like the kind, or is not a DOCUMENT, returns None. Sending the wrong document
  is worse than sending none.
* 401/403 RAISE. A broken token must never flatten to "no listing has a
  brochure" — that would send every applicant a buttonless email silently.
* The URL comes from the Files API response. It is never constructed here.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Protocol, Tuple
from urllib.parse import quote

import httpx

from app.services.hubspot_service import HUBSPOT_BASE, TIMEOUT, HubSpotError, _headers

log = logging.getLogger(__name__)

LISTINGS_OBJECT_TYPE = "0-420"          # Listings schema, 2026-10-06
NOTE_PROPERTIES = ["hs_note_body", "hs_attachment_ids", "hs_timestamp"]
BATCH_READ_LIMIT = 100                  # HubSpot batch read ceiling
ASSOCIATION_PAGE_SIZE = 500             # v4 associations ceiling
MAX_ASSOCIATION_PAGES = 100             # runaway-pagination guard

# NOT line-anchored: note bodies are HTML and lines are joined with <br>, so the
# whole body is frequently one physical line. `^...$` with re.M never matches.
DOC_MARKER_RE = re.compile(r"MyTeamAI\s+document:\s*([a-z_]+)", re.I)

# The Drive convention is "{short} - Brochure (Print).pdf" (3 mm bleed). Match the
# parenthesised form only, so a street called "Print Room Mews" is not refused.
_PRINT_VARIANT_RE = re.compile(r"\(\s*print\s*\)", re.I)


class HubSpotAuthError(HubSpotError):
    """401/403 from HubSpot. A credential problem, not a missing brochure."""


class HubSpotDocumentReader(Protocol):
    """
    The three read-only HubSpot calls the lookup needs. `HubSpotRestReader` is the
    real one; tests inject an in-memory double. Page-level, so pagination and
    chunking live in (and are tested through) the lookup itself.
    """

    def note_association_page(
        self, listing_id: str, after: Optional[str] = None
    ) -> Tuple[List[str], Optional[str]]:
        """One page of note ids associated to the listing, plus the next cursor."""

    def read_notes(self, note_ids: List[str]) -> List[Dict[str, Any]]:
        """Batch read (<= 100). Each item: {"id": str, "properties": {...}}."""

    def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Files API record (name, url, type, access, archived), or None if gone."""


# ---------------------------------------------------------------------------
# The lookup
# ---------------------------------------------------------------------------

def get_listing_document_link(
    hs: HubSpotDocumentReader, listing_id: str, kind: str = "brochure"
) -> Optional[str]:
    if not listing_id:
        raise ValueError("listing_id is required")
    kind = kind.strip().lower()

    note_ids = _associated_note_ids(hs, listing_id)
    if not note_ids:
        log.debug("no notes on listing %s", listing_id)
        return None
    notes = _read_notes(hs, note_ids)

    # 1. SELECT by marker, not by recency across all notes.
    candidates: List[Tuple[datetime, int, str, str]] = []   # (timestamp, note sort id, file id, note id)
    for n in notes:
        props = n.get("properties") or {}
        m = DOC_MARKER_RE.search(props.get("hs_note_body") or "")
        if not m or m.group(1).lower() != kind:
            continue
        ids = _split_attachment_ids(props.get("hs_attachment_ids"))
        if len(ids) != 1:
            log.warning(
                "listing %s: note %s is marked %r but carries %d attachments; "
                "ambiguous, skipped (not guessing)",
                listing_id, n.get("id"), kind, len(ids),
            )
            continue
        candidates.append(
            (_parse_ts(props.get("hs_timestamp")), _note_sort_id(n.get("id")), ids[0], str(n.get("id")))
        )

    if not candidates:
        log.debug("listing %s: no note marked %r", listing_id, kind)
        return None

    # 2. ORDER among that kind only. Timestamp first, then note id so two equal or
    #    unparseable timestamps still resolve deterministically (newer note id wins).
    candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)
    _, _, file_id, note_id = candidates[0]

    # 3. VERIFY. A refusal, not a repair — no fallback to an older candidate.
    meta = hs.get_file(file_id)
    if meta is None or meta.get("archived"):
        log.info("listing %s: file %s (note %s) is gone from HubSpot", listing_id, file_id, note_id)
        return None

    if (meta.get("type") or "").upper() != "DOCUMENT":
        log.warning(
            "listing %s: note %s is marked %r but file %r (id %s) has type %r, not DOCUMENT; refusing",
            listing_id, note_id, kind, meta.get("name"), file_id, meta.get("type"),
        )
        return None

    if not _name_matches(kind, meta.get("name")):
        log.warning(
            "listing %s: note %s is marked %r but its file %r (id %s) does not look like one; refusing",
            listing_id, note_id, kind, meta.get("name"), file_id,
        )
        return None

    url = meta.get("url")
    if (meta.get("access") or "").upper() == "PRIVATE" or not url:
        log.info(
            "listing %s: file %s (%r) is PRIVATE or has no usable url; FS-72 check 3 reports it",
            listing_id, file_id, meta.get("name"),
        )
        return None

    return url          # read from the Files API response, never constructed


def get_brochure_link(hs: HubSpotDocumentReader, listing_id: str) -> Optional[str]:
    """Alias so FS-55 step (c) needs no change."""
    return get_listing_document_link(hs, listing_id, "brochure")


class HubSpotBrochureLinkSource:
    """The real BrochureLinkSource: a HubSpot reader behind the one-method seam."""

    def __init__(self, hs: HubSpotDocumentReader) -> None:
        self._hs = hs

    def get_brochure_link(self, listing_id: str) -> Optional[str]:
        return get_listing_document_link(self._hs, listing_id, "brochure")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _associated_note_ids(hs: HubSpotDocumentReader, listing_id: str) -> List[str]:
    """Follow association pagination: the brochure note can sit on a later page."""
    ids: List[str] = []
    after: Optional[str] = None
    seen_cursors = set()
    for _ in range(MAX_ASSOCIATION_PAGES):
        page, after = hs.note_association_page(listing_id, after)
        ids.extend(str(i) for i in page)
        if not after:
            return ids
        if after in seen_cursors:
            log.warning("listing %s: association cursor repeated; stopping pagination", listing_id)
            return ids
        seen_cursors.add(after)
    log.warning("listing %s: more than %d association pages; stopping", listing_id, MAX_ASSOCIATION_PAGES)
    return ids


def _read_notes(hs: HubSpotDocumentReader, note_ids: Iterable[str]) -> List[Dict[str, Any]]:
    ids = list(dict.fromkeys(note_ids))
    out: List[Dict[str, Any]] = []
    for i in range(0, len(ids), BATCH_READ_LIMIT):
        out.extend(hs.read_notes(ids[i : i + BATCH_READ_LIMIT]))
    return out


def _split_attachment_ids(raw: Any) -> List[str]:
    """`hs_attachment_ids` is semicolon-separated; order is undocumented."""
    parts = [p.strip() for p in str(raw or "").split(";")]
    return list(dict.fromkeys(p for p in parts if p))


def _parse_ts(raw: Any) -> datetime:
    """
    Parse, never string-sort: records written by different tools mix formats and
    offsets. Accepts epoch milliseconds, ISO-8601 with Z / +hh:mm / no offset
    (assumed UTC). Unparseable sorts oldest.
    """
    oldest = datetime.min.replace(tzinfo=timezone.utc)
    if raw is None or raw == "":
        return oldest
    s = str(raw).strip()
    try:
        if re.fullmatch(r"\d{10,}", s):
            return datetime.fromtimestamp(int(s) / 1000, tz=timezone.utc)
        dt = datetime.fromisoformat(s.replace("Z", "+00:00").replace("z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError, OSError):
        return oldest


def _note_sort_id(raw: Any) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _name_matches(kind: str, name: Optional[str]) -> bool:
    """Verification only — selection is by marker. Refuses print variants."""
    if not name or _PRINT_VARIANT_RE.search(name):
        return False
    words = kind.replace("_", " ")
    norm = re.sub(r"[\s_\-]+", " ", name.lower())
    return words in norm or words.replace(" ", "") in norm.replace(" ", "")


# ---------------------------------------------------------------------------
# Real reader: HubSpot REST over httpx (the repo has no HubSpot SDK)
# ---------------------------------------------------------------------------

class HubSpotRestReader:
    """
    Synchronous, read-only. 401/403 raise HubSpotAuthError; 429/5xx/transport
    errors are retried with backoff then raise HubSpotError; 404 on a file is
    "gone" (None). Any other 4xx raises HubSpotError.

    Sync on purpose, matching the FS-71 signature. From an async orchestrator
    call it with `fastapi.concurrency.run_in_threadpool`.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        *,
        client: Optional[httpx.Client] = None,
        max_attempts: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._token = token
        self._client = client or httpx.Client(base_url=HUBSPOT_BASE, timeout=TIMEOUT)
        self._max_attempts = max_attempts
        self._sleep = sleep

    def close(self) -> None:
        self._client.close()

    # -- the three calls ---------------------------------------------------

    def note_association_page(
        self, listing_id: str, after: Optional[str] = None
    ) -> Tuple[List[str], Optional[str]]:
        params: Dict[str, Any] = {"limit": ASSOCIATION_PAGE_SIZE}
        if after:
            params["after"] = after
        r = self._request(
            "GET",
            f"/crm/v4/objects/{LISTINGS_OBJECT_TYPE}/{quote(str(listing_id), safe='')}/associations/notes",
            params=params,
        )
        self._raise_unless_ok(r, "note associations")
        body = r.json()
        ids = [str(x["toObjectId"]) for x in body.get("results", []) if "toObjectId" in x]
        nxt = ((body.get("paging") or {}).get("next") or {}).get("after")
        return ids, nxt

    def read_notes(self, note_ids: List[str]) -> List[Dict[str, Any]]:
        r = self._request(
            "POST",
            "/crm/v3/objects/notes/batch/read",
            json={"properties": NOTE_PROPERTIES, "inputs": [{"id": str(i)} for i in note_ids]},
        )
        self._raise_unless_ok(r, "notes batch read", ok=(200, 207))
        return r.json().get("results", [])

    def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        r = self._request("GET", f"/files/v3/files/{quote(str(file_id), safe='')}")
        if r.status_code == 404:
            return None
        self._raise_unless_ok(r, "file lookup")
        return r.json()

    # -- plumbing ----------------------------------------------------------

    def _auth_headers(self) -> Dict[str, str]:
        if self._token:
            return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}
        return _headers()

    def _request(self, method: str, path: str, **kw: Any) -> httpx.Response:
        last: Optional[str] = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                r = self._client.request(method, path, headers=self._auth_headers(), **kw)
            except httpx.TransportError as exc:
                last = f"transport error: {exc.__class__.__name__}"
                r = None
            if r is not None:
                if r.status_code in (401, 403):
                    raise HubSpotAuthError(
                        f"{r.status_code} from HubSpot on {method} {path}: credential or scope problem"
                    )
                if r.status_code != 429 and r.status_code < 500:
                    return r
                last = f"{r.status_code}"
            if attempt < self._max_attempts:
                self._sleep(self._backoff(attempt, r))
        raise HubSpotError(f"HubSpot {method} {path} failed after {self._max_attempts} attempts ({last})")

    @staticmethod
    def _backoff(attempt: int, r: Optional[httpx.Response]) -> float:
        if r is not None:
            ra = r.headers.get("Retry-After", "")
            if ra.isdigit():
                return min(float(ra), 5.0)
        return min(0.5 * 2 ** (attempt - 1), 5.0)

    @staticmethod
    def _raise_unless_ok(r: httpx.Response, what: str, ok: Tuple[int, ...] = (200,)) -> None:
        if r.status_code not in ok:
            raise HubSpotError(f"HubSpot {what} returned {r.status_code}: {r.text[:200]}")
