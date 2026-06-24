"""Tests for Phase B — downstream evidence consumption.

Verifies IntentReconstructor reads value_mutations, checked transitions,
and final_state; and RecordingNormalizer uses evidence before missing_fill.
"""

import json
import os
import tempfile

import pytest

from testforge.semantic.model import SemanticAction, SemanticTarget
from testforge.semantic.recording_normalizer import RecordingNormalizer


@pytest.fixture
def reconstructor():
    return RecordingNormalizer()


@pytest.fixture
def recording_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def _make_step(action="click", tag="input", name="campo1", value="",
               timestamp="2026-06-18T10:00:00Z", text="", label="Campo 1",
               placeholder="Digite", el_id="campo1"):
    target = SemanticTarget(
        tag=tag, name=name, element_id=el_id,
        label=label, placeholder=placeholder, text=text,
    )
    return SemanticAction(
        action=action, target=target, value=value,
        url="http://localhost/test", page_title="Test",
        context={"timestamp": timestamp},
    )


def _snapshot_batch(fp, value="", checked=None, field_type="text", tag="input",
                    name="campo1", label="Campo 1", ts="2026-06-18T10:00:01Z"):
    return json.dumps({
        "timestamp": ts,
        "snapshots": [{
            "timestamp": ts,
            "fingerprint": fp,
            "identifiers": {
                "id": name, "name": name, "label": label,
                "placeholder": None, "aria-label": None, "css_path": f"#{name}",
            },
            "tag": tag,
            "type": field_type,
            "value": value,
            "checked": checked,
            "visibility": "visible",
            "enabled": True,
        }],
        "count": 1,
    })


class TestSetterHookReconstruction:
    def test_value_mutations_currency_mask(self, reconstructor, recording_dir):
        path = os.path.join(recording_dir, "value_mutations.jsonl")
        with open(path, "w") as f:
            f.write(json.dumps({
                "type": "value_mutation",
                "timestamp": "2026-06-18T10:00:01Z",
                "tag": "input", "name": "renda", "id": "renda",
                "old_value": "", "new_value": "10.000,00",
                "fingerprint": "input#renda[name=renda]",
            }) + "\n")

        steps = [_make_step(name="renda", label="Renda", el_id="renda",
                            timestamp="2026-06-18T10:00:00Z")]
        entries = reconstructor._ir_value_mutations(recording_dir, steps)

        assert len(entries) == 1
        assert entries[0]["source"] == "setter_hook"
        assert entries[0]["value"] == "10.000,00"
        assert entries[0]["field_key"] == "renda"

    def test_value_mutations_last_wins(self, reconstructor, recording_dir):
        path = os.path.join(recording_dir, "value_mutations.jsonl")
        with open(path, "w") as f:
            for val in ("1", "12", "1.234,56"):
                f.write(json.dumps({
                    "type": "value_mutation",
                    "timestamp": "2026-06-18T10:00:01Z",
                    "tag": "input", "name": "valor", "id": "valor",
                    "old_value": "", "new_value": val,
                    "fingerprint": "input#valor[name=valor]",
                }) + "\n")

        entries = reconstructor._ir_value_mutations(recording_dir, [])
        assert entries[0]["value"] == "1.234,56"


class TestCheckedTransition:
    def test_radio_checked_transition(self, reconstructor, recording_dir):
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        fp = "input#mat-radio-5[name=experiencia]"
        with open(path, "w") as f:
            f.write(_snapshot_batch(fp, checked=False, field_type="radio",
                                    name="experiencia", label="",
                                    ts="2026-06-18T10:00:00Z") + "\n")
            f.write(_snapshot_batch(fp, checked=True, field_type="radio",
                                    name="experiencia",
                                    label="Sim, tenho 3 anos ou mais",
                                    ts="2026-06-18T10:00:01Z") + "\n")

        steps = [_make_step(tag="label", text="Sim, tenho 3 anos ou mais",
                            timestamp="2026-06-18T10:00:01Z")]
        entries = reconstructor._ir_snapshots(recording_dir, steps)

        assert len(entries) == 1
        assert entries[0]["source"] == "checked_transition"
        assert "Sim, tenho 3 anos ou mais" in entries[0]["value"]

    def test_checkbox_checked_transition(self, reconstructor, recording_dir):
        path = os.path.join(recording_dir, "field_snapshots.jsonl")
        fp = "input#mat-mdc-checkbox-0[name=aceite]"
        with open(path, "w") as f:
            f.write(_snapshot_batch(fp, checked=False, field_type="checkbox",
                                    name="aceite", label="Aceito os termos",
                                    ts="2026-06-18T10:00:00Z") + "\n")
            f.write(_snapshot_batch(fp, checked=True, field_type="checkbox",
                                    name="aceite", label="Aceito os termos",
                                    ts="2026-06-18T10:00:01Z") + "\n")

        entries = reconstructor._ir_snapshots(recording_dir, [])
        assert len(entries) == 1
        assert entries[0]["source"] == "checked_transition"
        assert entries[0]["value"] == "Aceito os termos"


