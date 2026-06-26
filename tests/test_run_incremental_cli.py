"""TestForge — CLI run-incremental registration & dispatch."""
import argparse
import pytest
from testforge.cli._run_incremental_patch import register, cmd_run_incremental, _resolve_script_path


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


def test_resolve_script_returns_file_unchanged(tmp_path):
    f = tmp_path / "test_foo.py"
    f.write_text("# noop")
    assert _resolve_script_path(str(f)) == str(f)


def test_resolve_script_accepts_directory(tmp_path):
    script = tmp_path / "test_bar.py"
    script.write_text("# noop")
    assert _resolve_script_path(str(tmp_path)) == str(script)


def test_resolve_script_directory_picks_first_when_multiple(tmp_path, capsys):
    a = tmp_path / "test_a.py"
    b = tmp_path / "test_b.py"
    a.write_text("# noop")
    b.write_text("# noop")
    result = _resolve_script_path(str(tmp_path))
    assert result == str(a)
    captured = capsys.readouterr()
    assert "2 scripts" in captured.err


def test_resolve_script_directory_without_test_file_raises(tmp_path):
    (tmp_path / "other.py").write_text("# noop")
    with pytest.raises(FileNotFoundError):
        _resolve_script_path(str(tmp_path))


def test_cmd_run_incremental_directory_resolves_to_script(tmp_path):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    register(sub)
    # Empty dir → FileNotFoundError → exit 2
    args = parser.parse_args(["run-incremental", str(tmp_path)])
    with pytest.raises(SystemExit) as exc:
        cmd_run_incremental(args)
    assert exc.value.code == 2