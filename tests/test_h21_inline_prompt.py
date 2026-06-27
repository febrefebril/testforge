"""H21 — inline value prompt as the new primary source.

When the overlay detects keystrokes followed by an empty input on blur,
it asks the user inline ("mascara interceptou — digite o valor"). The
typed value lands in raw_events.jsonl as `inline_field_value` and the
normalizer surfaces it as `user_supplied_inline` — the highest single-
source priority below form_values.

This file pins:
1. user_supplied_inline outranks fill_event / setter_hook / final_state.
2. The normalizer parses the raw event into a FieldValueMap entry with
   the right source, value, and identifier shape.
3. user_supplied_inline beats setter_hook on the same field.
4. Empty values are dropped.
"""
from __future__ import annotations

import json
from pathlib import Path

from testforge.semantic.recording_normalizer import RecordingNormalizer


def _write_raw_events(tmp_path: Path, events: list[dict]) -> Path:
    rec = tmp_path / "rec"
    rec.mkdir()
    with open(rec / "raw_events.jsonl", "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")
    return rec


def _inline(label: str, value: str, ts: str = "2026-06-27T22:00:00Z") -> dict:
    fp = f"input#mat-input-1[name=]"
    return {
        "type": "inline_field_value",
        "timestamp": ts,
        "fingerprint": fp,
        "label": label,
        "placeholder": "0,00",
        "aria_label": label,
        "element_id": "mat-input-1",
        "name": "",
        "tag": "input",
        "value": value,
        "source": "user_supplied_inline",
    }


class TestPriorityRanking:
    def test_user_supplied_inline_above_fill_event(self):
        p = RecordingNormalizer.IR_SOURCE_PRIORITY
        assert p["user_supplied_inline"] > p["fill_event"]
        assert p["user_supplied_inline"] > p["final_state"]
        assert p["user_supplied_inline"] > p["setter_hook"]

    def test_form_values_still_top(self):
        p = RecordingNormalizer.IR_SOURCE_PRIORITY
        assert p["form_values"] > p["user_supplied_inline"]

    def test_no_priority_collision(self):
        p = RecordingNormalizer.IR_SOURCE_PRIORITY
        assert len(set(p.values())) == len(p)


class TestNormalizerReadsInlineEvents:
    def test_inline_event_surfaces_as_user_supplied_inline(self, tmp_path):
        rec = _write_raw_events(tmp_path, [
            _inline("Renda mensal *", "2500"),
        ])
        n = RecordingNormalizer()
        entries = n._ir_inline_field_values(str(rec), [])
        assert len(entries) == 1
        e = entries[0]
        assert e["source"] == "user_supplied_inline"
        assert e["value"] == "2500"
        # Canonical key is built from the label, not the fingerprint.
        assert "mat-input" not in e["field_key"]
        assert "renda" in e["field_key"].lower()
        # Identifiers preserved for the downstream resolver.
        assert e["identifiers"]["label"] == "Renda mensal *"
        assert e["identifiers"]["id"] == "mat-input-1"

    def test_empty_value_is_dropped(self, tmp_path):
        rec = _write_raw_events(tmp_path, [
            _inline("Renda mensal *", ""),
            _inline("Valor do imóvel *", "1000000"),
        ])
        n = RecordingNormalizer()
        entries = n._ir_inline_field_values(str(rec), [])
        labels = [e["identifiers"]["label"] for e in entries]
        assert "Renda mensal *" not in labels
        assert "Valor do imóvel *" in labels

    def test_inline_beats_setter_hook_on_same_field(self, tmp_path):
        """When both sources fire for the same masked field, user-typed
        value must win the dedupe."""
        rec = _write_raw_events(tmp_path, [
            _inline("Renda mensal *", "2500"),
            # Also a value_mutation (setter_hook) that the mask
            # produced — usually a partial / wrong value.
            {
                "type": "value_mutation",
                "timestamp": "2026-06-27T22:00:01Z",
                "fingerprint": "input#mat-input-1[name=]",
                "value": "25,00",  # mask produced this; user meant 2500
            },
        ])
        n = RecordingNormalizer()
        # Run the full IR pipeline so dedupe runs.
        entries = n._ir_all(str(rec), [])
        # The merged entry for the renda field must be the user value.
        target = next(
            (e for e in entries if "renda" in e["field_key"].lower()),
            None,
        )
        assert target is not None
        assert target["source"] == "user_supplied_inline"
        assert target["value"] == "2500"


class TestSchemaBumped:
    def test_capture_schema_v4(self):
        from testforge.recorder.capture_fingerprint import CAPTURE_SCHEMA_VERSION
        assert CAPTURE_SCHEMA_VERSION >= 4, (
            "H21 added the inline_field_value raw event type. Bump "
            "CAPTURE_SCHEMA_VERSION when the event shape changes."
        )
