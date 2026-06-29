"""Phase 3: API de alto nivel para steps consumida por testes compilados.

Testes compilados v2 sao minimos:

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

A cadeia de fallback esta inteiramente no runtime — mudar estrategia
NAO requer recompilar os testes.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from .errors import StepExecutionError
from .resolver import LocatorResolver

logger = logging.getLogger(__name__)

# Cache de resolver em nivel de modulo indexado por id de pagina. Testes raramente compartilham paginas,
# mas o cache por pagina permite que `step.click(page, ...)` funcione sem uma
# chamada de setup explicita.
_resolvers: dict[int, LocatorResolver] = {}


def _resolver_for(page) -> LocatorResolver:
    """Retorna ou cria um LocatorResolver para a pagina dada."""
    key = id(page)
    r = _resolvers.get(key)
    if r is None:
        r = LocatorResolver(page)
        _resolvers[key] = r
    return r


def _resolve_path(candidates_file: str) -> str:
    """Resolve um caminho candidates_file relativo ao diretorio do script chamador.

    Testes compilados passam caminhos relativos como "step_001.json". O runtime
    resolve contra o diretorio do script de teste.
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
# API Publica
# ----------------------------------------------------------------------

def go(page, url: str) -> None:
    """Navega para URL. Wrapper simples mantido por paridade com outros helpers step.*."""
    page.goto(url)


def click(page, intent: str, candidates_file: str = "",
          candidates: Optional[list[dict]] = None,
          timeout_ms: int = 5000) -> None:
    """Resolve `intent` para um Locator e clica nele."""
    from ..metrics.telemetry import get_tracer
    with get_tracer().start_span("step.click") as span:
        span.set_attribute("intent_text", intent)
        locator, _ = _do_resolve(page, intent, candidates_file, candidates)
        try:
            locator.click(timeout=timeout_ms)
            page.wait_for_timeout(200)
        except Exception as exc:
            raise StepExecutionError(intent, "click", str(exc)) from exc


def fill(page, intent: str, value: str, candidates_file: str = "",
         candidates: Optional[list[dict]] = None,
         timeout_ms: int = 5000) -> None:
    """Resolve `intent` e preenche com `value`."""
    from ..metrics.telemetry import get_tracer
    with get_tracer().start_span("step.fill") as span:
        span.set_attribute("intent_text", intent)
        locator, result = _do_resolve(page, intent, candidates_file, candidates)
        try:
            locator.fill(value, timeout=timeout_ms)
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
    """Resolve `intent` e seleciona uma opcao de um <select> ou combobox."""
    from ..metrics.telemetry import get_tracer
    with get_tracer().start_span("step.select") as span:
        span.set_attribute("intent_text", intent)
        locator, _ = _do_resolve(page, intent, candidates_file, candidates)
        try:
            locator.select_option(value, timeout=timeout_ms)
            page.wait_for_timeout(200)
        except Exception as exc:
            raise StepExecutionError(intent, "select_option", str(exc)) from exc


def assert_text(page, intent: str, expected: str, candidates_file: str = "",
                candidates: Optional[list[dict]] = None,
                timeout_ms: int = 10000) -> None:
    """Resolve `intent`, aguarda visivel, e verifica se o elemento contem `expected`."""
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
    """Resolve `intent` e verifica se o elemento esta visivel."""
    locator, _ = _do_resolve(page, intent, candidates_file, candidates)
    locator.first.wait_for(state="visible", timeout=timeout_ms)


def _do_resolve(page, intent: str, candidates_file: str,
                inline_candidates: Optional[list[dict]]):
    """Interno: roteia para LocatorResolver, retorna (locator, result)."""
    resolver = _resolver_for(page)
    if inline_candidates is not None:
        result = resolver.resolve(intent, inline_candidates)
    else:
        path = _resolve_path(candidates_file)
        result = resolver.resolve_from_file(path, intent)
    return result.locator, result
