
"""Centralized browser launch with deterministic fallback chain."""

from __future__ import annotations

import logging
import os
from typing import Callable, Literal


logger = logging.getLogger(__name__)

BrowserType = Literal["chromium", "chrome", "edge"]


def _chromium_kwargs(*, headless: bool) -> dict:
    return {"headless": headless}


def _msedge_kwargs(*, headless: bool) -> dict:
    return {"channel": "msedge", "headless": headless}


def _chrome_kwargs(*, headless: bool) -> dict:
    return {"channel": "chrome", "headless": headless}


_FALLBACK_CHAIN: list[tuple[str, Callable[..., dict]]] = [
    ("chromium", _chromium_kwargs),
    ("msedge", _msedge_kwargs),
    ("chrome", _chrome_kwargs),
]


def _preferred_name(browser_type: str) -> str:
    if browser_type == "edge":
        return "msedge"
    if browser_type == "chrome":
        return "chrome"
    if browser_type == "chromium":
        return "chromium"
    return "chromium"


def _reorder_chain(browser_type: str, headless: bool) -> list[tuple[str, dict]]:
    """Return fallback strategies with preferred browser first."""
    preferred = _preferred_name(browser_type)
    ordered = sorted(
        _FALLBACK_CHAIN,
        key=lambda entry: 0 if entry[0] == preferred else 1,
    )
    return [(name, builder(headless=headless)) for name, builder in ordered]


def launch_browser(pw, browser_type: BrowserType = "chromium", headless: bool = False,
                   cdp_url: str = "", verify_ssl: bool = True):
    """Launch browser with launch-chain fallback and optional CDP attempts.

    The function intentionally keeps a stable, testable launch contract:
    launch kwargs are limited to ``headless`` and optional ``channel``.
    """
    del verify_ssl  # Kept for backward-compatible signature.

    errors: list[str] = []

    env_cdp = os.environ.get("TESTFORGE_USE_CDP", "").strip()
    if env_cdp:
        try:
            return pw.chromium.connect_over_cdp(env_cdp)
        except Exception as exc:
            errors.append(f"cdp_env: {exc}")

    for name, kwargs in _reorder_chain(browser_type, headless=headless):
        try:
            browser = pw.chromium.launch(**kwargs)
            logger.info("Browser launched via %s", name)
            return browser
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    default_cdp = cdp_url or "http://localhost:9222"
    try:
        return pw.chromium.connect_over_cdp(default_cdp)
    except Exception as exc:
        errors.append(f"cdp_fallback: {exc}")

    details = "\n  ".join(errors)
    raise RuntimeError(f"All browser launch strategies failed:\n  {details}")

