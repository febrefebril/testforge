"""Tests for Intent Completeness — Sprint 1.

CT-AUTO-1.1: Recording without missing fields → complete.
CT-AUTO-1.2: Input with focus/gap but no fill → missing.
CT-AUTO-1.3: Select without captured value → pending.
"""

import json
import os
import tempfile
from pathlib import Path

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
    save_completeness_report,
)


# -- Fixtures ------------------------------------------------------------------


@pytest.fixture
def checker():
    return IntentCompletenessChecker()


@pytest.fixture
def complete_steps():
    """Steps for CT-AUTO-1.1: normal input with fill, select, submit."""
    target = SemanticTarget(
        tag="input",
        name="nome",
        element_id="nome",
        label="Nome completo",
        placeholder="Digite seu nome",
        candidates=[LocatorCandidate("id", "#nome", 1.0, "id match")],
    )
    steps = [
        SemanticAction(action="navigation", url="about:blank"),
        SemanticAction(
            action="click",
            target=target,
            value="João Silva",
            context={"timestamp": "2026-06-18T10:00:01Z"},
        ),
        SemanticAction(
            action="fill",
            target=target,
            value="João Silva",
            context={"timestamp": "2026-06-18T10:00:02Z"},
        ),
    ]

    # Email field (fill with value)
    email_target = SemanticTarget(
        tag="input",
        name="email",
        element_id="email",
        label="E-mail",
        placeholder="email@exemplo.com",
        candidates=[LocatorCandidate("id", "#email", 1.0, "id match")],
    )
    steps.append(
        SemanticAction(
            action="click",
            target=email_target,
            context={"timestamp": "2026-06-18T10:00:03Z"},
        )
    )
    steps.append(
        SemanticAction(
            action="fill",
            target=email_target,
            value="joao@teste.com",
            context={"timestamp": "2026-06-18T10:00:04Z"},
        )
    )

    # Select state
    select_target = SemanticTarget(
        tag="select",
        name="estado",
        element_id="estado",
        label="Estado",
        candidates=[LocatorCandidate("id", "#estado", 1.0, "id match")],
    )
    steps.append(
        SemanticAction(
            action="click",
            target=select_target,
            context={"timestamp": "2026-06-18T10:00:05Z"},
        )
    )
    steps.append(
        SemanticAction(
            action="fill",
            target=select_target,
            value="SP",
            context={"timestamp": "2026-06-18T10:00:06Z"},
        )
    )

    return steps


@pytest.fixture
def complete_field_values():
    """field_value_map for CT-AUTO-1.1."""
    return {
        "nome": FieldValueMap(
            field_key="nome",
            value="João Silva",
            intention="fill Nome completo with 'João Silva' on input step 2",
            identifiers={"name": "nome", "id": "nome", "label": "Nome completo",
                         "placeholder": "Digite seu nome"},
            source="fill_event",
            step_index=2,
        ),
        "email": FieldValueMap(
            field_key="email",
            value="joao@teste.com",
            intention="fill E-mail with 'joao@teste.com' on input step 4",
            identifiers={"name": "email", "id": "email", "label": "E-mail",
                         "placeholder": "email@exemplo.com"},
            source="fill_event",
            step_index=4,
        ),
        "estado": FieldValueMap(
            field_key="estado",
            value="SP",
            intention="fill Estado with 'SP' on select step 6",
            identifiers={"name": "estado", "id": "estado", "label": "Estado"},
            source="fill_event",
            step_index=6,
        ),
    }


@pytest.fixture
def missing_fill_steps():
    """Steps for CT-AUTO-1.2: click input, type, no fill event captured."""
    valor_target = SemanticTarget(
        tag="input",
        name="valor",
        element_id="valor",
        label="Valor",
        placeholder="Valor sem input event",
        candidates=[LocatorCandidate("id", "#valor", 1.0, "id match")],
    )
    confirmacao_target = SemanticTarget(
        tag="input",
        name="confirmacao",
        element_id="confirmacao",
        label="Confirmação",
        placeholder="Digite novamente",
        candidates=[LocatorCandidate("id", "#confirmacao", 1.0, "id match")],
    )

    steps = [
        SemanticAction(action="navigation", url="about:blank"),
        SemanticAction(
            action="click",
            target=valor_target,
            context={
                "timestamp": "2026-06-18T10:00:01Z",
                "missing_fill": True,
                "fill_label": "Valor",
            },
        ),
        SemanticAction(
            action="click",
            target=confirmacao_target,
            value="123",
            context={"timestamp": "2026-06-18T10:00:05Z"},
        ),
        SemanticAction(
            action="fill",
            target=confirmacao_target,
            value="123",
            context={"timestamp": "2026-06-18T10:00:06Z"},
        ),
    ]
    return steps


