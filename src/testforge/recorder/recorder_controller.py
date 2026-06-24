"""TestForge — Recorder Controller com asserts e comandos de teclado.

Keyboard shortcuts: Shift+P pause, Shift+S stop, Shift+A assert mode
Assert types: textual, estado, visivel, automatico
"""
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import Page, Request, Response

from .raw_event import RawRecordedEvent, TargetInfo
from .raw_recording_store import RawRecordingStore
from .recording_session import RecordingSession, RecordingSessionManager

logger = logging.getLogger(__name__)

# Load overlay JS from file (next to this module)
_OVERLAY_JS_PATH = Path(__file__).parent / "overlay_inject.js"
if _OVERLAY_JS_PATH.exists():
    _OVERLAY_JS = _OVERLAY_JS_PATH.read_text(encoding="utf-8")
    logger.info("Loaded overlay JS from %s (%d bytes)", _OVERLAY_JS_PATH, len(_OVERLAY_JS))
else:
    _OVERLAY_JS = ""
    logger.warning("Overlay JS not found at %s", _OVERLAY_JS_PATH)


class RecorderController:
    def __init__(self, page: Page, recordings_root: str = "recordings"):
        self._page = page
        self._session_manager = RecordingSessionManager(recordings_root)
        self._store: RawRecordingStore = None  # type: ignore
        self._event_counter = 0
        self._step_counter = 0
        self._network_entries: list = []
        self._sensitive_alerts: list = []
        self._command_queue: list = []
        self._paused = False
        self._headless = False
        self._evidence_level = "light"

    def start(
        self,
        recording_id: str,
        application: str = "",
        base_url: str = "",
        headless: bool = False,
        evidence_level: str = "light",
        system: str = "",
        suite: str = "",
        test_case: str = "",
    ) -> RecordingSession:
        session = self._session_manager.start(recording_id, application, base_url)
        self._store = RawRecordingStore(session.session_dir)
        self._network_entries = []
        self._sensitive_alerts = []
        self._command_queue = []
        self._paused = False
        self._headless = headless
        self._evidence_level = evidence_level

        self._page.on("request", self._on_request)
        self._page.on("response", self._on_response)
        self._page.on("framenavigated", self._on_framenavigated)

        # Inject recording context so the overlay can display system/suite/test_case
        context_script = (
            "window.__tfRecordingInfo = {"
            f" rid: {json.dumps(recording_id)},"
            f" system: {json.dumps(system)},"
            f" suite: {json.dumps(suite)},"
            f" testCase: {json.dumps(test_case or recording_id)}"
            " };"
        )
        self._page.add_init_script(context_script)
        self._page.add_init_script(_OVERLAY_JS)
        self._store.save_metadata("recording_config", {
            "evidence_level": self._evidence_level,
            "headless": self._headless,
        })
        logger.info("Recording started id=%s app=%s url=%s headless=%s evidence=%s system=%s suite=%s",
                     recording_id, application, base_url, headless, evidence_level, system, suite)
        return session

    def wait_for_command(self, timeout_ms: int = 500) -> list[str]:
        """Polls JS command queue and returns pending commands."""
        try:
            cmds = self._page.evaluate("""() => {
                const q = window.__tfCommandQueue || [];
                window.__tfCommandQueue = [];
                return q;
            }""")
            if cmds:
                self._command_queue.extend(cmds)
            return [self._command_queue.pop(0) for _ in range(len(self._command_queue))]
        except Exception:
            return []

    def flush_events(self):
        """Read pending events and steps from JS."""
        try:
            events = self._page.evaluate("""() => {
                const evts = window.__tfEventQueue || [];
                window.__tfEventQueue = [];
                const steps = window.__tfStepQueue || [];
                window.__tfStepQueue = [];
                return {events: evts, steps: steps};
            }""")
            raw_events = events.get("events", [])
            raw_steps = events.get("steps", [])
            # Log per-type counts for audit
            type_counts = {}
            for data in raw_events:
                et = data.get("type", "unknown")
                type_counts[et] = type_counts.get(et, 0) + 1
                self._persist_raw_event(data)
            if type_counts:
                logger.debug("Flushed %d events: %s", len(raw_events), type_counts)
            for step_data in raw_steps:
                self._persist_step(step_data)
            if raw_steps:
                logger.debug("Flushed %d steps", len(raw_steps))
        except Exception as exc:
            logger.error("flush_events failed: %s", exc, exc_info=True)
        fsnap_count = self._flush_field_snapshots()
        vmut_count = self._flush_value_mutations()
        if fsnap_count or vmut_count:
            logger.debug("Flushed %d field snapshots, %d value mutations", fsnap_count, vmut_count)

    def handle_commands(self) -> str:
        """Process pending commands. Returns 'stop' if recording should end."""
        pending = self.wait_for_command()
        for cmd in pending:
            if cmd == "STOP":
                logger.info("Recording stop command received")
                return "stop"
            elif cmd == "TOGGLE_PAUSE":
                self._paused = not self._paused
                logger.info("Recording %s", "paused" if self._paused else "resumed")
            elif cmd == "ASSERT":
                logger.info("Assert mode activated by keyboard shortcut")
        return "continue" if not self._paused else "paused"

    def stop(self) -> RecordingSession:
        self._capture_final_state_snapshot("recording_stopped")
        self.flush_events()
        for event_name in ("request", "response", "framenavigated"):
            try:
                self._page.remove_listener(event_name, getattr(self, f"_on_{event_name}"))
            except Exception:
                pass
        session = self._session_manager.stop()
        self._store.save_network_log(self._network_entries)
        if self._sensitive_alerts:
            self._store.save_sensitive_data_alert(self._sensitive_alerts)
        evt_count = self._store.event_count() if hasattr(self._store, 'event_count') else 0
        logger.info("Recording stopped id=%s events=%d network=%d alerts=%d",
                     session.recording_id if session else "?",
                     evt_count, len(self._network_entries), len(self._sensitive_alerts))
        return session

    def finalize(self) -> RecordingSession:
        self._capture_final_state_snapshot("recording_finalized")
        self.flush_events()
        return self._session_manager.finalize()

    @property
    def active_session(self):
        return self._session_manager.active_session

    # --- Internal ---

    def _persist_raw_event(self, data: dict):
        target_data = data.get("target")
        target = None
        if target_data:
            target = TargetInfo(
                tag=target_data.get("tag"),
                text=target_data.get("text"),
                role=target_data.get("role"),
                accessible_name=target_data.get("accessible_name"),
                element_id=target_data.get("id"),
                name=target_data.get("name"),
                test_id=target_data.get("test_id"),
                placeholder=target_data.get("placeholder"),
                label=target_data.get("label"),
                attributes={
                    "class": target_data.get("className"),
                    "type": target_data.get("type"),
                    "value": target_data.get("value"),
                },
                all_attributes=target_data.get("all_attributes") or {},
                class_list=target_data.get("class_list") or [],
                aria_attrs=target_data.get("aria_attrs") or {},
                data_attrs=target_data.get("data_attrs") or {},
                parent_text=target_data.get("parent_text"),
                css_path=target_data.get("css_path"),
                xpath=target_data.get("xpath"),
                nth_child=target_data.get("nth_child") or 0,
                sibling_summary=target_data.get("sibling_summary") or [],
                inner_html=target_data.get("inner_html"),
                bounding_box=target_data.get("bounding_box"),
            )
        self._event_counter += 1
        event = RawRecordedEvent(
            event_id=f"evt_{self._event_counter:05d}",
            event_type=data.get("type", "unknown"),
            timestamp=data.get("timestamp", ""),
            url=data.get("url"),
            page_title=data.get("page_title"),
            target=target,
            value=data.get("value"),
            is_postback=data.get("is_postback", False),
            submit_method=data.get("submit_method"),
        )
        self._capture_snapshots(event)
        self._store.append_event(event)

    def _persist_step(self, data: dict):
        """Persist a user-intended step (click, fill, or assert)."""
        self._step_counter += 1
        path = os.path.join(self._store._session_dir, "steps.jsonl")
        step = {
            "step_id": f"step_{self._step_counter:04d}",
            "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "action": data.get("action"),
            "selector": data.get("selector", ""),
            "tag_name": data.get("tagName", ""),
            "text": data.get("text", ""),
            "value": data.get("value", ""),
            "url": self._page.url,
            "page_title": self._page.title(),
            "assert_type": data.get("assert_type", ""),
            "assert_state": data.get("assert_state", ""),
            "expected_value": data.get("expected_value", ""),
            "attrs": data.get("attrs", {}),
            "fallbacks": data.get("fallbacks", []),
            "element_id": data.get("element_id", ""),
            "aria_label": data.get("aria_label", ""),
            "role": data.get("role", ""),
            "css_path": data.get("css_path", ""),
            "accessible_name": data.get("accessible_name", ""),
        }
        with open(path, "a") as f:
            f.write(json.dumps(step, default=str) + "\n")

    def _capture_snapshots(self, event: RawRecordedEvent):
        eid = event.event_id
        # Screenshot only in full evidence mode (avoids flick, reduces disk I/O)
        if self._evidence_level == "full":
            try:
                data = self._page.screenshot(type="png", full_page=False)
                event.screenshot_path = self._store.save_screenshot(eid, data)
            except Exception:
                pass
        # DOM snapshot always (needed for normalizer / locator scoring)
        try:
            self._page.wait_for_load_state("domcontentloaded", timeout=3000)
        except Exception:
            pass
        try:
            dom = self._page.content()
            event.dom_snapshot_path = self._store.save_dom(eid, dom)
        except Exception:
            pass

    def _on_request(self, request: Request):
        post_data = None
        try:
            if request.method in ("POST", "PUT", "PATCH"):
                post_data = request.post_data
        except Exception:
            pass
        self._network_entries.append({
            "type": "request", "method": request.method,
            "url": request.url, "resource_type": request.resource_type,
            "post_data": post_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def _on_response(self, response: Response):
        self._network_entries.append({
            "type": "response", "url": response.url,
            "status": response.status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def _on_framenavigated(self, frame):
        """Track main-frame navigation from Python side."""
        if frame != self._page.main_frame:
            return
        try:
            current_url = self._page.url
            page_title = self._page.title()
        except Exception:
            current_url = frame.url
            page_title = ""
        self._event_counter += 1
        nav_event = RawRecordedEvent(
            event_id=f"evt_{self._event_counter:05d}",
            event_type="navigation",
            timestamp=datetime.now(timezone.utc).isoformat(),
            url=current_url,
            page_title=page_title,
            target=None,
            value=None,
        )
        self._store.append_event(nav_event)
        logger.info("Navigation detected: %s — %s", current_url, page_title[:60])

    # ---- Sprint 3: Field snapshot & value mutation persistence ----

    def _save_field_snapshot(self, snapshot_data: dict):
        """Append a single field snapshot to field_snapshots.jsonl."""
        path = os.path.join(self._store._session_dir, "field_snapshots.jsonl")
        with open(path, "a") as f:
            f.write(json.dumps(snapshot_data, default=str) + "\n")

    def _save_value_mutation(self, mutation_data: dict):
        """Append a value mutation to value_mutations.jsonl."""
        path = os.path.join(self._store._session_dir, "value_mutations.jsonl")
        with open(path, "a") as f:
            f.write(json.dumps(mutation_data, default=str) + "\n")

    def _flush_field_snapshots(self) -> int:
        """Read pending field snapshot batches from JS and persist. Returns count."""
        try:
            batches = self._page.evaluate("""() => {
                const q = window.__tfFieldSnapshotQueue || [];
                window.__tfFieldSnapshotQueue = [];
                return q;
            }""")
            count = len(batches or [])
            for batch in (batches or []):
                self._save_field_snapshot(batch)
            return count
        except Exception as exc:
            logger.warning("_flush_field_snapshots failed: %s", exc)
            return 0

    def _flush_value_mutations(self) -> int:
        """Read pending value mutations from JS and persist. Returns count."""
        try:
            mutations = self._page.evaluate("""() => {
                const q = window.__tfValueMutationQueue || [];
                window.__tfValueMutationQueue = [];
                return q;
            }""")
            count = len(mutations or [])
            for mut in (mutations or []):
                self._save_value_mutation(mut)
            return count
        except Exception as exc:
            logger.warning("_flush_value_mutations failed: %s", exc)
            return 0

    def _capture_final_state_snapshot(self, reason: str = "unknown"):
        """Read final state from JS sessionStorage and save to final_state_snapshot.json."""
        try:
            final_state = self._page.evaluate("""() => {
                const raw = sessionStorage.getItem('__tfFinalState');
                sessionStorage.removeItem('__tfFinalState');
                return raw ? JSON.parse(raw) : null;
            }""")
            if final_state:
                path = os.path.join(self._store._session_dir, "final_state_snapshot.json")
                with open(path, "w") as f:
                    json.dump(final_state, f, indent=2, default=str)
        except Exception:
            pass

    # --- Overlay JS injected from overlay_inject.js (loaded at module level) ---
