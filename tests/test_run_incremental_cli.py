"""TestForge — CLI run-incremental registration & dispatch."""
import argparse
import pytest
from testforge.cli._run_incremental_patch import register, cmd_run_incremental


def test_cli_has_run_incremental_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    register(sub)
    args = parser.parse_args(["run-incremental", "fake.py", "--headless", "--verbose"])
    assert args.command == "run-incremental"
    assert args.script == "fake.py"
    assert args.headless is True
    assert args.verbose is True


def test_run_incremental_fails_with_missing_script(tmp_path):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    register(sub)
    args = parser.parse_args(["run-incremental", str(tmp_path / "nao_existe.py")])
    with pytest.raises(SystemExit) as exc:
        cmd_run_incremental(args)
    assert exc.value.code in (2, 3)