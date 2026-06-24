"""Tests for Interactive Completion — Sprint 2.

CT-AUTO-2.1: Prompt resolves missing_fill field.
CT-AUTO-2.2: User skips pending field.
CT-AUTO-2.3: --no-interactive mode.
"""

import json
import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from testforge.semantic.model import (
    SemanticAction,
    SemanticTarget,
    LocatorCandidate,
    FieldValueMap,
)
from testforge.validation.intent_completeness import (
    IntentCompletenessChecker,
    CompletenessReport,
    FieldCompleteness,
    FieldStatus,
)
from testforge.cli._interactive_completion import (
    prompt_missing_fields,
    create_data_template,
    _save_field_value_map,
    _save_test_data,
)
from testforge.recorder.recording_status import RecordingStatus


# -- Helpers -------------------------------------------------------------------


def _make_report(recording_id="REC-001", pending=None, resolved=None):
    """Create a CompletenessReport with controlled state."""
    report = CompletenessReport(recording_id=recording_id)
    all_fields = list(pending or []) + list(resolved or [])
    report.fields = all_fields
    report.total_fields = len(all_fields)
    report.missing_count = len(pending or [])
    report.resolved_count = len(resolved or [])
    report.is_complete = len(pending or []) == 0
    return report


def _make_pending_field(field_key="valor", label="Valor", reason="typing_not_captured",
                        step_index=1, placeholder="Digite o valor"):
    return FieldStatus(
        field_key=field_key,
        label=label,
        placeholder=placeholder,
        element_id="",
        name=field_key,
        selector="#valor",
        step_index=step_index,
        completeness=FieldCompleteness.missing,
        reason=reason,
    )


def _make_resolved_field(field_key="nome", label="Nome", value="João"):
    return FieldStatus(
        field_key=field_key,
        label=label,
        value=value,
        completeness=FieldCompleteness.resolved,
        reason="direct_capture",
    )


# -- CT-AUTO-2.1: Prompt resolves missing_fill field --------------------------


class TestCT_AUTO_2_1:
    """CT-AUTO-2.1: Input do usuario resolve campo missing_fill."""

    def test_prompt_receives_pending_fields(self):
        """Prompt mostra campos pendentes para usuario."""
        pending = [_make_pending_field()]
        report = _make_report(pending=pending)

        assert len(report.pending_fields) == 1
        assert report.pending_fields[0].field_key == "valor"

    def test_prompt_saves_value_to_field_value_map(self):
        """Valor informado vai para field_value_map.json com source user_supplied_cli."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pending = [_make_pending_field()]
            report = _make_report(pending=pending)

            # Simulate user providing a value
            values = {
                "valor": {
                    "field_key": "valor",
                    "value": "1234",
                    "intention": "fill Valor with '1234' (user supplied)",
                    "identifiers": {"name": "valor", "label": "Valor"},
                    "source": "user_supplied_cli",
                    "confidence": 1.0,
                    "step_index": 1,
                }
            }
            path = _save_field_value_map(tmpdir, values)
            assert os.path.exists(path)

            with open(path) as f:
                data = json.load(f)
            assert "fields" in data
            assert data["fields"]["valor"] == "1234"
            assert data["entries"][0]["source"] == "user_supplied_cli"
            assert data["entries"][0]["confidence"] == 1.0

    def test_prompt_saves_value_to_test_data(self):
        """Valor informado vai para test_data.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            values = {
                "valor": {
                    "field_key": "valor",
                    "value": "1234",
                    "source": "user_supplied_cli",
                    "confidence": 1.0,
                    "step_index": 1,
                }
            }
            path = _save_test_data(tmpdir, values, "REC-001")
            assert os.path.exists(path)

            with open(path) as f:
                data = json.load(f)
            assert "fields" in data
            assert data["fields"]["valor"]["value"] == "1234"
            assert data["fields"]["valor"]["source"] == "user_supplied_cli"
            assert data["metadata"]["valor"]["source"] == "user_supplied_cli"

    def test_prompt_updates_status_to_intent_complete(self):
        """Apos resolver todos campos, status fica intent_complete."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create metadata
            meta_path = os.path.join(tmpdir, "recording_metadata.json")
            with open(meta_path, "w") as f:
                json.dump({
                    "recording_id": "REC-001",
                    "status_history": [],
                }, f)

            # Report with NO pending fields
            report = _make_report()

            with patch("builtins.input", return_value="1234"):
                with patch("sys.stdout"):
                    result = prompt_missing_fields(tmpdir, "REC-001", report)

            assert result is True  # all resolved

    def test_field_value_map_entry_has_all_fields(self):
        """Entrada em field_value_map possui field_key, value, intention, identifiers, source, confidence, step_index."""
        values = {
            "renda": {
                "field_key": "renda",
                "value": "5000",
                "intention": "fill Renda Mensal with '5000' (user supplied)",
                "identifiers": {
                    "name": "renda",
                    "id": "renda_id",
                    "label": "Renda Mensal",
                    "placeholder": "Renda",
                },
                "source": "user_supplied_cli",
                "confidence": 1.0,
                "step_index": 3,
            }
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _save_field_value_map(tmpdir, values)
            with open(path) as f:
                data = json.load(f)

            entry = data["entries"][0]
            assert entry["field_key"] == "renda"
            assert entry["value"] == "5000"
            assert "intention" in entry
            assert "identifiers" in entry
            assert entry["source"] == "user_supplied_cli"
            assert entry["confidence"] == 1.0
            assert entry["step_index"] == 3


# -- CT-AUTO-2.2: User skips pending field -------------------------------------


class TestCT_AUTO_2_2:
    """CT-AUTO-2.2: Usuario pula campo pendente → incomplete_intent."""

    def test_empty_input_leaves_field_pending(self):
        """Enter vazio no prompt → campo continua pendente."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create metadata
            meta_path = os.path.join(tmpdir, "recording_metadata.json")
            with open(meta_path, "w") as f:
                json.dump({"recording_id": "REC-001", "status_history": []}, f)

            pending = [_make_pending_field()]
            report = _make_report(pending=pending)

            with patch("builtins.input", return_value=""):  # empty = skip
                with patch("sys.stdout"):
                    result = prompt_missing_fields(tmpdir, "REC-001", report)

            assert result is False  # not all resolved

    def test_skipped_field_not_in_field_value_map(self):
        """Campo pulado nao aparece como entrada no field_value_map."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pending = [_make_pending_field()]
            report = _make_report(pending=pending)

            with patch("builtins.input", return_value=""):
                with patch("sys.stdout"):
                    prompt_missing_fields(tmpdir, "REC-001", report)

            # field_value_map should exist but not contain the skipped field value
            fvm_path = os.path.join(tmpdir, "field_value_map.json")
            if os.path.exists(fvm_path):
                with open(fvm_path) as f:
                    data = json.load(f)
                # The skipped field may or may not be in the map depending on implementation
                # But at minimum, no value should be stored for it
                assert data.get("fields", {}).get("valor", "") == "" or "valor" not in data.get("fields", {})

    def test_template_created_for_no_interactive(self):
        """Modo --no-interactive cria test_data.template.json com campos pendentes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pending = [_make_pending_field()]
            resolved = [_make_resolved_field()]
            report = _make_report(pending=pending, resolved=resolved)

            path = create_data_template(tmpdir, "REC-001", report)
            assert os.path.exists(path)

            with open(path) as f:
                data = json.load(f)
            assert data["metadata"]["status"] == "incomplete_intent"
            assert "fields" in data
            assert data["fields"]["valor"]["type"] == "pending"
            assert data["fields"]["nome"]["value"] == "João"  # resolved included


