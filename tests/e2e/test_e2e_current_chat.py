"""
Browser tests for the CURRENT frontend: the login page (/) and the chat page
(/chat) (FS-75). The scenarios live in tests/features/e2e_current_chat.feature.

Steps used by more than one feature file (sign-in, page checks, the offline
Background) are in conftest.py; steps specific to /chat are below.
"""
from pytest_bdd import scenarios

scenarios("../features/e2e_current_chat.feature")
