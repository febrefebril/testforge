"""H16 — Consolidacao de semantica de veredito.

Bug: `deve_logar_no_gas_do_povo_3` reportou verdict=pass com steps=0.
Dashboards mostravam verde para gravacoes sem nada executado. QA piloto nao
pode confiar em vereditos.

Nova regra (NEXT-SESSION.md):
    verdict == "pass" sse (
        criteria_passed == criteria_total
        AND steps.passed + steps.healed > 0
        AND (steps.failed + steps.healing_rejected) == 0
    )

Caso contrario:
    - 5 criterios verdes, 0 steps executaveis → GATED_ONLY (novo)
    - qualquer step falhou ou healing_rejected → FAIL
    - criterios falham → FAIL ou NEEDS_REVIEW
"""
from __future__ import annotations

from dataclasses import dataclass, field

from testforge.validation.readiness_gate import (
    ReadinessVerdict,
    RecordingReadinessGate,
)
from testforge.validation.intent_completeness import (
    CompletenessReport,
    FieldCompleteness,
    FieldStatus,
)
from testforge.recorder.recording_status import RecordingStatus


@dataclass
class StepStub:
    step_num: int
    action: str = "click"
    status: str = "passed"
    error_message: str = ""
    blocking: bool = False
    healing: object = None
    precondition: object = None
    postcondition: object = None
    value: str = ""
    original_locator: str = ""
    selected_locator: str = ""
    skip_reason: str = ""


def _complete_report() -> CompletenessReport:
    fields = [
        FieldStatus(
            field_key="nome",
            label="Nome",
            value="X",
            source="fill_event",
            completeness=FieldCompleteness.resolved,
            reason="ok",
        ),
    ]
    report = CompletenessReport(
        recording_id="rec-h16",
        total_fields=len(fields),
        resolved_count=len(fields),
        resolved_with_warning_count=0,
        review_required_count=0,
        missing_count=0,
        is_complete=True,
    )
    report.fields = fields
    return report


def _eval(steps, completeness=None) -> object:
    gate = RecordingReadinessGate()
    return gate.evaluate(
        recording_id="rec-h16",
        application="web",
        base_url="http://localhost",
        completeness_report=completeness or _complete_report(),
        step_results=steps,
    )


# ---- Invariantes centrais H16 ----------------------------------------------------


def test_criteria_green_zero_steps_returns_gated_only():
    """5 criterios passam, 0 steps → GATED_ONLY (era PASS pre-H16)."""
    report = _eval(steps=[])
    assert report.verdict == ReadinessVerdict.GATED_ONLY, (
        f"Esperado GATED_ONLY quando nenhum step executou, obteve {report.verdict}"
    )
    assert report.status == RecordingStatus.needs_review


def test_criteria_green_only_skipped_steps_returns_gated_only():
    """Todos ignorados → nenhuma execucao bem-sucedida → GATED_ONLY."""
    steps = [
        StepStub(step_num=1, status="skipped", skip_reason="duplicate"),
        StepStub(step_num=2, status="skipped", skip_reason="duplicate"),
    ]
    report = _eval(steps)
    assert report.verdict == ReadinessVerdict.GATED_ONLY


def test_criteria_green_one_passed_zero_failed_returns_pass():
    """Barra minima de sucesso: ao menos 1 step executado e nenhuma falha."""
    steps = [StepStub(step_num=1, status="passed")]
    report = _eval(steps)
    assert report.verdict == ReadinessVerdict.PASS
    assert report.status == RecordingStatus.ready_for_team


def test_criteria_green_many_passed_zero_failed_returns_pass():
    steps = [StepStub(step_num=i, status="passed") for i in range(1, 6)]
    report = _eval(steps)
    assert report.verdict == ReadinessVerdict.PASS


def test_healed_validated_counts_as_successful_execution():
    """healed_validated e uma execucao bem-sucedida (passou via healing)."""
    steps = [StepStub(step_num=1, status="healed_validated")]
    report = _eval(steps)
    assert report.verdict == ReadinessVerdict.PASS


def test_any_failed_step_returns_fail():
    """1 passo + 1 falha → FAIL, mesmo com criterios verdes."""
    steps = [
        StepStub(step_num=1, status="passed"),
        StepStub(step_num=2, status="failed", error_message="timeout"),
    ]
    report = _eval(steps)
    assert report.verdict == ReadinessVerdict.FAIL


def test_healing_rejected_step_returns_fail():
    """healing_rejected conta como falha no H16."""
    steps = [
        StepStub(step_num=1, status="passed"),
        StepStub(step_num=2, status="healing_rejected",
                 error_message="oracle failed"),
    ]
    report = _eval(steps)
    assert report.verdict == ReadinessVerdict.FAIL


def test_all_failed_returns_fail():
    steps = [
        StepStub(step_num=1, status="failed", error_message="boom"),
        StepStub(step_num=2, status="failed", error_message="boom"),
    ]
    report = _eval(steps)
    assert report.verdict == ReadinessVerdict.FAIL


# ---- Caminhos de falha de criterios ------------------------------------------------


def test_completeness_failure_returns_fail():
    fields = [
        FieldStatus(
            field_key="uf",
            label="UF",
            value="",
            source="fill_event",
            completeness=FieldCompleteness.missing,
            reason="absent",
        ),
    ]
    incomplete = CompletenessReport(
        recording_id="rec-h16",
        total_fields=1,
        resolved_count=0,
        resolved_with_warning_count=0,
        review_required_count=0,
        missing_count=1,
        is_complete=False,
    )
    incomplete.fields = fields
    steps = [StepStub(step_num=1, status="passed")]
    report = _eval(steps, completeness=incomplete)
    assert report.verdict == ReadinessVerdict.FAIL


# ---- Integridade do relatorio --------------------------------------------------


def test_gated_only_emits_warning():
    """GATED_ONLY exibe um aviso explicando a ausencia de evidencia de execucao."""
    report = _eval(steps=[])
    assert any(
        "no executable step" in w.lower() or "dashboard" in w.lower()
        for w in report.warnings
    ), f"Esperado aviso sobre execucao vazia, obteve {report.warnings}"


def test_gated_only_markdown_renders_new_section():
    """to_markdown emite um bloco GATED dedicado (nao a secao verde PASS)."""
    report = _eval(steps=[])
    md = report.to_markdown()
    assert "GATED" in md or "gated" in md.lower()
    assert "Ready for Team" not in md
