"""
Probe: what URL would a welcome email carry for this listing?

    python -m app.services.brochures LISTING_ID [--kind brochure]

John's suggested first test: "here is the ID for a listing, get me the URL for the
brochure." Run it locally (HUBSPOT_API_KEY in .env) or in the Render shell, where the
service's environment is already set.

READ-ONLY: three HubSpot GETs/POST-reads, no writes, no Google. Never prints the token.

Exit status
    0  a url was found (printed on stdout, and nothing else is)
    1  no such document for this listing. A NORMAL answer, not a failure
    2  an error: bad credentials/scopes, HubSpot failing, no HUBSPOT_API_KEY
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional, Sequence, TextIO

from .hubspot import HubspotAuthError, HubSpotRestReader, get_listing_document_link
from app.services.hubspot_registration import HubspotError


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    reader=None,
    out: Optional[TextIO] = None,
    err: Optional[TextIO] = None,
) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.services.brochures",
        description="Print the HubSpot URL of a listing's brochure (read-only).",
    )
    parser.add_argument("listing_id", help="HubSpot Listing (0-420) record id")
    parser.add_argument("--kind", default="brochure", help="document kind (default: brochure)")
    args = parser.parse_args(argv)
    out, err = out or sys.stdout, err or sys.stderr

    try:
        if reader is None:
            try:                                   # local runs: pick up .env; Render sets env directly
                from dotenv import load_dotenv
                load_dotenv()
            except ImportError:                    # pragma: no cover
                pass
            reader = HubSpotRestReader()
        url = get_listing_document_link(reader, args.listing_id, args.kind)
    except HubspotAuthError as exc:
        print(f"AUTH ERROR ({exc.status_code}): the HubSpot token is invalid or lacks a scope "
              f"(listings, notes and files read). {exc}", file=err)
        return 2
    except (HubspotError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=err)
        return 2

    if url is None:
        print(f"No {args.kind} for listing {args.listing_id}. This is a normal answer "
              f"(none attached, or withheld by a check above).", file=err)
        return 1
    print(url, file=out)
    return 0


if __name__ == "__main__":                         # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    raise SystemExit(main())
