"""H22 — Spike against a real-shape Material currencymask fixture.

Closes the gap left by SPIKE-keyboard-type-mask.md (vanilla mask did not
reproduce SIOPI's failure mode).

Two distinct questions:

* Q1 (Replay): when replay runs page.fill / press_sequentially /
  keyboard.type against an input with a per-instance value setter
  override, does the field end up with the correct masked value?

* Q2 (Record): if the overlay JS hooks HTMLInputElement.prototype.value
  setter (the way overlay_inject.js does), does it observe writes that
  happen through the per-instance override that ng2-currency-mask uses?

Q2 answers the kill-list in SPIKE-keyboard-type-mask.md: if the
prototype hook can't see writes, then the setter-hook capture pipeline
is structurally broken on Material masks regardless of any other fix.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import sync_playwright

PAGE_URI = Path(
    "tests/intent_lab/pages/material-currencymask/index.html"
).absolute().as_uri()


def _new_page(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_context().new_page()
    page.goto(PAGE_URI)
    return browser, page


def _install_prototype_hook(page) -> None:
    """Mimic overlay_inject.js _hookValue. Run BEFORE the page's own
    instance override; per-instance defineProperty shadows this hook,
    which is exactly the failure mode we want to expose."""
    page.evaluate("""() => {
        window.__captured = [];
        const proto = HTMLInputElement.prototype;
        const orig = Object.getOwnPropertyDescriptor(proto, 'value');
        Object.defineProperty(proto, 'value', {
            configurable: true,
            get: orig.get,
            set: function(v) {
                orig.set.call(this, v);
                window.__captured.push({
                    id: this.id || '',
                    name: this.name || '',
                    value: String(v).substring(0, 200),
                });
            },
        });
    }""")


def _captured(page) -> list[dict[str, Any]]:
    return page.evaluate("window.__captured || []") or []


def _internal_state(page, sel: str) -> dict[str, str]:
    """Reads the internal raw + display state through the diagnostic
    helpers the fixture exposes (input._tf_internal_raw, _display)."""
    return page.evaluate(
        f"""() => {{
            const el = document.querySelector({sel!r});
            return {{
                value: el.value,
                raw: el._tf_internal_raw ? el._tf_internal_raw() : '',
                display: el._tf_internal_display ? el._tf_internal_display() : '',
            }};
        }}"""
    )


# ----- Q1: REPLAY -----------------------------------------------------------


@pytest.mark.parametrize("api,expect_empty", [
    ("fill", True),                  # documented broken on instance override
    ("press_sequentially", False),
    ("keyboard.type", False),
])
def test_q1_replay_produces_masked_value(api, expect_empty):
    """When test runs an action against a Material-style mask, does the
    field end up with the correct formatted value?

    Pins the spike result: fill() fails on the per-instance override
    pattern (matches the hotfix 16 failure mode). press_sequentially and
    keyboard.type both work."""
    with sync_playwright() as pw:
        browser, page = _new_page(pw)
        loc = page.locator("#valor_imovel")
        if api == "fill":
            loc.fill("1000000")
        elif api == "press_sequentially":
            loc.click()
            loc.press_sequentially("1000000", delay=10)
        elif api == "keyboard.type":
            loc.click()
            page.keyboard.type("1000000")
        state = _internal_state(page, "#valor_imovel")
        browser.close()
    print(f"[Q1] api={api!r} state={state!r}")
    if expect_empty:
        # Documented failure mode — the spike answer is that fill() ends
        # in an unexpected empty state on this mask shape.
        assert state["value"] == "", (
            f"fill() now works on instance-override mask. Update the "
            f"spike doc — this changes the kill-list. Got: {state}"
        )
    else:
        assert state["value"] == "10.000,00", (
            f"Expected mask to format 1000000 as '10.000,00' via {api}, "
            f"got: {state}"
        )


# ----- Q2: RECORD -----------------------------------------------------------


def test_q2_prototype_hook_capture_pattern():
    """Real result: hook catches mask writes (because our fixture's mask
    delegates to the prototype setter when rendering display) but misses
    real keyboard typing on a plain input (browser-native typing bypasses
    the value setter entirely).

    The plain-input gap is the structural failure mode that
    `value_mutations.jsonl` cannot fix on its own.
    """
    with sync_playwright() as pw:
        browser, page = _new_page(pw)
        _install_prototype_hook(page)
        page.locator("#valor_imovel").click()
        page.keyboard.type("1000")
        captured_masked = _captured(page)
        page.locator("#plain").click()
        page.keyboard.type("hello")
        captured_after_plain = _captured(page)
        browser.close()

    masked_writes = [c for c in captured_after_plain if c["id"] == "valor_imovel"]
    plain_writes = [c for c in captured_after_plain if c["id"] == "plain"]
    print(f"[Q2] masked write count: {len(masked_writes)}")
    print(f"[Q2] plain write count:  {len(plain_writes)}")
    # Documented: real typing on a plain input never fires the value
    # setter, so value_mutations.jsonl will be empty for it. This is the
    # gap H22a / H22b will close via final_state + keystroke aggregation.
    assert len(plain_writes) == 0, (
        "Real keyboard typing on a plain input now fires the value "
        "setter. That changes the failure model — update the spike doc."
    )
    # The mask path delegates to the prototype setter, so the hook
    # catches those writes (one per digit, 4 total for "1000").
    assert len(masked_writes) >= 1, (
        "The fixture's mask delegates to the prototype setter; the hook "
        "should have caught at least one write. Got 0."
    )
