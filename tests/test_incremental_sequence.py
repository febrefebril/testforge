"""TestForge — execução sequencial de steps + bloqueio de dependentes."""
from unittest.mock import MagicMock
from testforge.runner.incremental_runner import IncrementalRunner
from tests.helpers.incremental_fakes import make_fake_step


def _build_runner(tmp_path):
    script = tmp_path / "t.py"
    script.write_text("")
    runner = IncrementalRunner(script_path=str(script))
    runner.page = MagicMock()
    runner.page.url = "http://localhost"
    runner.evidence_collector = None
    runner.metrics = None
    return runner


def test_blocked_step_when_dependency_failed(tmp_path):
    runner = _build_runner(tmp_path)
    step1 = make_fake_step("click", "#x", text="X", blocking=True)
    step2 = make_fake_step("click", "#y", text="Y", depends_on="step_0001")
    runner.steps = [step1, step2]
    runner.failed_step_indices = {0}
    from testforge.runner.step_precondition import StepPreconditionValidator
    runner.precondition_validator = StepPreconditionValidator(runner.page, actionability_validator=None)
    pre = runner.precondition_validator.validate(
        step=step2,
        failed_step_indices=runner.failed_step_indices,
        all_steps=runner.steps,
    )
    assert pre.passed is False
    assert "blocked_by_previous_failure" in pre.failures