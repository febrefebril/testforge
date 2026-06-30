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

from testforge.diagnostic.framework_detector import FrameworkDetector

from .cdp_snapshot import CDPSnapshotter
from .raw_event import RawRecordedEvent, TargetInfo
from .raw_recording_store import RawRecordingStore
from .recording_session import RecordingSession, RecordingSessionManager
from .tracing_manager import TracingManager

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
    _OVERLAY_JS: str = _OVERLAY_JS  # expose module-level for tests

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
        # Phase 1: parallel CDP/tracing capture (active by default)
        self._use_cdp = True
        self._tracing: TracingManager | None = None
        self._cdp: CDPSnapshotter | None = None
        # Framework detection (active by default)
        self._framework: str = "unknown"
        self._detector: FrameworkDetector | None = None
        # Sprint 0: diagnostic mode (feature-flagged)
        self._diagnostic_mode = False
        self._diagnostic = None  # DiagnosticSession instance
        # Hotfix H1: browser/page-closed flag (treat user close as graceful stop)
        self._closed = False

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
        use_cdp: bool = True,
        diagnostic_mode: bool = False,
        replay_mode: str = "batched",   # H17: was "immediate"
    ) -> RecordingSession:
        session = self._session_manager.start(recording_id, application, base_url)
        self._store = RawRecordingStore(session.session_dir)
        self._network_entries = []
        self._sensitive_alerts = []
        self._command_queue = []
        self._paused = False
        self._headless = headless
        self._evidence_level = evidence_level
        self._use_cdp = bool(use_cdp)

        self._page.on("request", self._on_request)
        self._page.on("response", self._on_response)
        self._page.on("framenavigated", self._on_framenavigated)
        # Hotfix H1: treat browser/page close as graceful stop. Same path as
        # Shift+S — sets a flag consumed by handle_commands() so the recording
        # loop drains and finalize() runs normally instead of leaving artifacts
        # half-written.
        self._closed = False
        self._page.on("close", self._on_target_closed)
        try:
            self._page.context.on("close", self._on_target_closed)
        except Exception:
            pass

        # Phase 1: start Playwright tracing + attach CDP for AX-tree snapshots.
        # Runs in parallel with legacy JS overlay capture. Active by default.
        if self._use_cdp:
            self._tracing = TracingManager(self._page)
            self._tracing.start(session.session_dir, recording_id)
            self._cdp = CDPSnapshotter(self._page)
            self._cdp.attach()
            logger.info("Phase 1 capture enabled: tracing + CDP AX snapshots")

        # Framework detection ativo por padrao — adapta captura ao framework detectado
        cdp_session = self._cdp._session if self._cdp and self._cdp._enabled else None
        self._detector = FrameworkDetector(self._page, cdp_session)
        self._detector.attach()
        self._detect_framework()

        # Sprint 0: diagnostic recorder (rich telemetry collection)
        self._diagnostic_mode = bool(diagnostic_mode)
        if self._diagnostic_mode:
            from testforge.diagnostic import DiagnosticSession
            cdp_session = self._cdp._session if self._cdp and self._cdp._enabled else None
            diag_dir = os.path.join(session.session_dir, "diagnostic")
            self._diagnostic = DiagnosticSession(
                page=self._page, cdp_session=cdp_session,
                session_dir=diag_dir, replay_mode=replay_mode,
            )
            self._diagnostic.start()
            logger.info("Sprint 0 diagnostic mode enabled dir=%s replay=%s",
                         diag_dir, replay_mode)

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
        """Return cached commands drained from last flush_events call."""
        return [self._command_queue.pop(0) for _ in range(len(self._command_queue))]

    def flush_events(self):
        """Read all pending JS queues in a single CDP call to minimise V8 pauses."""
        # Hotfix BUG 2: silently no-op when the page/browser/context is gone.
        try:
            _ = self._page.url  # cheap check; raises if closed
        except Exception:
            return
        try:
            payload = self._page.evaluate("""() => {
                const evts  = window.__tfEventQueue         || []; window.__tfEventQueue         = [];
                const steps = window.__tfStepQueue          || []; window.__tfStepQueue          = [];
                const cmds  = window.__tfCommandQueue       || []; window.__tfCommandQueue       = [];
                const fsnap = window.__tfFieldSnapshotQueue || []; window.__tfFieldSnapshotQueue = [];
                const vmuts = window.__tfValueMutationQueue || []; window.__tfValueMutationQueue = [];
                return {events: evts, steps: steps, commands: cmds, fieldSnapshots: fsnap, valueMutations: vmuts};
            }""")
            raw_events   = payload.get("events", [])
            raw_steps    = payload.get("steps", [])
            raw_commands = payload.get("commands", [])
            raw_fsnaps   = payload.get("fieldSnapshots", [])
            raw_vmuts    = payload.get("valueMutations", [])

            if raw_commands:
                self._command_queue.extend(raw_commands)

            type_counts = {}
            for data in raw_events:
                et = data.get("type", "unknown")
                type_counts[et] = type_counts.get(et, 0) + 1
                self._persist_raw_event(data)
                # Hotfix BUG 10: keep a short tail of recent clicks so the
                # request handler can promote them to pseudo-submit when a
                # POST/PUT/PATCH XHR fires shortly after.
                if et == "click":
                    if not hasattr(self, "_recent_clicks"):
                        self._recent_clicks = []
                    self._recent_clicks.append({
                        "event_id": data.get("event_id"),
                        "ts": datetime.now(timezone.utc).timestamp(),
                    })
            if type_counts:
                logger.debug("Flushed %d events: %s | counters raw=%d steps=%d commands=%d",
                             len(raw_events), type_counts,
                             self._event_counter, self._step_counter, len(self._command_queue))

            for step_data in raw_steps:
                self._persist_step(step_data)
            if raw_steps:
                logger.debug("Flushed %d steps", len(raw_steps))

            for batch in raw_fsnaps:
                self._save_field_snapshot(batch)
            for mut in raw_vmuts:
                self._save_value_mutation(mut)
            if raw_fsnaps or raw_vmuts:
                logger.debug("Flushed %d field snapshots, %d value mutations", len(raw_fsnaps), len(raw_vmuts))
        except Exception as exc:
            # Hotfix BUG 2: closed-target errors during the recorder's
            # natural shutdown are not real failures — log at debug only.
            msg = str(exc)
            if "closed" in msg.lower() or "target" in msg.lower():
                logger.debug("flush_events tolerated (page closed): %s", exc)
            else:
                logger.error("flush_events failed: %s", exc, exc_info=True)

    def handle_commands(self) -> str:
        """Process pending commands. Returns 'stop' if recording should end."""
        # Hotfix H1: user-closed browser/page is equivalent to Shift+S.
        if self._closed:
            logger.info("Recording stop triggered by browser/page close")
            return "stop"
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

    def _on_target_closed(self, *_args) -> None:
        """Hotfix H1: page or context closed by user — flag for graceful stop."""
        if self._closed:
            return
        self._closed = True
        logger.info("Recording target closed by user — graceful stop scheduled")

    def detach_page_listeners(self) -> None:
        """Hotfix BUG 2: remove page listeners synchronously.

        Called before any blocking input (Gherkin prompt) so the browser
        can be closed by the user without triggering callbacks that race
        against a torn-down page.
        """
        for event_name in ("request", "response", "framenavigated"):
            try:
                self._page.remove_listener(event_name, getattr(self, f"_on_{event_name}"))
            except Exception:
                pass

    def stop(self,
             gherkin_funcionalidade: str = "",
             gherkin_cenario: str = "") -> RecordingSession:
        # Hotfix BUG 2: capture final snapshot + flush tolerating a closed page.
        try:
            self._capture_final_state_snapshot("recording_stopped")
        except Exception:
            pass
        try:
            self.flush_events()
        except Exception as exc:
            logger.debug("flush_events tolerated (page may be closed): %s", exc)
        # Sprint 0: finalize diagnostic session (writes session.json + scenario.feature)
        if self._diagnostic is not None:
            try:
                self._diagnostic.finalize(
                    funcionalidade_override=gherkin_funcionalidade,
                    cenario_override=gherkin_cenario,
                )
            except Exception as exc:
                logger.error("Diagnostic finalize failed: %s", exc)
        # Phase 1: stop tracing + detach CDP before tearing down page listeners.
        if self._tracing is not None and self._tracing.is_active:
            try:
                self._tracing.stop()
            except Exception as exc:
                logger.error("Tracing stop failed: %s", exc)
        if self._detector is not None:
            try:
                self._detector.detach()
            except Exception:
                pass
        if self._cdp is not None:
            try:
                self._cdp.detach()
            except Exception:
                pass
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
        # Hotfix H1: tolerate closed page during finalize (browser may have
        # been closed by user — same path as Shift+S, just no live page).
        try:
            self._capture_final_state_snapshot("recording_finalized")
        except Exception:
            pass
        try:
            self.flush_events()
        except Exception:
            pass
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
        # Sprint 0: diagnostic per-event assessment
        if self._diagnostic is not None:
            try:
                # Hotfix BUG 7: build quick heuristic candidates so ReplayCheck
                # has something to probe — the legacy overlay does not surface
                # the v2 LocatorExtractor output during recording.
                from ..diagnostic.heuristic_candidates import build_quick_candidates
                quick_candidates = build_quick_candidates(target_data)
                self._diagnostic.assess_event(
                    raw_event={
                        "event_id": event.event_id,
                        "type": event.event_type,
                        "timestamp": event.timestamp,
                        "value": event.value,
                        "target": target_data,
                    },
                    target_data=target_data,
                    candidates=quick_candidates,
                )
            except Exception as exc:
                logger.debug("Diagnostic assess failed: %s", exc)

    def _persist_step(self, data: dict):
        """Persist a user-intended step (click, fill, or assert)."""
        self._step_counter += 1
        path = os.path.join(self._store._session_dir, "steps.jsonl")
        try:
            try:
                page_title = self._page.title()
            except Exception:
                page_title = ""
            try:
                page_url = self._page.url
            except Exception:
                page_url = ""
            step = {
                "step_id": f"step_{self._step_counter:04d}",
                "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "action": data.get("action"),
                "selector": data.get("selector", ""),
                "tag_name": data.get("tagName", ""),
                "text": data.get("text", ""),
                "value": data.get("value", ""),
                "url": page_url,
                "page_title": page_title,
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
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(step, default=str) + "\n")
        except Exception as exc:
            logger.error("[TestForge] Falha ao salvar step: %s", exc)
            import sys
            print(f"[TestForge] AVISO: step nao salvo — {exc}", file=sys.stderr)

    def _capture_snapshots(self, event: RawRecordedEvent):
        eid = event.event_id
        if self._evidence_level == "full":
            try:
                data = self._page.screenshot(type="png", full_page=False)
                event.screenshot_path = self._store.save_screenshot(eid, data)
            except Exception:
                pass
        try:
            self._page.wait_for_load_state("domcontentloaded", timeout=2000)
        except Exception:
            pass
        try:
            dom = self._page.content()
            if dom and len(dom.strip()) >= 20:
                event.dom_snapshot_path = self._store.save_dom(eid, dom)
        except Exception:
            pass
        # Phase 1: AX-tree snapshot via CDP (parallel to legacy DOM snapshot).
        if self._cdp is not None and self._cdp._enabled:
            try:
                ax_tree = self._cdp.get_full_ax_tree()
                if ax_tree:
                    event.ax_snapshot_path = self._store.save_ax_snapshot(eid, ax_tree)
            except Exception as exc:
                logger.debug("AX snapshot failed for %s: %s", eid, exc)

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
        # Hotfix BUG 10 (+ hotfix 12 follow-up): in SPA Angular apps
        # `<form action>` submits are rare. The user clicks a button and the
        # framework dispatches an XHR/fetch POST/PUT/PATCH that carries the
        # form payload. Promote the latest click event to a pseudo-submit
        # when a same-origin POST/PUT/PATCH fires within 1500 ms of it so
        # downstream IntentReconstructor and form-values capture get the
        # payload they expect.
        #
        # Hotfix 12 fix: the click that triggered the XHR usually arrives on
        # the JS overlay's __tfEventQueue *before* this _on_request handler
        # runs, but it is still in JS-land — Python's _recent_clicks is
        # empty until the next flush_events tick. Drain the queue here
        # before matching so the tail actually contains the triggering
        # click. The cost is one extra CDP evaluate per POST/PUT/PATCH XHR.
        try:
            if request.method in ("POST", "PUT", "PATCH") \
               and request.resource_type in ("xhr", "fetch") \
               and post_data:
                try:
                    self.flush_events()
                except Exception:
                    pass
                self._mark_pseudo_submit(request.url, request.method, post_data)
        except Exception:
            pass

    def _mark_pseudo_submit(self, url: str, method: str, post_data) -> None:
        """Promote the most-recent click event to a submit-like event."""
        if not self._network_entries:
            return
        # Try to find a recent click in raw_events. Look at events written in
        # the last 1.5 s by reading the in-memory event counter is not enough
        # — they are already serialized. Use a small in-memory tail.
        if not hasattr(self, "_recent_clicks"):
            self._recent_clicks = []
        # Drop clicks older than 1.5 s
        now = datetime.now(timezone.utc).timestamp()
        self._recent_clicks = [c for c in self._recent_clicks
                                if now - c["ts"] < 1.5]
        if not self._recent_clicks:
            return
        latest = self._recent_clicks[-1]
        # Decode the post_data into a dict best-effort
        form_values = {}
        try:
            import json as _json
            from urllib.parse import parse_qsl
            if post_data.lstrip().startswith("{"):
                parsed = _json.loads(post_data)
                if isinstance(parsed, dict):
                    form_values = {str(k): str(v) for k, v in parsed.items()
                                    if v not in (None, "")}
            else:
                form_values = dict(parse_qsl(post_data)) or {}
        except Exception:
            pass
        latest["pseudo_submit"] = {
            "url": url, "method": method,
            "form_values": form_values,
        }
        # Hotfix 12: also tag the matching network entry so audit/auditors
        # and downstream consumers see the postback signal in the persisted
        # network_log.json. Match the most recent request entry by url+method
        # (single-pass from the end — typical case is the request we just
        # appended a few microseconds ago).
        try:
            for entry in reversed(self._network_entries):
                if not isinstance(entry, dict):
                    continue
                if entry.get("type") != "request":
                    continue
                if entry.get("url") == url and entry.get("method") == method:
                    entry["is_pseudo_submit"] = True
                    entry["pseudo_submit_click_event_id"] = latest.get("event_id")
                    if form_values:
                        entry["form_values"] = form_values
                    break
        except Exception:
            pass

    def _on_response(self, response: Response):
        self._network_entries.append({
            "type": "response", "url": response.url,
            "status": response.status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # BUG-007: dedup navigation events — skip if URL hasn't changed
    _last_nav_url: str | None = None

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
        # Skip navigations where the URL hasn't changed (reloads, SIMAX flicker)
        if current_url == self._last_nav_url:
            return
        self._last_nav_url = current_url
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
        # Sprint 0: feed navigation into diagnostic Gherkin writer
        if self._diagnostic is not None:
            try:
                self._diagnostic.on_navigation(current_url, page_title)
            except Exception:
                pass
        logger.info("Navigation detected: %s — %s", current_url, page_title[:60])
        # Re-detect framework apos navegacao (SPA pode mudar de framework)
        self._detect_framework()

    # ---- Sprint 3: Field snapshot & value mutation persistence ----

    def _save_field_snapshot(self, snapshot_data: dict):
        """Append a single field snapshot to field_snapshots.jsonl."""
        path = os.path.join(self._store._session_dir, "field_snapshots.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(snapshot_data, default=str) + "\n")

    def _save_value_mutation(self, mutation_data: dict):
        """Append a value mutation to value_mutations.jsonl."""
        path = os.path.join(self._store._session_dir, "value_mutations.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(mutation_data, default=str) + "\n")

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
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(final_state, f, indent=2, default=str)
        except Exception:
            pass

    # ---- Framework detection ----
    def _detect_framework(self) -> str:
        """Detecta framework e adapta estrategias de captura no overlay."""
        if self._detector is None:
            return "unknown"
        try:
            result = self._detector.detect()
            new_fw = result.get("primary", "unknown")
            if new_fw != "unknown":
                self._framework = new_fw
                logger.info("Framework detected: %s (evidence: %s)",
                            new_fw, result.get("evidence", [])[:3])
                # Sinaliza para o overlay JS adaptar estrategias
                try:
                    if new_fw in ("react", "mui"):
                        self._page.evaluate("window.__tfReactCompat = true")
                    elif new_fw in ("angular", "angular-material"):
                        self._page.evaluate("window.__tfAngularCompat = true")
                except Exception:
                    pass
            return self._framework
        except Exception as exc:
            logger.debug("Framework detection failed: %s", exc)
            return self._framework

    # --- Overlay JS injected from overlay_inject.js (loaded at module level) ---
