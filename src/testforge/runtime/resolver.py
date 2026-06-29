"""Phase 3+4: LocatorResolver — cadeia de fallback em runtime (substitui try/except fixo).

Le candidatos locator de arquivo JSON (um por step) e resolve
para um `Locator` Playwright usando cadeia L0→L1:

    L0   cache hit por intent                      ~1 ms
         - dict em memoria (Phase 3)
         - SQLite IntentCatalog persistente (Phase 4, opt-in)
    L1   percorre candidatos por score, primeiro hit vence    ~50-2000 ms

L2 (agentes especialistas) e L3 (LLM) permanecem no fallback_runner legado
por enquanto e serao plugados aqui em uma fase posterior. O resolver foca
em produzir um Locator funcional da lista de candidatos super-selector v2
e persistir o que funcionou.
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

from ._pw_dispatch import dispatch
from .errors import LocatorNotFoundError

logger = logging.getLogger(__name__)

# Per-candidate timeout when probing. Keep low so the chain finishes fast.
DEFAULT_PROBE_TIMEOUT_MS = 1500


@dataclass
class ResolveResult:
    """Outcome of a resolve() call — locator plus diagnostics."""
    locator: object
    strategy: str
    score: float
    intent: str
    level: str  # "L0_cache" | "L1_candidate"
    elapsed_ms: float
    candidate_index: int = -1
    attempted: list = field(default_factory=list)


class LocatorResolver:
    """Resolve a intent de um step para um Locator Playwright vivo.

    Nao thread-safe; um resolver por processo de teste. O cache e apenas
    em memoria aqui; Phase 4 persistira para SQLite.
    """

    def __init__(self, page, probe_timeout_ms: int = DEFAULT_PROBE_TIMEOUT_MS,
                 sqlite_catalog: Optional[object] = None) -> None:
        self._page = page
        self._probe_timeout_ms = probe_timeout_ms
        # intent -> winning candidate dict (in-memory; per-test-process)
        self._cache: dict[str, dict] = {}
        # Optional persistent SQLite intent catalog (Phase 4).
        # Duck-typed: anything with lookup/record_success methods works.
        self._sqlite = sqlite_catalog

    # ------------------------------------------------------------------
    def _current_url(self) -> str:
        try:
            return self._page.url
        except Exception:
            return ""

    # ------------------------------------------------------------------
    def resolve_from_file(self, candidates_path: str, intent: str) -> ResolveResult:
        """Carrega candidatos de um arquivo JSON e resolve."""
        candidates = self._load(candidates_path)
        return self.resolve(intent, candidates)

    def resolve(self, intent: str, candidates: list[dict],
                action: str = "click") -> ResolveResult:
        """Tenta cache L0 (memoria depois SQLite), depois candidatos em ordem."""
        from ..metrics.telemetry import get_tracer
        tracer = get_tracer()
        with tracer.start_span("resolve") as span:
            span.set_attribute("intent_text", intent)
            span.set_attribute("action", action)
            span.set_attribute("candidate_count", len(candidates))
            try:
                result = self._resolve_impl(intent, candidates, action)
                span.set_attribute("level", result.level)
                span.set_attribute("strategy", result.strategy)
                span.set_attribute("score", result.score)
                span.set_attribute("candidate_index", result.candidate_index)
                span.set_attribute("elapsed_ms", result.elapsed_ms)
                return result
            except LocatorNotFoundError as exc:
                span.set_attribute("level", "FAILED")
                span.set_attribute("attempted_count", len(getattr(exc, "candidates", []) or []))
                raise

    def _resolve_impl(self, intent: str, candidates: list[dict],
                      action: str) -> ResolveResult:
        t0 = time.perf_counter()
        attempted: list[str] = []
        last_error = ""
        url = self._current_url()

        # L0a: cache hit em memoria (por processo de teste)
        cached = self._cache.get(intent)
        if cached:
            try:
                locator = self._build(cached)
                if self._exists(locator):
                    elapsed = (time.perf_counter() - t0) * 1000
                    logger.info("L0 cache memoria hit intent=%s strategy=%s elapsed=%.1fms",
                                 intent, cached.get("strategy"), elapsed)
                    return ResolveResult(
                        locator=locator,
                        strategy=cached.get("strategy", "cached"),
                        score=cached.get("score", 0.0),
                        intent=intent,
                        level="L0_cache",
                        elapsed_ms=elapsed,
                        attempted=["L0_mem_hit"],
                    )
            except Exception as exc:
                last_error = str(exc)
                attempted.append("L0_mem_miss")
                self._cache.pop(intent, None)

        # L0b: cache persistente SQLite (entre execucoes)
        if self._sqlite is not None:
            try:
                row = self._sqlite.lookup(intent, url, action)
                if row and row.resolved_call:
                    cand = {
                        "strategy": "sqlite_cached",
                        "playwright_call": row.resolved_call,
                        "selector": row.resolved_selector or f"page.{row.resolved_call}",
                        "score": row.confidence,
                    }
                    try:
                        locator = self._build(cand)
                        if self._exists(locator):
                            self._cache[intent] = cand
                            elapsed = (time.perf_counter() - t0) * 1000
                            logger.info("L0 sqlite hit intent=%s call=%s elapsed=%.1fms",
                                         intent, row.resolved_call, elapsed)
                            return ResolveResult(
                                locator=locator,
                                strategy="sqlite_cached",
                                score=row.confidence,
                                intent=intent,
                                level="L0_cache",
                                elapsed_ms=elapsed,
                                attempted=["L0_sqlite_hit"],
                            )
                    except Exception as exc:
                        last_error = str(exc)
                        attempted.append("L0_sqlite_miss")
                        try:
                            self._sqlite.record_failure(intent, url, action)
                        except Exception:
                            pass
            except Exception as exc:
                logger.debug("SQLite lookup falhou (nao-fatal): %s", exc)

        # L1: percorre candidatos por score, retorna primeiro hit
        for idx, c in enumerate(candidates):
            strategy = c.get("strategy", "?")
            attempted.append(f"L1_{strategy}")
            try:
                locator = self._build(c)
                if self._exists(locator):
                    self._cache[intent] = c
                    if self._sqlite is not None:
                        try:
                            self._sqlite.record_success(
                                intent_text=intent, url=url, action=action,
                                resolved_call=c.get("playwright_call", ""),
                                resolved_selector=c.get("selector", ""),
                                attributes_at_record=c.get("attribute_stability"),
                            )
                        except Exception as exc:
                            logger.debug("SQLite record_success falhou: %s", exc)
                    elapsed = (time.perf_counter() - t0) * 1000
                    logger.info(
                        "L1 hit intent=%s strategy=%s score=%.2f idx=%d elapsed=%.1fms",
                        intent, strategy, c.get("score", 0.0), idx, elapsed,
                    )
                    return ResolveResult(
                        locator=locator,
                        strategy=strategy,
                        score=c.get("score", 0.0),
                        intent=intent,
                        level="L1_candidate",
                        elapsed_ms=elapsed,
                        candidate_index=idx,
                        attempted=attempted,
                    )
            except Exception as exc:
                last_error = str(exc)
                continue

        elapsed = (time.perf_counter() - t0) * 1000
        logger.warning("Resolve FALHOU intent=%s attempted=%s elapsed=%.1fms",
                        intent, attempted, elapsed)
        raise LocatorNotFoundError(intent, candidates, last_error)

    # ------------------------------------------------------------------
    def _build(self, candidate: dict):
        """Converte um dict candidato em um Locator Playwright."""
        call = candidate.get("playwright_call")
        if call:
            return dispatch(self._page, call)
        # Fallback: CSS selector via page.locator()
        sel = candidate.get("selector", "")
        if not sel:
            raise ValueError("candidate has neither playwright_call nor selector")
        # Remove o prefixo "page." que v2 emite por simetria com playwright_call.
        if sel.startswith("page."):
            return dispatch(self._page, sel[len("page."):])
        return self._page.locator(sel)

    def _exists(self, locator) -> bool:
        """Retorna True se o locator resolve para pelo menos um elemento."""
        try:
            return locator.count() > 0
        except Exception:
            return False

    def _load(self, candidates_path: str) -> list[dict]:
        if not os.path.exists(candidates_path):
            raise FileNotFoundError(f"Arquivo de candidatos nao encontrado: {candidates_path}")
        with open(candidates_path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "candidates" in data:
            return data["candidates"]
        raise ValueError(f"unexpected candidates schema in {candidates_path}")

    # ------------------------------------------------------------------
    def cache_size(self) -> int:
        """Retorna tamanho do cache em memoria."""
        return len(self._cache)

    def clear_cache(self) -> None:
        """Limpa o cache em memoria."""
        self._cache.clear()
