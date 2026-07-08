"""TestForge — IncrementalRunner._make_curator tests."""
from testforge.runner.incremental_runner import IncrementalRunner
from testforge.healing import CuradorAutomatico, HealingCatalog


def test_make_curator_returns_curador_automatico(tmp_path):
    script = tmp_path / "t.py"
    script.write_text('BASE_URL = "http://localhost"\n# source: REC-test\n')
    runner = IncrementalRunner(script_path=str(script))
    def fake_runner(step_data):
        return True
    curator = runner._make_curator(catalog=HealingCatalog(), step_runner=fake_runner)
    assert isinstance(curator, CuradorAutomatico)


def test_make_curator_uses_injected_step_runner(tmp_path):
    script = tmp_path / "t.py"
    script.write_text("")
    runner = IncrementalRunner(script_path=str(script))
    called = {"n": 0}
    def fake_runner(step_data):
        called["n"] += 1
        return True
    curator = runner._make_curator(step_runner=fake_runner)
    result = curator._step_runner({"selector": "#x", "action": "click", "value": ""})
    assert result is True
    assert called["n"] == 1