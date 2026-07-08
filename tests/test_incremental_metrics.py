"""TestForge — métricas registradas pelo IncrementalRunner."""
from unittest.mock import MagicMock
from testforge.runner.incremental_runner import IncrementalRunner
from testforge.runner.step_result import IncrementalStepResult
from tests.helpers.incremental_fakes import (
    make_fake_step, make_fake_outcome, FakePostconditionValidator,
)


class _CountingMetrics:
    def __init__(self):
        self.events = []
    def record_step(self, outcome, **kwargs):
        self.events.append(str(outcome))


def _build_runner(tmp_path, post_passed=True):
    script = tmp_path / "t.py"
    script.write_text("")
    runner = IncrementalRunner(script_path=str(script))
    runner.page = MagicMock()
    runner.page.url = "http://localhost"
    runner.steps = []
    runner.metrics = _CountingMetrics()
    runner.postcondition_validator = FakePostconditionValidator(passed=post_passed)
    runner.evidence_collector = MagicMock()
    payload = MagicMock()
    payload.is_sufficient = True
    runner.evidence_collector.build_llm_payload = MagicMock(return_value=payload)
    curator = MagicMock()
    curator.cure = MagicMock(return_value=make_fake_outcome())
    runner._make_curator = MagicMock(return_value=curator)
    return runner


def test_metrics_for_validated_healing(tmp_path):
    runner = _build_runner(tmp_path, post_passed=True)
    step = make_fake_step("click", "#old", text="Pesquisar")
    result = IncrementalStepResult(step_num=1, action="click")
    runner._heal_failed_step(
        step=step, step_num=1, original_error="err",
        failure_phase="execution", result=result,
    )
    evs = " ".join(runner.metrics.events)
    assert "FAILURE_DETECTED" in evs
    assert "HEALING_ATTEMPTED" in evs
    assert "HEALING_APPLIED" in evs
    assert "ORACLE_VALIDATED" in evs


def test_metrics_for_rejected_healing(tmp_path):
    runner = _build_runner(tmp_path, post_passed=False)
    step = make_fake_step("click", "#old", text="Pesquisar")
    result = IncrementalStepResult(step_num=1, action="click")
    runner._heal_failed_step(
        step=step, step_num=1, original_error="err",
        failure_phase="execution", result=result,
    )
    evs = " ".join(runner.metrics.events)
    assert "FAILURE_DETECTED" in evs
    assert "HEALING_REJECTED" in evs
    assert "ORACLE_VALIDATED" not in evs