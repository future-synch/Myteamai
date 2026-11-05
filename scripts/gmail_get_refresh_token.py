"""
One-off helper: obtain the Gmail refresh token for the shared sending mailbox (FS-42).

Run this ON YOUR OWN COMPUTER, not on Render. It opens a browser; sign in as the
mailbox the drafts should land in and click Allow. It prints the mailbox address
and the refresh token to your terminal and writes NOTHING to disk.

    pip install google-auth-oauthlib google-api-python-client
    python scripts/gmail_get_refresh_token.py --client-secrets ~/Downloads/client_secret_XXXX.json

Treat the printed refresh token like a password: paste it straight into Render's
Environment tab (GMAIL_DEV_REFRESH_TOKEN). Never put it in chat, a ticket, a
commit or a screenshot. Full steps: docs/GMAIL_DRAFT_SETUP.md
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.transports.gmail import SCOPES  # noqa: E402  (single source for the scope)


def format_result(mailbox: str, refresh_token: str) -> str:
    """The text shown to the person running the script. Pure, so it is testable."""
    return "\n".join(
        [
            "",
            f"Signed in as: {mailbox}",
            "Scope granted: " + ", ".join(SCOPES),
            "",
            "Set these in Render (Environment tab). Values are shown once, below:",
            "",
            f"  GMAIL_DEV_MAILBOX={mailbox}",
            f"  GMAIL_DEV_REFRESH_TOKEN={refresh_token}",
            "",
            "GMAIL_DEV_CLIENT_ID and GMAIL_DEV_CLIENT_SECRET come from the downloaded client JSON.",
            "",
            "This token is a password for that mailbox's drafts. Do not paste it into chat,",
            "tickets, commits or screenshots. Clear this terminal when you are done.",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Get the Gmail refresh token for the MyTeamAI sending mailbox.")
    parser.add_argument("--client-secrets", required=True, help="Path to the OAuth client JSON downloaded from Google Cloud (Desktop app).")
    args = parser.parse_args(argv)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        print("Missing libraries. Run: pip install google-auth-oauthlib google-api-python-client", file=sys.stderr)
        return 2

    path = os.path.expanduser(args.client_secrets)
    if not os.path.isfile(path):
        print(f"Client secrets file not found: {path}", file=sys.stderr)
        return 2

    flow = InstalledAppFlow.from_client_secrets_file(path, SCOPES)
    # access_type=offline + prompt=consent make Google return a refresh token even
    # if this account has authorised the app before.
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    if not creds.refresh_token:
        print("Google did not return a refresh token. Remove the app at "
              "https://myaccount.google.com/permissions and run this again.", file=sys.stderr)
        return 1

    profile = build("gmail", "v1", credentials=creds, cache_discovery=False).users().getProfile(userId="me").execute()
    print(format_result(profile.get("emailAddress", "(unknown)"), creds.refresh_token))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
