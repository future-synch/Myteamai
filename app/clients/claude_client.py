"""
Claude API client wrapper supporting three modes:

- real:   live calls to Anthropic API (production, acceptance testing)
- mock:   deterministic templated responses (development without credits, unit tests)
- record: live calls + save responses to fixture files (for building eval datasets)

Mode is controlled by the ANTHROPIC_MODE environment variable.
Default: 'real' if ANTHROPIC_API_KEY is set, otherwise 'mock'.

The mock mode returns responses that intentionally include fields passed in,
so tests can verify field propagation independently of real API behaviour.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

@dataclass
class ClaudeContent:
    """Mimics anthropic.types.TextBlock with a .text attribute."""
    text: str


@dataclass
class ClaudeMessage:
    """Mimics anthropic.types.Message with a .content list of TextBlocks."""
    content: List[ClaudeContent]


# ---------------------------------------------------------------------------
# Mode resolution
# ---------------------------------------------------------------------------

def _current_mode() -> str:
    """Return current mode: 'real', 'mock', or 'record'."""
    explicit = os.getenv("ANTHROPIC_MODE", "").strip().lower()
    if explicit in {"real", "mock", "record"}:
        return explicit
    # Auto: real if API key set, else mock
    return "real" if os.getenv("ANTHROPIC_API_KEY") else "mock"


# ---------------------------------------------------------------------------
# Mock implementation — produces templated responses with passed-in fields
# ---------------------------------------------------------------------------

class _MockClaudeClient:
    """
    In-memory mock that returns deterministic responses.

    The mock inspects the prompt to figure out which function it's serving
    and returns a templated welcome message / extraction JSON / etc that
    INCLUDES whatever input fields the prompt mentions. This lets tests
    verify field propagation: if the test passes 'August' as timeline and
    the mock output contains 'August', then the prompt-construction layer
    correctly threaded the field through.
    """

    class _Messages:
        def __init__(self, parent: "_MockClaudeClient") -> None:
            self._parent = parent

        def create(
            self,
            model: str,
            max_tokens: int,
            messages: List[Dict[str, Any]],
            **kwargs: Any,
        ) -> ClaudeMessage:
            prompt_text = ""
            for msg in messages:
                content = msg.get("content", "")
                if isinstance(content, str):
                    prompt_text += content
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and "text" in block:
                            prompt_text += block["text"]

            # Extraction prompt detected? Return JSON object.
            if "extracting structured data" in prompt_text.lower():
                response_text = self._parent._mock_extract(prompt_text)
            else:
                response_text = self._parent._mock_generate(prompt_text)

            return ClaudeMessage(content=[ClaudeContent(text=response_text)])

    def __init__(self) -> None:
        self.messages = self._Messages(self)

    # ------ extraction (Haiku) ------

    def _mock_extract(self, prompt: str) -> str:
        """Mock the field-extraction prompt — return JSON with extracted fields."""
        # Find the user's text inside the prompt: it's wrapped in Text: "..."
        text_match = re.search(r'Text:\s*"([^"]*)"', prompt)
        user_text = text_match.group(1) if text_match else ""

        client_name = self._extract_name(user_text)
        source = self._extract_source(user_text)
        budget_gbp = self._extract_budget(user_text)
        timeline = self._extract_timeline(user_text)

        return json.dumps({
            "client_name": client_name,
            "source": source,
            "budget_gbp": budget_gbp,
            "timeline": timeline,
        })

    @staticmethod
    def _extract_name(text: str) -> str:
        """Crude name extraction for mock purposes."""
        # Strip common preamble words
        cleaned = re.sub(
            r"^(welcome\s+(?:new\s+client\s*[\u2014\-]?\s*)?)",
            "",
            text.strip(),
            flags=re.IGNORECASE,
        )
        # Take chars up to first comma or "came" or "via"
        m = re.match(r"([A-Z][\w\s'\-\.]{1,60}?)(?:[,;]|\s+came|\s+via|\s+through|$)", cleaned)
        if m:
            return m.group(1).strip()
        # Fallback: first 2-3 capitalised words
        words = [w for w in re.findall(r"[A-Z][a-zA-Z\-']+", cleaned)]
        return " ".join(words[:2]) if words else "Unknown Client"

    @staticmethod
    def _extract_source(text: str) -> str:
        lowered = text.lower()
        if "rightmove" in lowered:
            return "Rightmove"
        if "zoopla" in lowered:
            return "Zoopla"
        if "referral" in lowered or "recommended" in lowered or "friend" in lowered:
            return "Referral"
        if "direct" in lowered or "walked in" in lowered:
            return "Direct"
        return "Other"

    @staticmethod
    def _extract_budget(text: str) -> Optional[int]:
        # Match patterns like "3M", "2.5M", "500k", "£3,000,000"
        m = re.search(r"(?:budget\s+)?\u00a3?\s*([\d.]+)\s*([mk])\b", text, re.IGNORECASE)
        if m:
            num = float(m.group(1))
            unit = m.group(2).lower()
            return int(num * (1_000_000 if unit == "m" else 1_000))
        m = re.search(r"\u00a3\s*([\d,]+)", text)
        if m:
            try:
                return int(m.group(1).replace(",", ""))
            except ValueError:
                return None
        return None

    @staticmethod
    def _extract_timeline(text: str) -> Optional[str]:
        # Look for month names, "summer", "spring", or "X weeks/months"
        months = (
            "January February March April May June "
            "July August September October November December"
        ).split()
        for month in months:
            if re.search(rf"\b{month}\b", text, re.IGNORECASE):
                return month
        for season in ("spring", "summer", "autumn", "winter"):
            if re.search(rf"\b{season}\b", text, re.IGNORECASE):
                return season.capitalize()
        m = re.search(r"\b(\d+)\s+(weeks?|months?)\b", text, re.IGNORECASE)
        if m:
            return f"{m.group(1)} {m.group(2)}"
        return None

    # ------ generation (Sonnet) ------

    def _mock_generate(self, prompt: str) -> str:
        """Mock the welcome generation prompt — return a templated draft."""
        # Pull fields out of the prompt that fn_generate_welcome constructs
        client_name = self._field_from_prompt(prompt, r"new client named\s+([^\s,.]+(?:\s+[^\s,.]+)*?)\s+who")
        agent_name  = self._field_from_prompt(prompt, r"You are\s+([^,]+),")
        source      = self._field_from_prompt(prompt, r"found you through\s+([A-Za-z]+)")
        budget_str  = self._field_from_prompt(prompt, r"budget is\s+\u00a3([\d,]+)")
        timeline    = self._field_from_prompt(prompt, r"timeline[^.]*?:\s*([A-Za-z0-9 ]+?)[\.\n]")

        budget_phrase = f"with a budget of \u00a3{budget_str}" if budget_str else ""
        timeline_phrase = f"and your timeline of {timeline}" if timeline else ""
        ctx_phrase = " ".join(p for p in [budget_phrase, timeline_phrase] if p)

        # Templated welcome that explicitly includes the fields if present
        draft = (
            f"Dear {client_name or 'there'},\n\n"
            f"Thank you for reaching out via {source or 'Curtis Sloane'}. "
            f"I'm {agent_name or 'your agent'} from Curtis Sloane, and I'd be "
            f"delighted to help you find the right property in W11.\n\n"
        )
        if ctx_phrase:
            draft += (
                f"I see you're working {ctx_phrase}, which gives us a clear "
                f"target. There's quite a bit of interesting activity in that range "
                f"right now in Notting Hill and Holland Park.\n\n"
            )
        draft += (
            f"I'd love to learn more about what matters most to you \u2014 preferred "
            f"areas, must-haves, the kind of home that would make you feel \"this is it.\" "
            f"When would be a good time to chat?\n\n"
            f"Best regards,\n{agent_name or 'Curtis Sloane'}"
        )
        return draft

    @staticmethod
    def _field_from_prompt(prompt: str, pattern: str) -> Optional[str]:
        m = re.search(pattern, prompt)
        return m.group(1).strip() if m else None


# ---------------------------------------------------------------------------
# Real client wrapper (lazy-imported anthropic SDK)
# ---------------------------------------------------------------------------

def _real_client():
    """Return a real anthropic.Anthropic client. Requires ANTHROPIC_API_KEY."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Either set it or use ANTHROPIC_MODE=mock"
        )
    import anthropic
    return anthropic.Anthropic(api_key=api_key)


