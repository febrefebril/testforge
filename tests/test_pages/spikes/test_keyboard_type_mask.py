"""Spike (2026-06-27): does page.keyboard.type() trigger a JS currency mask?

Background: see .planning/spikes/SPIKE-keyboard-type-mask.md.

Goal: decide whether recorder can stop intercepting HTMLInputElement value
setter and instead rely on keystroke events + final_state snapshot.

Probes three APIs against the same currency-mask fixture; asserts the
DOM-visible value.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

PAGE_URI = Path(
    "tests/intent_lab/pages/currency-mask/index.html"
).absolute().as_uri()


def _probe(api: str) -> str:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_context().new_page()
        page.goto(PAGE_URI)
        loc = page.locator("#valor")
        if api == "fill":
            loc.fill("1000")
        elif api == "press_sequentially":
            loc.click()
            loc.press_sequentially("1000", delay=10)
        elif api == "keyboard.type":
            loc.click()
            page.keyboard.type("1000")
        else:
            raise ValueError(api)
        value = page.evaluate("document.getElementById('valor').value")
        browser.close()
        return value


@pytest.mark.parametrize("api,expected_pattern", [
    ("fill", ""),                # unknown, asserted descriptive
    ("press_sequentially", ""),
    ("keyboard.type", ""),
])
def test_currency_mask_probe(api, expected_pattern):
    """Pin: which API surfaces the masked value? Spike artifact, no assertion
    on a specific value — the output is the data, captured in the docstring
    of the spike file."""
    value = _probe(api)
    print(f"[SPIKE] api={api!r} dom_value={value!r}")
    # No hard assertion: this is exploratory. The value is logged so the
    # spike doc can record it. If we ever delete the spike, also delete
    # this test.
    assert value is not None
