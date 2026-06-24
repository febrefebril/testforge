"""Phase 1 — Tracing + CDP AX snapshot capture (parallel to legacy overlay JS).

Unit tests for TracingManager, CDPSnapshotter, and RecorderController
integration under the --use-cdp-recorder flag.
"""
import os
import tempfile
from unittest.mock import MagicMock

import pytest

from testforge.recorder.cdp_snapshot import CDPSnapshotter
from testforge.recorder.recorder_controller import RecorderController
from testforge.recorder.tracing_manager import TracingManager


def _make_page():
    page = MagicMock()
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
    page.content = MagicMock(return_value="<html><body>x</body></html>")
    page.title = MagicMock(return_value="t")
    page.url = "http://localhost"
    page.wait_for_load_state = MagicMock()
    page.main_frame = MagicMock()
    return page


class TestTracingManager:
    def test_start_calls_context_tracing_start(self):
        page = _make_page()
        tm = TracingManager(page)
        with tempfile.TemporaryDirectory() as d:
            tm.start(d, "REC-001")
        page.context.tracing.start.assert_called_once()
        assert tm.is_active is True

    def test_start_idempotent(self):
        page = _make_page()
        tm = TracingManager(page)
        with tempfile.TemporaryDirectory() as d:
            tm.start(d, "REC-001")
            tm.start(d, "REC-001")
        assert page.context.tracing.start.call_count == 1

    def test_stop_writes_trace_zip(self):
        page = _make_page()
        tm = TracingManager(page)
        with tempfile.TemporaryDirectory() as d:
            tm.start(d, "REC-001")
            out = tm.stop()
            assert out is not None
            assert out.endswith("trace.zip")
            assert os.path.dirname(out) == d
        page.context.tracing.stop.assert_called_once()
        assert tm.is_active is False

    def test_stop_without_start_is_safe(self):
        page = _make_page()
        tm = TracingManager(page)
        assert tm.stop() is None
        page.context.tracing.stop.assert_not_called()

    def test_start_swallows_exceptions(self):
        page = _make_page()
        page.context.tracing.start.side_effect = RuntimeError("boom")
        tm = TracingManager(page)
        with tempfile.TemporaryDirectory() as d:
            tm.start(d, "REC-001")
        assert tm.is_active is False


class TestCDPSnapshotter:
    def test_attach_enables_domains(self):
        page = _make_page()
        session = MagicMock()
        page.context.new_cdp_session.return_value = session
        snap = CDPSnapshotter(page)
        ok = snap.attach()
        assert ok is True
        domains = [call.args[0] for call in session.send.call_args_list]
        assert "DOM.enable" in domains
        assert "Accessibility.enable" in domains

    def test_attach_idempotent(self):
        page = _make_page()
        session = MagicMock()
        page.context.new_cdp_session.return_value = session
        snap = CDPSnapshotter(page)
        snap.attach()
        snap.attach()
        assert page.context.new_cdp_session.call_count == 1

    def test_attach_failure_returns_false(self):
        page = _make_page()
        page.context.new_cdp_session.side_effect = RuntimeError("no cdp")
        snap = CDPSnapshotter(page)
        assert snap.attach() is False

    def test_get_full_ax_tree_returns_nodes(self):
        page = _make_page()
        session = MagicMock()
        page.context.new_cdp_session.return_value = session
        snap = CDPSnapshotter(page)
        snap.attach()
        # mock the AX response
        session.send.side_effect = lambda method, *a, **kw: (
            {"nodes": [{"nodeId": "1", "role": {"value": "button"},
                        "name": {"value": "Save"}, "backendDOMNodeId": 42}]}
            if method == "Accessibility.getFullAXTree" else None
        )
        tree = snap.get_full_ax_tree()
        assert tree is not None
        assert tree["nodes"][0]["role"]["value"] == "button"

    def test_get_full_ax_tree_without_attach_returns_none(self):
        page = _make_page()
        snap = CDPSnapshotter(page)
        assert snap.get_full_ax_tree() is None

    def test_serialize_ax_yaml_basic(self):
        snap = CDPSnapshotter(_make_page())
        tree = {
            "nodes": [
                {"nodeId": "1", "role": {"value": "WebArea"}, "name": {"value": "Page"},
                 "childIds": ["2"]},
                {"nodeId": "2", "parentId": "1", "role": {"value": "button"},
                 "name": {"value": "Salvar"}, "childIds": []},
            ]
        }
        out = snap.serialize_ax_yaml(tree)
        assert "- WebArea" in out
        assert '"Page"' in out
        assert "- button" in out
        assert '"Salvar"' in out
        assert "[ref=e" in out

    def test_serialize_skips_ignored_nodes_but_walks_children(self):
        snap = CDPSnapshotter(_make_page())
        tree = {
            "nodes": [
                {"nodeId": "1", "role": {"value": "WebArea"}, "name": {"value": ""},
                 "childIds": ["2"]},
                {"nodeId": "2", "parentId": "1", "ignored": True, "childIds": ["3"]},
                {"nodeId": "3", "parentId": "2", "role": {"value": "link"},
                 "name": {"value": "Home"}, "childIds": []},
            ]
        }
        out = snap.serialize_ax_yaml(tree)
        assert "- link" in out
        assert '"Home"' in out

    def test_find_node_by_backend_id(self):
        snap = CDPSnapshotter(_make_page())
        tree = {"nodes": [
            {"nodeId": "1", "backendDOMNodeId": 10},
            {"nodeId": "2", "backendDOMNodeId": 20},
        ]}
        assert snap.find_node_by_backend_id(tree, 20)["nodeId"] == "2"
        assert snap.find_node_by_backend_id(tree, 999) is None

    def test_ancestor_roles(self):
        snap = CDPSnapshotter(_make_page())
        tree = {"nodes": [
            {"nodeId": "1", "role": {"value": "dialog"}},
            {"nodeId": "2", "parentId": "1", "role": {"value": "group"}},
            {"nodeId": "3", "parentId": "2", "role": {"value": "button"}},
        ]}
        roles = snap.ancestor_roles(tree, "3", limit=5)
        assert roles == ["group", "dialog"]


