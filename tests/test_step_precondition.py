"""TestForge — StepPreconditionValidator tests (sem browser real)."""
import pytest
from testforge.runner.step_precondition import StepPreconditionValidator
from tests.helpers.incremental_fakes import make_fake_step


class _PageStub:
    def __init__(self, **kwargs):
        self.url = "http://localhost"
        self._behavior = kwargs


def test_skip_reason_passes_precondition():
    page = _PageStub()
    val = StepPreconditionValidator(page, actionability_validator=None)
    step = make_fake_step("click", "#btn")
    step.skip_reason = "duplicate"
    result = val.validate(step)
    assert result.passed is True
    assert result.checks.get("skipped") is True


def test_dependency_blocks_step():
    page = _PageStub()
    val = StepPreconditionValidator(page, actionability_validator=None)
    step = make_fake_step("click", "#btn")
    step.depends_on = "step_0001"
    result = val.validate(step, failed_step_indices={0})
    assert result.passed is False
    assert "blocked_by_previous_failure" in result.failures


def test_navigation_passes_without_selector():
    page = _PageStub()
    val = StepPreconditionValidator(page, actionability_validator=None)
    step = make_fake_step("navigation", selector="")
    result = val.validate(step)
    assert result.passed is True


def test_click_requires_selector():
    page = _PageStub()
    val = StepPreconditionValidator(page, actionability_validator=None)
    step = make_fake_step("click", selector="", text="x")
    result = val.validate(step)
    assert result.passed is False
    assert "missing_selector" in result.failures


def test_fill_requires_value():
    page = _PageStub()
    val = StepPreconditionValidator(page, actionability_validator=None)
    step = make_fake_step("fill", selector="#x", value="")
    result = val.validate(step)
    assert result.passed is False
    assert "missing_value" in result.failures


def test_assert_requires_expected_text():
    page = _PageStub()
    val = StepPreconditionValidator(page, actionability_validator=None)
    step = make_fake_step("assert", selector="body", value="")
    result = val.validate(step)
    assert result.passed is False
    assert "missing_expected" in result.failures