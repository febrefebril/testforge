"""Phase 1 instrumentation — silent skip counters.

Functional coverage for the new observability hooks added in the handoff plan.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from testforge.metrics.metrics_repository import MetricsRepository
from testforge.recorder.recorder_controller import RecorderController
from testforge.semantic.model import SemanticAction, SemanticTestCase
from testforge.semantic.recording_normalizer import RecordingNormalizer


class _FailingDiagnostic:
    def assess_event(self, **kwargs):
        raise RuntimeError("diagnostic boom")


class TestPhase1NormalizerInstrumentation:
    def test_when_click_event_has_no_candidates_then_counter_is_recorded(self):
        # Arrange
        MetricsRepository.reset_silent_skip_summary_global()
        normalizer = RecordingNormalizer()

        # Act
        out = normalizer._convert_event({"type": "click", "target": {}})

        # Assert
        assert out is None
        summary = MetricsRepository.get_silent_skip_summary_global()
        assert summary.get("click_no_candidates", 0) >= 1

    def test_when_overlay_detection_sees_missing_target_then_counter_is_recorded(self):
        # Arrange
        MetricsRepository.reset_silent_skip_summary_global()
        normalizer = RecordingNormalizer()
        steps = [SemanticAction(action="click", target=None)]

        # Act
        normalizer._detect_overlay_steps(steps)

        # Assert
        summary = MetricsRepository.get_silent_skip_summary_global()
        assert summary.get("overlay_detect", 0) == 1

    def test_when_dedupe_receives_empty_key_or_value_then_counters_increment(self):
        # Arrange
        MetricsRepository.reset_silent_skip_summary_global()
        normalizer = RecordingNormalizer()
        entries = [
            {"field_key": "", "value": "x", "source": "polling"},
            {"field_key": "campo", "value": "", "source": "polling"},
            {"field_key": "ok", "value": "1", "source": "final_state"},
        ]

        # Act
        out = normalizer._ir_dedupe_entries(entries)

        # Assert
        assert len(out) == 1
        summary = MetricsRepository.get_silent_skip_summary_global()
        assert summary.get("ir_dedupe_empty_key", 0) == 1
        assert summary.get("ir_dedupe_empty_value", 0) == 1

    def test_when_final_state_has_missing_and_empty_values_then_counters_increment(self, tmp_path):
        # Arrange
        MetricsRepository.reset_silent_skip_summary_global()
        normalizer = RecordingNormalizer()
        payload = {
            "timestamp": "2026-07-01T00:00:00Z",
            "fields": [
                {"fingerprint": "a", "value": None, "identifiers": {}},
                {"fingerprint": "b", "value": "", "identifiers": {}},
            ],
        }
        path = Path(tmp_path) / "final_state_snapshot.json"
        path.write_text(json.dumps(payload), encoding="utf-8")

        # Act
        out = normalizer._ir_final_state(str(tmp_path), [])

        # Assert
        assert out == []
        summary = MetricsRepository.get_silent_skip_summary_global()
        assert summary.get("ir_final_state_field_missing", 0) == 1
        assert summary.get("ir_final_state_field_empty_at_end", 0) == 1

    def test_when_reconstruct_intents_has_empty_entry_label_then_counter_increments(self):
        # Arrange
        MetricsRepository.reset_silent_skip_summary_global()
        normalizer = RecordingNormalizer()
        stc = SemanticTestCase(
            test_id="ST-phase1",
            source_recording_id="rec-phase1",
            steps=[SemanticAction(action="fill")],
        )

        def _fake_ir_all(recording_dir, steps):
            return [{
                "source": "polling",
                "value": "",
                "field_key": "campo",
                "step_index": 0,
                "intention": "",
                "identifiers": {},
            }]

        normalizer._ir_all = _fake_ir_all  # type: ignore[attr-defined]

        # Act
        normalizer._reconstruct_intents(stc, ".")

        # Assert
        summary = MetricsRepository.get_silent_skip_summary_global()
        assert summary.get("entry_label_empty", 0) == 1


class TestPhase1RecorderInstrumentation:
    def test_when_flush_events_contains_snapshot_errors_then_counter_is_recorded(self, tmp_path):
        # Arrange
        MetricsRepository.reset_silent_skip_summary_global()
        page = MagicMock()
        page.url = "http://example.local"
        page.evaluate.return_value = {
            "events": [],
            "steps": [],
            "commands": [],
            "fieldSnapshots": [],
            "snapshotErrors": [{"error": "x"}, {"error": "y"}],
            "valueMutations": [],
            "keystrokes": [],
            "rrwebEvents": [],
        }
        recorder = RecorderController(page, recordings_root=str(tmp_path))

        # Act
        recorder.flush_events()

        # Assert
        summary = MetricsRepository.get_silent_skip_summary_global()
        assert summary.get("snapshot_exception", 0) == 2

    def test_when_diagnostic_assess_raises_then_counter_is_recorded(self, tmp_path):
        # Arrange
        MetricsRepository.reset_silent_skip_summary_global()
        page = MagicMock()
        recorder = RecorderController(page, recordings_root=str(tmp_path))
        with patch.object(recorder, "_capture_snapshots"):
            recorder.start(recording_id="REC-PHASE1")
        recorder._diagnostic = _FailingDiagnostic()

        # Act
        recorder._persist_raw_event({
            "type": "click",
            "timestamp": "2026-07-01T00:00:00Z",
            "target": {},
            "url": "http://example.local",
        })

        # Assert
        summary = MetricsRepository.get_silent_skip_summary_global()
        assert summary.get("diagnostic_assess_error", 0) == 1
