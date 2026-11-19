"""
Browser tests for the new workspace page, /workspace (FS-76). The scenarios live
in tests/features/e2e_workspace.feature.

Steps shared with the /chat suite (offline Background, login checks, request
recording) are in conftest.py. Below: steps specific to the workspace, the
stubbed backend responses, and the HubSpot seams.

Two layers, as the feature file explains:

* "the backend will answer ... with the 'x' response" stubs ONE endpoint with
  page.route. That tests the UI contract without HubSpot. The FS-75 network guard
  uses route.fallback(), so a stub registered here answers first and anything
  the test lets through is still guarded.
* "HubSpot is faked" goes through the real app, with the same two seams as
  tests/step_definitions/test_m3_register.py. The live server runs in this
  process, so monkeypatch reaches it.
"""
from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, Route, expect
from pytest_bdd import given, parsers, scenarios, then, when

import app.functions.bot_functions as bot_functions
from app.classifier import CAPABILITIES, classify
from app.services import hubspot_service
from app.services.hubspot_registration import RegistrationResult


scenarios("../features/e2e_workspace.feature")

GREETING = "Ready. Type a command or use the chips above to run a flow."
WEATHER = "What is the weather in London?"
PAYLOAD = "<img src=x onerror=window.__xss=1>"

# What the page calls each intent when it says "<flow> isn't connected yet".
INTENT_LABELS = {
    "MATCH_APPLICANTS": "Match applicants",
    "VALUATION_BRIEF": "Valuation brief",
    "KYC_STATUS": "KYC status",
    "DRAFT_OUTREACH": "Draft outreach",
}

MODEL_IDS = {
    "Claude Sonnet": "sonnet",
    "Claude Opus": "opus",
    "Claude Haiku": "haiku",
    "GPT-4o": "gpt4o",
}


# ---------------------------------------------------------------------------
# Stubbed backend responses (the shapes app/models/schemas.py defines)
# ---------------------------------------------------------------------------

def _registered(applicant_id="7001", created=True, diff=None, matches=None, draft=None, errors=None):
    return {
        "status": "ok",
        "applicant_id": applicant_id,
        "created": created,
        "diff": diff,
        "first_matches": matches if matches is not None else [],
        "welcome_draft": draft,
        "draft_ref": None,
        "errors": errors or [],
    }


def _match(n: int):
    return {"property_id": f"L{n}", "address": f"{n} Test Road, W11", "price_gbp": 3_000_000 + n,
            "bedrooms": 4, "match_score": None, "match_reason": "Meets your budget and bedroom criteria.",
            "brochure_url": None}


