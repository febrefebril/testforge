
"""TestForge — Esperas por estado assincrono de tela.

Cobre: loading/spinner central; conteudo lazy-loaded; redirecionamento;
sessao expirada; waits compostos por estado de tela.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Sequence

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


class AsyncStateError(Exception):
    """Estado assincrono nao convergiu no tempo esperado."""


class SessionExpiredError(AsyncStateError):
    """Sessao expirada detectada durante espera."""


DEFAULT_SPINNER_SELECTORS = (
    ".mat-progress-spinner", ".mat-spinner", ".cdk-overlay-backdrop-showing",
    ".ui-widget-overlay", ".ui-blockui", ".blockUI",
    ".MuiCircularProgress-root", ".MuiBackdrop-root",
    "[aria-busy='true']", ".loading", ".spinner", ".overlay-loading",
)

DEFAULT_LOGIN_MARKERS = (
    "input[type='password']", "#login", "form[action*='login']",
    "text=/sess(a|\u00e3)o expirad/i", "text=/fa(c|\u00e7)a login/i",
)


def wait_spinner_gone(page: Page, *, selectors: Sequence[str] = DEFAULT_SPINNER_SELECTORS,
                      timeout_ms: int = 30_000) -> None:
    """Aguarda todos os spinners/overlays conhecidos ficarem hidden."""
    deadline = time.time() + timeout_ms / 1000.0
    joined = ", ".join(selectors)
    while time.time() < deadline:
        try:
            loc = page.locator(joined)
            count = loc.count()
        except Exception:
            count = 0
        if count == 0:
            return
        visible = False
        for i in range(min(count, 10)):
            try:
                if loc.nth(i).is_visible():
                    visible = True
                    break
            except Exception:
                continue
        if not visible:
            return
        page.wait_for_timeout(200)
    raise AsyncStateError(f"Spinner/overlay ainda visivel apos {timeout_ms} ms.")


def wait_lazy_element(page: Page, selector: str, *, timeout_ms: int = 20_000,
                      stable_ms: int = 400) -> None:
    """Aguarda elemento lazy-loaded aparecer e estabilizar (bounding box)."""
    page.wait_for_selector(selector, state="visible", timeout=timeout_ms)
    loc = page.locator(selector).first
    last_box = None
    stable_deadline = time.time() + stable_ms / 1000.0
    hard_deadline = time.time() + timeout_ms / 1000.0
    while time.time() < hard_deadline:
        try:
            box = loc.bounding_box()
        except Exception:
            box = None
        if box is not None and box == last_box:
            if time.time() >= stable_deadline:
                return
        else:
            last_box = box
            stable_deadline = time.time() + stable_ms / 1000.0
        page.wait_for_timeout(100)


def wait_redirect(page: Page, *, url_pattern: str = "", from_url: str = "",
                  timeout_ms: int = 20_000) -> str:
    """Aguarda redirecionamento e retorna a URL final."""
    if url_pattern:
        page.wait_for_url(re.compile(url_pattern), timeout=timeout_ms)
    else:
        start = from_url or page.url
        deadline = time.time() + timeout_ms / 1000.0
        changed = False
        while time.time() < deadline:
            if page.url != start:
                changed = True
                break
            page.wait_for_timeout(150)
        if not changed:
            raise AsyncStateError(f"Sem redirecionamento a partir de {start}.")
    page.wait_for_load_state("domcontentloaded")
    return page.url


def detect_session_expired(page: Page, *, login_markers: Sequence[str] = DEFAULT_LOGIN_MARKERS,
                           login_url_hint: str = "login") -> bool:
    """True se a tela atual indica sessao expirada/tela de login."""
    if login_url_hint and login_url_hint.lower() in (page.url or "").lower():
        return True
    for marker in login_markers:
        try:
            loc = page.locator(marker)
            if loc.count() and loc.first.is_visible():
                return True
        except Exception:
            continue
    return False


def wait_screen_ready(page: Page, *, ready_selector: str = "",
                      spinner_selectors: Sequence[str] = DEFAULT_SPINNER_SELECTORS,
                      check_session: bool = True, timeout_ms: int = 30_000) -> None:
    """Espera composta: networkidle -> spinner some -> ancora visivel."""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except PlaywrightTimeout:
        logger.debug("networkidle nao atingido; seguindo demais checagens.")
    if check_session and detect_session_expired(page):
        raise SessionExpiredError("Sessao expirada detectada em wait_screen_ready.")
    wait_spinner_gone(page, selectors=spinner_selectors, timeout_ms=timeout_ms)
    if ready_selector:
        page.wait_for_selector(ready_selector, state="visible", timeout=timeout_ms)

