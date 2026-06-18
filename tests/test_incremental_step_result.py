"""TestForge — IncrementalStepResult serialization tests."""
import json
from testforge.runner.step_result import (
    PreconditionResult, PostconditionResult, HealingAttempt, IncrementalStepResult,
)


def test_step_result_serializes_to_json():
    pre = PreconditionResult(passed=True, checks={"ok": True}, message="ok")
    post = PostconditionResult(passed=True, checks={"a": True}, message="ok")
    healing = HealingAttempt(
        attempted=True, layer="L2", family="FAM-01", taxonomy_id="SEL-004",
        strategy="has_text_fallback", original_locator="#old",
        proposed_locator="text=Pesquisar", confidence=0.9,
        validated=True, oracle_passed=True,
    )
    result = IncrementalStepResult(
        step_num=1, action="click", status="healed_validated",
        original_locator="#old", selected_locator="text=Pesquisar",
        precondition=pre, postcondition=post, healing=healing, duration_ms=123,
    )
    d = result.to_dict()
    s = json.dumps(d, default=str)
    assert "healed_validated" in s
    assert "text=Pesquisar" in s
    assert d["healing"]["validated"] is True


def test_healing_attempt_has_required_fields():
    h = HealingAttempt(attempted=True, layer="L0", family="FAM-01")
    assert h.attempted is True
    assert h.rejection_reason == []
    assert h.confidence == 0.0


def test_step_result_without_post_or_pre():
    result = IncrementalStepResult(step_num=2, action="navigation", status="passed")
    d = result.to_dict()
    assert d["precondition"] is None
    assert d["postcondition"] is None