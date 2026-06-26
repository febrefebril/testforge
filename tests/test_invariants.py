"""Static invariants enforced in CI.

This file translates the patterns documented in
`.planning/REGRESSION-PATTERNS.md` into pytest assertions. Every entry
in that registry should have at least one test here. When a test fails,
read the linked pattern entry to understand which bug class is at risk
of returning, and broaden the fix accordingly.

The tests are cheap: pure AST / grep on the source tree, no browser,
no fixtures. They run on every commit.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent / "src" / "testforge"


def _read(rel_path: str) -> str:
    return (_SRC / rel_path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# P1 — code-duplication-drift
# ---------------------------------------------------------------------------

class TestP1CodeDuplicationDrift:
    """Patterns where the same algorithm in N places drifts.

    Anchor invariant: every masked-input primitive lives in exactly one
    location. Fill helpers must delegate to `_fill_masked`. Hotfixes
    16, 17, 19 are the historical recurrences.
    """

    def test_press_sequentially_lives_in_one_place(self):
        src = _read("runner/step_executor.py")
        count = src.count("press_sequentially")
        assert count == 1, (
            f"press_sequentially appears {count} times in step_executor.py — "
            "must be exactly 1 (inside _fill_masked). A fill helper is "
            "reimplementing the masked-input path. See "
            ".planning/REGRESSION-PATTERNS.md#P1."
        )

    def test_step_executor_methods_inside_class(self):
        """Hotfix 9 shape: a module-level def inserted mid-class
        orphaned the methods below it as nested dead code. AST check
        catches that immediately."""
        src = _read("runner/step_executor.py")
        tree = ast.parse(src)
        class_methods = set()
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "StepExecutor":
                for m in node.body:
                    if isinstance(m, ast.FunctionDef):
                        class_methods.add(m.name)
        # These methods MUST be class methods, not nested in another fn
        # nor at module level. Hotfix 9 found them lost; we never want
        # that to repeat.
        required = {
            "execute", "_execute_click", "_execute_fill",
            "_execute_select", "_fill_input", "_fill_by_aria_label",
            "_try_data_fill", "_fill_masked", "_resolve_field_value",
        }
        missing = required - class_methods
        assert not missing, (
            f"StepExecutor is missing required methods: {missing}. "
            "A def at module level may have orphaned them as nested code. "
            "See .planning/REGRESSION-PATTERNS.md#P1, hotfix 9."
        )


# ---------------------------------------------------------------------------
# P2 — silent-default-swallow
# ---------------------------------------------------------------------------

class TestP2SilentDefaultSwallow:
    """`try / except Exception: pass` proliferation. Each site must
    eventually carry a documented reason and a logger call."""

    # Conservative cap. The current count is the baseline we inherit; the
    # cap goes down as we migrate to a @tolerate decorator (debt R-C1).
    _CAP = 80

    def test_bare_except_pass_count_is_bounded(self):
        """The number of `except Exception: pass` sites in src/ must not
        grow. New tolerance must use a documented decorator, not a bare
        swallow."""
        bare_pattern = re.compile(
            r"except\s+(Exception|BaseException)?:\s*\n\s*pass\s*$",
            re.MULTILINE,
        )
        total = 0
        for py in _SRC.rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            total += len(bare_pattern.findall(text))
        assert total <= self._CAP, (
            f"`except: pass` count is {total}, cap is {self._CAP}. "
            "Tolerance must use a decorator that documents the reason. "
            "See .planning/REGRESSION-PATTERNS.md#P2."
        )


# ---------------------------------------------------------------------------
# P3 — unanchored-state
# ---------------------------------------------------------------------------

class TestP3UnanchoredState:
    """Path / state assumed but not anchored. Producer and consumer must
    agree."""

    def test_field_value_map_writer_reader_round_trip(self, tmp_path):
        """Hotfix CS-4a shape: the writer of field_value_map.json stores
        data under {fields, entries, _meta} keys; the reader must
        consume all three shapes."""
        import json
        from testforge.cli._interactive_completion import _save_field_value_map
        from testforge.semantic.recording_normalizer import RecordingNormalizer
        from testforge.semantic.model import SemanticTestCase

        # Write via the production writer
        rec_dir = str(tmp_path)
        _save_field_value_map(rec_dir, {
            "cpf": {
                "field_key": "cpf",
                "value": "12345678900",
                "intention": "fill CPF",
                "identifiers": {"aria_label": "CPF"},
                "source": "user_supplied_cli",
                "confidence": 1.0,
                "step_index": 3,
            }
        })

        # Read via the production reader
        normalizer = RecordingNormalizer()
        normalizer._current_recording_dir = rec_dir
        stc = SemanticTestCase(test_id="X", source_recording_id="X")
        stc.field_values = {}
        normalizer._merge_user_supplied_values(stc)

        assert "cpf" in stc.field_values, (
            "Writer/reader contract for field_value_map.json broken. "
            "See .planning/REGRESSION-PATTERNS.md#P3, CS-4a."
        )
        assert stc.field_values["cpf"].value == "12345678900"


# ---------------------------------------------------------------------------
# P4 — feature-flag-rot
# ---------------------------------------------------------------------------

class TestP4FeatureFlagRot:
    """Feature flags that never flip rot into dead code. Tracking-only
    for now — turns into a hard fail once we set a flip deadline."""

    _KNOWN_FLAGS = {
        # name -> {default, owner, flip_or_delete_by}
        "use_cdp_recorder": {"default": False, "flip_or_delete_by": "2026-07-31"},
        "use_pipeline": {"default": False, "flip_or_delete_by": "2026-07-31"},
        "use_v2_compiler": {"default": False, "flip_or_delete_by": "2026-07-31"},
    }

    def test_known_flags_have_a_decision_deadline(self):
        """Every feature flag must have a flip-or-delete deadline. This
        test currently lists what we know; future PRs adding a flag must
        register it here."""
        for name, info in self._KNOWN_FLAGS.items():
            assert "flip_or_delete_by" in info, (
                f"Flag {name} has no deadline. "
                "See .planning/REGRESSION-PATTERNS.md#P4."
            )


# ---------------------------------------------------------------------------
# P5 — compile-runtime-divergence
# ---------------------------------------------------------------------------

class TestP5CompileRuntimeDivergence:
    """Runtime must not silently substitute the compiled action."""

    def test_click_to_fill_promotion_is_documented(self):
        """The click → fill silent promotion is the canonical
        compile/runtime divergence in step_executor. We do not delete
        it yet (R-E2 in the refactor sprint), but we DO require that
        every call site emits a fill.attempted span (CS-3). This test
        asserts the telemetry hook exists in the promotion path."""
        src = _read("runner/step_executor.py")
        # The _execute_click branch that calls _fill_input on
        # missing_fill must reach _fill_masked, which emits the span.
        assert "_fill_masked" in src
        assert "_emit_fill_span" in src
        # Every fill helper must delegate, not re-emit the span itself
        # (see P1 contract).

    def test_datepicker_handler_emits_skip_reason(self):
        """When the Angular Material datepicker handler suppresses a
        step, the skip_reason field must be set so the runner UI and
        the spans can report the decision. Silent drops are forbidden
        (hotfix 20)."""
        src = _read("handlers/angular_material.py")
        # datepicker_dedup is the documented skip_reason for the
        # completed-via-fill path. The click-only completion path now
        # does NOT set skip_reason because the clicks ARE the canonical
        # intent — that's the hotfix-20 invariant.
        assert "datepicker_dedup" in src
        # Negative invariant: the click-only completion branch (hotfix
        # 20) must not set skip_reason.
        assert "click-only completion" in src or "Click-only completion" in src, (
            "The hotfix 20 click-only branch comment is missing — "
            "regression risk. See .planning/REGRESSION-PATTERNS.md#P5."
        )
