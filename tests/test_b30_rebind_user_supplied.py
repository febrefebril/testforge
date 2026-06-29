"""B30 — user_supplied_cli rebind from synthetic step_N keys.

When the normalizer cannot derive a canonical field_key from a step
(target.name / element_id / label / placeholder / test_id all empty),
it falls back to `step_{i+1}` and the completeness checker further
fallbacks to `field_step_{i}`. Both leak into field_value_map.json
via the `--complete` prompt.

On load, the merge layer used to apply the value under the same
synthetic key. Result: the runner's _resolve_field_value could not
match it against the SemanticAction's aria-label and the field stayed
empty at replay.

Fix: when applying an entry whose key looks synthetic AND a valid
step_index points at a step with a real target, rebind the key to that
step's accessible_name / label / name / placeholder / element_id and
preserve the discovered identifiers.

This file pins:
1. Synthetic keys (`step_*`, `field_step_*`, `select_step_*`) trigger
   rebind when step_index is valid.
2. Non-synthetic keys are left alone (back-compat for retro recordings
   where the prompt produced a real key).
3. The rebind preserves the user's value and source.
4. user_supplied_cli now appears in IR_SOURCE_PRIORITY at 89 (between
   user_supplied_inline 90 and fill_event 80).
"""
from __future__ import annotations

import json
from pathlib import Path

from testforge.semantic.model import (
    LocatorCandidate,
    SemanticAction,
    SemanticTarget,
    SemanticTestCase,
)
from testforge.semantic.recording_normalizer import RecordingNormalizer


class TestPriorityRanking:
    def test_user_supplied_cli_in_priority_table(self):
        p = RecordingNormalizer.IR_SOURCE_PRIORITY
        assert "user_supplied_cli" in p

    def test_cli_below_inline_above_fill_event(self):
        p = RecordingNormalizer.IR_SOURCE_PRIORITY
        assert p["user_supplied_inline"] > p["user_supplied_cli"]
        assert p["user_supplied_cli"] > p["fill_event"]
        assert p["user_supplied_cli"] > p["final_state"]
        assert p["user_supplied_cli"] > p["setter_hook"]

    def test_no_priority_collisions(self):
        p = RecordingNormalizer.IR_SOURCE_PRIORITY
        assert len(set(p.values())) == len(p)


def _make_stc_with_step(label: str, element_id: str = "") -> SemanticTestCase:
    target = SemanticTarget(
        accessible_name=label,
        label=label,
        placeholder="0,00",
        element_id=element_id,
        candidates=[LocatorCandidate("aria_label",
                                     f'input[aria-label="{label}"]',
                                     0.9, "aria_label")],
    )
    step = SemanticAction(action="click", target=target)
    stc = SemanticTestCase(test_id="X", source_recording_id="X")
    stc.steps = [step]
    return stc


def _write_field_value_map(rec_dir: Path, entries: list[dict]) -> None:
    payload = {
        "entries": entries,
        "_meta": {"writer": "interactive_completion"},
    }
    (rec_dir / "field_value_map.json").write_text(json.dumps(payload),
                                                  encoding="utf-8")


class TestRebindSyntheticKeys:
    def _normalize(self, tmp_path: Path, stc: SemanticTestCase,
                   entries: list[dict]) -> SemanticTestCase:
        # Drive _merge_user_supplied_values directly. Mirror what
        # normalize() sets up: a recording dir + field_value_map.json.
        rec_dir = tmp_path / "rec"
        rec_dir.mkdir()
        _write_field_value_map(rec_dir, entries)
        n = RecordingNormalizer()
        n._current_recording_dir = str(rec_dir)
        n._merge_user_supplied_values(stc)
        return stc

    def test_step_N_key_rebinds_to_step_label(self, tmp_path):
        """The exact failure mode from test-pos-hotfix10."""
        stc = _make_stc_with_step("Quanto vale seu imóvel hoje?*")
        stc.field_values = {}
        self._normalize(tmp_path, stc, [{
            "field_key": "step_25",
            "value": "1000000",
            "source": "user_supplied_cli",
            "step_index": 0,
            "identifiers": {},
        }])
        # The value must be stored under a key derived from the step
        # label, NOT under "step_25".
        assert "step_25" not in stc.field_values
        assert any("quanto_vale" in k.lower() for k in stc.field_values), (
            f"Rebind failed; got keys: {list(stc.field_values.keys())}"
        )

    def test_field_step_N_key_also_rebinds(self, tmp_path):
        stc = _make_stc_with_step("CPF")
        stc.field_values = {}
        self._normalize(tmp_path, stc, [{
            "field_key": "field_step_3",
            "value": "12345678900",
            "source": "user_supplied_cli",
            "step_index": 0,
            "identifiers": {},
        }])
        assert "field_step_3" not in stc.field_values
        assert "cpf" in stc.field_values

    def test_select_step_N_key_also_rebinds(self, tmp_path):
        stc = _make_stc_with_step("UF")
        stc.field_values = {}
        self._normalize(tmp_path, stc, [{
            "field_key": "select_step_2",
            "value": "DF",
            "source": "user_supplied_cli",
            "step_index": 0,
            "identifiers": {},
        }])
        assert "select_step_2" not in stc.field_values
        assert "uf" in stc.field_values

    def test_real_key_left_alone(self, tmp_path):
        stc = _make_stc_with_step("CPF")
        stc.field_values = {}
        # A key that DOESN'T look synthetic — back-compat with retro
        # recordings where the prompt produced a real label key.
        self._normalize(tmp_path, stc, [{
            "field_key": "cpf",
            "value": "12345678900",
            "source": "user_supplied_cli",
            "step_index": 0,
            "identifiers": {"label": "CPF"},
        }])
        assert "cpf" in stc.field_values
        # No spurious rebind.
        assert len(stc.field_values) == 1

    def test_invalid_step_index_keeps_key(self, tmp_path):
        stc = _make_stc_with_step("CPF")
        stc.field_values = {}
        # step_index out of range → no rebind possible.
        self._normalize(tmp_path, stc, [{
            "field_key": "step_99",
            "value": "x",
            "source": "user_supplied_cli",
            "step_index": 99,
            "identifiers": {},
        }])
        # Should still apply, just under the original (canonicalised) key.
        assert any("step_99" in k or "99" in k for k in stc.field_values)

    def test_identifiers_preserved_after_rebind(self, tmp_path):
        stc = _make_stc_with_step(
            "Quanto vale seu imóvel hoje?*",
            element_id="mat-input-2",
        )
        stc.field_values = {}
        self._normalize(tmp_path, stc, [{
            "field_key": "step_25",
            "value": "1000000",
            "source": "user_supplied_cli",
            "step_index": 0,
            "identifiers": {},
        }])
        key = next(iter(stc.field_values))
        fvm = stc.field_values[key]
        assert fvm.identifiers.get("aria_label") == "Quanto vale seu imóvel hoje?*"
        assert fvm.identifiers.get("label") == "Quanto vale seu imóvel hoje?*"
        assert fvm.identifiers.get("id") == "mat-input-2"
        assert fvm.value == "1000000"
        assert fvm.source == "user_supplied_cli"
