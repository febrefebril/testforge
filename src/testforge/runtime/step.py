"""Phase 3: High-level step API consumed by compiled tests.

Compiled v2 tests are minimal:

    from testforge.runtime import step

    def test_login(page):
        step.go(page, "http://localhost:8765")
        step.click(page, intent='click button "Login"',
                   candidates_file="step_001.json")
        step.fill(page, intent='fill textbox "Email"',
                  value="alice@example.com",
                  candidates_file="step_002.json")
        step.assert_text(page, intent='assert text "Welcome"',
                         expected="Welcome",
                         candidates_file="step_003.json")

The fallback chain is entirely in the runtime — changing strategy
does NOT require recompiling tests.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from .errors import StepExecutionError
from .resolver import LocatorResolver

logger = logging.getLogger(__name__)

# Module-level resolver cache keyed by page id. Tests rarely share pages,
# but the per-page cache lets `step.click(page, ...)` work without an
# explicit setup call.
_resolvers: dict[int, LocatorResolver] = {}


def _resolver_for(page) -> LocatorResolver:
    key = id(page)
    r = _resolvers.get(key)
    if r is None:
        r = LocatorResolver(page)
        _resolvers[key] = r
    return r


def _resolve_path(candidates_file: str) -> str:
    """Resolve a candidates_file path relative to caller's script dir.

    Compiled tests pass relative paths like "step_001.json". The runtime
    resolves them against the test script's directory.
    """
    if os.path.isabs(candidates_file):
        return candidates_file
    # Walk back through frames to find the calling test file
    import inspect
    for frame in inspect.stack()[2:]:
        fname = frame.filename
        if fname and os.path.basename(fname).startswith("test_") and fname.endswith(".py"):
            return os.path.join(os.path.dirname(fname), candidates_file)
    return candidates_file


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------

def go(page, url: str) -> None:
    """Navigate to URL. Simple wrapper kept for parity with other step.* helpers."""
    page.goto(url)


def click(page, intent: str, candidates_file: str = "",
          candidates: Optional[list[dict]] = None,
          timeout_ms: int = 5000) -> None:
    """Resolve `intent` to a Locator and click it."""
    locator, _ = _do_resolve(page, intent, candidates_file, candidates)
    try:
        locator.click(timeout=timeout_ms)
        page.wait_for_timeout(200)
    except Exception as exc:
        raise StepExecutionError(intent, "click", str(exc)) from exc


def fill(page, intent: str, value: str, candidates_file: str = "",
         candidates: Optional[list[dict]] = None,
         timeout_ms: int = 5000) -> None:
    """Resolve `intent` and fill it with `value`."""
    locator, result = _do_resolve(page, intent, candidates_file, candidates)
    try:
        locator.fill(value, timeout=timeout_ms)
        # Press Tab for real-keyboard blur — Angular Zone.js requirement.
        try:
            locator.first.press("Tab")
        except Exception:
            try:
                page.keyboard.press("Tab")
            except Exception:
                pass
        page.wait_for_timeout(200)
    except Exception as exc:
        raise StepExecutionError(intent, "fill", str(exc)) from exc


def select(page, intent: str, value: str, candidates_file: str = "",
           candidates: Optional[list[dict]] = None,
           timeout_ms: int = 5000) -> None:
    """Resolve `intent` and select an option from a <select> or combobox."""
    locator, _ = _do_resolve(page, intent, candidates_file, candidates)
    try:
        locator.select_option(value, timeout=timeout_ms)
        page.wait_for_timeout(200)
    except Exception as exc:
        raise StepExecutionError(intent, "select_option", str(exc)) from exc


def assert_text(page, intent: str, expected: str, candidates_file: str = "",
                candidates: Optional[list[dict]] = None,
                timeout_ms: int = 10000) -> None:
    """Resolve `intent`, wait for visible, and assert the element contains `expected`."""
    locator, _ = _do_resolve(page, intent, candidates_file, candidates)
    locator.first.wait_for(state="visible", timeout=timeout_ms)
    actual = locator.first.text_content(timeout=3000) or ""
    if expected.lower() not in actual.lower():
        raise AssertionError(
            f'assert_text: intent="{intent}" expected="{expected}" got="{actual[:80]}"'
        )


def assert_visible(page, intent: str, candidates_file: str = "",
                   candidates: Optional[list[dict]] = None,
                   timeout_ms: int = 10000) -> None:
    """Resolve `intent` and assert the element is visible."""
    locator, _ = _do_resolve(page, intent, candidates_file, candidates)
    locator.first.wait_for(state="visible", timeout=timeout_ms)


def _do_resolve(page, intent: str, candidates_file: str,
                inline_candidates: Optional[list[dict]]):
    """Internal: route to LocatorResolver, return (locator, result)."""
    resolver = _resolver_for(page)
    if inline_candidates is not None:
        result = resolver.resolve(intent, inline_candidates)
    else:
        path = _resolve_path(candidates_file)
        result = resolver.resolve_from_file(path, intent)
    return result.locator, result
