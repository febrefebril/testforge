"""TestForge — Pendentes sweep 2026-06-30.

Cobre as 4 mudancas implementadas nesta leva:

1. Sprint L: keystroke_buffer.jsonl + _ir_keystroke_buffer reconstruct
2. DOM diff signature + suggested_assertions.jsonl
3. Iframe + Shadow DOM event delegation
4. React MUI + PrimeFaces handlers execute() MVP

Sprint N (network backfill) ja existia em _ir_network — sem mudancas.
BUG-005 verificado: _resolve_name OK, sem append silencioso.
"""
from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest


OVERLAY = Path(__file__).parent.parent / "src" / "testforge" / "recorder" / "overlay_inject.js"


# ---------------------------------------------------------------------------
# Sprint L
# ---------------------------------------------------------------------------


class TestKeystrokeBufferOverlayJS:
    def test_keystroke_queue_initialized(self):
        src = OVERLAY.read_text(encoding="utf-8")
        assert "__tfKeystrokeQueue" in src

    def test_keydown_listener_registered(self):
        src = OVERLAY.read_text(encoding="utf-8")
        assert 'addEventListener("keydown"' in src or "addEventListener('keydown'" in src

    def test_keystroke_captures_modifiers(self):
        src = OVERLAY.read_text(encoding="utf-8")
        # Captura ctrlKey, metaKey, etc — necessario para detectar ctrl+a / ctrl+v
        assert "ctrlKey" in src
        assert "metaKey" in src

    def test_keystroke_text_editable_check(self):
        src = OVERLAY.read_text(encoding="utf-8")
        assert "_isTextEditable" in src

    def test_keystroke_cap_at_5000(self):
        src = OVERLAY.read_text(encoding="utf-8")
        assert "5000" in src  # buffer cap para nao OOM


class TestKeystrokeBufferReconstruct:
    def test_reconstruct_simple_chars(self):
        from testforge.semantic.recording_normalizer import RecordingNormalizer
        session = [
            {"key": "h", "kind": "char"},
            {"key": "e", "kind": "char"},
            {"key": "l", "kind": "char"},
            {"key": "l", "kind": "char"},
            {"key": "o", "kind": "char"},
        ]
        assert RecordingNormalizer._ir_reconstruct_from_keystrokes(session) == "hello"

    def test_reconstruct_backspace(self):
        from testforge.semantic.recording_normalizer import RecordingNormalizer
        session = [
            {"key": "h", "kind": "char"},
            {"key": "e", "kind": "char"},
            {"key": "l", "kind": "char"},
            {"key": "Backspace", "kind": "named"},
            {"key": "l", "kind": "char"},
            {"key": "p", "kind": "char"},
        ]
        assert RecordingNormalizer._ir_reconstruct_from_keystrokes(session) == "help"

    def test_reconstruct_ctrl_a_clears(self):
        from testforge.semantic.recording_normalizer import RecordingNormalizer
        session = [
            {"key": "x", "kind": "char"},
            {"key": "y", "kind": "char"},
            {"key": "a", "kind": "char", "ctrl": True},
            {"key": "z", "kind": "char"},
        ]
        assert RecordingNormalizer._ir_reconstruct_from_keystrokes(session) == "z"

    def test_reconstruct_filters_named_navigation_keys(self):
        from testforge.semantic.recording_normalizer import RecordingNormalizer
        session = [
            {"key": "a", "kind": "char"},
            {"key": "Tab", "kind": "named"},
            {"key": "b", "kind": "char"},
            {"key": "Enter", "kind": "named"},
            {"key": "c", "kind": "char"},
        ]
        # Tab/Enter nao entram no buffer
        assert RecordingNormalizer._ir_reconstruct_from_keystrokes(session) == "abc"

    def test_ir_keystroke_buffer_emits_field_value_entry(self):
        from testforge.semantic.recording_normalizer import RecordingNormalizer
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "keystroke_buffer.jsonl")
            keystrokes = [
                {"timestamp": "2026-06-30T12:00:00.100Z",
                 "fingerprint": "input#renda[name=]",
                 "key": "1", "kind": "char",
                 "accessible_name": "Renda mensal *", "placeholder": "R$0,00"},
                {"timestamp": "2026-06-30T12:00:00.200Z",
                 "fingerprint": "input#renda[name=]",
                 "key": "0", "kind": "char",
                 "accessible_name": "Renda mensal *", "placeholder": "R$0,00"},
                {"timestamp": "2026-06-30T12:00:00.300Z",
                 "fingerprint": "input#renda[name=]",
                 "key": "0", "kind": "char",
                 "accessible_name": "Renda mensal *", "placeholder": "R$0,00"},
            ]
            with open(path, "w") as f:
                for k in keystrokes:
                    f.write(json.dumps(k) + "\n")
            norm = RecordingNormalizer()
            entries = norm._ir_keystroke_buffer(tmp, [])
            assert len(entries) == 1
            assert entries[0]["value"] == "100"
            assert entries[0]["source"] == "keystroke"
            assert "Renda mensal" in entries[0]["intention"]


# ---------------------------------------------------------------------------
# DOM diff signature
# ---------------------------------------------------------------------------


