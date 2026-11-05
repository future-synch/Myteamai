"""FS-42 helper script: the parts that can be checked without a browser or Google."""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

from app.services.transports.gmail import SCOPES

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "gmail_get_refresh_token.py"


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location("gmail_get_refresh_token", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_output_names_the_settings_to_fill_and_warns_about_the_token(script):
    text = script.format_result("drafts@dev.example.test", "1//the-token")
    assert "GMAIL_DEV_MAILBOX=drafts@dev.example.test" in text
    assert "GMAIL_DEV_REFRESH_TOKEN=1//the-token" in text
    assert "GMAIL_DEV_CLIENT_ID" in text and "password" in text


def test_the_script_asks_for_the_same_single_scope_as_the_transport(script):
    assert script.SCOPES == SCOPES == ["https://www.googleapis.com/auth/gmail.compose"]


def test_a_missing_client_file_is_reported_not_a_traceback(script, capsys, tmp_path):
    pytest.importorskip("google_auth_oauthlib")
    code = script.main(["--client-secrets", str(tmp_path / "nope.json")])
    assert code == 2 and "not found" in capsys.readouterr().err


def test_a_full_run_prints_the_mailbox_and_token_and_writes_no_file(script, capsys, tmp_path, monkeypatch):
    flow_mod = pytest.importorskip("google_auth_oauthlib.flow")
    import googleapiclient.discovery as discovery

    from tests.support.gmail_stub import MAILBOX, StubGmail

    seen = {}

    class FakeCreds:
        refresh_token = "1//fake-refresh-token"

    class FakeFlow:
        def run_local_server(self, **kwargs):
            seen.update(kwargs)
            return FakeCreds()

    def fake_from_file(path, scopes):
        seen["scopes"] = scopes
        return FakeFlow()

    monkeypatch.setattr(flow_mod.InstalledAppFlow, "from_client_secrets_file", staticmethod(fake_from_file))
    monkeypatch.setattr(discovery, "build", lambda *a, **k: StubGmail())
    secrets = tmp_path / "client.json"
    secrets.write_text("{}")
    before = set(tmp_path.iterdir())

    code = script.main(["--client-secrets", str(secrets)])

    out = capsys.readouterr().out
    assert code == 0
    assert f"GMAIL_DEV_MAILBOX={MAILBOX}" in out and "GMAIL_DEV_REFRESH_TOKEN=1//fake-refresh-token" in out
    assert seen["scopes"] == SCOPES
    assert seen["access_type"] == "offline" and seen["prompt"] == "consent"
    assert set(tmp_path.iterdir()) == before, "the script must not write the token to disk"
