"""Tests for scripts/consolidate_artifacts.py."""
import json
import os
import sys
from pathlib import Path

import pytest

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from consolidate_artifacts import (
    _normalize,
    _read_recording,
    _read_semantic_test,
    main,
    output_jsonl,
    output_markdown,
    pair_artifacts,
    scan_recordings,
    scan_semantic_tests,
)


# -- Helpers -----------------------------------------------------


def _make_recording(tmp_path: Path, rec_id: str, status: str = "completed") -> Path:
    """Create a minimal recording directory with metadata, events, steps."""
    rec_dir = tmp_path / rec_id
    rec_dir.mkdir()

    meta = {
        "recording_id": rec_id,
        "application": "fake-bank",
        "base_url": "http://localhost:8765",
        "started_at": "2026-06-16T01:40:18+00:00",
        "finished_at": "2026-06-16T01:40:20+00:00",
        "status": status,
    }
    (rec_dir / "recording_metadata.json").write_text(json.dumps(meta))

    raw = [
        json.dumps({"event_id": "evt_0001", "type": "navigation", "url": "http://localhost:8765/"}),
        json.dumps({"event_id": "evt_0002", "type": "fill", "target": {"tag": "input"}}),
        json.dumps({"event_id": "evt_0003", "type": "click", "target": {"tag": "button"}}),
    ]
    (rec_dir / "raw_events.jsonl").write_text("\n".join(raw))

    steps = [
        json.dumps({"step_id": "step_0001", "action": "assert", "assert_type": "textual"}),
        json.dumps({"step_id": "step_0002", "action": "assert", "assert_type": "visivel"}),
    ]
    (rec_dir / "steps.jsonl").write_text("\n".join(steps))

    return rec_dir


def _make_semantic_test(tmp_path: Path, st_id: str) -> Path:
    """Create a minimal semantic test directory with a compiled test file."""
    st_dir = tmp_path / st_id
    st_dir.mkdir()

    code = f'''"""Teste gerado pelo TestForge — {st_id}."""\nfrom playwright.sync_api import Page\n\n\ndef test_{st_id.lower().replace("-", "_")}(page: Page):\n    page.goto("http://localhost:8765")\n    page.fill("#cpfField", "12345678900")\n'''
    (st_dir / "test_st_example.py").write_text(code)

    return st_dir


# -- Scan tests --------------------------------------------------


class TestScanRecordings:
    def test_empty_dir(self, tmp_path):
        """Nonexistent dir returns empty list."""
        assert scan_recordings(tmp_path / "nope") == []

    def test_ignores_files(self, tmp_path):
        """Non-directory entries are skipped."""
        (tmp_path / "oops.json").write_text("{}")
        assert scan_recordings(tmp_path) == []

    def test_reads_one_recording(self, tmp_path):
        _make_recording(tmp_path, "REC-001")
        results = scan_recordings(tmp_path)
        assert len(results) == 1
        r = results[0]
        assert r["type"] == "recording"
        assert r["recording_id"] == "REC-001"
        assert r["metadata"]["application"] == "fake-bank"
        assert r["metadata"]["status"] == "completed"
        assert r["raw_events"]["count"] == 3
        assert r["raw_events"]["by_type"] == {"navigation": 1, "fill": 1, "click": 1}
        assert r["steps"]["count"] == 2
        assert r["steps"]["by_action"] == {"assert": 2}

    def test_reads_multiple_sorted(self, tmp_path):
        _make_recording(tmp_path, "REC-B")
        _make_recording(tmp_path, "REC-A")
        results = scan_recordings(tmp_path)
        assert [r["recording_id"] for r in results] == ["REC-A", "REC-B"]

    def test_missing_optional_files(self, tmp_path):
        """Recording without steps/raw_events still works."""
        rec_dir = tmp_path / "REC-MIN"
        rec_dir.mkdir()
        meta = {"recording_id": "REC-MIN", "status": "completed"}
        (rec_dir / "recording_metadata.json").write_text(json.dumps(meta))
        results = scan_recordings(tmp_path)
        assert len(results) == 1
        assert "raw_events" not in results[0]
        assert "steps" not in results[0]

    def test_recording_with_network_log(self, tmp_path):
        rec_dir = tmp_path / "REC-NET"
        rec_dir.mkdir()
        (rec_dir / "recording_metadata.json").write_text(json.dumps({"recording_id": "REC-NET"}))
        (rec_dir / "network_log.json").write_text(json.dumps([{"url": "x"}, {"url": "y"}]))
        results = scan_recordings(tmp_path)
        assert results[0]["network"]["entries"] == 2

    def test_recording_with_assets(self, tmp_path):
        rec_dir = tmp_path / "REC-ASSETS"
        rec_dir.mkdir()
        (rec_dir / "recording_metadata.json").write_text(json.dumps({"recording_id": "REC-ASSETS"}))
        ss_dir = rec_dir / "screenshots"
        ss_dir.mkdir()
        (ss_dir / "img1.png").write_text("")
        (ss_dir / "img2.png").write_text("")
        (ss_dir / "img3.png").write_text("")
        results = scan_recordings(tmp_path)
        assert results[0]["assets"]["screenshots"] == 3


