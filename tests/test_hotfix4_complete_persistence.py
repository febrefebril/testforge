"""Hotfix 4 — valores do prompt --complete persistidos entre chamadas normalize."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from testforge.semantic.recording_normalizer import RecordingNormalizer
from testforge.validation.intent_completeness import IntentCompletenessChecker


def _write_raw(rec_dir: str, events: list) -> None:
    os.makedirs(rec_dir, exist_ok=True)
    with open(os.path.join(rec_dir, "raw_events.jsonl"), "w",
              encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")


def _write_field_value_map(rec_dir: str, payload: dict) -> None:
    with open(os.path.join(rec_dir, "field_value_map.json"), "w",
              encoding="utf-8") as f:
        json.dump(payload, f)


class TestUserSuppliedMerge:
    def test_merges_into_empty_field_values(self):
        with tempfile.TemporaryDirectory() as d:
            _write_raw(d, [])
            _write_field_value_map(d, {
                "renda_mensal_*": {
                    "field_key": "renda_mensal_*", "value": "10000",
                    "intention": "fill Renda mensal * with '10000' (user supplied)",
                    "identifiers": {"label": "Renda mensal *"},
                    "source": "user_supplied_cli", "step_index": 25,
                },
            })
            stc = RecordingNormalizer().normalize(
                d, "ST-x", "app", "http://x/")
        assert "renda_mensal_*" in stc.field_values
        fv = stc.field_values["renda_mensal_*"]
        assert fv.value == "10000"
        assert fv.source == "user_supplied_cli"

    def test_does_not_overwrite_form_values(self):
        """Pre-seed stc.field_values para verificar que o merger respeita form_values."""
        from testforge.semantic.model import FieldValueMap
        with tempfile.TemporaryDirectory() as d:
            _write_raw(d, [])
            _write_field_value_map(d, {
                "renda_mensal_*": {
                    "value": "user_typed", "source": "user_supplied_cli",
                },
            })
            n = RecordingNormalizer()
            # Constroi um stc minimal diretamente e chama o merger para isolar a regra.
            from testforge.semantic.model import SemanticTestCase
            stc = SemanticTestCase(test_id="x", source_recording_id=os.path.basename(d))
            stc.field_values = {
                "renda_mensal_*": FieldValueMap(
                    field_key="renda_mensal_*", value="from_form_submit",
                    intention="trusted", identifiers={}, source="form_values",
                    step_index=0,
                ),
            }
            n._current_recording_dir = d
            n._merge_user_supplied_values(stc)
            # form_values ainda deve vencer
            assert stc.field_values["renda_mensal_*"].source == "form_values"
            assert stc.field_values["renda_mensal_*"].value == "from_form_submit"

    def test_idempotent_when_no_file(self):
        with tempfile.TemporaryDirectory() as d:
            _write_raw(d, [])
            stc1 = RecordingNormalizer().normalize(d, "ST-x", "app", "http://x/")
            stc2 = RecordingNormalizer().normalize(d, "ST-x", "app", "http://x/")
        assert stc1.field_values == stc2.field_values

    def test_meta_keys_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            _write_raw(d, [])
            _write_field_value_map(d, {
                "_meta": {"updated_at": "x"},
                "real_field": {"value": "v", "source": "user_supplied_cli"},
            })
            stc = RecordingNormalizer().normalize(d, "ST-x", "app", "http://x/")
        assert "_meta" not in stc.field_values
        assert any("real_field" in k for k in stc.field_values)


class TestEndToEndCompleteness:
    def test_second_run_sees_supplied_values(self):
        """Fim-a-fim: segunda chamada normalize() apos --complete deve ver os valores."""
        with tempfile.TemporaryDirectory() as d:
            _write_raw(d, [])
            normalizer = RecordingNormalizer()
            stc1 = normalizer.normalize(d, "ST-x", "app", "http://x/")
            assert stc1.field_values == {}
            # --complete prompt escreve o arquivo
            _write_field_value_map(d, {
                "renda_mensal_*": {"value": "10000",
                                     "source": "user_supplied_cli",
                                     "intention": "u"},
                "valor_do_imovel_*": {"value": "100000",
                                       "source": "user_supplied_cli",
                                       "intention": "u"},
            })
            stc2 = normalizer.normalize(d, "ST-x", "app", "http://x/")
            assert stc2.field_values["renda_mensal_*"].value == "10000"
            assert stc2.field_values["valor_do_imovel_*"].value == "100000"
            assert stc2.field_values["renda_mensal_*"].source == "user_supplied_cli"
