"""
Browser tests for the CURRENT frontend: the login page (/) and the chat page
(/chat) (FS-75). The scenarios live in tests/features/e2e_current_chat.feature.

Steps used by more than one feature file (sign-in, page checks, request
recording, the offline Background) are in conftest.py; steps specific to /chat
are below. Locators are the ids and classes chat.html already has.
"""
from playwright.sync_api import Page, expect
from pytest_bdd import given, parsers, scenarios, then, when

from app.classifier import CAPABILITIES

scenarios("../features/e2e_current_chat.feature")

FORM_PANELS = {"Welcome Client": "#form-welcome"}


@when(parsers.parse('I type "{text}" in the free-text box and send it'))
def step_send_free_text(page: Page, text: str):
    page.fill("#freeText", text)
    page.get_by_role("button", name="Send", exact=True).click()


@given(parsers.parse('I open the "{label}" form'))
def step_open_form(page: Page, label: str):
    page.get_by_role("button", name=label, exact=True).click()
    expect(page.locator(FORM_PANELS[label])).to_be_visible()


@given(parsers.parse('I fill in the Welcome Client form with source "{source}" and agent name "{agent}"'))
def step_fill_welcome_form(page: Page, source: str, agent: str):
    page.select_option("#w-source", label=source)
    page.fill("#w-agent_name", agent)


@when("I submit the Welcome Client form with the client name left blank")
def step_submit_welcome_blank(page: Page):
    page.fill("#w-client_name", "")
    page.locator("#form-welcome .send-btn").click()


@when(parsers.parse('I submit the Welcome Client form with the client name "{name}"'))
def step_submit_welcome_named(page: Page, name: str):
    page.fill("#w-client_name", name)
    page.locator("#form-welcome .send-btn").click()


@when("I click into the client name field and tab out without typing")
def step_blur_client_name(page: Page):
    page.focus("#w-client_name")
    page.keyboard.press("Tab")


@then(parsers.parse('an error card says "{message}"'))
def step_error_card_says(page: Page, message: str):
    expect(page.locator("#messages .msg.error strong")).to_have_text(message)


@then("the error card lists the six capabilities")
def step_error_card_lists_capabilities(page: Page):
    assert len(CAPABILITIES) == 6
    expect(page.locator("#messages .msg.error ul.capabilities li")).to_have_text(CAPABILITIES)


@then(parsers.parse('the client name field shows the error "{message}"'))
def step_client_name_error(page: Page, message: str):
    expect(page.locator("#err-w-client_name")).to_have_text(message)


@then(parsers.parse('a bot message greets "{name}"'))
def step_bot_message_greets(page: Page, name: str):
    expect(page.locator("#messages .msg.bot", has_text=f"Dear {name},")).to_be_visible()
