"""Sprint 0 — DiagnosticTelemetryStore unit tests."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from testforge.diagnostic.telemetry_store import DiagnosticTelemetryStore
from testforge.metrics import telemetry


@pytest.fixture(autouse=True)
def _isolate_tracer(tmp_path):
    telemetry.reset_tracer()
    telemetry._tracer = telemetry.Tracer(
        spans_path=str(tmp_path / "spans.jsonl"))
    yield
    telemetry.reset_tracer()


class TestJSONLPersistence:
    def test_step_append(self, tmp_path):
        store = DiagnosticTelemetryStore(str(tmp_path))
        store.append_step({"step_id": "s1", "action": "fill",
                           "capture_quality": {"value_kind": "currency_BR"}})
        lines = open(store.steps_path).readlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["step_id"] == "s1"

    def test_replay_append(self, tmp_path):
        store = DiagnosticTelemetryStore(str(tmp_path))
        store.append_replay({"step_id": "s1", "resolved": True,
                             "elapsed_ms": 12.3})
        lines = open(store.replay_path).readlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["resolved"] is True

    def test_session_write_overwrites(self, tmp_path):
        store = DiagnosticTelemetryStore(str(tmp_path))
        store.write_session({"session_id": "v1"})
        store.write_session({"session_id": "v2"})
        data = json.loads(open(tmp_path / "session.json").read())
        assert data["session_id"] == "v2"

    def test_files_inventory(self, tmp_path):
        store = DiagnosticTelemetryStore(str(tmp_path))
        store.write_session({"x": 1})
        store.append_step({"step_id": "s1"})
        files = store.files()
        assert files["session"]
        assert files["steps"]
        assert files["replay"] is None  # never written
        assert files["feature"] is None


class TestSpanEmission:
    def test_step_emits_span(self, tmp_path):
        store = DiagnosticTelemetryStore(str(tmp_path / "d"))
        store.append_step({
            "step_id": "s1", "action": "fill",
            "capture_quality": {
                "value_kind": "currency_BR",
                "value_captured_at_event": True,
                "value_len": 11,
            },
            "framework_signal": {"is_inside_mat_form_field": True},
            "blind_spots": ["typing_not_captured"],
        })
        spans_path = telemetry.get_tracer().spans_path
        line = open(spans_path).read().strip()
        span = json.loads(line)
        assert span["name"] == "diagnostic.step"
        attrs = span["attributes"]
        assert attrs["action"] == "fill"
        assert attrs["capture_quality.value_kind"] == "currency_BR"
        assert attrs["capture_quality.value_captured_at_event"] is True
        assert attrs["framework_signal.is_inside_mat_form_field"] is True
        assert attrs["blind_spots"] == "typing_not_captured"

    def test_replay_emits_span(self, tmp_path):
        store = DiagnosticTelemetryStore(str(tmp_path / "d"))
        store.append_replay({"step_id": "s1", "resolved": False,
                             "elapsed_ms": 47.0, "error": "missing"})
        spans = open(telemetry.get_tracer().spans_path).read().strip()
        span = json.loads(spans)
        assert span["name"] == "diagnostic.replay"
        assert span["attributes"]["resolved"] is False
        assert span["attributes"]["elapsed_ms"] == 47.0

    def test_nested_dict_flattens(self, tmp_path):
        store = DiagnosticTelemetryStore(str(tmp_path / "d"))
        store.append_step({"a": {"b": {"c": 1}}})
        spans = open(telemetry.get_tracer().spans_path).read().strip()
        attrs = json.loads(spans)["attributes"]
        assert attrs["a.b.c"] == 1

    def test_lists_serialized_to_csv(self, tmp_path):
        store = DiagnosticTelemetryStore(str(tmp_path / "d"))
        store.append_step({"tags": ["x", "y", "z"]})
        spans = open(telemetry.get_tracer().spans_path).read().strip()
        attrs = json.loads(spans)["attributes"]
        assert attrs["tags"] == "x,y,z"


class TestResilience:
    def test_creates_dir_if_missing(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c"
        store = DiagnosticTelemetryStore(str(deep))
        assert os.path.isdir(deep)
        store.append_step({"x": 1})