class TestScanSemanticTests:
    def test_empty_dir(self, tmp_path):
        assert scan_semantic_tests(tmp_path / "nope") == []

    def test_ignores_files(self, tmp_path):
        (tmp_path / "nope.txt").write_text("nope")
        assert scan_semantic_tests(tmp_path) == []

    def test_reads_one_semantic_test(self, tmp_path):
        _make_semantic_test(tmp_path, "ST-TEST1")
        results = scan_semantic_tests(tmp_path)
        assert len(results) == 1
        r = results[0]
        assert r["type"] == "semantic_test"
        assert r["test_id"] == "ST-TEST1"
        assert r["test_file"] == "test_st_example.py"
        assert "test_code" in r
        assert "playwright.sync_api" in r["test_code"]

    def test_skips_dir_without_test_file(self, tmp_path):
        st_dir = tmp_path / "ST-EMPTY"
        st_dir.mkdir()
        (st_dir / "data.json").write_text("{}")
        results = scan_semantic_tests(tmp_path)
        assert results == []

    def test_reads_multiple_sorted(self, tmp_path):
        _make_semantic_test(tmp_path, "ST-B")
        _make_semantic_test(tmp_path, "ST-A")
        results = scan_semantic_tests(tmp_path)
        assert [r["test_id"] for r in results] == ["ST-A", "ST-B"]

    def test_reads_test_data_json(self, tmp_path):
        st_dir = tmp_path / "ST-DATA"
        st_dir.mkdir()
        (st_dir / "test_st_data.py").write_text("import playwright\n")
        (st_dir / "test_data.json").write_text(json.dumps({"cpf": "123"}))
        results = scan_semantic_tests(tmp_path)
        assert results[0]["test_data"] == {"cpf": "123"}


# -- Normalize ---------------------------------------------------


class TestNormalize:
    def test_strips_st_prefix(self):
        assert _normalize("ST-HEAL-DEMO") == "heal_demo"

    def test_replaces_hyphens_and_spaces(self):
        assert _normalize("fluxo teste") == "fluxo_teste"
        assert _normalize("REC-FULL-001") == "rec_full_001"

    def test_lowercases(self):
        assert _normalize("FullTest") == "fulltest"

    def test_empty_string(self):
        assert _normalize("") == ""


# -- Pairing -----------------------------------------------------


class TestPairArtifacts:
    def test_exact_match(self):
        rec = [{"type": "recording", "recording_id": "REC-001"}]
        st = [{"type": "semantic_test", "test_id": "ST-REC-001"}]
        pairs = pair_artifacts(rec, st)
        assert len(pairs) == 1
        assert pairs[0]["recording"]["recording_id"] == "REC-001"
        assert pairs[0]["semantic_test"]["test_id"] == "ST-REC-001"

    def test_fuzzy_match(self):
        """ST-FULLTEST-001 matches FULLTEST-001."""
        rec = [{"type": "recording", "recording_id": "FULLTEST-001"}]
        st = [{"type": "semantic_test", "test_id": "ST-FULLTEST-001"}]
        pairs = pair_artifacts(rec, st)
        assert pairs[0]["semantic_test"] is not None
        assert pairs[0]["semantic_test"]["test_id"] == "ST-FULLTEST-001"

    def test_match_with_spaces(self):
        rec = [{"type": "recording", "recording_id": "fluxo teste"}]
        st = [{"type": "semantic_test", "test_id": "ST-fluxo_teste"}]
        pairs = pair_artifacts(rec, st)
        assert pairs[0]["semantic_test"] is not None

    def test_no_match_sets_none(self):
        rec = [{"type": "recording", "recording_id": "UNKNOWN-999"}]
        st = [{"type": "semantic_test", "test_id": "ST-OTHER"}]
        pairs = pair_artifacts(rec, st)
        assert pairs[0]["semantic_test"] is None

    def test_unmatched_st_adds_recording_none(self):
        rec = [{"type": "recording", "recording_id": "REC-A"}]
        st1 = [{"type": "semantic_test", "test_id": "ST-REC-A"}]
        st2 = [{"type": "semantic_test", "test_id": "ST-LONELY"}]
        pairs = pair_artifacts(rec, st1 + st2)
        assert len(pairs) == 2
        lonely = [p for p in pairs if p.get("recording") is None]
        assert len(lonely) == 1
        assert lonely[0]["semantic_test"]["test_id"] == "ST-LONELY"

    def test_empty_inputs(self):
        assert pair_artifacts([], []) == []
        rec = [{"type": "recording", "recording_id": "X"}]
        assert pair_artifacts(rec, []) == [{"recording": rec[0], "semantic_test": None}]
        st = [{"type": "semantic_test", "test_id": "ST-X"}]
        assert pair_artifacts([], st) == [{"recording": None, "semantic_test": st[0]}]


