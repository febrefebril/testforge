"""TestForge — IncrementalUI.

Renderiza saída de terminal por step (verbose ou compacta).
"""
from __future__ import annotations
import sys


class IncrementalUI:
    def __init__(self, verbose: bool = False, stream=None):
        self.verbose = verbose
        self.stream = stream or sys.stdout

    def _w(self, msg: str = ""):
        print(msg, file=self.stream)

    def header(self, script_path, recording_id, base_url, healer, mode):
        self._w("[TestForge] run-incremental")
        self._w(f"  Script: {script_path}")
        self._w(f"  Recording: {recording_id}")
        self._w(f"  URL base: {base_url}")
        self._w(f"  Healer: {healer}")
        self._w(f"  Modo: {mode}")
        self._w("")

    def step(self, idx, total, result):
        status = result.status
        icon = {
            "passed": "OK",
            "healed_validated": "HEAL",
            "healing_rejected": "REJ",
            "failed": "FAIL",
            "blocked": "BLK",
            "skipped": "SKIP",
        }.get(status, "?")
        action = result.action
        loc = result.selected_locator or result.original_locator
        msg = f"Step {idx}/{total} {action} [{icon}] {status}"
        if loc:
            msg += f"  [{loc[:50]}]"
        self._w(msg)
        if self.verbose:
            if result.precondition:
                pre = result.precondition
                self._w(f"  PRE  {'OK' if pre.passed else 'X'} {pre.message}")
            if result.postcondition:
                post = result.postcondition
                self._w(f"  POST {'OK' if post.passed else 'X'} {post.message}")
            if result.healing and result.healing.attempted:
                h = result.healing
                self._w(f"  HEAL layer={h.layer} family={h.family} strategy={h.strategy}")
                self._w(f"       proposta={h.proposed_locator[:60]} conf={h.confidence:.2f}")
                if h.rejection_reason:
                    self._w(f"       rejection={','.join(h.rejection_reason)}")
            if result.error_message:
                self._w(f"  ERR  {result.error_message[:120]}")

    def summary(self, totals):
        self._w("")
        self._w("[TestForge] Sumario:")
        for k in ("total", "passed", "healed_validated", "healing_rejected",
                  "failed", "blocked", "skipped"):
            v = totals.get(k, 0)
            self._w(f"  {k:>20}: {v}")