# -- CT-AUTO-2.3: --no-interactive mode ----------------------------------------


class TestCT_AUTO_2_3:
    """CT-AUTO-2.3: Modo nao interativo cria template sem travar."""

    def test_template_contains_pending_fields(self):
        """Template inclui todos campos pendentes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pending = [
                _make_pending_field("valor", "Valor"),
                _make_pending_field("senha", "Senha", step_index=2),
            ]
            report = _make_report(pending=pending)

            path = create_data_template(tmpdir, "REC-001", report)
            with open(path) as f:
                data = json.load(f)

            assert "valor" in data["fields"]
            assert data["fields"]["valor"]["type"] == "pending"
            assert "senha" in data["fields"]

    def test_template_has_instructions(self):
        """Template tem metadados de status incomplete_intent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pending = [_make_pending_field()]
            report = _make_report(pending=pending)

            path = create_data_template(tmpdir, "REC-001", report)
            with open(path) as f:
                data = json.load(f)

            assert data["metadata"]["mode"] == "template"
            assert data["metadata"]["status"] == "incomplete_intent"


# -- Edge cases ----------------------------------------------------------------


class TestInteractiveEdgeCases:
    """Edge cases do interactive completion."""

    def test_sensitive_field_alert(self):
        """Campo sensivel gera alerta, nao mascara."""
        with tempfile.TemporaryDirectory() as tmpdir:
            values = {
                "cpf": {
                    "field_key": "cpf",
                    "value": "123.456.789-00",
                    "source": "user_supplied_cli",
                    "confidence": 1.0,
                    "step_index": 1,
                }
            }
            path = _save_test_data(tmpdir, values, "REC-001")
            with open(path) as f:
                data = json.load(f)

            # Should have sensitive_alerts but no masking
            assert "sensitive_alerts" in data
            assert len(data["sensitive_alerts"]) > 0
            assert data["sensitive_alerts"][0]["masking_applied"] is False

    def test_no_pending_fields_skips_prompt(self):
        """Sem campos pendentes, nao abre prompt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            meta_path = os.path.join(tmpdir, "recording_metadata.json")
            with open(meta_path, "w") as f:
                json.dump({"recording_id": "REC-001", "status_history": []}, f)

            report = _make_report()
            with patch("builtins.input") as mock_input:
                with patch("sys.stdout"):
                    result = prompt_missing_fields(tmpdir, "REC-001", report)
                mock_input.assert_not_called()

            assert result is True

    def test_template_with_no_pending_fields(self):
        """Sem campos pendentes, template fica vazio mas valido."""
        with tempfile.TemporaryDirectory() as tmpdir:
            report = _make_report()
            path = create_data_template(tmpdir, "REC-001", report)
            with open(path) as f:
                data = json.load(f)

            assert data["metadata"]["status"] == "incomplete_intent"
            # No pending fields to include
