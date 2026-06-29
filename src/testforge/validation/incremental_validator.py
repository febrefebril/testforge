"""TestForge — Validador Incremental de Gravação.

Orquestra o pipeline de validação para uma gravação completa:
1. Normaliza eventos brutos → SemanticTestCase
2. Verifica completude (IntentCompletenessChecker)
3. Re-executa passos incrementalmente (IncrementalRunner)
4. Avalia portão de prontidão (RecordingReadinessGate)
5. Salva relatórios

O validador é a ponte entre Sprint 1-4 (completude + reconstrução)
e Sprint 5+ (validação incremental + portão de prontidão).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from testforge.recorder.recording_status import (
    RecordingStatus,
    RecordingStatusHistory,
    RecordingStatusEntry,
)
from testforge.validation.intent_completeness import (
    IntentCompletenessChecker,
    CompletenessReport,
    save_completeness_report,
)
from testforge.validation.readiness_gate import (
    RecordingReadinessGate,
    ReadinessReport,
    ReadinessVerdict,
    save_readiness_report,
)


class IncrementalRecordingValidator:
    """Valida uma gravação normalizando, verificando completude,
    e executando incrementalmente antes de avaliar prontidão."""

    def __init__(
        self,
        recording_dir: str,
        output_dir: str = "",
        headless: bool = True,
        timeout: int = 60,
        browser: str = "chromium",
        interactive: bool = False,
        no_healing: bool = False,
    ):
        self.recording_dir = recording_dir
        self.output_dir = output_dir or recording_dir
        self.headless = headless
        self.timeout = timeout
        self.browser_type = browser
        self.interactive = interactive
        self.no_healing = no_healing

        self.application = ""
        self.base_url = ""
        self.recording_id = ""

        self.status_history = RecordingStatusHistory()
        self.semantic_test_case = None
        self.completeness_report: Optional[CompletenessReport] = None
        self.readiness_report: Optional[ReadinessReport] = None
        self.step_results: list = []

    def _get_recording_metadata(self) -> dict:
        """Carrega metadados da gravacao de recording.json se existir."""
        meta_path = os.path.join(self.recording_dir, "recording.json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                return json.load(f)
        return {}

    def _normalize(self) -> bool:
        """Normaliza eventos brutos em SemanticTestCase.

        Returns:
            True se normalizacao bem-sucedida.
        """
        from testforge.semantic.recording_normalizer import RecordingNormalizer

        try:
            normalizer = RecordingNormalizer()
            self.semantic_test_case = normalizer.normalize(
                self.recording_dir,
                test_id=f"ST-{self.recording_id}",
                application=self.application,
                base_url=self.base_url,
            )
            self.status_history.record(
                RecordingStatus.intent_reconstructed,
                reason="Normalizacao concluida com sucesso",
            )
            return True
        except Exception as exc:
            import sys
            print(f"[TestForge] Normalizacao falhou: {exc}", file=sys.stderr)
            self.status_history.record(
                RecordingStatus.incomplete_intent,
                reason=f"Normalizacao falhou: {exc}",
            )
            return False

    def _check_completeness(self) -> CompletenessReport:
        """Verifica completude da gravacao normalizada.

        Returns:
            CompletenessReport com status por campo.
        """
        checker = IntentCompletenessChecker()
        report = checker.check_steps(
            steps=self.semantic_test_case.steps if self.semantic_test_case else [],
            field_values=(
                self.semantic_test_case.field_values
                if self.semantic_test_case
                else None
            ),
        )
        report.recording_id = self.recording_id
        report.application = self.application
        report.base_url = self.base_url

        if report.is_complete:
            self.status_history.record(
                RecordingStatus.intent_complete,
                reason="Todos os campos resolvidos",
                metadata={
                    "total_fields": report.total_fields,
                    "resolved": report.resolved_count,
                    "resolved_with_warning": report.resolved_with_warning_count,
                },
            )
        elif report.missing_count > 0:
            self.status_history.record(
                RecordingStatus.incomplete_intent,
                reason=f"{report.missing_count} campo(s) ausente(s)",
                metadata={
                    "missing": report.missing_count,
                    "review_required": report.review_required_count,
                },
            )
        elif report.review_required_count > 0:
            self.status_history.record(
                RecordingStatus.needs_user_input,
                reason=f"{report.review_required_count} campo(s) requerem revisao",
            )

        self.completeness_report = report
        return report

    def _run_incremental(self) -> list:
        """Executa execucao incremental nos passos normalizados.

        Encapsula IncrementalRunner para validar que passos executam
        corretamente com os valores de campo resolvidos.

        Returns:
            Lista de objetos IncrementalStepResult.
        """
        from testforge.runner.incremental_runner import IncrementalRunner

        if not self.semantic_test_case or not self.semantic_test_case.steps:
            return []

        # Encontra o caminho do script compilado se existir
        script_path = self._find_compiled_script()

        self.status_history.record(
            RecordingStatus.incremental_validation_running,
            reason=f"Iniciando validacao incremental de {len(self.semantic_test_case.steps)} step(s)",
        )

        if script_path and os.path.exists(script_path):
            # Usa script compilado para reproducao
            runner = IncrementalRunner(
                script_path=script_path,
                headless=self.headless,
                timeout=self.timeout,
                verbose=not self.headless,
                browser=self.browser_type,
                stop_on_failure=False,
                interactive=self.interactive,
                no_healing=self.no_healing,
                output_root=os.path.join(self.output_dir, "validation_run"),
            )
        else:
            # Executa diretamente dos passos semanticos — cria script minimo
            # que IncrementalRunner pode carregar
            runner = self._make_runner_from_steps()

        try:
            report = runner.run()
            self.step_results = report.get("steps", []) if isinstance(report, dict) else []
        except Exception as exc:
            import sys
            print(f"[TestForge] [ERRO] Validacao incremental: {exc}", file=sys.stderr)
            self.step_results = []

        return self.step_results

    def _find_compiled_script(self) -> str:
        """Encontra script de teste compilado no diretorio da gravacao."""
        for entry in os.listdir(self.recording_dir):
            if entry.startswith("test_") and entry.endswith(".py"):
                return os.path.join(self.recording_dir, entry)
        return ""

    def _make_runner_from_steps(self):
        """Cria IncrementalRunner configurado para executar diretamente de passos semanticos.

        Como IncrementalRunner espera um caminho de script, criamos um runner
        configurado apenas com a URL base e passos.
        """
        from testforge.runner.incremental_runner import IncrementalRunner

        runner = IncrementalRunner(
            script_path="",
            headless=self.headless,
            timeout=self.timeout,
            verbose=not self.headless,
            browser=self.browser_type,
            stop_on_failure=False,
            interactive=self.interactive,
            no_healing=self.no_healing,
            output_root=os.path.join(self.output_dir, "validation_run"),
        )
        runner.recording_id = self.recording_id
        runner.base_url = self.base_url or ""
        runner.steps = self.semantic_test_case.steps if self.semantic_test_case else []
        runner._field_value_map = (
            self.semantic_test_case.field_values if self.semantic_test_case else {}
        )
        return runner

    def _evaluate_gate(self) -> ReadinessReport:
        """Avalia portao de prontidao com resultados atuais.

        Returns:
            ReadinessReport com veredito final.
        """
        gate = RecordingReadinessGate()
        report = gate.evaluate(
            recording_id=self.recording_id,
            application=self.application,
            base_url=self.base_url,
            completeness_report=self.completeness_report,
            step_results=self.step_results,
            field_values=(
                self.semantic_test_case.field_values
                if self.semantic_test_case
                else None
            ),
        )

        self.readiness_report = report

        # Registra status final
        if report.verdict == ReadinessVerdict.PASS:
            self.status_history.record(
                RecordingStatus.ready_for_team,
                reason="Todos os criterios de prontidao aprovados",
                metadata={"verdict": "pass"},
            )
        elif report.verdict == ReadinessVerdict.NEEDS_REVIEW:
            self.status_history.record(
                RecordingStatus.needs_review,
                reason=f"{len(report.failures)} failure(s) need review",
                metadata={
                    "failures": report.failures,
                    "verdict": "needs_review",
                },
            )
        else:
            self.status_history.record(
                RecordingStatus.incomplete_intent,
                reason=f"{len(report.failures)} blocking failure(s)",
                metadata={
                    "failures": report.failures,
                    "verdict": "fail",
                },
            )

        return report

    def _save_status_history(self):
        """Salva historico de status no diretorio da gravacao."""
        history_path = os.path.join(self.output_dir, "status_history.json")
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "recording_id": self.recording_id,
                    "entries": self.status_history.to_dict(),
                    "current_status": (
                        self.status_history.current.value
                        if self.status_history.current
                        else None
                    ),
                },
                f,
                indent=2,
                default=str,
            )

    def validate(self) -> ReadinessReport:
        """Executa o pipeline completo de validacao.

        Passos:
        1. Carregar metadados da gravacao
        2. Normalizar eventos brutos → SemanticTestCase
        3. Verificar completude → CompletenessReport
        4. Executar execucao incremental → resultados dos passos
        5. Avaliar portao de prontidao → ReadinessReport
        6. Salvar todos os relatorios

        Returns:
            ReadinessReport com veredito final.
        """
        import sys

        # 1. Load metadata
        meta = self._get_recording_metadata()
        self.recording_id = meta.get("recording_id", os.path.basename(self.recording_dir))
        self.application = meta.get("application", "")
        self.base_url = meta.get("base_url", "")

        print(f"[TestForge] [BUSCA] Validando gravacao: {self.recording_id}", file=sys.stderr)

        # 2. Normalize
        if not self._normalize():
            print("[TestForge] [FAIL] Normalizacao falhou — impossivel validar", file=sys.stderr)
            return self._make_failed_report("Normalizacao falhou")

        # 3. Check completeness
        completeness = self._check_completeness()
        save_completeness_report(
            completeness,
            self.output_dir,
            recording_id=self.recording_id,
        )
        total = completeness.total_fields
        missing = completeness.missing_count
        print(
            f"[TestForge] [DADOS] Completude: {total} campo(s), "
            f"{'[OK] completo' if completeness.is_complete else f'[FAIL] {missing} ausente(s)'}",
            file=sys.stderr,
        )

        # 4. Run incremental validation
        self._run_incremental()
        step_count = len(self.step_results)
        print(
            f"[TestForge] [EXEC] Validacao incremental: {step_count} step(s) executado(s)",
            file=sys.stderr,
        )

        # 5. Evaluate gate
        report = self._evaluate_gate()

        # 6. Save reports
        self._save_status_history()
        save_readiness_report(report, self.output_dir)

        return report

    def _make_failed_report(self, reason: str) -> ReadinessReport:
        """Cria relatorio de prontidao falho quando a validacao nao pode executar."""
        from datetime import datetime, timezone
        report = ReadinessReport(
            recording_id=self.recording_id,
            application=self.application,
            base_url=self.base_url,
            status=RecordingStatus.incomplete_intent,
            verdict=ReadinessVerdict.FAIL,
            failures=[reason],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        self.readiness_report = report
        save_readiness_report(report, self.output_dir)
        self._save_status_history()
        return report