# ---------------------------------------------------------------------------
# Recording wrapper -- calls real, saves response to fixture file
# ---------------------------------------------------------------------------

class _RecordingClient:
    """Wraps a real client and saves each response to fixtures/claude/."""

    def __init__(self) -> None:
        self._real = _real_client()
        self._fixtures_dir = "fixtures/claude"
        os.makedirs(self._fixtures_dir, exist_ok=True)

    class _Messages:
        def __init__(self, parent: "_RecordingClient") -> None:
            self._parent = parent

        def create(self, **kwargs: Any) -> Any:
            response = self._parent._real.messages.create(**kwargs)
            timestamp = int(time.time() * 1000)
            path = os.path.join(self._parent._fixtures_dir, f"call_{timestamp}.json")
            try:
                with open(path, "w") as f:
                    json.dump({
                        "request": {"model": kwargs.get("model"), "messages": kwargs.get("messages")},
                        "response_text": response.content[0].text,
                    }, f, indent=2, default=str)
                log.info("Recorded Claude call to %s", path)
            except Exception as exc:
                log.warning("Failed to record fixture: %s", exc)
            return response

    @property
    def messages(self):
        return self._Messages(self)


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------

def get_client():
    """
    Return a Claude client appropriate for the current mode.

    Returns None if mode is 'real' and no ANTHROPIC_API_KEY is configured --
    callers should treat this as 'service unavailable'.
    """
    mode = _current_mode()
    log.debug("Claude client mode: %s", mode)

    if mode == "mock":
        return _MockClaudeClient()
    if mode == "record":
        return _RecordingClient()
    # mode == "real"
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    return _real_client()