STUBBED = {
    "created": (200, _registered(
        matches=[_match(1), _match(2)],
        draft={"subject": "Welcome to Curtis Sloane, Tom",
               "html_body": "<p>Dear Tom,</p>",
               "text_body": "Dear Tom,\n\nThank you for registering with us."})),
    "existing": (200, _registered(
        applicant_id="7002", created=False,
        diff={"budget_gbp": {"submitted": 3500000, "existing": 2000000},
              "property_types": {"submitted": ["flat", "house"], "existing": ["house"]}})),
    "errors": (200, {"status": "error", "applicant_id": None, "created": False, "diff": None,
                     "first_matches": [], "welcome_draft": None, "draft_ref": None,
                     "errors": ["HUBSPOT_SYNC_FAIL"]}),
    "unprocessable": (422, {"detail": [{"type": "value_error", "loc": ["body", "email"],
                                        "msg": "value is not a valid email address", "input": "x"}]}),
    "unauthorised": (401, {"detail": "Not authenticated"}),
    # Every string a server could put in the page, carrying markup.
    "markup": (200, _registered(
        applicant_id=PAYLOAD, matches=[dict(_match(1), address=PAYLOAD)],
        draft={"subject": PAYLOAD,
               "html_body": PAYLOAD + "<script>window.__xss=1</script>",
               "text_body": f"Dear {PAYLOAD},"})),
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class HubSpotSeams:
    """The two seams test_m3_register.py patches, with knobs a scenario can turn."""

    def __init__(self) -> None:
        self.result = RegistrationResult(contact_id="7001", created=True)
        self.listings = [{"id": "L1", "address": "14 Test Road, W11", "price_gbp": 3_200_000,
                          "bedrooms": 4, "listing_type": "house"}]
        self.registered: list[dict] = []


@pytest.fixture
def hubspot(monkeypatch) -> HubSpotSeams:
    seams = HubSpotSeams()

    async def fake_register(criteria, hs_client):
        seams.registered.append(criteria)
        return seams.result

    async def fake_get_all_listings(*args, **kwargs):
        return seams.listings

    monkeypatch.setattr(bot_functions, "register_applicant_in_hubspot", fake_register)
    monkeypatch.setattr(hubspot_service, "get_all_listings", fake_get_all_listings)
    return seams


@pytest.fixture
def viewport() -> dict:
    """The window the page is opened in; the mobile steps change it."""
    return {"width": 1440, "height": 900}


@pytest.fixture
def held_routes() -> list[Route]:
    return []


# ---------------------------------------------------------------------------
# Locators
# ---------------------------------------------------------------------------

def thread(page: Page, mobile: bool = False):
    return page.locator("#mob-agent-body" if mobile else "#agent-body")


def form(page: Page, kind: str, mobile: bool = False):
    return thread(page, mobile).locator(f"[data-form={kind}]").last


def cards(page: Page, selector: str):
    return page.locator(f"#agent-body {selector}")


# ---------------------------------------------------------------------------
# Given: setup
# ---------------------------------------------------------------------------

@given(parsers.parse("the viewport is {width:d} by {height:d}"))
def step_viewport(viewport: dict, width: int, height: int):
    viewport.update(width=width, height=height)


@given("I am signed in as the agent on the workspace")
def step_signed_in_on_workspace(page: Page, token_login, viewport: dict):
    token_login()
    page.set_viewport_size(viewport)
    page.goto("/workspace")
    expect(page.locator("#mob-agent-input" if viewport["width"] <= 768 else "#agent-input")).to_be_visible()


@given("HubSpot is faked: registering creates a new contact and one listing matches")
def step_hubspot_creates(hubspot: HubSpotSeams):
    hubspot.result = RegistrationResult(contact_id="7001", created=True)


@given("HubSpot is faked: the applicant already exists and their budget differs")
def step_hubspot_existing(hubspot: HubSpotSeams):
    hubspot.result = RegistrationResult(
        contact_id="7002", created=False,
        diff={"budget_gbp": {"submitted": 3500000, "existing": 2000000}},
    )


@given(parsers.parse('the backend will answer POST "{path}" with the "{name}" response'))
def step_stub_backend(page: Page, path: str, name: str):
    status, body = STUBBED[name]
    page.route(f"**{path}", lambda route: route.fulfill(status=status, json=body))


@given(parsers.parse('the backend holds POST "{path}" until I let it through'))
def step_hold_backend(page: Page, held_routes: list[Route], path: str):
    page.route(f"**{path}", lambda route: held_routes.append(route))


@given(parsers.parse('I have sent "{text}" from the agent box'))
def step_have_sent(page: Page, text: str):
    page.fill("#agent-input", text)
    page.get_by_role("button", name="Run ↵", exact=True).click()
    expect(cards(page, ".agent-result-card")).to_have_count(1)


# ---------------------------------------------------------------------------
# When: session
# ---------------------------------------------------------------------------

@when("I open the workspace with no stored session")
def step_open_workspace_without_session(page: Page):
    page.goto("/workspace")


@when("I open the account menu")
def step_open_account_menu(page: Page):
    page.locator("#avatar-btn").click()
    expect(page.locator("#user-dropdown")).to_have_class(re.compile(r"\bopen\b"))


@when("I sign out from the account menu")
def step_sign_out(page: Page):
    page.locator("#avatar-btn").click()
    page.locator("#signout").click()


@when(parsers.parse('I choose "{item}" from the account menu'))
def step_choose_account_item(page: Page, item: str):
    page.locator("#user-dropdown .user-dd-item", has_text=re.compile(f"^\\s*{re.escape(item)}\\s*$")).click()


@when("I close the user panel")
def step_close_user_panel(page: Page):
    page.locator(".up-close").click()


# ---------------------------------------------------------------------------
# When: agent box, chips, Action Flows
# ---------------------------------------------------------------------------

@when(parsers.parse('I type "{text}" in the agent box and press Enter'))
def step_type_and_enter(page: Page, text: str):
    box = page.locator("#agent-input")
    box.fill(text)
    box.press("Enter")


@when(parsers.parse('I type "{text}" in the agent box and click Run'))
def step_type_and_run(page: Page, text: str):
    page.fill("#agent-input", text)
    page.get_by_role("button", name="Run ↵", exact=True).click()


@when(parsers.parse('I type "{first}" then Shift+Enter then "{second}" in the agent box'))
def step_type_shift_enter(page: Page, first: str, second: str):
    box = page.locator("#agent-input")
    box.press_sequentially(first)
    box.press("Shift+Enter")
    box.press_sequentially(second)


@when("I click Run with the agent box empty")
def step_run_empty(page: Page):
    expect(page.locator("#agent-input")).to_have_value("")
    page.get_by_role("button", name="Run ↵", exact=True).click()


@when("I click Clear")
def step_click_clear(page: Page):
    page.get_by_role("button", name="Clear", exact=True).click()


@when(parsers.parse('I click the "{chip}" chip'))
def step_click_chip(page: Page, chip: str):
    page.locator(".agent-chip", has_text=re.compile(f"^{re.escape(chip)}$")).click()


@when(parsers.parse('I run the "{flow}" flow from Action Flows'))
def step_run_flow(page: Page, flow: str):
    page.locator("#tn-af").click()
    page.locator(f"#fc-{flow}").click()
    page.locator("#d-run").click()


@when("I let the held request through")
def step_release_held(held_routes: list[Route]):
    assert held_routes, "no request was held"
    held_routes.pop(0).fallback()


@when(parsers.parse('I click the "{tab}" tab'))
def step_click_tab(page: Page, tab: str):
    page.locator(".topbar-nav .tn", has_text=re.compile(f"^{re.escape(tab)}$")).click()


@when("I open the model dropdown")
def step_open_model_dropdown(page: Page):
    page.locator("#model-switcher").click()
    expect(page.locator("#model-dropdown")).to_have_class(re.compile(r"\bopen\b"))


@when(parsers.parse('I choose the "{model}" model'))
def step_choose_model(page: Page, model: str):
    page.locator(f"#mopt-{MODEL_IDS[model]}").click()


@when("I open the welcome email preview")
def step_open_preview(page: Page):
    cards(page, "details summary").last.click()


# ---------------------------------------------------------------------------
# When: forms
# ---------------------------------------------------------------------------

def _fill_registration(page: Page, name: str) -> None:
    reg = form(page, "register")
    reg.locator("[data-field=full_name]").fill(name)
    reg.locator("[data-field=email]").fill("tom@example.com")
    reg.locator("[data-field=phone]").fill("+44 7700 900123")
    reg.locator("[data-field=budget]").fill("3500000")
    reg.locator("[data-field=financing]").select_option("cash")
    reg.locator("[data-field=preferred_channel]").select_option("email")
    reg.locator("[data-field=source]").fill("Rightmove")
    reg.locator("[data-field=property_types][value=house]").check()


@when(parsers.parse('I fill in and submit the registration form for "{name}"'))
def step_fill_and_submit_registration(page: Page, name: str):
    _fill_registration(page, name)
    form(page, "register").get_by_role("button", name="Register applicant").click()


@when("I submit the registration form with nothing filled in")
def step_submit_registration_blank(page: Page):
    form(page, "register").get_by_role("button", name="Register applicant").click()


@when(parsers.parse('I click into the "{field}" field and tab out without typing'))
def step_blur_field(page: Page, field: str):
    form(page, "register").locator(f"[data-field={field}]").focus()
    page.keyboard.press("Tab")


@when(parsers.parse('I submit the welcome form for "{name}"'))
def step_submit_welcome(page: Page, name: str):
    welcome = form(page, "welcome")
    welcome.locator("[data-field=client_name]").fill(name)
    welcome.locator("[data-field=source]").select_option("Rightmove")
    welcome.locator("[data-field=agent_name]").fill("Alex Agent")
    welcome.get_by_role("button", name="Generate welcome").click()


@when("I submit the welcome form with the client name left blank")
def step_submit_welcome_blank(page: Page):
    welcome = form(page, "welcome")
    welcome.locator("[data-field=source]").select_option("Rightmove")
    welcome.locator("[data-field=agent_name]").fill("Alex Agent")
    welcome.get_by_role("button", name="Generate welcome").click()


@when(parsers.parse('I type "{text}" in the mobile agent box and tap send'))
def step_mobile_type_and_send(page: Page, text: str):
    page.fill("#mob-agent-input", text)
    page.locator(".mob-agent-send").click()


# ---------------------------------------------------------------------------
# Then: thread and cards
# ---------------------------------------------------------------------------

@then(parsers.parse('the thread holds one message, "{text}"'))
def step_thread_one_message(page: Page, text: str):
    messages = page.locator("#agent-body > *")
    expect(messages).to_have_count(1)
    expect(messages.first).to_have_text(re.compile(r"^\s*(AI\s*)?" + re.escape(text) + r"\s*$"))


@then(parsers.parse("the thread mentions none of {names}"))
def step_thread_mentions_none(page: Page, names: str):
    text = page.locator("#agent-body").inner_text()
    present = [n for n in re.findall(r'"([^"]+)"', names) if n in text]
    assert not present, f"the thread mentions {present}"


@then("the agent shows the capability card")
def step_capability_card(page: Page):
    card = cards(page, ".agent-result-card").last
    expect(card).to_contain_text(classify(WEATHER).message)
    expect(card.locator("ul li")).to_have_text(CAPABILITIES)


@then("the agent box holds two lines")
def step_two_lines(page: Page):
    expect(page.locator("#agent-input")).to_have_value("first line\nsecond line")


@then("the typing indicator is shown")
def step_typing_shown(page: Page):
    expect(page.locator("#agent-typing")).to_be_visible()


@then("the typing indicator is gone")
def step_typing_gone(page: Page):
    expect(page.locator("#agent-typing")).to_have_count(0)


@then(parsers.parse('a result card says "{text}"'))
def step_result_card_says(page: Page, text: str):
    expect(cards(page, ".agent-result-card").last).to_contain_text(text)


@then(parsers.parse('the result card has an "{label}" line naming "{first}" and "{second}"'))
def step_result_card_extracted(page: Page, label: str, first: str, second: str):
    card = cards(page, ".agent-result-card").last
    expect(card).to_contain_text(label)
    expect(card).to_contain_text(first)
    expect(card).to_contain_text(second)


@then(parsers.parse('the result card has no "{text}" placeholder'))
def step_result_card_no_placeholder(page: Page, text: str):
    expect(cards(page, ".agent-result-card").last).not_to_contain_text(text)


@then(parsers.parse('the agent says "{flow}" isn\'t connected yet'))
def step_not_connected(page: Page, flow: str):
    expect(cards(page, ".agent-result-card").last).to_contain_text(f"{flow} isn't connected yet")


@then(parsers.parse('the agent says the flow the classifier chose for "{chip}" isn\'t connected yet'))
def step_not_connected_for_chip(page: Page, chip: str):
    # The chip's own text is in its onclick: runChip('...'). Ask the real
    # classifier what it makes of it, so this follows the classifier, not a guess.
    onclick = page.locator(".agent-chip", has_text=re.compile(f"^{re.escape(chip)}$")).get_attribute("onclick")
    text = re.search(r"runChip\('(.*)'\)", onclick).group(1)
    result = classify(text)
    card = cards(page, ".agent-result-card").last
    if result.is_unknown:
        expect(card.locator("ul li")).to_have_text(CAPABILITIES)
    else:
        expect(card).to_contain_text(f"{INTENT_LABELS[result.intent]} isn't connected yet")


# ---------------------------------------------------------------------------
# Then: forms
# ---------------------------------------------------------------------------

@then("the welcome form is shown in the Command Centre")
def step_welcome_form_shown(page: Page):
    expect(page.locator("#page-cc")).to_have_class(re.compile(r"\bactive\b"))
    expect(form(page, "welcome")).to_be_visible()


@then("the registration form is shown in the Command Centre")
def step_registration_form_shown(page: Page):
    expect(page.locator("#page-cc")).to_have_class(re.compile(r"\bactive\b"))
    expect(form(page, "register")).to_be_visible()


@then("the registration form is shown in the mobile thread")
def step_registration_form_in_mobile_thread(page: Page):
    expect(form(page, "register", mobile=True)).to_be_visible()


@then("the registration form is still open")
def step_registration_form_open(page: Page):
    expect(form(page, "register")).to_be_visible()


@then("the welcome form has no dispatch field")
def step_welcome_form_no_dispatch(page: Page):
    welcome = form(page, "welcome")
    expect(welcome.locator("[data-field=dispatch]")).to_have_count(0)
    expect(welcome).not_to_contain_text(re.compile("dispatch", re.IGNORECASE))


@then("the welcome form has collapsed")
def step_welcome_form_collapsed(page: Page):
    expect(page.locator("#agent-body [data-form=welcome]")).to_have_count(0)


@then("the registration form has collapsed")
def step_registration_form_collapsed(page: Page):
    expect(page.locator("#agent-body [data-form=register]")).to_have_count(0)


@then(parsers.parse('the "{field}" field shows the error "{message}"'))
def step_welcome_field_error(page: Page, field: str, message: str):
    expect(form(page, "welcome").locator(f"[data-err={field}]")).to_have_text(message)


@then(parsers.parse('the registration form shows the inline error "{message}" under "{field}"'))
def step_registration_field_error(page: Page, message: str, field: str):
    expect(form(page, "register").locator(f"[data-err={field}]")).to_have_text(message)


@then("the registration form's submit button is disabled")
def step_submit_disabled(page: Page):
    expect(form(page, "register").get_by_role("button", name="Register applicant")).to_be_disabled()


# ---------------------------------------------------------------------------
# Then: registration results
# ---------------------------------------------------------------------------

@then(parsers.parse('the confirmation says "{text}" with ID "{applicant_id}" and "{matches}"'))
def step_confirmation(page: Page, text: str, applicant_id: str, matches: str):
    confirmation = cards(page, ".agent-confirmation").last
    expect(confirmation).to_contain_text(text)
    expect(confirmation.locator("strong")).to_have_text(applicant_id)
    expect(confirmation).to_contain_text(matches)


@then("the welcome email preview is collapsed")
def step_preview_collapsed(page: Page):
    details = cards(page, "details").last
    expect(details.locator("summary")).to_have_text("Welcome email preview (not sent)")
    assert details.evaluate("el => el.open") is False
    expect(details.locator("div").first).not_to_be_visible()


@then(parsers.parse('the preview shows the subject "{subject}" and the text "{text}"'))
def step_preview_content(page: Page, subject: str, text: str):
    details = cards(page, "details").last
    expect(details).to_contain_text(subject)
    expect(details).to_contain_text(text)


@then("the info card says the applicant already exists and the record was left unchanged")
def step_info_card(page: Page):
    info = cards(page, ".agent-info").last
    expect(info).to_contain_text("already exists")
    expect(info).to_contain_text("left unchanged")


@then(parsers.parse('the info card has a row for "{field}" saying "{text}"'))
def step_info_row(page: Page, field: str, text: str):
    row = cards(page, ".agent-info").last.locator(f"[data-diff-field={field}]")
    expect(row).to_have_count(1)
    expect(row).to_contain_text(text)


@then(parsers.parse('an error card says "{text}"'))
def step_error_card(page: Page, text: str):
    expect(cards(page, ".agent-error").last).to_contain_text(text)


@then("the error card says what to do next")
def step_error_next(page: Page):
    expect(cards(page, ".agent-error").last).to_contain_text(re.compile("try again", re.IGNORECASE))


# ---- XSS ------------------------------------------------------------------

@then(parsers.parse('the confirmation shows the text "{text}" literally'))
def step_confirmation_literal(page: Page, text: str):
    expect(cards(page, ".agent-confirmation").last).to_contain_text(text)


@then(parsers.parse('the preview shows the text "{text}" literally'))
def step_preview_literal(page: Page, text: str):
    expect(cards(page, "details").last).to_contain_text(text)


@then("the thread contains no image, script or frame elements")
def step_no_active_elements(page: Page):
    expect(page.locator("#agent-body img, #agent-body script, #agent-body iframe, #agent-body object, #agent-body embed")).to_have_count(0)


@then("window.__xss is undefined")
def step_xss_undefined(page: Page):
    assert page.evaluate("typeof window.__xss") == "undefined"


# ---------------------------------------------------------------------------
# Then: requests, client-side smoke, mobile
# ---------------------------------------------------------------------------

@then("no POST was sent")
def step_no_post_at_all(sent_requests):
    posted = [r.path for r in sent_requests if r.method == "POST"]
    assert posted == [], f"the page sent POST {posted}"


@then(parsers.parse('the browser sent only POST "{path}"'))
def step_only_post(sent_requests, path: str):
    posted = [r.path for r in sent_requests if r.method == "POST"]
    assert posted == [path], f"POST requests were {posted}"


@then(parsers.parse('the "{tab}" tab and the "{page_id}" page are active and no other is'))
def step_tab_and_page_active(page: Page, tab: str, page_id: str):
    active_tabs = page.locator(".topbar-nav .tn.active")
    expect(active_tabs).to_have_count(1)
    expect(active_tabs).to_have_text(tab)
    active_pages = page.locator(".page.active")
    expect(active_pages).to_have_count(1)
    expect(active_pages).to_have_id(f"page-{page_id}")


@then(parsers.parse('the model label reads "{model}"'))
def step_model_label(page: Page, model: str):
    expect(page.locator("#model-label")).to_have_text(model)
    expect(page.locator(f"#mopt-{MODEL_IDS[model]}")).to_have_class(re.compile(r"\bactive\b"))


@then(parsers.parse('the agent header tag reads "{text}"'))
def step_agent_tag(page: Page, text: str):
    expect(page.locator("#agent-model-tag")).to_have_text(text)


@then("the model dropdown is closed")
def step_model_dropdown_closed(page: Page):
    expect(page.locator("#model-dropdown")).not_to_have_class(re.compile(r"\bopen\b"))


@then(parsers.parse('the user panel is open and titled "{title}"'))
def step_user_panel_open(page: Page, title: str):
    expect(page.locator("#up-overlay")).to_have_class(re.compile(r"\bopen\b"))
    expect(page.locator("#up-panel-title")).to_have_text(title)
    expect(page.locator("#up-tabs .up-tab.active")).to_have_text(title)


@then("the user panel is closed")
def step_user_panel_closed(page: Page):
    expect(page.locator("#up-overlay")).not_to_have_class(re.compile(r"\bopen\b"))


@then("the Stripe card element is empty")
def step_stripe_element_empty(page: Page):
    element = page.locator("#stripe-card-element")
    expect(element).to_be_visible()
    expect(element).to_be_empty()
    expect(page.locator("#stripe-card-error")).to_be_empty()


@then("there is no card number, expiry or CVC input anywhere in the page")
def step_no_card_inputs(page: Page):
    card_inputs = page.locator(
        "input[autocomplete^='cc-'], select[autocomplete^='cc-'], "
        "#cc-name, #cc-number, #cc-month, #cc-year, #cc-cvc, input[maxlength='19']"
    )
    expect(card_inputs).to_have_count(0)


@then(parsers.parse('the mobile thread shows a result card saying "{text}"'))
def step_mobile_result_card(page: Page, text: str):
    expect(page.locator("#mob-agent-body .agent-result-card").last).to_contain_text(text)


@then("the page has no horizontal scroll")
def step_no_horizontal_scroll(page: Page):
    widths = page.evaluate(
        "() => ({doc: document.documentElement.scrollWidth, body: document.body.scrollWidth,"
        " view: document.documentElement.clientWidth})"
    )
    assert widths["doc"] <= widths["view"] and widths["body"] <= widths["view"], widths
