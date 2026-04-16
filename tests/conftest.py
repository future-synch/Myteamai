"""
Shared pytest fixtures for My Team AI test suite.
"""
import pytest


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
