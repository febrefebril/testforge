"""Hotfix 7 — SPA pseudo-submit detection via XHR/fetch POST."""
from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest


def _make_page():
    page = MagicMock()
    page.url = "http://x/"
    page.context = MagicMock()
    page.context.tracing = MagicMock()
    page.context.new_cdp_session = MagicMock()
    page.add_init_script = MagicMock()
    page.on = MagicMock()
    page.remove_listener = MagicMock()
    page.evaluate = MagicMock(return_value={
        "events": [], "steps": [], "commands": [],
        "fieldSnapshots": [], "valueMutations": [],
    })
    page.screenshot = MagicMock(return_value=b"\x89PNG")
    page.content = MagicMock(return_value="<html/>")
    page.title = MagicMock(return_value="App")
    page.wait_for_load_state = MagicMock()
    page.main_frame = MagicMock()
    return page


def _request(method="POST", resource_type="xhr",
             url="http://api/submit", post_data='{"renda":"5000"}'):
    req = MagicMock()
    req.method = method
    req.resource_type = resource_type
    req.url = url
    req.post_data = post_data
    return req


class TestPseudoSubmitPromotion:
    def test_post_xhr_promotes_recent_click(self):
        from testforge.recorder.recorder_controller import RecorderController
        page = _make_page()
        with tempfile.TemporaryDirectory() as tmp:
            ctrl = RecorderController(page, recordings_root=tmp)
            ctrl.start("REC-001")
            # Simulate a recent click
            ctrl._recent_clicks = [{
                "event_id": "evt_001",
                "ts": datetime.now(timezone.utc).timestamp(),
            }]
            ctrl._on_request(_request())
            assert ctrl._recent_clicks[-1].get("pseudo_submit")
            ps = ctrl._recent_clicks[-1]["pseudo_submit"]
            assert ps["method"] == "POST"
            assert ps["form_values"]["renda"] == "5000"
            ctrl.stop()

    def test_get_does_not_promote(self):
        from testforge.recorder.recorder_controller import RecorderController
        page = _make_page()
        with tempfile.TemporaryDirectory() as tmp:
            ctrl = RecorderController(page, recordings_root=tmp)
            ctrl.start("REC-002")
            ctrl._recent_clicks = [{
                "event_id": "evt_001",
                "ts": datetime.now(timezone.utc).timestamp(),
            }]
            ctrl._on_request(_request(method="GET", post_data=None))
            assert "pseudo_submit" not in ctrl._recent_clicks[-1]
            ctrl.stop()

    def test_navigation_resource_skipped(self):
        from testforge.recorder.recorder_controller import RecorderController
        page = _make_page()
        with tempfile.TemporaryDirectory() as tmp:
            ctrl = RecorderController(page, recordings_root=tmp)
            ctrl.start("REC-003")
            ctrl._recent_clicks = [{
                "event_id": "evt_001",
                "ts": datetime.now(timezone.utc).timestamp(),
            }]
            ctrl._on_request(_request(resource_type="document"))
            assert "pseudo_submit" not in ctrl._recent_clicks[-1]
            ctrl.stop()

    def test_old_click_not_promoted(self):
        from testforge.recorder.recorder_controller import RecorderController
        page = _make_page()
        with tempfile.TemporaryDirectory() as tmp:
            ctrl = RecorderController(page, recordings_root=tmp)
            ctrl.start("REC-004")
            # Click 5 s ago — outside 1.5 s window
            ctrl._recent_clicks = [{
                "event_id": "evt_001",
                "ts": datetime.now(timezone.utc).timestamp() - 5.0,
            }]
            ctrl._on_request(_request())
            # _mark_pseudo_submit drops stale entries -> latest is gone
            assert ctrl._recent_clicks == []
            ctrl.stop()

    def test_form_encoded_payload_parsed(self):
        from testforge.recorder.recorder_controller import RecorderController
        page = _make_page()
        with tempfile.TemporaryDirectory() as tmp:
            ctrl = RecorderController(page, recordings_root=tmp)
            ctrl.start("REC-005")
            ctrl._recent_clicks = [{
                "event_id": "evt_x",
                "ts": datetime.now(timezone.utc).timestamp(),
            }]
            ctrl._on_request(_request(
                post_data="renda=5000&valor=100000"))
            ps = ctrl._recent_clicks[-1]["pseudo_submit"]
            assert ps["form_values"]["renda"] == "5000"
            assert ps["form_values"]["valor"] == "100000"
            ctrl.stop()


class TestHotfix12NetworkPersistence:
    """Hotfix 12: pseudo_submit metadata also tags the persisted network entry."""

    def test_mark_pseudo_submit_tags_matching_network_entry(self):
        from testforge.recorder.recorder_controller import RecorderController
        page = _make_page()
        with tempfile.TemporaryDirectory() as tmp:
            ctrl = RecorderController(page, recordings_root=tmp)
            ctrl.start("REC-PSP-001")
            ctrl._network_entries = [{
                "type": "request",
                "method": "POST",
                "url": "http://api/save",
                "resource_type": "xhr",
                "post_data": '{"renda":"5000"}',
            }]
            ctrl._recent_clicks = [{
                "event_id": "evt_010",
                "ts": datetime.now(timezone.utc).timestamp(),
            }]
            ctrl._mark_pseudo_submit("http://api/save", "POST", '{"renda":"5000"}')
            entry = ctrl._network_entries[-1]
            assert entry.get("is_pseudo_submit") is True
            assert entry.get("pseudo_submit_click_event_id") == "evt_010"
            assert entry.get("form_values", {}).get("renda") == "5000"
            ctrl.stop()

    def test_mark_pseudo_submit_does_not_tag_unrelated_entry(self):
        from testforge.recorder.recorder_controller import RecorderController
        page = _make_page()
        with tempfile.TemporaryDirectory() as tmp:
            ctrl = RecorderController(page, recordings_root=tmp)
            ctrl.start("REC-PSP-002")
            ctrl._network_entries = [{
                "type": "request", "method": "GET",
                "url": "http://api/other", "resource_type": "fetch",
                "post_data": None,
            }, {
                "type": "request", "method": "POST",
                "url": "http://api/save", "resource_type": "xhr",
                "post_data": '{"a":"b"}',
            }]
            ctrl._recent_clicks = [{
                "event_id": "evt_020",
                "ts": datetime.now(timezone.utc).timestamp(),
            }]
            ctrl._mark_pseudo_submit("http://api/save", "POST", '{"a":"b"}')
            assert "is_pseudo_submit" not in ctrl._network_entries[0]
            assert ctrl._network_entries[1].get("is_pseudo_submit") is True
            ctrl.stop()


class TestHotfix12AuditorCounts:
    """Auditor recognizes is_pseudo_submit entries as postbacks."""

    def test_auditor_counts_pseudo_submit_as_postback(self):
        from testforge.recorder.recording_auditor import RecordingAuditor
        import os, json
        with tempfile.TemporaryDirectory() as tmp:
            rec_dir = os.path.join(tmp, "REC-AUD-001")
            os.makedirs(rec_dir)
            with open(os.path.join(rec_dir, "network_log.json"), "w") as f:
                json.dump([
                    {"type": "request", "method": "POST", "url": "http://api/save",
                     "resource_type": "xhr", "is_pseudo_submit": True},
                    {"type": "request", "method": "GET", "url": "http://api/data",
                     "resource_type": "xhr"},
                ], f)
            auditor = RecordingAuditor()
            report = auditor.audit(rec_dir)
            assert report["network"]["postbacks_detected"] == 1