class TestFinalState:
    def test_final_state_fallback(self, reconstructor, recording_dir):
        path = os.path.join(recording_dir, "final_state_snapshot.json")
        with open(path, "w") as f:
            json.dump({
                "reason": "recording_stopped",
                "timestamp": "2026-06-18T10:05:00Z",
                "fields": [{
                    "fingerprint": "input#renda[name=renda]",
                    "identifiers": {"name": "renda", "label": "Renda bruta mensal"},
                    "tag": "input", "type": "text",
                    "value": "10.000,00", "checked": None,
                }],
            }, f)

        entries = reconstructor._ir_final_state(recording_dir, [])
        assert len(entries) == 1
        assert entries[0]["source"] == "final_state"
        assert entries[0]["value"] == "10.000,00"


class TestReconstructAllPriority:
    def test_form_values_beats_final_state(self, reconstructor, recording_dir):
        snap_path = os.path.join(recording_dir, "final_state_snapshot.json")
        with open(snap_path, "w") as f:
            json.dump({
                "timestamp": "2026-06-18T10:05:00Z",
                "fields": [{
                    "fingerprint": "input#tel[name=telefone]",
                    "identifiers": {"name": "telefone", "label": "Telefone"},
                    "tag": "input", "type": "text",
                    "value": "final_val", "checked": None,
                }],
            }, f)

        steps = [_make_step(name="telefone", timestamp="2026-06-18T10:00:00Z")]
        steps[0].context["form_values"] = {"telefone": "form_val"}

        entries = reconstructor._ir_all(recording_dir, steps)
        tel = [e for e in entries if e["field_key"] == "telefone"]
        assert len(tel) == 1
        assert tel[0]["source"] == "form_values"
        assert tel[0]["value"] == "form_val"


class TestNormalizerPhaseB:
    def _write_raw_click(self, recording_dir, tag="input", name="renda",
                         label="Renda", el_id="renda", ts="2026-06-18T10:00:00Z"):
        events_path = os.path.join(recording_dir, "raw_events.jsonl")
        with open(events_path, "w") as f:
            f.write(json.dumps({
                "event_id": "evt_00001", "type": "click",
                "timestamp": ts,
                "url": "http://localhost/test", "page_title": "Test",
                "target": {
                    "tag": tag, "id": el_id, "name": name,
                    "label": label, "placeholder": "", "value": "",
                },
                "value": None, "is_postback": False,
            }) + "\n")
            f.write(json.dumps({
                "event_id": "evt_00002", "type": "click",
                "timestamp": "2026-06-18T10:00:15Z",
                "url": "http://localhost/test", "page_title": "Test",
                "target": {"tag": "button", "id": "btn", "text": "Continuar"},
                "value": None, "is_postback": False,
            }) + "\n")

    def test_setter_hook_resolves_missing_fill(self, recording_dir):
        self._write_raw_click(recording_dir, name="renda", label="Renda", el_id="renda")

        mut_path = os.path.join(recording_dir, "value_mutations.jsonl")
        with open(mut_path, "w") as f:
            f.write(json.dumps({
                "type": "value_mutation",
                "timestamp": "2026-06-18T10:00:05Z",
                "tag": "input", "name": "renda", "id": "renda",
                "old_value": "", "new_value": "10.000,00",
                "fingerprint": "input#renda[name=renda]",
            }) + "\n")

        stc = RecordingNormalizer().normalize(recording_dir, test_id="ST-PHASE-B")

        assert "renda" in stc.field_values
        assert stc.field_values["renda"].value == "10.000,00"
        assert stc.field_values["renda"].source == "setter_hook"
        assert not any(bs["pattern"] == "typing_not_captured" for bs in stc.blind_spots)

    def test_radio_label_resolved_via_checked_transition(self, recording_dir):
        events_path = os.path.join(recording_dir, "raw_events.jsonl")
        with open(events_path, "w") as f:
            f.write(json.dumps({
                "event_id": "evt_00001", "type": "click",
                "timestamp": "2026-06-18T10:00:00Z",
                "url": "http://localhost/test", "page_title": "Test",
                "target": {
                    "tag": "label", "id": "", "name": "",
                    "text": "Sim, tenho 3 anos ou mais",
                    "label": "Sim, tenho 3 anos ou mais",
                },
                "value": None, "is_postback": False,
            }) + "\n")

        snap_path = os.path.join(recording_dir, "field_snapshots.jsonl")
        fp = "input#mat-radio-5[name=experiencia]"
        with open(snap_path, "w") as f:
            f.write(_snapshot_batch(fp, checked=False, field_type="radio",
                                    ts="2026-06-18T10:00:00Z") + "\n")
            f.write(_snapshot_batch(fp, checked=True, field_type="radio",
                                    label="Sim, tenho 3 anos ou mais",
                                    ts="2026-06-18T10:00:01Z") + "\n")

        stc = RecordingNormalizer().normalize(recording_dir, test_id="ST-RADIO")

        resolved = [v for v in stc.field_values.values() if v.value]
        assert any("Sim, tenho 3 anos ou mais" in v.value for v in resolved)
        assert stc.steps[0].value == "Sim, tenho 3 anos ou mais"

    def test_blind_spots_stored_on_stc(self, recording_dir):
        self._write_raw_click(recording_dir, name="campo_sem_evidencia",
                              label="Campo X", el_id="campo_x")

        stc = RecordingNormalizer().normalize(recording_dir, test_id="ST-BS")
        assert isinstance(stc.blind_spots, list)
