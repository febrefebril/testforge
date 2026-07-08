"""Regression tests for recording directory discovery in IncrementalRunner."""

from pathlib import Path

from testforge.runner.incremental_runner import IncrementalRunner


def _make_runner(tmp_path: Path) -> IncrementalRunner:
    script = tmp_path / "semantic_tests" / "ST-sample" / "test_st_sample.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("", encoding="utf-8")
    return IncrementalRunner(script_path=str(script))


def test_find_recording_dir_prefers_direct_path(tmp_path, monkeypatch):
    direct = tmp_path / "recordings" / "test-pos-hotfix22"
    direct.mkdir(parents=True, exist_ok=True)
    (direct / "raw_events.jsonl").write_text("", encoding="utf-8")

    nested = tmp_path / "recordings" / "uncategorized" / "test-pos-hotfix22"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "raw_events.jsonl").write_text("", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    runner = _make_runner(tmp_path)

    found = runner._find_recording_dir("test-pos-hotfix22")

    assert found == str(direct)


def test_find_recording_dir_supports_nested_category_path(tmp_path, monkeypatch):
    nested = tmp_path / "recordings" / "uncategorized" / "test-pos-hotfix22"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "raw_events.jsonl").write_text("", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    runner = _make_runner(tmp_path)

    found = runner._find_recording_dir("test-pos-hotfix22")

    assert found == str(nested)
