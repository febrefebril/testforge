"""B29 — compiler emits one pytest function per scenario segment.

H20 captured scenario_segments on SemanticTestCase. The compiler kept
emitting one test function regardless, so a single failure cascaded
through what the recorder intended as independent flows. B29 closes
that gap: one `def test_*` per segment, named after the segment's
sanitised label.

This file pins:
1. Single-segment (default) recordings still emit exactly one
   `def test_<base>(...)` function (back-compat).
2. Multi-segment recordings emit N functions named
   `test_<base>__<segment>(...)`.
3. Each segment's body only contains the steps in its slice.
4. Each function carries the segment name in its docstring.
"""
from __future__ import annotations

import os

from testforge.semantic.compiler import PlaywrightCompiler
from testforge.semantic.model import (
    LocatorCandidate,
    SemanticAction,
    SemanticTarget,
    SemanticTestCase,
)


def _click(text: str) -> SemanticAction:
    target = SemanticTarget(
        accessible_name=text,
        text=text,
        tag="button",
        candidates=[LocatorCandidate(
            "aria_label",
            f'button[aria-label="{text}"]',
            0.9,
            "aria_label",
        )],
    )
    return SemanticAction(action="click", target=target, context={})


def _stc(steps: list[SemanticAction],
         segments: list[dict] | None = None) -> SemanticTestCase:
    tc = SemanticTestCase(
        test_id="ST-multi-scenario-test",
        source_recording_id="rec-multi",
        application="WebApp",
        base_url="https://example.test",
    )
    tc.steps = steps
    tc.scenario_segments = segments or []
    return tc


class TestSingleSegmentBackCompat:
    def test_single_segment_emits_one_function(self, tmp_path):
        steps = [_click("A"), _click("B")]
        tc = _stc(steps, segments=[
            {"start_step": 0, "end_step_exclusive": 2, "name": "default"},
        ])
        out = PlaywrightCompiler().compile(tc, str(tmp_path))
        code = open(out, encoding="utf-8").read()
        assert code.count("def test_") == 1
        assert "test_st_multi_scenario_test(" in code

    def test_no_segments_field_defaults_to_single(self, tmp_path):
        steps = [_click("A")]
        tc = _stc(steps, segments=[])  # empty list, not None
        out = PlaywrightCompiler().compile(tc, str(tmp_path))
        code = open(out, encoding="utf-8").read()
        assert code.count("def test_") == 1


class TestMultiSegmentEmission:
    def test_two_segments_two_functions(self, tmp_path):
        steps = [
            _click("Login"),
            _click("Dashboard"),
            _click("Logout"),
            _click("Outra coisa"),
        ]
        tc = _stc(steps, segments=[
            {"start_step": 0, "end_step_exclusive": 2, "name": "happy_path"},
            {"start_step": 2, "end_step_exclusive": 4, "name": "logout_flow"},
        ])
        out = PlaywrightCompiler().compile(tc, str(tmp_path))
        code = open(out, encoding="utf-8").read()
        assert code.count("def test_") == 2
        assert "test_st_multi_scenario_test__happy_path(" in code
        assert "test_st_multi_scenario_test__logout_flow(" in code

    def test_segment_name_in_docstring(self, tmp_path):
        tc = _stc(
            [_click("X"), _click("Y")],
            segments=[
                {"start_step": 0, "end_step_exclusive": 1, "name": "primeiro"},
                {"start_step": 1, "end_step_exclusive": 2, "name": "segundo"},
            ],
        )
        out = PlaywrightCompiler().compile(tc, str(tmp_path))
        code = open(out, encoding="utf-8").read()
        assert "cenário: primeiro" in code
        assert "cenário: segundo" in code

    def test_segment_body_only_covers_its_slice(self, tmp_path):
        steps = [
            _click("STEP_ALFA"),
            _click("STEP_BETA"),
            _click("STEP_GAMMA"),
        ]
        tc = _stc(steps, segments=[
            {"start_step": 0, "end_step_exclusive": 1, "name": "s1"},
            {"start_step": 1, "end_step_exclusive": 3, "name": "s2"},
        ])
        out = PlaywrightCompiler().compile(tc, str(tmp_path))
        code = open(out, encoding="utf-8").read()
        # Split by function definitions
        parts = code.split("def test_")
        assert len(parts) >= 3  # preamble + 2 functions
        s1_block = parts[1]
        s2_block = parts[2]
        # STEP_ALFA lives in s1 only.
        assert "STEP_ALFA" in s1_block
        assert "STEP_ALFA" not in s2_block
        # STEP_BETA + STEP_GAMMA live in s2 only.
        assert "STEP_BETA" not in s1_block
        assert "STEP_GAMMA" not in s1_block
        assert "STEP_BETA" in s2_block
        assert "STEP_GAMMA" in s2_block

    def test_unnamed_segments_get_numeric_fallback(self, tmp_path):
        tc = _stc(
            [_click("A"), _click("B")],
            segments=[
                {"start_step": 0, "end_step_exclusive": 1, "name": ""},
                {"start_step": 1, "end_step_exclusive": 2, "name": ""},
            ],
        )
        out = PlaywrightCompiler().compile(tc, str(tmp_path))
        code = open(out, encoding="utf-8").read()
        assert "test_st_multi_scenario_test__cenario_1(" in code
        assert "test_st_multi_scenario_test__cenario_2(" in code
