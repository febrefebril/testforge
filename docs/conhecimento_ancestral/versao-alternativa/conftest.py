"""
TestForge — conftest.py
Shared pytest fixtures for all generated tests.
"""
import pytest
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext


@pytest.fixture(scope="session")
def browser_instance():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def context(browser_instance: Browser):
    ctx: BrowserContext = browser_instance.new_context(
        viewport={"width": 1280, "height": 800},
        locale="pt-BR",
    )
    yield ctx
    ctx.close()


@pytest.fixture(scope="function")
def page(context: BrowserContext) -> Page:
    p = context.new_page()
    yield p
    p.close()