# -- Output ------------------------------------------------------


class TestOutputJsonl:
    def test_writes_lines(self, tmp_path):
        artifacts = [
            {
                "recording": {"type": "recording", "recording_id": "REC-001"},
                "semantic_test": None,
            },
        ]
        out = tmp_path / "out.jsonl"
        output_jsonl(artifacts, out)
        assert out.exists()
        lines = out.read_text().strip().splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["recording"]["recording_id"] == "REC-001"
        assert parsed["semantic_test"] is None

    def test_empty_list_writes_empty_file(self, tmp_path):
        out = tmp_path / "empty.jsonl"
        output_jsonl([], out)
        assert out.exists()
        assert out.read_text() == ""


class TestOutputMarkdown:
    def test_writes_markdown(self, tmp_path):
        artifacts = [
            {
                "recording": {
                    "type": "recording",
                    "recording_id": "REC-001",
                    "metadata": {
                        "application": "fake-bank",
                        "base_url": "http://localhost:8765",
                        "status": "completed",
                        "started_at": "2026-06-16T01:40:18+00:00",
                    },
                    "raw_events": {"count": 3, "by_type": {"navigation": 1, "fill": 1, "click": 1}},
                    "steps": {"count": 2, "by_action": {"assert": 2}},
                },
                "semantic_test": {
                    "type": "semantic_test",
                    "test_id": "ST-REC-001",
                    "test_file": "test_st_rec_001.py",
                    "test_code": "def test_stuff(page):\n    page.goto('/')\n",
                },
            }
        ]
        out = tmp_path / "report.md"
        output_markdown(artifacts, out)
        text = out.read_text()
        assert "REC-001" in text
        assert "ST-REC-001" in text
        assert "fake-bank" in text
        assert "**Paired:** 1" in text
        assert "```python" in text
        assert "test_stuff" in text

    def test_markdown_handles_none_sections(self, tmp_path):
        artifacts = [
            {"recording": None, "semantic_test": {"type": "semantic_test", "test_id": "ST-LONELY", "test_code": "pass"}},
        ]
        out = tmp_path / "report2.md"
        output_markdown(artifacts, out)
        text = out.read_text()
        assert "ST-LONELY" in text
        # Should NOT have the recording section table
        assert "Base URL" not in text

    def test_markdown_counts_correctly(self, tmp_path):
        """Unpaired artifacts counted correctly."""
        artifacts = [
            {"recording": {"type": "recording", "recording_id": "A"}, "semantic_test": None},
            {"recording": None, "semantic_test": {"type": "semantic_test", "test_id": "ST-B", "test_code": "pass"}},
        ]
        out = tmp_path / "report3.md"
        output_markdown(artifacts, out)
        text = out.read_text()
        assert "**Recordings:** 1" in text
        assert "**Semantic Tests:** 1" in text
        assert "**Paired:** 0" in text


# -- CLI ---------------------------------------------------------


class TestCLI:
    def test_main_jsonl(self, tmp_path):
        rec_dir = tmp_path / "recordings"
        rec_dir.mkdir()
        _make_recording(rec_dir, "REC-CLI")

        out = tmp_path / "cli_out.jsonl"
        main(["--recordings-dir", str(rec_dir), "--semantic-dir", str(tmp_path / "nope"), "--output", str(out)])

        assert out.exists()
        parsed = [json.loads(l) for l in out.read_text().strip().splitlines()]
        assert parsed[0]["recording"]["recording_id"] == "REC-CLI"

    def test_main_markdown(self, tmp_path):
        rec_dir = tmp_path / "recordings"
        rec_dir.mkdir()
        _make_recording(rec_dir, "REC-MD")

        out = tmp_path / "cli_out.md"
        main(["--recordings-dir", str(rec_dir), "--semantic-dir", str(tmp_path / "nope"), "--output", str(out), "--format", "markdown"])

        assert out.exists()
        text = out.read_text()
        assert "REC-MD" in text

    def test_main_default_output(self, tmp_path, monkeypatch):
        rec_dir = tmp_path / "recordings"
        rec_dir.mkdir()
        _make_recording(rec_dir, "REC-DEF")
        monkeypatch.chdir(tmp_path)

        out = tmp_path / "consolidated_artifacts.jsonl"
        main(["--recordings-dir", str(rec_dir), "--semantic-dir", str(tmp_path / "nope")])

        assert out.exists()

    def test_main_no_dirs(self, tmp_path):
        """Graceful when neither dir exists."""
        out = tmp_path / "out.jsonl"
        main(["--recordings-dir", str(tmp_path / "nope_rec"), "--semantic-dir", str(tmp_path / "nope_st"), "--output", str(out)])
        assert out.exists()
