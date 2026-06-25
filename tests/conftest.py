"""
Shared pytest fixtures for My Team AI test suite.

Sets ANTHROPIC_MODE=mock at import time so any test that hits a Claude-backed
bot function gets deterministic templated responses without burning credits.
The mock client (app/clients/claude_client.py) intentionally echoes prompt
fields back, so tests can verify field propagation end-to-end.
"""
import os
import pytest

# Force mock Claude before app modules are imported by step def files.
os.environ.setdefault("ANTHROPIC_MODE", "mock")


class StepContext:
    """Mutable context bag shared between BDD step functions."""
    def __init__(self):
        self.text = None
        self.result = None
        self.results = []
        self.validation_error = None
        self.request_data = {}


@pytest.fixture
def ctx():
    return StepContext()
