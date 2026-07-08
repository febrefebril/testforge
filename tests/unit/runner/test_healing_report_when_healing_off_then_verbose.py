"""REC-15: healing_report.md verboso quando healing desativado."""
from pathlib import Path

import pytest


@pytest.mark.unit
class TestHealingReportWhenHealingOffThenVerbose:
    def _make_runner(self, tmp_path, no_healing: bool):
        """Constroi IncrementalRunner minimo suficiente para chamar _write_healing_report."""
        from testforge.runner.incremental_runner import IncrementalRunner

        # Cria um script fake para satisfazer o constructor
        script = tmp_path / "fake.py"
        script.write_text("# fake\n")
        runner = IncrementalRunner(
            script_path=str(script),
            headless=True,
            timeout=30,
            stop_on_failure=False,
            no_healing=no_healing,
            capture=False,
            output_root=str(tmp_path),
        )
        return runner

    def _make_step_result(self, num: int, status: str, error: str = ""):
        from testforge.runner.step_result import IncrementalStepResult
        return IncrementalStepResult(
            step_num=num, action="click", status=status, error_message=error,
        )

    def test_report_says_desativado_when_no_healing(self, tmp_path):
        runner = self._make_runner(tmp_path, no_healing=True)
        runner.step_results = [
            self._make_step_result(1, "failed", "element not found"),
            self._make_step_result(2, "failed", "timeout"),
        ]
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        runner._write_healing_report(out_dir)
        content = (out_dir / "healing_report.md").read_text(encoding="utf-8")
        assert "DESATIVADO" in content, "REC-15: report deve indicar healing off"
        assert "Falhas registradas: 2" in content, "REC-15: contagem de falhas ausente"

    def test_report_lists_activation_options(self, tmp_path):
        runner = self._make_runner(tmp_path, no_healing=True)
        runner.step_results = []
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        runner._write_healing_report(out_dir)
        content = (out_dir / "healing_report.md").read_text(encoding="utf-8")
        assert "--no-healing" in content, "REC-15: deve mencionar remocao da flag"
        assert "TESTFORGE_HEALING" in content, "REC-15: deve mencionar env var"
        assert "config.yml" in content or "config" in content, "REC-15: deve mencionar config"

    def test_report_groups_by_family_when_off(self, tmp_path):
        runner = self._make_runner(tmp_path, no_healing=True)
        runner.step_results = [
            self._make_step_result(1, "failed", "timeout waiting"),
            self._make_step_result(2, "failed", "element not found"),
            self._make_step_result(3, "failed", "element not visible"),
        ]
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        runner._write_healing_report(out_dir)
        content = (out_dir / "healing_report.md").read_text(encoding="utf-8")
        assert "Falhas por" in content or "familia" in content or "família" in content, (
            "REC-15: deve incluir breakdown por familia"
        )
        # 1 timeout, 2 selector (not found + not visible)
        assert "timeout" in content.lower()
        assert "selector" in content.lower()

    def test_report_when_healing_on_stays_original_shape(self, tmp_path):
        """Sanity: quando healing on, report continua no formato antigo."""
        runner = self._make_runner(tmp_path, no_healing=False)
        runner.step_results = []
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        runner._write_healing_report(out_dir)
        content = (out_dir / "healing_report.md").read_text(encoding="utf-8")
        assert "DESATIVADO" not in content, (
            "REC-15: quando healing on, nao deve mostrar mensagem 'DESATIVADO'"
        )
        assert "Validados" in content, "REC-15: healing on deve manter secao Validados"
