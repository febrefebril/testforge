"""Phase 3: LocatorResolver — runtime fallback chain (replaces hard-coded try/except).

Reads candidate locators from a JSON file (one per step) and resolves
to a Playwright `Locator` using an L0→L1 chain:

    L0   intent-keyed cache hit                      ~1 ms
    L1   walk candidates by score, first hit wins    ~50-2000 ms

L2 (specialist agents) and L3 (LLM) are wired into the legacy
fallback_runner today and will be plugged here in Phase 4 when the
catalog migrates to SQLite. For now the resolver focuses on producing
a working Locator from the v2 super-selector candidate list.
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
    """Resolves a step's intent to a live Playwright Locator.

    Thread-unsafe; one resolver per test process. The cache is in-memory
    only here; Phase 4 will persist it to SQLite.
    """

    def __init__(self, page, probe_timeout_ms: int = DEFAULT_PROBE_TIMEOUT_MS) -> None:
        self._page = page
        self._probe_timeout_ms = probe_timeout_ms
        # intent -> winning candidate dict (so cache replays the exact call)
        self._cache: dict[str, dict] = {}

    # ------------------------------------------------------------------
    def resolve_from_file(self, candidates_path: str, intent: str) -> ResolveResult:
        """Load candidates from a JSON file and resolve."""
        candidates = self._load(candidates_path)
        return self.resolve(intent, candidates)

    def resolve(self, intent: str, candidates: list[dict]) -> ResolveResult:
        """Try L0 cache, then candidates in order."""
        t0 = time.perf_counter()
        attempted: list[str] = []
        last_error = ""

        # L0: cache hit
        cached = self._cache.get(intent)
        if cached:
            try:
                locator = self._build(cached)
                if self._exists(locator):
                    elapsed = (time.perf_counter() - t0) * 1000
                    logger.info("L0 cache hit intent=%s strategy=%s elapsed=%.1fms",
                                 intent, cached.get("strategy"), elapsed)
                    return ResolveResult(
                        locator=locator,
                        strategy=cached.get("strategy", "cached"),
                        score=cached.get("score", 0.0),
                        intent=intent,
                        level="L0_cache",
                        elapsed_ms=elapsed,
                        attempted=["L0_cache_hit"],
                    )
            except Exception as exc:
                last_error = str(exc)
                attempted.append("L0_cache_miss")
                self._cache.pop(intent, None)

        # L1: walk candidates by score, return first hit
        for idx, c in enumerate(candidates):
            strategy = c.get("strategy", "?")
            attempted.append(f"L1_{strategy}")
            try:
                locator = self._build(c)
                if self._exists(locator):
                    self._cache[intent] = c
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
        logger.warning("Resolve FAILED intent=%s attempted=%s elapsed=%.1fms",
                        intent, attempted, elapsed)
        raise LocatorNotFoundError(intent, candidates, last_error)

    # ------------------------------------------------------------------
    def _build(self, candidate: dict):
        """Turn a candidate dict into a Playwright Locator."""
        call = candidate.get("playwright_call")
        if call:
            return dispatch(self._page, call)
        # Fallback: CSS selector via page.locator()
        sel = candidate.get("selector", "")
        if not sel:
            raise ValueError("candidate has neither playwright_call nor selector")
        # Strip the "page." prefix that v2 emits for symmetry with playwright_call.
        if sel.startswith("page."):
            return dispatch(self._page, sel[len("page."):])
        return self._page.locator(sel)

    def _exists(self, locator) -> bool:
        """Return True if the locator resolves to at least one element."""
        try:
            return locator.count() > 0
        except Exception:
            return False

    def _load(self, candidates_path: str) -> list[dict]:
        if not os.path.exists(candidates_path):
            raise FileNotFoundError(candidates_path)
        with open(candidates_path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "candidates" in data:
            return data["candidates"]
        raise ValueError(f"unexpected candidates schema in {candidates_path}")

    # ------------------------------------------------------------------
    def cache_size(self) -> int:
        return len(self._cache)

    def clear_cache(self) -> None:
        self._cache.clear()
