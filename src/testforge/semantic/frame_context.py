
"""TestForge — Resolucao de contexto de pagina/frame.

Resolve o escopo correto (Page, Frame ou FrameLocator) onde uma acao deve
ser executada, cobrindo: frame_locator; iframe same-origin; iframe
cross-origin como LIMITACAO EXPLICITA; nova aba (page popup); popup
(window.open).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from playwright.sync_api import (
    Page, Frame, FrameLocator, BrowserContext,
    Error as PlaywrightError, TimeoutError as PlaywrightTimeout,
)

logger = logging.getLogger(__name__)


class FrameContextError(Exception):
    """Erro ao resolver contexto de frame/pagina."""


@dataclass
class FrameResolution:
    kind: str
    selector: str = ""
    url: str = ""
    cross_origin: bool = False
    warnings: list = field(default_factory=list)
    scope: object = None


def _page_origin(page: Page) -> str:
    try:
        return page.evaluate("() => location.origin")
    except Exception:
        return ""


def resolve_frame_locator(page: Page, iframe_selector: str) -> FrameLocator:
    """FrameLocator deterministico (lazy) para o <iframe> informado."""
    if not iframe_selector:
        raise FrameContextError("iframe_selector vazio para frame_locator.")
    return page.frame_locator(iframe_selector)


def resolve_same_origin_frame(page: Page, *, name: str = "",
                              url_contains: str = "",
                              timeout_ms: int = 10_000) -> Frame:
    """Resolve um Frame same-origin por name ou por trecho de URL."""
    deadline = time.time() + timeout_ms / 1000.0
    while time.time() < deadline:
        for fr in page.frames:
            if name and fr.name == name:
                return fr
            if url_contains and url_contains in (fr.url or ""):
                return fr
        page.wait_for_timeout(200)
    raise FrameContextError(
        f"Frame same-origin nao encontrado (name={name!r}, url_contains={url_contains!r})."
    )


def classify_iframe(page: Page, iframe_selector: str) -> FrameResolution:
    """Classifica <iframe> como same-origin ou cross-origin (limitacao)."""
    res = FrameResolution(kind="iframe_same_origin", selector=iframe_selector)
    try:
        handle = page.wait_for_selector(iframe_selector, timeout=10_000)
    except PlaywrightTimeout as e:
        raise FrameContextError(f"iframe nao encontrado: {iframe_selector!r}") from e

    frame = handle.content_frame()
    parent_origin = _page_origin(page)
    if frame is None:
        res.kind = "iframe_cross_origin"
        res.cross_origin = True
        res.scope = page.frame_locator(iframe_selector)
        res.warnings.append(
            "iframe cross-origin (OOPIF): content_frame indisponivel. "
            "Use apenas acoes via frame_locator; leitura de DOM/JS nao suportada."
        )
        logger.warning("iframe cross-origin detectado: %s", iframe_selector)
        return res

    res.url = frame.url or ""
    try:
        frame_origin = frame.evaluate("() => location.origin")
    except PlaywrightError:
        frame_origin = ""

    if frame_origin and parent_origin and frame_origin != parent_origin:
        res.kind = "iframe_cross_origin"
        res.cross_origin = True
        res.warnings.append(
            f"iframe cross-origin: origem {frame_origin} difere de {parent_origin}. "
            f"LIMITACAO: sem acesso a DOM/JS/storage cross-origin. "
            f"Acoes possiveis via frame_locator."
        )
        logger.warning("iframe cross-origin: %s vs %s", frame_origin, parent_origin)
        res.scope = page.frame_locator(iframe_selector)
    else:
        res.scope = frame
    return res


def open_new_tab(context: BrowserContext, trigger, *, timeout_ms: int = 15_000) -> Page:
    """Executa trigger() e captura a nova aba aberta no contexto."""
    with context.expect_page(timeout=timeout_ms) as info:
        trigger()
    new_page = info.value
    new_page.wait_for_load_state("domcontentloaded")
    return new_page


def open_popup(page: Page, trigger, *, timeout_ms: int = 15_000) -> Page:
    """Executa trigger() e captura um popup (window.open) da pagina."""
    with page.expect_popup(timeout=timeout_ms) as info:
        trigger()
    popup = info.value
    popup.wait_for_load_state("domcontentloaded")
    return popup

