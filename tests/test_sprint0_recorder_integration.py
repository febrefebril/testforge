"""Sprint 0 — Testes de integracao DiagnosticSession + RecorderController."""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, PropertyMock

import pytest

from testforge.diagnostic import DiagnosticSession
from testforge.recorder.recorder_controller import RecorderController


def _make_page(eval_result: dict | None = None):
    page = MagicMock()
    page.url = "http://x/"
    page.context = MagicMock()
    page.context.tracing = MagicMock()
    page.context.new_cdp_session = MagicMock()
    page.add_init_script = MagicMock()
    page.on = MagicMock()
    page.remove_listener = MagicMock()
    page.evaluate = MagicMock(return_value=eval_result or {
        "events": [], "steps": [], "commands": [],
        "fieldSnapshots": [], "valueMutations": [],
    })
    page.screenshot = MagicMock(return_value=b"\x89PNG")
    page.content = MagicMock(return_value="<html><body>x</body></html>")
    page.title = MagicMock(return_value="App")
    page.wait_for_load_state = MagicMock()
    page.main_frame = MagicMock()
    return page


class TestDiagnosticSessionIntegration:
    def _detection_payload(self):
        return {
            "angular": True, "angular_version": "16.2.0",
            "angular_material": True, "zone_js": True,
            "custom_components": ["dsc-input-currency"],
            "shadow_dom_count": 5, "iframe_count": 0,
            "dom_size": 200, "max_depth": 10,
            "interactive_elements": 10, "form_count": 1,
            "evidence": ["[ng-version=16.2.0]"],
        }

    def test_full_flow_writes_all_artifacts(self, tmp_path):
        page = _make_page(self._detection_payload())
        sess = DiagnosticSession(page=page, cdp_session=None,
                                  session_dir=str(tmp_path))
        sess.start()
        sess.on_navigation("http://app/", title="Simulador")
        sess.assess_event(
            {"event_id": "evt_001", "type": "click",
             "timestamp": "2026-06-25T00:00:00Z",
             "target": {"accessible_name": "Calcular", "role": "button"}},
            target_data={"accessible_name": "Calcular", "role": "button"},
            candidates=[],
        )
        sess.assess_event(
            {"event_id": "evt_002", "type": "fill",
             "timestamp": "2026-06-25T00:00:01Z", "value": "R$ 5.000,00",
             "target": {"label": "Renda mensal", "tag": "input"}},
            target_data={"label": "Renda mensal", "tag": "input"},
            candidates=[],
        )
        sess.assess_event(
            {"event_id": "evt_003", "type": "assert",
             "timestamp": "2026-06-25T00:00:02Z",
             "target": {"text": "Parcela estimada"}},
            target_data={"text": "Parcela estimada"},
            candidates=[],
        )
        payload = sess.finalize()
        # session.json presente
        on_disk = json.loads((tmp_path / "session.json").read_text())
        assert on_disk["framework_detection"]["primary"] == "angular-material"
        assert on_disk["totals"]["steps"] == 3
        assert on_disk["totals"]["asserts"] == 1
        # steps.jsonl presente
        steps_lines = open(tmp_path / "steps.jsonl").readlines()
        assert len(steps_lines) == 3
        # scenario.feature presente + formato Gherkin OK
        feature = (tmp_path / "scenario.feature").read_text()
        assert "Funcionalidade: Simulador" in feature
        assert "Quando clico no botao \"Calcular\"" in feature
        assert "preencho \"Renda mensal\" com valor monetario" in feature
        assert "Entao vejo o texto \"Parcela estimada\"" in feature

    def test_totals_track_value_capture(self, tmp_path):
        page = _make_page(self._detection_payload())
        sess = DiagnosticSession(page=page, cdp_session=None,
                                  session_dir=str(tmp_path))
        sess.start()
        sess.assess_event(
            {"event_id": "e1", "type": "fill",
             "timestamp": "2026-06-25T00:00:00Z", "value": "R$ 1,00",
             "target": {"label": "A"}},
            target_data={"label": "A"}, candidates=[],
        )
        sess.assess_event(
            {"event_id": "e2", "type": "fill",
             "timestamp": "2026-06-25T00:00:01Z", "value": "",
             "target": {"label": "B"}},
            target_data={"label": "B"}, candidates=[],
        )
        sess.finalize()
        assert sess.totals["value_captured"] == 1
        assert sess.totals["value_missing"] == 1
        assert sess.totals["blind_spots"] >= 1  # 'typing_not_captured' do e2

    def test_gherkin_override(self, tmp_path):
        page = _make_page(self._detection_payload())
        sess = DiagnosticSession(page=page, cdp_session=None,
                                  session_dir=str(tmp_path))
        sess.start()
        sess.on_navigation("http://app/", title="App")
        sess.assess_event(
            {"event_id": "e1", "type": "click",
             "timestamp": "2026-06-25T00:00:00Z",
             "target": {"accessible_name": "Login"}},
            target_data={"accessible_name": "Login"}, candidates=[],
        )
        sess.finalize(funcionalidade_override="Autenticacao",
                       cenario_override="Login com sucesso")
        feature = (tmp_path / "scenario.feature").read_text()
        assert "Funcionalidade: Autenticacao" in feature
        assert "Cenario: Login com sucesso" in feature