class TestRecorderControllerCDPIntegration:
    def test_use_cdp_false_does_not_attach(self):
        page = _make_page()
        ctrl = RecorderController(page, recordings_root=tempfile.mkdtemp())
        ctrl.start("REC-NOCDP", use_cdp=False)
        assert ctrl._tracing is None
        assert ctrl._cdp is None
        # context.tracing.start MUST NOT be called
        page.context.tracing.start.assert_not_called()

    def test_use_cdp_true_starts_tracing_and_attaches(self):
        page = _make_page()
        session = MagicMock()
        page.context.new_cdp_session.return_value = session
        ctrl = RecorderController(page, recordings_root=tempfile.mkdtemp())
        ctrl.start("REC-CDP", use_cdp=True)
        assert ctrl._tracing is not None and ctrl._tracing.is_active
        assert ctrl._cdp is not None and ctrl._cdp._enabled
        page.context.tracing.start.assert_called_once()
        # DOM + AX must be enabled on the CDP session
        domains = [c.args[0] for c in session.send.call_args_list]
        assert "DOM.enable" in domains and "Accessibility.enable" in domains

    def test_stop_closes_tracing_and_cdp(self):
        page = _make_page()
        session = MagicMock()
        page.context.new_cdp_session.return_value = session
        ctrl = RecorderController(page, recordings_root=tempfile.mkdtemp())
        ctrl.start("REC-CDP-STOP", use_cdp=True)
        ctrl.stop()
        page.context.tracing.stop.assert_called_once()
        session.detach.assert_called_once()
        assert not ctrl._tracing.is_active

    def test_capture_snapshots_saves_ax_snapshot_when_cdp(self):
        page = _make_page()
        session = MagicMock()
        page.context.new_cdp_session.return_value = session
        # AX tree for the event
        session.send.side_effect = lambda method, *a, **kw: (
            {"nodes": [{"nodeId": "1", "role": {"value": "button"},
                        "name": {"value": "X"}}]}
            if method == "Accessibility.getFullAXTree" else None
        )
        with tempfile.TemporaryDirectory() as tmproot:
            ctrl = RecorderController(page, recordings_root=tmproot)
            ctrl.start("REC-AXSNAP", use_cdp=True)
            # Now feed one fake event through the queue path
            ctrl._persist_raw_event({
                "type": "click",
                "timestamp": "2026-06-24T00:00:00Z",
                "url": "http://localhost",
                "target": {"tag": "button", "role": "button"},
            })
            # Verify the ax_snapshots dir was used
            ax_dir = os.path.join(ctrl._store._session_dir, "ax_snapshots")
            # Path may not exist if no save happened — check the saved event has ax_snapshot_path
            ev_path = os.path.join(ctrl._store._session_dir, "raw_events.jsonl")
            assert os.path.exists(ev_path)
            content = open(ev_path).read()
            assert "ax_snapshot" in content
