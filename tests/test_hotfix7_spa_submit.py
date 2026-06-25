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