class TestDomDiffSuggestion:
    def test_compute_dom_diff_appeared(self):
        from testforge.recorder.recorder_controller import RecorderController
        before = {"elements": {"h1:Welcome": "Welcome"}}
        after = {"elements": {"h1:Welcome": "Welcome",
                              "div.alert:Error": "Error: invalid"}}
        diff = RecorderController._compute_dom_diff(before, after)
        assert any(c["type"] == "appeared" for c in diff)

    def test_compute_dom_diff_disappeared(self):
        from testforge.recorder.recorder_controller import RecorderController
        before = {"elements": {"h1:Login": "Login", "p:hint": "Insert credentials"}}
        after = {"elements": {"h1:Login": "Login"}}
        diff = RecorderController._compute_dom_diff(before, after)
        assert any(c["type"] == "disappeared" for c in diff)

    def test_compute_dom_diff_changed(self):
        from testforge.recorder.recorder_controller import RecorderController
        before = {"elements": {"INPUT:cpf": "012"}}
        after = {"elements": {"INPUT:cpf": "012.345.678-90"}}
        diff = RecorderController._compute_dom_diff(before, after)
        assert any(c["type"] == "changed" for c in diff)

    def test_empty_inputs_no_diff(self):
        from testforge.recorder.recorder_controller import RecorderController
        assert RecorderController._compute_dom_diff({}, {}) == []
        assert RecorderController._compute_dom_diff(None, None) == []

    def test_diff_caps_at_20(self):
        from testforge.recorder.recorder_controller import RecorderController
        before = {"elements": {}}
        after = {"elements": {f"k{i}": f"v{i}" for i in range(50)}}
        diff = RecorderController._compute_dom_diff(before, after)
        assert len(diff) == 20


# ---------------------------------------------------------------------------
# Iframe + Shadow DOM delegation
# ---------------------------------------------------------------------------


class TestEventDelegationStatic:
    def test_delegation_helper_defined(self):
        src = OVERLAY.read_text(encoding="utf-8")
        assert "_delegateToRoot" in src
        assert "_scanIframesAndShadows" in src

    def test_scans_iframes(self):
        src = OVERLAY.read_text(encoding="utf-8")
        assert 'querySelectorAll("iframe")' in src

    def test_scans_shadow_roots_open_only(self):
        src = OVERLAY.read_text(encoding="utf-8")
        # mode === "open" filtra closed
        assert 'mode === "open"' in src

    def test_dedup_via_weakset(self):
        src = OVERLAY.read_text(encoding="utf-8")
        assert "__tfDelegatedRoots" in src
        assert "WeakSet" in src

    def test_periodic_rescan(self):
        src = OVERLAY.read_text(encoding="utf-8")
        assert "__tfDelegationInterval" in src
        assert "setInterval(_scanIframesAndShadows" in src


# ---------------------------------------------------------------------------
# Handlers MUI + PrimeFaces
# ---------------------------------------------------------------------------


class TestReactMUIHandlerExecute:
    def _build_step(self, selectors, value="", accessible_name=""):
        step = MagicMock()
        step.value = value
        step.target = MagicMock()
        step.target.accessible_name = accessible_name
        step.target.text = ""
        cands = []
        for s in selectors:
            c = MagicMock()
            c.selector = s
            cands.append(c)
        step.target.candidates = cands
        return step

    def test_select_clicks_trigger_then_option(self):
        from testforge.handlers.react_mui import ReactMUIHandler
        page = MagicMock()
        h = ReactMUIHandler()
        step = self._build_step(['.MuiSelect-root[id="x"]'],
                                 accessible_name="Brasil")
        result = h.execute(page, step)
        assert "mui_select" in result
        page.locator.assert_any_call('.MuiSelect-root[id="x"]')
        page.wait_for_selector.assert_called_with(
            '[role="listbox"]', state="visible", timeout=4000
        )

    def test_menu_item_click(self):
        from testforge.handlers.react_mui import ReactMUIHandler
        page = MagicMock()
        h = ReactMUIHandler()
        step = self._build_step([".MuiMenuItem-root[data-value='a']"])
        result = h.execute(page, step)
        assert ".MuiMenuItem-root" in result

    def test_unknown_pattern_raises_not_implemented(self):
        from testforge.handlers.react_mui import ReactMUIHandler
        page = MagicMock()
        h = ReactMUIHandler()
        step = self._build_step(["#some-random-id"])
        with pytest.raises(NotImplementedError):
            h.execute(page, step)


class TestPrimeFacesHandlerExecute:
    def _build_step(self, selectors, value=""):
        step = MagicMock()
        step.value = value
        step.target = MagicMock()
        cands = []
        for s in selectors:
            c = MagicMock()
            c.selector = s
            cands.append(c)
        step.target.candidates = cands
        return step

    def test_select_one_menu(self):
        from testforge.handlers.primeFaces import PrimeFacesHandler
        page = MagicMock()
        h = PrimeFacesHandler()
        step = self._build_step([".ui-selectonemenu[id='x']"], value="Brasil")
        result = h.execute(page, step)
        assert "pf_dropdown" in result

    def test_autocomplete(self):
        from testforge.handlers.primeFaces import PrimeFacesHandler
        page = MagicMock()
        h = PrimeFacesHandler()
        step = self._build_step([".p-autocomplete[id='x']"], value="termo")
        result = h.execute(page, step)
        assert "pf_autocomplete" in result

    def test_unknown_raises_not_implemented(self):
        from testforge.handlers.primeFaces import PrimeFacesHandler
        page = MagicMock()
        h = PrimeFacesHandler()
        step = self._build_step(["div.random"])
        with pytest.raises(NotImplementedError):
            h.execute(page, step)
