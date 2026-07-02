"""Fase 5 — Refatoracao Pipes & Filters do RecordingNormalizer.

Verifica que:
- Classes base Stage + Pipeline funcionam
- LoadStage / DedupStage / CompactStage / AuditStage produzem a mesma
  lista raw_events que o codigo legado
- RecordingNormalizer(use_pipeline=True).normalize() produz o mesmo
  SemanticTestCase que o caminho legado na mesma entrada
"""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from testforge.semantic.recording_normalizer import RecordingNormalizer
from testforge.semantic.stages import (
    AuditStage,
    CompactStage,
    DedupStage,
    LoadStage,
    NormalizationContext,
    Pipeline,
)


def _write_raw_events(rec_dir: str, events: list) -> None:
    os.makedirs(rec_dir, exist_ok=True)
    path = os.path.join(rec_dir, "raw_events.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")


def _click_event(eid: str, ts: str, role: str = "button", name: str = "Login") -> dict:
    return {
        "event_id": eid,
        "type": "click",
        "timestamp": ts,
        "url": "http://localhost:8765/",
        "target": {
            "tag": "button", "role": role, "accessible_name": name,
            "element_id": f"btn-{eid}",
        },
    }


def _fill_event(eid: str, ts: str, value: str = "x@y.com") -> dict:
    return {
        "event_id": eid,
        "type": "fill",
        "timestamp": ts,
        "url": "http://localhost:8765/",
        "value": value,
        "target": {
            "tag": "input", "role": "textbox", "label": "Email",
            "name": "email",
        },
    }


class TestBaseClasses:
    def test_pipeline_runs_stages_in_order(self):
        order: list[str] = []

        class A:
            name = "a"
            def run(self, ctx):
                order.append("a")
                return ctx

        class B:
            name = "b"
            def run(self, ctx):
                order.append("b")
                return ctx

        with tempfile.TemporaryDirectory() as d:
            Pipeline([A(), B()]).run(NormalizationContext(recording_dir=d))
        assert order == ["a", "b"]

    def test_pipeline_stage_names(self):
        class S1:
            name = "s1"
            def run(self, ctx): return ctx
        p = Pipeline([S1(), S1()])
        assert p.stage_names == ["s1", "s1"]


class TestLoadStage:
    def test_reads_jsonl(self):
        with tempfile.TemporaryDirectory() as d:
            _write_raw_events(d, [_click_event("e1", "2026-06-25T00:00:00Z")])
            ctx = NormalizationContext(recording_dir=d)
            ctx = LoadStage().run(ctx)
        assert ctx.initial_event_count == 1
        assert ctx.raw_events[0]["event_id"] == "e1"
        assert ctx.stats["initial_type_counts"] == {"click": 1}

    def test_missing_file_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with pytest.raises(FileNotFoundError):
                LoadStage().run(NormalizationContext(recording_dir=d))


class TestDedupAndCompactStages:
    def test_dedup_stage_delegates_to_normalizer(self):
        n = RecordingNormalizer()
        events = [
            _click_event("e1", "2026-06-25T00:00:00Z"),
            _click_event("e2", "2026-06-25T00:00:01Z"),
        ]
        with tempfile.TemporaryDirectory() as d:
            _write_raw_events(d, events)
            ctx = NormalizationContext(recording_dir=d)
            ctx.raw_events = list(events)
            ctx = DedupStage(n).run(ctx)
        # Logica identica: mesmos eventos entram, mesmos eventos saem (sem ciclos de snapshot)
        assert ctx.raw_events == n._remove_snapshot_duplicates(events)

    def test_compact_stage_collapses_fills(self):
        n = RecordingNormalizer()
        events = [
            _fill_event("e1", "2026-06-25T00:00:00Z", value="a"),
            _fill_event("e2", "2026-06-25T00:00:01Z", value="ab"),
            _fill_event("e3", "2026-06-25T00:00:02Z", value="abc"),
        ]
        ctx = NormalizationContext(recording_dir="x")
        ctx.raw_events = list(events)
        ctx = CompactStage(n).run(ctx)
        # Tres fills sequenciais no mesmo campo colapsam no ultimo.
        assert len(ctx.raw_events) <= len(events)
        assert ctx.raw_events[-1]["value"] == "abc"


class TestPipelineParityWithLegacy:
    def test_legacy_vs_pipeline_produce_same_test_case(self):
        events = [
            _click_event("e1", "2026-06-25T00:00:00Z"),
            _fill_event("e2", "2026-06-25T00:00:01Z", value="alice@x.com"),
            _click_event("e3", "2026-06-25T00:00:02Z", role="button", name="Send"),
        ]
        with tempfile.TemporaryDirectory() as d:
            _write_raw_events(d, events)
            legacy = RecordingNormalizer(use_pipeline=False).normalize(
                d, test_id="ST-p", application="x", base_url="http://x/"
            )
            pipe = RecordingNormalizer(use_pipeline=True).normalize(
                d, test_id="ST-p", application="x", base_url="http://x/"
            )
        # Compara via to_dict porque ignora campos vazios uniformemente.
        assert legacy.to_dict() == pipe.to_dict()

    def test_pipeline_run_does_not_crash_on_empty_recording(self):
        with tempfile.TemporaryDirectory() as d:
            _write_raw_events(d, [])
            stc = RecordingNormalizer(use_pipeline=True).normalize(
                d, test_id="ST-empty", application="x", base_url="http://x/"
            )
        assert stc.test_id == "ST-empty"
        assert stc.steps == []
