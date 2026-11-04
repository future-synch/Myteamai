"""
Brochure link seam (FS-71).

One question, one answer: "what is the URL of this listing's brochure?"
The answer is a URL, or None. None is a NORMAL answer — a confidential listing
deliberately has no brochure in HubSpot — and is never an error.

Read-only by construction. Implementations make no Google Drive call, hold no
Drive credential, and write nothing to HubSpot (decision record, 20 Oct 2026).
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class BrochureLinkSource(Protocol):
    """Anything that can turn a listing id into a brochure URL (or None)."""

    def get_brochure_link(self, listing_id: str) -> Optional[str]:
        ...
