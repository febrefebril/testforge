"""H20 — scenario boundary partitioning.

Recorder emits a `scenario_boundary` raw event when the user presses
Shift+N. Normalizer drops it from the step stream and instead records
the position as a partition between scenarios. Default (no boundaries)
remains a single segment that spans every step.

The compiler/runner do not yet emit one test-per-segment — that lives
in a follow-up. This file pins the data plumbing so the follow-up has
something to consume.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from testforge.semantic.recording_normalizer import RecordingNormalizer


def _write_raw_events(tmp_path: Path, events: list[dict]) -> Path:
    rec = tmp_path / "rec"
    rec.mkdir()
    with open(rec / "raw_events.jsonl", "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")
    return rec


def _click(idx: int, label: str = "Continuar") -> dict:
    return {
        "event_id": f"evt_{idx:05d}",
        "type": "click",
        "timestamp": f"2026-06-27T22:00:{idx:02d}Z",
        "url": "https://example.test/page",
        "page_title": "Page",
        "target": {
            "tag": "button",
            "text": label,
            "accessible_name": label,
            "css_path": "button",
        },
    }


def _boundary(name: str = "") -> dict:
    return {
        "type": "scenario_boundary",
        "timestamp": "2026-06-27T22:01:00Z",
        "url": "https://example.test/page",
        "page_title": "Page",
        "scenario_name": name,
    }


class TestSingleSegmentByDefault:
    def test_no_boundaries_gives_one_segment(self, tmp_path):
        rec = _write_raw_events(tmp_path, [_click(1), _click(2), _click(3)])
        n = RecordingNormalizer()
        stc = n.normalize(str(rec))
        assert len(stc.scenario_segments) == 1
        seg = stc.scenario_segments[0]
        assert seg["start_step"] == 0
        assert seg["end_step_exclusive"] == len(stc.steps)
        assert seg["name"] == "default"

    def test_empty_recording_has_no_segments(self, tmp_path):
        rec = _write_raw_events(tmp_path, [])
        n = RecordingNormalizer()
        stc = n.normalize(str(rec))
        assert stc.scenario_segments == []
        assert stc.steps == []


class TestBoundaryPartitions:
    def test_single_boundary_splits_into_two_segments(self, tmp_path):
        rec = _write_raw_events(tmp_path, [
            _click(1),
            _click(2),
            _boundary("fluxo_alternativo"),
            _click(3),
            _click(4),
        ])
        n = RecordingNormalizer()
        stc = n.normalize(str(rec))
        assert len(stc.scenario_segments) == 2
        a, b = stc.scenario_segments
        assert a["start_step"] == 0 and a["end_step_exclusive"] == 2
        assert b["start_step"] == 2 and b["end_step_exclusive"] == 4
        # The named boundary names the segment that follows it.
        assert b["name"] == "fluxo_alternativo"

    def test_two_boundaries_make_three_segments(self, tmp_path):
        rec = _write_raw_events(tmp_path, [
            _click(1),
            _boundary("b"),
            _click(2),
            _boundary("c"),
            _click(3),
        ])
        n = RecordingNormalizer()
        stc = n.normalize(str(rec))
        assert len(stc.scenario_segments) == 3
        starts = [s["start_step"] for s in stc.scenario_segments]
        ends = [s["end_step_exclusive"] for s in stc.scenario_segments]
        assert starts == [0, 1, 2]
        assert ends == [1, 2, 3]

    def test_boundary_does_not_become_step(self, tmp_path):
        rec = _write_raw_events(tmp_path, [
            _click(1),
            _boundary("foo"),
            _click(2),
        ])
        n = RecordingNormalizer()
        stc = n.normalize(str(rec))
        assert len(stc.steps) == 2  # only the two clicks
        assert all(
            getattr(s, "action", "") != "scenario_boundary"
            for s in stc.steps
        )

    def test_empty_segments_are_dropped(self, tmp_path):
        """Two consecutive boundaries with no steps between → no zero-
        length segment in the output."""
        rec = _write_raw_events(tmp_path, [
            _click(1),
            _boundary("a"),
            _boundary("b"),
            _click(2),
        ])
        n = RecordingNormalizer()
        stc = n.normalize(str(rec))
        for s in stc.scenario_segments:
            assert s["end_step_exclusive"] > s["start_step"], (
                f"Empty segment leaked: {s}"
            )


class TestCaptureSchemaBump:
    def test_schema_at_least_v3(self):
        # H20 introduced v3 (scenario_boundary). Later bumps in the same
        # session (H21 → v4) climb past it; only the lower bound is
        # invariant for this feature.
        from testforge.recorder.capture_fingerprint import CAPTURE_SCHEMA_VERSION
        assert CAPTURE_SCHEMA_VERSION >= 3, (
            "H20 added the scenario_boundary raw event. Bump CAPTURE_"
            "SCHEMA_VERSION when this event shape changes."
        )
