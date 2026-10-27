"""
Test doubles for the FS-71 brochure lookup. Offline, deterministic.

FakeHubSpot       in-memory HubSpotDocumentReader (the lookup's port)
rest_transport()  an httpx.MockTransport that speaks the three HubSpot REST
                  endpoints backed by a FakeHubSpot, so HubSpotRestReader itself
                  (paths, params, JSON shapes, status handling, retry) is tested
                  without a network.
"""
from __future__ import annotations

import hashlib
import itertools
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

ADDRESS = "88 Westbourne Park Road"
_TITLES = {"brochure": "Brochure", "floor_plan": "Floor Plan", "epc": "EPC", "lease": "Lease"}


def marker_body(kind: str, filename: str, joiner: str = "<br>") -> str:
    """A note body shaped like the real thing: HTML, lines joined with <br>, so
    the whole body is ONE physical line and wrapped in markup before the marker."""
    lines = [
        f"MyTeamAI document: {kind}",
        f"Source file: {filename}",
        f"Source folder: PROPERTIES 2026/{ADDRESS}",
        "Date: 2026-10-19",
        "Attached at publish",
    ]
    return "<div><p>" + joiner.join(lines) + "</p></div>"


def default_filename(kind: str) -> str:
    return f"{ADDRESS} - {_TITLES.get(kind, kind)}.pdf"


class FakeHubSpot:
    def __init__(self, order: str = "asc", page_size: int = 500) -> None:
        self.order = order                    # association order: asc | desc
        self.page_size = page_size
        self.notes: Dict[str, Dict[str, Any]] = {}
        self.assoc: Dict[str, List[str]] = {}
        self._explicit: set[str] = set()
        self.files: Dict[str, Dict[str, Any]] = {}
        self._ids = itertools.count(7001)

    # -- building ----------------------------------------------------------

    def add_file(self, name: str, *, type: str = "DOCUMENT", access: str = "PUBLIC_NOT_INDEXABLE") -> str:
        fid = str(next(self._ids))
        token = hashlib.sha1(f"{name}|{fid}".encode()).hexdigest()[:14]
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        # Deliberately NOT derivable from the file id, so a test can tell a url that
        # was read from the Files API from one assembled in application code.
        url = f"https://cdn.example-hubfs.test/{token}/{slug}"
        self.files[fid] = {
            "id": fid, "name": name, "url": url, "type": type,
            "access": access, "archived": False,
        }
        return fid

    def add_note(self, listing_id: str, body: str, attachment_ids: List[str], timestamp: str) -> str:
        nid = str(next(self._ids))
        self.notes[nid] = {
            "hs_note_body": body,
            "hs_attachment_ids": ";".join(attachment_ids),
            "hs_timestamp": timestamp,
        }
        self.assoc.setdefault(listing_id, []).append(nid)
        return nid

    def set_assoc_order(self, listing_id: str, ids: List[str]) -> None:
        """Pin the exact association order (bypasses asc/desc)."""
        self.assoc[listing_id] = list(ids)
        self._explicit.add(listing_id)

    def url_of(self, file_id: str) -> str:
        return self.files[file_id]["url"]

    # -- the HubSpotDocumentReader port ------------------------------------

    def note_association_page(self, listing_id: str, after: Optional[str] = None) -> Tuple[List[str], Optional[str]]:
        ids = list(self.assoc.get(listing_id, []))
        if self.order == "desc" and listing_id not in self._explicit:
            ids.reverse()
        start = int(after) if after else 0
        end = start + self.page_size
        return ids[start:end], (str(end) if end < len(ids) else None)

    def read_notes(self, note_ids: List[str]) -> List[Dict[str, Any]]:
        assert len(note_ids) <= 100, "batch read must be chunked to 100"
        return [{"id": i, "properties": dict(self.notes[i])} for i in note_ids if i in self.notes]

    def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        f = self.files.get(str(file_id))
        return dict(f) if f else None


class RestTransport:
    """httpx.MockTransport handler that serves a FakeHubSpot over REST."""

    TOKEN = "test-token"

    def __init__(self, fake: Optional[FakeHubSpot] = None, *, always: Optional[int] = None,
                 fail_first: Optional[Tuple[int, int]] = None) -> None:
        self.fake = fake or FakeHubSpot()
        self.always = always                  # every request gets this status
        self.fail_first = fail_first          # (status, n): first n requests fail
        self.requests: List[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.always is not None:
            return httpx.Response(self.always, json={"status": "error"})
        if self.fail_first and len(self.requests) <= self.fail_first[1]:
            return httpx.Response(self.fail_first[0], json={"status": "error"}, headers={"Retry-After": "0"})
        if request.headers.get("authorization") != f"Bearer {self.TOKEN}":
            return httpx.Response(401, json={"status": "error", "message": "missing token"})

        path = request.url.path
        m = re.fullmatch(r"/crm/v4/objects/0-420/([^/]+)/associations/notes", path)
        if request.method == "GET" and m:
            assert request.url.params.get("limit") == "500"
            ids, nxt = self.fake.note_association_page(m.group(1), request.url.params.get("after"))
            body: Dict[str, Any] = {"results": [
                {"toObjectId": int(i), "associationTypes": [
                    {"category": "HUBSPOT_DEFINED", "typeId": 898, "label": None}]} for i in ids]}
            if nxt:
                body["paging"] = {"next": {"after": nxt}}
            return httpx.Response(200, json=body)

        if request.method == "POST" and path == "/crm/v3/objects/notes/batch/read":
            import json
            payload = json.loads(request.content)
            assert set(payload["properties"]) >= {"hs_note_body", "hs_attachment_ids", "hs_timestamp"}
            ids = [i["id"] for i in payload["inputs"]]
            return httpx.Response(200, json={"status": "COMPLETE", "results": self.fake.read_notes(ids)})

        m = re.fullmatch(r"/files/v3/files/([^/]+)", path)
        if request.method == "GET" and m:
            f = self.fake.get_file(m.group(1))
            return httpx.Response(200, json=f) if f else httpx.Response(404, json={"status": "error"})

        return httpx.Response(500, json={"status": "error", "message": f"unrouted {request.method} {path}"})