class TestRecorderControllerDiagnostic:
    def test_diagnostic_off_does_not_create_diagnostic_dir(self):
        page = _make_page()
        with tempfile.TemporaryDirectory() as tmproot:
            ctrl = RecorderController(page, recordings_root=tmproot)
            ctrl.start("REC-001", diagnostic_mode=False)
            ctrl.stop()
            session_dir = ctrl._store._session_dir
            assert not os.path.isdir(os.path.join(session_dir, "diagnostic"))
            assert ctrl._diagnostic is None

    def test_diagnostic_on_creates_session(self):
        page = _make_page({
            "evidence": [], "custom_components": [],
            "shadow_dom_count": 0, "iframe_count": 0, "dom_size": 10,
            "max_depth": 3, "interactive_elements": 0, "form_count": 0,
        })
        with tempfile.TemporaryDirectory() as tmproot:
            ctrl = RecorderController(page, recordings_root=tmproot)
            ctrl.start("REC-002", diagnostic_mode=True)
            assert ctrl._diagnostic is not None
            session_dir = ctrl._store._session_dir
            assert os.path.isdir(os.path.join(session_dir, "diagnostic"))
            ctrl.stop()
            # session.json escrito
            assert os.path.exists(os.path.join(
                session_dir, "diagnostic", "session.json"))

    def test_persist_raw_event_feeds_diagnostic(self):
        page = _make_page({
            "evidence": [], "custom_components": [],
            "shadow_dom_count": 0, "iframe_count": 0, "dom_size": 10,
            "max_depth": 3, "interactive_elements": 0, "form_count": 0,
        })
        with tempfile.TemporaryDirectory() as tmproot:
            ctrl = RecorderController(page, recordings_root=tmproot)
            ctrl.start("REC-003", diagnostic_mode=True)
            ctrl._persist_raw_event({
                "type": "click",
                "timestamp": "2026-06-25T00:00:00Z",
                "target": {"accessible_name": "X", "tag": "button"},
            })
            session_dir = ctrl._store._session_dir
            steps = open(os.path.join(session_dir, "diagnostic", "steps.jsonl")).read()
            assert "X" in steps or "click" in steps
            ctrl.stop()


class TestHotfix15PrecaptureForClose:
    """Hotfix 15: precapture_for_close armazena framework + url para finalize
    apos browser.close()."""

    def _make_page(self, url="https://app.test/"):
        p = MagicMock()
        type(p).url = PropertyMock(return_value=url)
        p.evaluate = MagicMock(return_value={})
        p.context = MagicMock()
        p.context.new_cdp_session = MagicMock()
        return p

    def test_precapture_caches_framework(self, tmp_path):
        from unittest.mock import patch
        page = self._make_page()
        sess = DiagnosticSession(
            page=page, cdp_session=None,
            session_dir=str(tmp_path / "diag"), replay_mode="immediate",
        )
        sess.start()
        # Simula o detector para controlar o que e armazenado em cache.
        with patch.object(
            sess._detector, "detect",
            return_value={"primary": "angular-material"},
        ):
            sess.precapture_for_close()
        assert sess._cached_framework == {"primary": "angular-material"}
        assert sess._cached_url == "https://app.test/"

    def test_finalize_uses_cached_framework_after_page_closed(self, tmp_path):
        from unittest.mock import patch
        page = self._make_page()
        sess = DiagnosticSession(
            page=page, cdp_session=None,
            session_dir=str(tmp_path / "diag2"), replay_mode="immediate",
        )
        sess.start()
        with patch.object(
            sess._detector, "detect",
            return_value={"primary": "angular-material"},
        ):
            sess.precapture_for_close()
        # Agora quebra a pagina — simula browser.close()
        type(page).url = PropertyMock(side_effect=Exception("closed"))
        page.evaluate = MagicMock(side_effect=Exception("closed"))
        # detector.detect() tambem quebrado agora
        with patch.object(
            sess._detector, "detect", side_effect=Exception("closed"),
        ):
            payload = sess.finalize()
        # Framework ainda presente no payload
        assert payload["framework_detection"] == {"primary": "angular-material"}
        # URL tambem
        assert payload["app_url_signature"]

    def test_precapture_tolerates_detector_failure(self, tmp_path):
        from unittest.mock import patch
        page = self._make_page()
        sess = DiagnosticSession(
            page=page, cdp_session=None,
            session_dir=str(tmp_path / "diag3"), replay_mode="immediate",
        )
        sess.start()
        with patch.object(
            sess._detector, "detect", side_effect=Exception("boom"),
        ):
            sess.precapture_for_close()
        assert sess._cached_framework == {}
