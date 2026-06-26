"""Hotfix 22: value_mutations.jsonl writer/reader contract + element_id.

The overlay JS (_hookValue in overlay_inject.js) and the normalizer's
_ir_value_mutations had different schemas — writer wrote
`{type, timestamp, fingerprint, value}`, reader expected `new_value`,
`tag`, `id`, `name`, `old_value`. Reader silently returned an empty
list, so every masked field that the recorder had successfully
captured ended up on the --complete prompt as `typing_not_captured`.

Same bug class produced a second mismatch: _extractTarget emits
`element_id` while the normalizer's SemanticTarget builder looked for
`id`. Both fixes pin the writer/reader contract.
"""
from __future__ import annotations

import json
from testforge.semantic.recording_normalizer import RecordingNormalizer


def _write_mutations(tmp_path, mutations):
    path = tmp_path / "value_mutations.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for m in mutations:
            f.write(json.dumps(m) + "\n")


def test_value_mutations_reader_uses_value_key(tmp_path):
    """The reader must consume the `value` key — not `new_value`."""
    _write_mutations(tmp_path, [
        {"type": "value_mutation", "timestamp": "2026-06-26T18:00:00Z",
         "fingerprint": "input#mat-input-1[name=]", "value": " 1.000,00 "},
    ])
    n = RecordingNormalizer()
    entries = n._ir_value_mutations(str(tmp_path), [])
    assert len(entries) == 1
    assert entries[0]["value"] == "1.000,00"
    # Fingerprint parsed correctly
    ids = entries[0]["identifiers"]
    assert ids["id"] == "mat-input-1"
    assert ids["tag"] == "input"


def test_value_mutations_keeps_last_value_per_fingerprint(tmp_path):
    """Masks emit partial values during typing; only the last is the
    user's intended final value."""
    _write_mutations(tmp_path, [
        {"type": "value_mutation", "timestamp": "2026-06-26T18:00:00Z",
         "fingerprint": "input#mat-input-1[name=]", "value": "100,00"},
        {"type": "value_mutation", "timestamp": "2026-06-26T18:00:01Z",
         "fingerprint": "input#mat-input-1[name=]", "value": "1.000,00"},
        {"type": "value_mutation", "timestamp": "2026-06-26T18:00:02Z",
         "fingerprint": "input#mat-input-1[name=]", "value": "10.000,00"},
    ])
    n = RecordingNormalizer()
    entries = n._ir_value_mutations(str(tmp_path), [])
    assert len(entries) == 1
    assert entries[0]["value"] == "10.000,00"


def test_value_mutations_empty_values_are_skipped(tmp_path):
    """Initial empty state (focus, blur) should not produce entries."""
    _write_mutations(tmp_path, [
        {"type": "value_mutation", "timestamp": "...",
         "fingerprint": "input#mat-input-1[name=]", "value": ""},
        {"type": "value_mutation", "timestamp": "...",
         "fingerprint": "input#mat-input-1[name=]", "value": "1.000,00"},
    ])
    n = RecordingNormalizer()
    entries = n._ir_value_mutations(str(tmp_path), [])
    assert len(entries) == 1
    assert entries[0]["value"] == "1.000,00"


def test_value_mutations_correlates_by_element_id(tmp_path):
    """When a step's target.element_id matches the mutation fingerprint
    id, that step's aria_label / placeholder become the canonical key
    of the entry. This is how a `mat_input_1` fingerprint gets renamed
    to `prestação_desejada_*` so the runtime resolver can match it."""
    from testforge.semantic.model import SemanticAction, SemanticTarget

    target = SemanticTarget(
        accessible_name="Prestação desejada *",
        placeholder="R$0,00",
        element_id="mat-input-1",
        tag="input",
    )
    step = SemanticAction(action="click", target=target)

    _write_mutations(tmp_path, [
        {"type": "value_mutation", "timestamp": "2026-06-26T18:00:00Z",
         "fingerprint": "input#mat-input-1[name=]", "value": "1.000,00"},
    ])
    n = RecordingNormalizer()
    entries = n._ir_value_mutations(str(tmp_path), [step])
    assert len(entries) == 1
    assert entries[0]["field_key"] == "prestação_desejada_*"
    assert entries[0]["value"] == "1.000,00"


def test_value_mutations_correlates_via_selector_chain(tmp_path):
    """When element_id is not on the target but appears in a candidate
    selector, the correlation still finds the right step."""
    from testforge.semantic.model import (
        SemanticAction, SemanticTarget, LocatorCandidate,
    )

    target = SemanticTarget(
        accessible_name="Renda mensal *",
        placeholder="R$0,00",
        element_id="",
        candidates=[LocatorCandidate(
            strategy="css", score=1.0,
            selector="form > mat-form-field > input#mat-input-3.mat-mdc-input-element",
        )],
    )
    step = SemanticAction(action="click", target=target)

    _write_mutations(tmp_path, [
        {"type": "value_mutation", "timestamp": "...",
         "fingerprint": "input#mat-input-3[name=]", "value": "2.000,00"},
    ])
    n = RecordingNormalizer()
    entries = n._ir_value_mutations(str(tmp_path), [step])
    assert len(entries) == 1
    assert entries[0]["field_key"] == "renda_mensal_*"


def test_build_target_reads_element_id_from_overlay_schema():
    """The overlay JS writes element_id; the SemanticTarget builder
    used to look for `id`. Both keys must populate element_id."""
    n = RecordingNormalizer()
    target_data = {
        "tag": "input",
        "accessible_name": "Prestação desejada *",
        "placeholder": "R$0,00",
        "element_id": "mat-input-1",   # overlay-style key
        "css_path": "input#mat-input-1",
    }
    target = n._build_target(target_data)
    assert target.element_id == "mat-input-1"


def test_build_target_falls_back_to_id_key():
    """Back-compat: legacy events with `id` still populate element_id."""
    n = RecordingNormalizer()
    target = n._build_target({
        "tag": "input",
        "id": "legacy-id-format",
        "css_path": "input#legacy-id-format",
    })
    assert target.element_id == "legacy-id-format"
