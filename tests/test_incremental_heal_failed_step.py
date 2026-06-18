"""TestForge — IncrementalRunner._heal_failed_step tests."""
import pytest
from unittest.mock import MagicMock
from testforge.runner.incremental_runner import IncrementalRunner
from testforge.runner.step_result import IncrementalStepResult
from tests.helpers.incremental_fakes import (
    make_fake_step, make_fake_outcome, FakePostconditionValidator,
)


class _StubMetrics:
    def __init__(self):
        self.events = []
    def record_step(self, outcome, **kwargs):
        self.events.append((str(outcome), kwargs))
    @property
    def snapshot(self):
        s = MagicMock()
        s.to_dict.return_value = {"events": len(self.events)}
        return s


def _make_runner_with_stubs(tmp_path, post_passed=True, post_failures=None):
    script = tmp_path / "t.py"
    script.write_text("")
    runner = IncrementalRunner(script_path=str(script))
    runner.page = MagicMock()
    runner.page.url = "http://localhost"
    runner.steps = []
    runner.metrics = _StubMetrics()
    runner.postcondition_validator = FakePostconditionValidator(
        passed=post_passed, message="oracle", failures=post_failures or [],
    )
    runner.evidence_collector = MagicMock()
    payload = MagicMock()
    payload.is_sufficient = True
    runner.evidence_collector.build_llm_payload = MagicMock(return_value=payload)
    return runner


def _patch_make_curator(runner, outcome):
    curator = MagicMock()
    curator.cure = MagicMock(return_value=outcome)
    runner._make_curator = MagicMock(return_value=curator)


def test_heal_failed_step_validates_true_healing(tmp_path):
    runner = _make_runner_with_stubs(tmp_path, post_passed=True)
    outcome = make_fake_outcome()
    _patch_make_curator(runner, outcome)
    step = make_fake_step("click", "#old", text="Pesquisar")
    result = IncrementalStepResult(step_num=1, action="click", original_locator="#old")
    healed = runner._heal_failed_step(
        step=step, step_num=1, original_error="element not found",
        failure_phase="execution", result=result,
    )
    assert healed.status == "healed_validated"
    assert healed.healing.validated is True
    assert healed.healing.oracle_passed is True


def test_heal_failed_step_rejects_false_healing(tmp_path):
    runner = _make_runner_with_stubs(
        tmp_path, post_passed=False, post_failures=["oracle_failed"],
    )
    outcome = make_fake_outcome()
    _patch_make_curator(runner, outcome)
    step = make_fake_step("click", "#old", text="Pesquisar")
    result = IncrementalStepResult(step_num=1, action="click", original_locator="#old")
    healed = runner._heal_failed_step(
        step=step, step_num=1, original_error="element not found",
        failure_phase="execution", result=result,
    )
    assert healed.status == "healing_rejected"
    assert healed.healing.validated is False
    assert "postcondition_failed" in healed.healing.rejection_reason


def test_heal_failed_step_blocks_insufficient_evidence(tmp_path):
    runner = _make_runner_with_stubs(tmp_path)
    payload = MagicMock()
    payload.is_sufficient = False
    payload.insufficiency_reason = "DOM vazio"
    runner.evidence_collector.build_llm_payload = MagicMock(return_value=payload)
    step = make_fake_step("click", "#old")
    result = IncrementalStepResult(step_num=1, action="click")
    healed = runner._heal_failed_step(
        step=step, step_num=1, original_error="err",
        failure_phase="execution", result=result,
    )
    assert healed.status == "failed"
    assert "insufficient_evidence" in healed.healing.rejection_reason


def test_heal_failed_step_rejects_invalid_proposal(tmp_path):
    runner = _make_runner_with_stubs(tmp_path)
    outcome = make_fake_outcome(new_locator="button", confidence=0.9)
    _patch_make_curator(runner, outcome)
    step = make_fake_step("click", "#old", text="Pesquisar")
    result = IncrementalStepResult(step_num=1, action="click", original_locator="#old")
    healed = runner._heal_failed_step(
        step=step, step_num=1, original_error="err",
        failure_phase="execution", result=result,
    )
    assert healed.status == "healing_rejected"
    assert "generic_or_dangerous_locator" in healed.healing.rejection_reason