"""
FS-42: the Register page shows the composed HTML email in an iframe. That frame
must stay cut off from the page: no scripts, no same-origin access. The email body
is built server-side from escaped values, but the page must not depend on that.
"""
from __future__ import annotations

import pathlib
import re

CHAT = pathlib.Path(__file__).resolve().parents[1] / "frontend" / "chat.html"


def _sandbox_value() -> str:
    match = re.search(r"setAttribute\('sandbox',\s*'([^']*)'\)", CHAT.read_text())
    assert match, "the email preview iframe must set a sandbox attribute"
    return match.group(1)


def test_email_preview_frame_is_sandboxed():
    _sandbox_value()


def test_email_preview_frame_cannot_run_scripts_or_reach_the_page():
    tokens = _sandbox_value().split()
    assert "allow-scripts" not in tokens
    assert "allow-same-origin" not in tokens


def test_email_preview_buttons_can_still_open_the_brochure_in_a_new_tab():
    tokens = _sandbox_value().split()
    assert "allow-popups" in tokens and "allow-popups-to-escape-sandbox" in tokens


def test_email_html_goes_into_srcdoc_never_into_the_page_dom():
    source = CHAT.read_text()
    assert "frame.srcdoc" in source
    assert not re.search(r"\.innerHTML\s*=\s*[^;\n]*html_body", source)