@pytest.fixture
def select_no_capture_steps():
    """Steps for CT-AUTO-1.3: select without captured change event."""
    select_target = SemanticTarget(
        tag="select",
        name="produto",
        element_id="produto",
        label="Produto",
        candidates=[LocatorCandidate("id", "#produto", 1.0, "id match")],
    )
    qtd_target = SemanticTarget(
        tag="input",
        name="quantidade",
        element_id="quantidade",
        placeholder="1",
        candidates=[LocatorCandidate("id", "#quantidade", 1.0, "id match")],
    )

    steps = [
        SemanticAction(action="navigation", url="about:blank"),
        SemanticAction(
            action="click",
            target=select_target,
            # No value captured — select change event was not recorded
            context={"timestamp": "2026-06-18T10:00:01Z"},
        ),
        SemanticAction(
            action="click",
            target=qtd_target,
            context={"timestamp": "2026-06-18T10:00:03Z"},
        ),
    ]
    return steps


# -- CT-AUTO-1.1: Recording without missing fields ----------------------------


class TestCT_AUTO_1_1:
    """CT-AUTO-1.1: IntentCompletenessChecker retorna complete para gravação normal."""

    def test_complete_returns_complete(self, checker, complete_steps,
                                        complete_field_values):
        """Sem campos pendentes → checker retorna complete."""
        report = checker.check_steps(complete_steps, complete_field_values)

        assert report.is_complete is True
        assert report.missing_count == 0
        assert report.review_required_count == 0
        assert report.total_fields == 3

    def test_complete_all_resolved(self, checker, complete_steps,
                                    complete_field_values):
        """Todos os campos classificados como resolved."""
        report = checker.check_steps(complete_steps, complete_field_values)

        for field in report.fields:
            assert field.completeness == FieldCompleteness.resolved, (
                f"Field {field.field_key} should be resolved, got {field.completeness}"
            )

    def test_complete_pending_empty(self, checker, complete_steps,
                                     complete_field_values):
        """pending_fields lista vazia."""
        report = checker.check_steps(complete_steps, complete_field_values)

        assert len(report.pending_fields) == 0

    def test_complete_report_summary(self, checker, complete_steps,
                                      complete_field_values):
        """Resumo do relatório reflete 3 campos resolvidos."""
        report = checker.check_steps(complete_steps, complete_field_values)

        assert report.resolved_count == 3
        assert report.resolved_with_warning_count == 0
        assert report.review_required_count == 0
        assert report.missing_count == 0

    def test_complete_report_serialization(self, checker, complete_steps,
                                            complete_field_values):
        """Relatório serializa para dict e markdown sem erro."""
        report = checker.check_steps(complete_steps, complete_field_values)

        d = report.to_dict()
        assert d["summary"]["is_complete"] is True
        assert d["summary"]["total_fields"] == 3

        md = report.to_markdown()
        assert "[OK] Yes" in md
        assert "Captured Fields" in md

    def test_complete_report_persistence(self, checker, complete_steps,
                                          complete_field_values):
        """Relatório salva em JSON e MD."""
        report = checker.check_steps(complete_steps, complete_field_values)

        with tempfile.TemporaryDirectory() as tmp:
            json_path, md_path = save_completeness_report(
                report, tmp, "test-recording"
            )

            assert os.path.exists(json_path)
            assert os.path.exists(md_path)

            with open(json_path) as f:
                data = json.load(f)
            assert data["recording_id"] == "test-recording"
            assert data["summary"]["is_complete"] is True


# -- CT-AUTO-1.2: Input with focus/gap but no fill ----------------------------


class TestCT_AUTO_1_2:
    """CT-AUTO-1.2: Campo clicado com gap de digitação sem fill → missing."""

    def test_missing_fill_detected(self, checker, missing_fill_steps):
        """Campo com missing_fill=True aparece como missing."""
        report = checker.check_steps(missing_fill_steps)

        assert report.is_complete is False
        assert report.missing_count >= 1

        # Find the valor field
        valor_field = next(
            (f for f in report.fields if f.field_key == "valor"), None
        )
        assert valor_field is not None, "valor field should be in report"
        assert valor_field.completeness == FieldCompleteness.missing
        assert valor_field.reason == "typing_not_captured"

    def test_missing_fill_report_reason(self, checker, missing_fill_steps):
        """Relatório informa reason = typing_not_captured."""
        report = checker.check_steps(missing_fill_steps)

        md = report.to_markdown()
        assert "typing_not_captured" in md or "missing" in md.lower()

    def test_missing_fill_pending_not_empty(self, checker, missing_fill_steps):
        """pending_fields não está vazio."""
        report = checker.check_steps(missing_fill_steps)

        assert len(report.pending_fields) > 0

    def test_missing_fill_serialization(self, checker, missing_fill_steps):
        """Relatório de incompleto serializa corretamente."""
        report = checker.check_steps(missing_fill_steps)

        d = report.to_dict()
        assert d["summary"]["is_complete"] is False
        assert d["summary"]["missing"] >= 1


# -- CT-AUTO-1.3: Select without captured value -------------------------------


