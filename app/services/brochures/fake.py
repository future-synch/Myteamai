"""
In-memory BrochureLinkSource (FS-71).

Used by every automated test outside FS-71's own suite, so FS-55 / FS-57 can be
built and tested with no network and no HubSpot. Maps listing id -> URL or None.
"""

from __future__ import annotations

from typing import Dict, Optional


class FakeBrochureLinkSource:
    def __init__(self, links: Optional[Dict[str, Optional[str]]] = None) -> None:
        self._links: Dict[str, Optional[str]] = dict(links or {})
        self.requested: list[str] = []

    def set(self, listing_id: str, url: Optional[str]) -> None:
        self._links[str(listing_id)] = url

    def get_brochure_link(self, listing_id: str) -> Optional[str]:
        self.requested.append(str(listing_id))
        return self._links.get(str(listing_id))
