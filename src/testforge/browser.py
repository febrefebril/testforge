"""Centralized browser launch with fallback chain for corporate environments.

Fallback chain: chromium -> channel=msedge -> channel=chrome -> connect_over_cdp
Use --browser edge|chrome|chromium to set preferred browser (reorders chain).
"""
from __future__ import annotations

import logging
from typing import Literal

from playwright.sync_api import Browser, Playwright

logger = logging.getLogger(__name__)

BrowserType = Literal["chromium", "chrome", "edge"]

# Ordered fallback strategies: (name, launch_kwargs_builder)
_FALLBACK_CHAIN: list[tuple[str, callable]] = [
    ("chromium", lambda headless: {"headless": headless}),
    ("msedge", lambda headless: {"channel": "msedge", "headless": headless}),
    ("chrome", lambda headless: {"channel": "chrome", "headless": headless}),
]


def _reorder_chain(preferred: BrowserType, headless: bool) -> list[tuple[str, dict]]:
    """Reorder fallback chain so preferred browser is tried first."""
    strategies = [
        (name, builder(headless)) for name, builder in _FALLBACK_CHAIN
    ]
    preferred_map = {
        "chromium": "chromium",
        "chrome": "chrome",
        "edge": "msedge",
    }
    target_name = preferred_map.get(preferred, "chromium")

    # Find preferred strategy and move it to front
    for i, (name, _) in enumerate(strategies):
        if name == target_name:
            strategies.insert(0, strategies.pop(i))
            break

    return strategies


def launch_browser(
    pw: Playwright,
    browser_type: BrowserType = "chromium",
    headless: bool = False,
    cdp_url: str = "http://localhost:9222",
) -> Browser:
    """Launch browser with fallback chain for corporate environments.

    Tries each strategy in order:
    1. Preferred browser (from --browser flag)
    2. Remaining browsers from fallback chain
    3. connect_over_cdp as last resort

    Args:
        pw: Playwright instance
        browser_type: Preferred browser ("chromium", "chrome", "edge")
        headless: Run in headless mode
        cdp_url: CDP endpoint for connect_over_cdp fallback

    Returns:
        Launched Browser instance

    Raises:
        RuntimeError: If all launch strategies fail
    """
    strategies = _reorder_chain(browser_type, headless)
    errors: list[str] = []

    for name, kwargs in strategies:
        try:
            logger.info(f"Launching browser: {name} kwargs={kwargs}")
            browser = pw.chromium.launch(**kwargs)
            logger.info(f"Browser launched successfully via {name}")
            return browser
        except Exception as exc:
            err_msg = f"{name}: {exc}"
            errors.append(err_msg)
            logger.warning(f"Browser launch failed: {err_msg}")

    # Last resort: connect to existing browser via CDP
    try:
        logger.info(f"Connecting via CDP: {cdp_url}")
        browser = pw.chromium.connect_over_cdp(cdp_url)
        logger.info("Browser connected via CDP")
        return browser
    except Exception as exc:
        errors.append(f"cdp ({cdp_url}): {exc}")
        logger.error(f"CDP connection failed: {exc}")

    raise RuntimeError(
        f"All browser launch strategies failed:\n  " + "\n  ".join(errors)
    )
