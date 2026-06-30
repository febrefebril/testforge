"""TestForge — Sprint A2/A3/B2/B3/D/F: 6 fixes pos SIOPI 15a-f analise.

Cobre:
- A2: _eliminate_prefill_clicks consulta field_snapshots visibility
- A3: _ensure_input_visible chama scroll + wait_for visible
- B2: _fingerprint_match rejeita cura para elemento com aria-label diferente
- B3: drift threshold subido para 0.75 + top_heading no signature
- D:  --strict-asserts no run-incremental retorna exit 1 quando asserts_hit < total
- F:  tab-like clicks (role=tab, mat-tab, mat-expansion-panel) preservados
"""
from __future__ import annotations
import json
import os
import tempfile
from unittest.mock import MagicMock

import pytest

from testforge.semantic.recording_normalizer import RecordingNormalizer
from testforge.runner.screen_state import (
    ScreenState, capture_screen_state, compare,
)
from testforge.runner.incremental_runner import IncrementalRunner


# ---------------------------------------------------------------------------
# Sprint A2: visibility check no prefill_click skip
# ---------------------------------------------------------------------------


class TestSprintA2InputVisibilityCheck:
    def _make_step(self, action, element_id, ts, candidates=None, tag="input"):
        step = MagicMock()
        step.action = action
        step.skip_reason = ""
        step.context = {"timestamp": ts}
        step.target = MagicMock()
        step.target.tag = tag
        step.target.element_id = element_id
        step.target.accessible_name = ""
        step.target.role = ""
        cands = []
        for sel in (candidates or [f"input#{element_id}"]):
            c = MagicMock()
            c.selector = sel
            cands.append(c)
        step.target.candidates = cands
        return step

    def _write_snapshots(self, tmpdir, entries):
        path = os.path.join(tmpdir, "field_snapshots.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")
        return tmpdir

    def test_skip_when_input_visible_at_click(self):
        norm = RecordingNormalizer()
        with tempfile.TemporaryDirectory() as tmp:
            self._write_snapshots(tmp, [
                {
                    "timestamp": "2026-06-30T12:00:00Z",
                    "fingerprint": "input#mat-input-1[name=]",
                    "visibility": "visible",
                },
            ])
            click = self._make_step("click", "mat-input-1", "2026-06-30T12:00:00Z")
            fill = self._make_step("fill", "mat-input-1", "2026-06-30T12:00:01Z")
            steps = [click, fill]
            norm._eliminate_prefill_clicks(steps, tmp)
            assert click.skip_reason == "prefill_click_noise"

    def test_keep_click_when_input_hidden_at_click(self):
        norm = RecordingNormalizer()
        with tempfile.TemporaryDirectory() as tmp:
            self._write_snapshots(tmp, [
                {
                    "timestamp": "2026-06-30T12:00:00Z",
                    "fingerprint": "input#mat-input-1[name=]",
                    "visibility": "hidden",
                },
            ])
            click = self._make_step("click", "mat-input-1", "2026-06-30T12:00:00Z")
            fill = self._make_step("fill", "mat-input-1", "2026-06-30T12:00:01Z")
            steps = [click, fill]
            norm._eliminate_prefill_clicks(steps, tmp)
            assert click.skip_reason == ""
            assert click.context.get("preserved_reason") == "input_hidden_at_click_time"

    def test_legacy_behavior_when_no_snapshots(self):
        norm = RecordingNormalizer()
        with tempfile.TemporaryDirectory() as tmp:
            click = self._make_step("click", "mat-input-1", "2026-06-30T12:00:00Z")
            fill = self._make_step("fill", "mat-input-1", "2026-06-30T12:00:01Z")
            steps = [click, fill]
            # Sem field_snapshots.jsonl, conservador: skip (comportamento legado).
            norm._eliminate_prefill_clicks(steps, tmp)
            assert click.skip_reason == "prefill_click_noise"


# ---------------------------------------------------------------------------
# Sprint A3: scroll_into_view + wait_for visible defensivo
# ---------------------------------------------------------------------------