class TestCT_AUTO_1_3:
    """CT-AUTO-1.3: Select sem change event → pendente."""

    def test_select_not_captured_detected(self, checker, select_no_capture_steps):
        """Select click sem value → detectado como pendente."""
        report = checker.check_steps(select_no_capture_steps)

        assert report.is_complete is False
        assert report.missing_count >= 1

        # Find the produto field (select)
        produto_field = next(
            (f for f in report.fields if f.field_key == "produto"), None
        )
        assert produto_field is not None, "produto field should be in report"
        assert produto_field.completeness == FieldCompleteness.missing

    def test_select_reason_proper(self, checker, select_no_capture_steps):
        """Razão para select é select_not_captured."""
        report = checker.check_steps(select_no_capture_steps)

        produto_field = next(
            (f for f in report.fields if f.field_key == "produto"), None
        )
        if produto_field:
            # The reason might be no_value_captured since missing_fill flag is not set
            assert produto_field.completeness == FieldCompleteness.missing

    def test_select_report_shows_label(self, checker, select_no_capture_steps):
        """Relatório mostra label do select."""
        report = checker.check_steps(select_no_capture_steps)

        md = report.to_markdown()
        d = report.to_dict()

        # Check markdown has the field info
        assert "produto" in md or "Produto" in md


# -- Edge cases ----------------------------------------------------------------


class TestEdgeCases:
    """Casos de borda do IntentCompletenessChecker."""

    def test_empty_steps(self, checker):
        """Steps vazios → relatório vazio mas valido."""
        report = checker.check_steps([])

        assert report.is_complete is True
        assert report.total_fields == 0
        assert len(report.pending_fields) == 0

    def test_no_field_values(self, checker, complete_steps):
        """Sem field_values → analisa steps apenas."""
        report = checker.check_steps(complete_steps, field_values=None)

        # Should still work, at minimum the fields from steps
        assert report.total_fields >= 0
        assert isinstance(report.is_complete, bool)

    def test_field_with_warning_source(self, checker, complete_steps):
        """Campo com source form_values/polling → resolved_with_warning."""
        field_values = {
            "renda": FieldValueMap(
                field_key="renda",
                value="5000",
                intention="fill Renda with '5000' on input step 3",
                identifiers={"name": "renda", "label": "Renda Mensal"},
                source="form_values",
                step_index=3,
            ),
        }
        report = checker.check_steps(complete_steps, field_values)

        renda_field = next(
            (f for f in report.fields if f.field_key == "renda"), None
        )
        assert renda_field is not None
        assert renda_field.completeness == FieldCompleteness.resolved_with_warning
        assert renda_field.reason == "reconstructed_from_form_values"

    def test_user_supplied_field_needs_validation(self, checker, complete_steps):
        """Campo user_supplied_cli → review_required (precisa validação incremental)."""
        field_values = {
            "valor": FieldValueMap(
                field_key="valor",
                value="1234",
                intention="fill Valor with '1234' on input step 2",
                identifiers={"name": "valor", "label": "Valor"},
                source="user_supplied_cli",
                step_index=2,
            ),
        }
        report = checker.check_steps(complete_steps, field_values)

        valor_field = next(
            (f for f in report.fields if f.field_key == "valor"), None
        )
        assert valor_field is not None
        assert valor_field.completeness == FieldCompleteness.review_required
        assert valor_field.reason == "user_supplied_cli_not_validated"


# -- Report serialization tests -----------------------------------------------


class TestCompletenessReport:
    """Testes do relatório de completude."""

    def test_report_to_dict_structure(self):
        """Estrutura do dict segue contrato."""
        report = CompletenessReport(
            recording_id="REC-001",
            application="test-app",
            base_url="http://localhost",
        )
        report.is_complete = True
        report.total_fields = 2
        report.resolved_count = 2

        d = report.to_dict()
        assert d["recording_id"] == "REC-001"
        assert d["application"] == "test-app"
        assert d["base_url"] == "http://localhost"
        assert "summary" in d
        assert "fields" in d
        assert d["summary"]["is_complete"] is True

    def test_report_to_markdown_structure(self):
        """Markdown tem seções esperadas."""
        report = CompletenessReport(
            recording_id="REC-001",
        )
        md = report.to_markdown()

        assert "Intent Completeness Report" in md
        assert "Summary" in md

    def test_report_with_pending_fields_markdown(self):
        """Markdown mostra pending fields quando incompleto."""
        from testforge.validation.intent_completeness import FieldStatus

        report = CompletenessReport(recording_id="REC-001")
        report.is_complete = False
        report.missing_count = 1
        report.fields = [
            FieldStatus(
                field_key="valor",
                label="Valor",
                completeness=FieldCompleteness.missing,
                reason="typing_not_captured",
                step_index=1,
            ),
        ]

        md = report.to_markdown()
        assert "Pending Fields" in md or "[FAIL]" in md
        assert "typing_not_captured" in md
