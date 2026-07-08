"""TestForge — _validate_curator_proposal tests."""
from testforge.runner.incremental_runner import IncrementalRunner
from tests.helpers.incremental_fakes import make_fake_step, make_fake_outcome


def _runner(tmp_path):
    script = tmp_path / "t.py"
    script.write_text("")
    return IncrementalRunner(script_path=str(script))


def test_rejects_missing_locator(tmp_path):
    runner = _runner(tmp_path)
    outcome = make_fake_outcome(new_locator="")
    step = make_fake_step("click", "#btn", text="Pesquisar")
    ok, fails = runner._validate_curator_proposal(outcome, step, "#btn")
    assert not ok
    assert "missing_new_locator" in fails


def test_rejects_low_confidence(tmp_path):
    runner = _runner(tmp_path)
    outcome = make_fake_outcome(confidence=0.3)
    step = make_fake_step("click", "#btn", text="Pesquisar")
    ok, fails = runner._validate_curator_proposal(outcome, step, "#btn")
    assert not ok
    assert "low_confidence" in fails


def test_rejects_generic_locator(tmp_path):
    runner = _runner(tmp_path)
    outcome = make_fake_outcome(new_locator="button", confidence=0.9)
    step = make_fake_step("click", "#btn", text="Pesquisar")
    ok, fails = runner._validate_curator_proposal(outcome, step, "#btn")
    assert not ok
    assert "generic_or_dangerous_locator" in fails


def test_rejects_incompatible_strategy(tmp_path):
    runner = _runner(tmp_path)
    # press_sequentially is now ALLOWED for click (masked input fields),
    # but dialog_handler is not allowed for fill
    outcome = make_fake_outcome(strategy="dialog_handler", new_locator="#new", confidence=0.9)
    step = make_fake_step("fill", "#input", text="valor")
    ok, fails = runner._validate_curator_proposal(outcome, step, "#input")
    assert not ok
    assert "incompatible_action_strategy" in fails


def test_accepts_press_sequentially_for_click(tmp_path):
    """press_sequentially must be accepted for click — masked input fields
    are recorded as click but need sequential typing when fill() fails."""
    runner = _runner(tmp_path)
    # Use different locator to avoid same_locator_as_failed_original rejection
    outcome = make_fake_outcome(
        strategy="press_sequentially",
        new_locator="input[placeholder=\"R$0,00\"]",
        confidence=0.82, layer_used="L2",
    )
    step = make_fake_step("click", "#old-selector")
    ok, fails = runner._validate_curator_proposal(outcome, step, "#old-selector")
    assert ok, f"press_sequentially should be accepted for click on masked input, got fails: {fails}"


def test_accepts_valid_proposal(tmp_path):
    runner = _runner(tmp_path)
    outcome = make_fake_outcome(
        strategy="has_text_fallback", new_locator="text=Pesquisar",
        confidence=0.85, layer_used="L2",
    )
    step = make_fake_step("click", "#btn-old", text="Pesquisar")
    ok, fails = runner._validate_curator_proposal(outcome, step, "#btn-old")
    assert ok, f"esperava aceitar, falhou: {fails}"


def test_rejects_same_locator_as_failed(tmp_path):
    runner = _runner(tmp_path)
    outcome = make_fake_outcome(new_locator="#btn-old", layer_used="L2", confidence=0.9)
    step = make_fake_step("click", "#btn-old", text="Pesquisar")
    ok, fails = runner._validate_curator_proposal(outcome, step, "#btn-old")
    assert not ok
    assert "same_locator_as_failed_original" in fails