class TestSprintA3EnsureVisible:
    def test_ensure_visible_calls_scroll_and_wait(self):
        from testforge.runner.step_executor import StepExecutor
        ex = StepExecutor.__new__(StepExecutor)
        ex.page = MagicMock()
        loc = MagicMock()
        ex._ensure_input_visible(loc)
        loc.scroll_into_view_if_needed.assert_called_once_with(timeout=2000)
        loc.wait_for.assert_called_once_with(state="visible", timeout=5000)

    def test_ensure_visible_swallows_scroll_failure(self):
        from testforge.runner.step_executor import StepExecutor
        ex = StepExecutor.__new__(StepExecutor)
        ex.page = MagicMock()
        loc = MagicMock()
        loc.scroll_into_view_if_needed.side_effect = RuntimeError("offscreen")
        ex._ensure_input_visible(loc)
        # Should NOT raise; wait_for ainda chamado
        loc.wait_for.assert_called_once()

    def test_ensure_visible_swallows_wait_failure(self):
        from testforge.runner.step_executor import StepExecutor
        ex = StepExecutor.__new__(StepExecutor)
        ex.page = MagicMock()
        loc = MagicMock()
        loc.wait_for.side_effect = RuntimeError("not visible")
        ex._ensure_input_visible(loc)
        loc.scroll_into_view_if_needed.assert_called_once()


# ---------------------------------------------------------------------------
# Sprint B2: fingerprint match validation
# ---------------------------------------------------------------------------


def _build_runner_with_page():
    r = IncrementalRunner.__new__(IncrementalRunner)
    r.page = MagicMock()
    return r


def _build_step(accessible_name="Calcular", label="", text=""):
    step = MagicMock()
    step.target = MagicMock()
    step.target.accessible_name = accessible_name
    step.target.label = label
    step.target.text = text
    return step


class TestSprintB2FingerprintMatch:
    def test_substring_match_passes(self):
        r = _build_runner_with_page()
        loc = MagicMock()
        loc.get_attribute.return_value = "Calcular"
        loc.text_content.return_value = "Calcular"
        r.page.locator.return_value.first = loc

        matched, reason = r._fingerprint_match("button:has-text('Calcular')",
                                                _build_step("Calcular"))
        assert matched
        assert "substring" in reason or "char_overlap" in reason

    def test_completely_different_name_fails(self):
        r = _build_runner_with_page()
        loc = MagicMock()
        loc.get_attribute.return_value = "Confirmar"
        loc.text_content.return_value = "Confirmar"
        r.page.locator.return_value.first = loc

        matched, reason = r._fingerprint_match("button:has-text('Confirmar')",
                                                _build_step("Calcular"))
        assert not matched
        assert "fingerprint_mismatch" in reason

    def test_expected_too_short_passes_through(self):
        r = _build_runner_with_page()
        matched, reason = r._fingerprint_match("button", _build_step("OK"))
        # Too short — sem evidencia, deixa passar
        assert matched
        assert "too_short" in reason

    def test_resolve_unavailable_passes_through(self):
        r = _build_runner_with_page()
        r.page.locator.side_effect = RuntimeError("not found")
        matched, reason = r._fingerprint_match("button:has-text('X')",
                                                _build_step("Calcular"))
        # Sem evidencia, conservador
        assert matched
        assert "unavailable" in reason

    def test_no_target_passes_through(self):
        r = _build_runner_with_page()
        step = MagicMock()
        step.target = None
        matched, _ = r._fingerprint_match("button", step)
        assert matched


# ---------------------------------------------------------------------------
# Sprint B3: drift threshold + top_heading
# ---------------------------------------------------------------------------


class TestSprintB3DriftTuning:
    def test_top_heading_extracted_from_heading_role(self):
        page = MagicMock()
        page.url = "https://app/"
        page.title.return_value = "X"
        page.evaluate.return_value = [
            {"role": "button", "name": "Click"},
            {"role": "heading", "name": "Welcome"},
            {"role": "link", "name": "Home"},
        ]
        state = capture_screen_state(page)
        assert state.top_heading == "Welcome"

    def test_top_heading_in_signature(self):
        s = ScreenState(url="u", title="t", top_heading="H1")
        assert "H1" in s.signature()

    def test_threshold_raised_to_075(self):
        # Overlap of exactly 0.66 (2/3) — was OK with 0.6, now flags with 0.75
        a = ScreenState(top_roles=[
            {"role": "button", "name": "A"},
            {"role": "button", "name": "B"},
            {"role": "button", "name": "C"},
        ])
        b = ScreenState(top_roles=[
            {"role": "button", "name": "A"},
            {"role": "button", "name": "B"},
            {"role": "button", "name": "X"},
            {"role": "button", "name": "Y"},
        ])
        # 2 shared / 5 union = 0.4 — already low; pick a finer test.
        c = ScreenState(top_roles=[
            {"role": "button", "name": "A"},
            {"role": "button", "name": "B"},
        ])
        d = ScreenState(top_roles=[
            {"role": "button", "name": "A"},
            {"role": "button", "name": "B"},
            {"role": "button", "name": "C"},
        ])
        # 2 shared / 3 union = 0.66 — previously matched, now drifts
        diff = compare(c, d)
        assert not diff.matched
        assert "role_overlap" in diff.reason

    def test_heading_change_flags_drift(self):
        a = ScreenState(top_heading="Home", top_roles=[{"role": "button", "name": "X"}])
        b = ScreenState(top_heading="Login", top_roles=[{"role": "button", "name": "X"}])
        diff = compare(a, b)
        assert not diff.matched
        assert diff.heading_changed
        assert "heading" in diff.reason


