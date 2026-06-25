"""Sprint 0 commit 2 — ReplayCheck.

Right after the recorder captures a user action, immediately try the
generated primary selector against the live DOM and record whether it
resolves. Catches selector-fragility at *record time* — the team sees
the bug before they ever try to play the test back.

Modes:
- "immediate" (B1)  probe synchronously; ~50-200 ms per step
- "batched"   (B4)  queue probes, drain on demand or at stop

Probing reuses LocatorResolver (Phase 3) so the result is consistent
with what the runtime would do.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class ReplayCheck:
    def __init__(self, page, mode: str = "immediate",
                 probe_timeout_ms: int = 600) -> None:
        self._page = page
        self._mode = mode if mode in ("immediate", "batched") else "immediate"
        self._probe_timeout_ms = probe_timeout_ms
        self._pending: list[tuple[str, list]] = []
        self._records: list[dict] = []

    # ------------------------------------------------------------------
    def check(self, step_id: str, candidates: list) -> Optional[dict]:
        """Probe immediately (B1) or queue for later (B4)."""
        if self._mode == "batched":
            self._pending.append((step_id, list(candidates)))
            return None
        return self._do_check(step_id, candidates)

    def drain(self) -> list[dict]:
        """Process queued probes (called at stop in batched mode)."""
        out: list[dict] = []
        for sid, cands in self._pending:
            rec = self._do_check(sid, cands)
            if rec:
                out.append(rec)
        self._pending.clear()
        return out

    @property
    def records(self) -> list[dict]:
        return list(self._records)

    # ------------------------------------------------------------------
    def _do_check(self, step_id: str, candidates: list) -> dict:
        from ..runtime.resolver import LocatorResolver
        from ..runtime.errors import LocatorNotFoundError
        resolver = LocatorResolver(self._page,
                                    probe_timeout_ms=self._probe_timeout_ms)
        t0 = time.perf_counter()
        primary_selector = self._first_selector(candidates)
        attempted_dicts = [self._candidate_dict(c) for c in candidates]
        try:
            result = resolver.resolve(
                intent=f"replay_check:{step_id}",
                candidates=attempted_dicts,
                action="probe",
            )
            elapsed = (time.perf_counter() - t0) * 1000
            rec = {
                "step_id": step_id,
                "ts_checked": datetime.now(timezone.utc).isoformat(),
                "delay_after_record_ms": 0,
                "selector_attempted": primary_selector,
                "resolved": True,
                "fallback_resolved_at_index": result.candidate_index,
                "fallback_strategy": result.strategy
                    if result.candidate_index > 0 else None,
                "fallback_selector": attempted_dicts[result.candidate_index].get("selector")
                    if result.candidate_index > 0 else None,
                "elapsed_ms": round(elapsed, 1),
                "error": None,
            }
        except LocatorNotFoundError as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            rec = {
                "step_id": step_id,
                "ts_checked": datetime.now(timezone.utc).isoformat(),
                "delay_after_record_ms": 0,
                "selector_attempted": primary_selector,
                "resolved": False,
                "fallback_resolved_at_index": -1,
                "fallback_strategy": None,
                "fallback_selector": None,
                "elapsed_ms": round(elapsed, 1),
                "error": str(exc.last_error or "")[:200],
            }
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            rec = {
                "step_id": step_id,
                "ts_checked": datetime.now(timezone.utc).isoformat(),
                "selector_attempted": primary_selector,
                "resolved": False,
                "elapsed_ms": round(elapsed, 1),
                "error": f"probe_failed: {exc}",
            }
        self._records.append(rec)
        return rec

    # ------------------------------------------------------------------
    @staticmethod
    def _first_selector(candidates) -> Optional[str]:
        if not candidates:
            return None
        first = candidates[0]
        return getattr(first, "selector", None) or first.get("selector")

    @staticmethod
    def _candidate_dict(c) -> dict:
        if isinstance(c, dict):
            return c
        return {
            "strategy": getattr(c, "strategy", "?"),
            "selector": getattr(c, "selector", ""),
            "score": getattr(c, "score", 0.0),
            "playwright_call": getattr(c, "playwright_call", None),
        }
