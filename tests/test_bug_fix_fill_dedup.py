"""Regression test — Bug 9: fill events deduplicated correctly."""
import pytest


def test_compact_fills_same_field_with_intermediate_click():
    """Consecutive fills on same field separated by a focus-click must collapse to one."""
    from testforge.semantic.recording_normalizer import RecordingNormalizer

    target_renda = {"tag": "input", "id": "mat-input-1", "name": "", "placeholder": "R$0,00",
                    "test_id": "", "accessible_name": "Renda mensal"}

    raw_events = [
        {"type": "click",  "target": target_renda, "value": "", "timestamp": "T1", "url": "http://x"},
        {"type": "fill",   "target": target_renda, "value": "1", "timestamp": "T2", "url": "http://x"},
        {"type": "fill",   "target": target_renda, "value": "10", "timestamp": "T3", "url": "http://x"},
        {"type": "fill",   "target": target_renda, "value": "100", "timestamp": "T4", "url": "http://x"},
        {"type": "fill",   "target": target_renda, "value": "1.000,00", "timestamp": "T5", "url": "http://x"},
    ]

    norm = RecordingNormalizer()
    compacted = norm._compact_fill_events(raw_events)

    fill_events = [e for e in compacted if e["type"] == "fill"]
    assert len(fill_events) == 1, \
        f"Expected 1 fill after compaction, got {len(fill_events)}: {[e['value'] for e in fill_events]}"
    assert fill_events[0]["value"] == "1.000,00", "Must keep last (final) value"


def test_fills_different_fields_not_collapsed():
    """Fills on different fields must NOT be collapsed."""
    from testforge.semantic.recording_normalizer import RecordingNormalizer

    target_renda  = {"tag": "input", "id": "mat-input-1", "name": "", "placeholder": "R$0,00",
                     "test_id": "", "accessible_name": "Renda mensal"}
    target_imovel = {"tag": "input", "id": "mat-input-2", "name": "", "placeholder": "R$0,00",
                     "test_id": "", "accessible_name": "Valor do imóvel"}

    raw_events = [
        {"type": "fill", "target": target_renda,  "value": "1.000,00", "timestamp": "T1", "url": "http://x"},
        {"type": "fill", "target": target_imovel, "value": "500.000,00", "timestamp": "T2", "url": "http://x"},
    ]

    norm = RecordingNormalizer()
    compacted = norm._compact_fill_events(raw_events)

    fill_events = [e for e in compacted if e["type"] == "fill"]
    assert len(fill_events) == 2, "Different fields must produce separate fill steps"


def test_overlay_js_fillkey_uses_index_fallback():
    """overlay_inject.js must use _fillKey() with DOM index fallback, not bare tagName."""
    from pathlib import Path
    overlay_src = (
        Path(__file__).parent.parent /
        "src/testforge/recorder/overlay_inject.js"
    ).read_text(encoding="utf-8")

    assert "function _fillKey(" in overlay_src, "_fillKey function missing from overlay_inject.js"
    assert "|| el.tagName;" not in overlay_src and "|| el.tagName\n" not in overlay_src, \
        "Bare el.tagName fallback still present — causes fill dedup collision"
    assert "tagName + ':' + idx" in overlay_src or "tagName + \":\" + idx" in overlay_src, \
        "_fillKey must use tagName + DOM index as fallback"
