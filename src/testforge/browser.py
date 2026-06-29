"""Centralized browser launcher with CDP-first fallback."""
from __future__ import annotations
import logging
import os
import platform
from typing import Literal

from playwright.sync_api import Browser, Playwright

logger = logging.getLogger(__name__)

BrowserType = Literal["chromium", "chrome", "edge"]

_WINDOWS_GPU_ARGS = [
    "--use-angle=d3d11",
    "--enable-features=Vulkan,UseSkiaRenderer",
    "--ignore-gpu-blocklist",
    "--disable-gpu-sandbox",
    "--window-size=1280,720",
    "--no-first-run",
    "--no-default-browser-check",
]


def _is_windows():
    return platform.system() == "Windows"


def _gpu_args(headless=False):
    if not _is_windows():
        return []
    args = list(_WINDOWS_GPU_ARGS)
    if not headless:
        # modo headed: remove --window-size para evitar flicker
        args = [a for a in args if not a.startswith("--window-size")]
    return args


def launch_browser(pw, browser_type="chromium", headless=False, cdp_url="", verify_ssl=True):
    errors = []

        # P1: CDP via ENV
    env_cdp = os.environ.get("TESTFORGE_USE_CDP", "").strip()
    if env_cdp:
        try:
            browser = pw.chromium.connect_over_cdp(env_cdp, timeout=10000)
            logger.info(f"[OK] Navegador CDP env ({env_cdp})")
            return browser
        except Exception as e:
            errors.append(f"cdp_env: {e}")

        # P2: CDP via param
    if cdp_url:
        try:
            browser = pw.chromium.connect_over_cdp(cdp_url, timeout=10000)
            return browser
        except Exception as e:
            errors.append(f"cdp_param: {e}")

    gpu_args = _gpu_args(headless=headless)
    ssl_args = [] if verify_ssl else ["--ignore-certificate-errors"]
    launch_args = gpu_args + ssl_args

    if _is_windows() and browser_type in ("chromium", "edge"):
        strategies = [
            ("msedge", {"channel": "msedge", "headless": headless, "args": launch_args}),
            ("chrome", {"channel": "chrome", "headless": headless, "args": launch_args}),
            ("chromium", {"headless": headless, "args": launch_args}),
        ]
    elif browser_type == "chrome":
        strategies = [
            ("chrome", {"channel": "chrome", "headless": headless, "args": launch_args}),
            ("msedge", {"channel": "msedge", "headless": headless, "args": launch_args}),
            ("chromium", {"headless": headless, "args": launch_args}),
        ]
    elif browser_type == "edge":
        strategies = [
            ("msedge", {"channel": "msedge", "headless": headless, "args": launch_args}),
            ("chrome", {"channel": "chrome", "headless": headless, "args": launch_args}),
            ("chromium", {"headless": headless, "args": launch_args}),
        ]
    else:
        strategies = [
            ("chromium", {"headless": headless, "args": launch_args}),
            ("msedge", {"channel": "msedge", "headless": headless, "args": launch_args}),
            ("chrome", {"channel": "chrome", "headless": headless, "args": launch_args}),
        ]

    for name, kwargs in strategies:
        try:
            browser = pw.chromium.launch(**kwargs)
            logger.info(f"[OK] Navegador via {name}")
            return browser
        except Exception as e:
            errors.append(f"{name}: {e}")

    default_cdp = cdp_url or "http://localhost:9222"
    try:
        return pw.chromium.connect_over_cdp(default_cdp, timeout=5000)
    except Exception as e:
        errors.append(f"cdp_fallback: {e}")

    raise RuntimeError("Todas as estratégias de navegador falharam:\n  " + "\n  ".join(errors))