# ---------------------------------------------------------------------------
# Sprint D: --strict-asserts exit code (sanity at CLI arg parser level)
# ---------------------------------------------------------------------------


class TestSprintDStrictAsserts:
    def test_strict_asserts_flag_registered(self):
        from testforge.cli._run_incremental_patch import register
        import argparse
        sub = argparse.ArgumentParser().add_subparsers()
        register(sub)
        # Parse with --strict-asserts to ensure no SystemExit
        parser = list(sub.choices.values())[0]
        ns = parser.parse_args(["script.py", "--strict-asserts"])
        assert ns.strict_asserts is True

    def test_strict_asserts_default_false(self):
        from testforge.cli._run_incremental_patch import register
        import argparse
        sub = argparse.ArgumentParser().add_subparsers()
        register(sub)
        parser = list(sub.choices.values())[0]
        ns = parser.parse_args(["script.py"])
        assert ns.strict_asserts is False


# ---------------------------------------------------------------------------
# Sprint F: tab-like clicks preserved
# ---------------------------------------------------------------------------


class TestSprintFTabLikePreservation:
    def _make_click(self, role="", selector=""):
        step = MagicMock()
        step.action = "click"
        step.skip_reason = ""
        step.context = {"timestamp": "2026-06-30T12:00:00Z"}
        step.target = MagicMock()
        step.target.role = role
        step.target.tag = "div"
        step.target.element_id = "x"
        step.target.accessible_name = ""
        c = MagicMock()
        c.selector = selector
        step.target.candidates = [c]
        return step

    def test_role_tab_detected(self):
        s = self._make_click(role="tab")
        assert RecordingNormalizer._is_tab_like_click(s) is True

    def test_role_menuitem_detected(self):
        s = self._make_click(role="menuitem")
        assert RecordingNormalizer._is_tab_like_click(s) is True

    def test_mat_tab_selector_detected(self):
        s = self._make_click(selector='div.mat-tab-header > div')
        assert RecordingNormalizer._is_tab_like_click(s) is True

    def test_mat_expansion_panel_header_detected(self):
        s = self._make_click(selector='mat-expansion-panel-header')
        assert RecordingNormalizer._is_tab_like_click(s) is True

    def test_aria_controls_detected(self):
        s = self._make_click(selector='button[aria-controls="panel1"]')
        assert RecordingNormalizer._is_tab_like_click(s) is True

    def test_regular_button_not_tab_like(self):
        s = self._make_click(role="button", selector="button.calcular")
        assert RecordingNormalizer._is_tab_like_click(s) is False

    def test_tab_click_followed_by_fill_not_skipped(self):
        norm = RecordingNormalizer()
        tab_click = self._make_click(role="tab")
        tab_click.target.tag = "div"

        fill_step = MagicMock()
        fill_step.action = "fill"
        fill_step.skip_reason = ""
        fill_step.context = {"timestamp": "2026-06-30T12:00:01Z"}
        fill_step.target = MagicMock()
        fill_step.target.tag = "input"
        fill_step.target.element_id = "renda"
        fill_step.target.accessible_name = "Renda"
        c = MagicMock()
        c.selector = "input#renda"
        fill_step.target.candidates = [c]

        norm._eliminate_prefill_clicks([tab_click, fill_step], "")
        # Tab click NUNCA marcado como noise — Sprint F early-skip
        assert tab_click.skip_reason == ""
