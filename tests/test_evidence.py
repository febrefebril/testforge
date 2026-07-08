"""Testes do EvidenceCollector e EvidenceStore."""
import json
import os
import tempfile

from playwright.sync_api import Page
import pytest

from testforge.evidence import EvidenceCollector, EvidenceStore


class TestEvidenceCollector:
    def test_start_creates_dirs(self, page: Page):
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = EvidenceCollector(page, tmpdir)
            collector.start("RUN-001")
            assert os.path.isdir(os.path.join(tmpdir, "RUN-001", "screenshots"))
            assert os.path.isdir(os.path.join(tmpdir, "RUN-001", "dom"))

    def test_capture_screenshot(self, page: Page):
        page.set_content("<h1>Test</h1>")
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = EvidenceCollector(page, tmpdir)
            collector.start("RUN-001")
            path = collector.capture_screenshot("step_0001", "after")
            assert path.endswith(".png")
            assert os.path.exists(path)

    def test_capture_dom(self, page: Page):
        page.set_content("<h1>Test</h1>")
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = EvidenceCollector(page, tmpdir)
            collector.start("RUN-001")
            path = collector.capture_dom("step_0001", "after")
            assert path.endswith(".html")
            with open(path) as f:
                assert "<h1>Test</h1>" in f.read()

    def test_finalize_creates_manifest(self, page: Page):
        page.set_content("<h1>Test</h1>")
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = EvidenceCollector(page, tmpdir)
            collector.start("RUN-001", {"app": "test"})
            collector.capture_screenshot("step_0001")
            collector.capture_dom("step_0001")
            collector.add_step_evidence({"action": "click"})
            pkg_dir = collector.finalize()

            assert os.path.exists(os.path.join(pkg_dir, "manifest.json"))
            with open(os.path.join(pkg_dir, "manifest.json")) as f:
                m = json.load(f)
            assert m["run_id"] == "RUN-001"
            assert m["step_count"] == 1
            assert m["screenshot_count"] == 1

    def test_finalize_steps_jsonl(self, page: Page):
        page.set_content("<h1>Test</h1>")
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = EvidenceCollector(page, tmpdir)
            collector.start("RUN-001")
            collector.add_step_evidence({"action": "fill", "value": "test"})
            collector.add_step_evidence({"action": "click"})
            collector.finalize()

            path = os.path.join(tmpdir, "RUN-001", "steps.jsonl")
            with open(path) as f:
                steps = [json.loads(l) for l in f]
            assert len(steps) == 2

    def test_sensitive_alerts(self, page: Page):
        page.set_content("<h1>Test</h1>")
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = EvidenceCollector(page, tmpdir)
            collector.start("RUN-001")
            collector.add_sensitive_alert({"field": "cpf", "type": "CPF"})
            collector.finalize()

            path = os.path.join(tmpdir, "RUN-001", "sensitive_data_alert.json")
            with open(path) as f:
                data = json.load(f)
            assert data["policy"] == "alert_only"


class TestEvidenceStore:
    def test_list_runs(self, page: Page):
        with tempfile.TemporaryDirectory() as tmpdir:
            col = EvidenceCollector(page, tmpdir)
            col.start("RUN-A")
            col.finalize()
            col.start("RUN-B")
            col.finalize()

            store = EvidenceStore(tmpdir)
            runs = store.list_runs()
            assert "RUN-A" in runs
            assert "RUN-B" in runs

    def test_get_manifest(self, page: Page):
        with tempfile.TemporaryDirectory() as tmpdir:
            col = EvidenceCollector(page, tmpdir)
            col.start("RUN-001", {"app": "test"})
            col.finalize()

            store = EvidenceStore(tmpdir)
            m = store.get_manifest("RUN-001")
            assert m["run_id"] == "RUN-001"

    def test_list_pending_reviews(self, page: Page):
        with tempfile.TemporaryDirectory() as tmpdir:
            col = EvidenceCollector(page, tmpdir)
            col.start("RUN-001")
            col.add_sensitive_alert({"type": "CPF"})
            col.finalize()

            store = EvidenceStore(tmpdir)
            pending = store.list_pending_reviews()
            assert len(pending) == 1
            assert pending[0]["alert_count"] == 1
