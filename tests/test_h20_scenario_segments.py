"""H20 — particionamento de limite de cenario.

O gravador emite um evento bruto `scenario_boundary` quando o usuario
pressiona Shift+N. O normalizer o remove do fluxo de passos e em vez disso
registra a posicao como uma particao entre cenarios. O padrao (sem limites)
permanece um unico segmento que abrange todos os passos.

O compilador/executor ainda nao emite um teste-por-segmento — isso esta
em um trabalho futuro. Este arquivo fixa a tubulacao de dados para que o
trabalho futuro tenha algo para consumir.
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
        # O limite nomeado nomeia o segmento que o segue.
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
        """Dois limites consecutivos sem passos entre eles → nenhum segmento de
        comprimento zero na saida."""
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
                f"Segmento vazio vazou: {s}"
            )


class TestCaptureSchemaBump:
    def test_schema_at_least_v3(self):
        # H20 introduziu v3 (scenario_boundary). Aumentos posteriores na
        # mesma sessao (H21 → v4) ultrapassam; apenas o limite inferior e
        # invariante para esta funcionalidade.
        from testforge.recorder.capture_fingerprint import CAPTURE_SCHEMA_VERSION
        assert CAPTURE_SCHEMA_VERSION >= 3, (
            "H20 adicionou o evento bruto scenario_boundary. Aumente CAPTURE_"
            "SCHEMA_VERSION quando esta forma de evento mudar."
        )
