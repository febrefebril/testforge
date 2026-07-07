"""Fase 3 BUG-REC-03: pilot mode uses healing ON by default.

Previously hardcoded no_healing=True → recordings CAIXA (R2/R3/R6*) showed
"Healing desativado" in every failure. QA thought healing was broken.
"""
import argparse
from pathlib import Path

import pytest


APP_SRC = (
    Path(__file__).resolve().parents[3]
    / "src" / "testforge" / "cli" / "app.py"
)


@pytest.mark.unit
class TestPilotHealingDefaults:
    def test_pilot_uses_pilot_strict_selectors_flag(self):
        # Arrange
        source = APP_SRC.read_text(encoding="utf-8")

        # Assert — hardcoded no_healing=True removed
        assert "no_healing=True," not in source or "pilot_strict_selectors" in source, (
            "pilot mode must not hardcode no_healing=True. "
            "BUG-REC-03: use --pilot-strict-selectors opt-in instead."
        )

    def test_pilot_no_healing_flag_registered(self):
        source = APP_SRC.read_text(encoding="utf-8")
        assert "--pilot-strict-selectors" in source, (
            "opt-in flag --pilot-strict-selectors missing"
        )

    def test_pilot_default_is_healing_on(self):
        """Runner receives no_healing=False when args.pilot_strict_selectors absent."""
        source = APP_SRC.read_text(encoding="utf-8")
        # Fingerprint: no_healing=_pilot_no_healing where _pilot_no_healing
        # defaults to False via getattr()
        assert "getattr(args, \"pilot_strict_selectors\", False)" in source, (
            "must use getattr fallback False for pilot healing"
        )
        assert "no_healing=_pilot_no_healing" in source, (
            "runner must receive computed flag, not hardcoded True"
        )

    def test_run_incremental_parser_registers_no_healing_flag(self):
        # Arrange
        from testforge.cli._run_incremental_patch import register
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()

        # Act
        register(sub)

        # Assert — --no-healing flag exists (opt-out)
        # Parse test — default should be no_healing=False (healing ON)
        args = parser.parse_args(["run-incremental", "dummy.py"])
        assert args.no_healing is False, (
            "run-incremental default must have healing ON. "
            "BUG-REC-03: --no-healing is opt-out."
        )

        args_off = parser.parse_args(["run-incremental", "dummy.py", "--no-healing"])
        assert args_off.no_healing is True
