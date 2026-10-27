"""
FS-71 — brochure link lookup.

    BROCHURE_LINK_SOURCE = fake | hubspot

Unset: `hubspot` when HUBSPOT_API_KEY is present, otherwise `fake` (same shape as
ANTHROPIC_MODE). Anything else raises — a typo must not quietly mean "no brochures".
"""

from __future__ import annotations

import os

from .base import BrochureLinkSource
from .fake import FakeBrochureLinkSource
from .hubspot import (
    HubSpotAuthError,
    HubSpotBrochureLinkSource,
    HubSpotRestReader,
    get_brochure_link,
    get_listing_document_link,
)

__all__ = [
    "BrochureLinkSource",
    "FakeBrochureLinkSource",
    "HubSpotAuthError",
    "HubSpotBrochureLinkSource",
    "HubSpotRestReader",
    "get_brochure_link",
    "get_brochure_link_source",
    "get_listing_document_link",
]


def get_brochure_link_source() -> BrochureLinkSource:
    mode = os.getenv("BROCHURE_LINK_SOURCE", "").strip().lower()
    if not mode:
        mode = "hubspot" if os.getenv("HUBSPOT_API_KEY") else "fake"
    if mode == "fake":
        return FakeBrochureLinkSource()
    if mode == "hubspot":
        return HubSpotBrochureLinkSource(HubSpotRestReader())
    raise ValueError(f"BROCHURE_LINK_SOURCE must be 'fake' or 'hubspot', got {mode!r}")
