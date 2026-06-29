"""Teste de regressão — Bug 7: form_values do submit deve evitar detecção de missing_fill."""
import json
import os
import tempfile
import pytest


def test_form_values_prevent_missing_fill():
    """Campos capturados via form_values no submit não devem ser marcados como missing_fill."""
    from testforge.semantic.recording_normalizer import RecordingNormalizer

    renda_target = {
        "tag": "input", "id": "mat-input-1", "name": "rendaMensal",
        "placeholder": "R$0,00", "accessible_name": "Renda mensal",
        "aria_label": "Renda mensal *", "test_id": "", "label": "Renda mensal *",
    }
    submit_target = {
        "tag": "button", "id": "", "name": "", "placeholder": "",
        "accessible_name": "Calcular",
    }

    raw_events = [
        {
            "type": "click", "target": renda_target, "value": "",
            "timestamp": "2026-06-24T10:00:00Z", "url": "http://x", "page_title": "Teste",
        },
        {
            "type": "submit", "target": submit_target, "value": "",
            "timestamp": "2026-06-24T10:00:05Z", "url": "http://x", "page_title": "Teste",
            "form_values": {"rendaMensal": "1.000,00", "Renda mensal *": "1.000,00"},
        },
    ]

    with tempfile.TemporaryDirectory() as td:
        events_file = os.path.join(td, "raw_events.jsonl")
        with open(events_file, "w", encoding="utf-8") as f:
            for evt in raw_events:
                f.write(json.dumps(evt) + "\n")
        meta_file = os.path.join(td, "recording_metadata.json")
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({"recording_id": "test_mf", "base_url": "http://x",
                       "application": "web", "status": "stopped"}, f)

        norm = RecordingNormalizer()
        stc = norm.normalize(td)

    missing = [
        s for s in stc.steps
        if (getattr(s, "context", {}) or {}).get("missing_fill")
        and "renda" in ((getattr(s, "context", {}) or {}).get("fill_label", "") or "").lower()
    ]
    assert not missing, \
        f"Renda mensal estava em form_values mas marcado como missing_fill: {missing}"
