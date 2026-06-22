"""TestForge — Recorder Controller com asserts e comandos de teclado.

Keyboard shortcuts: Shift+P pause, Shift+S stop, Shift+A assert mode
Assert types: textual, estado, visivel, automatico
"""
import json
import os
import re
import time
from datetime import datetime, timezone

from playwright.sync_api import Page, Request, Response

from .raw_event import RawRecordedEvent, TargetInfo
from .raw_recording_store import RawRecordingStore
from .recording_session import RecordingSession, RecordingSessionManager


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

    def start(self, recording_id: str, application: str = "", base_url: str = "", headless: bool = False, evidence_level: str = "light") -> RecordingSession:
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

        self._page.add_init_script(self._OVERLAY_JS)
        self._store.save_metadata("recording_config", {
            "evidence_level": self._evidence_level,
            "headless": self._headless,
        })
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
            for data in events.get("events", []):
                self._persist_raw_event(data)
            for step_data in events.get("steps", []):
                self._persist_step(step_data)
        except Exception:
            pass
        self._flush_field_snapshots()
        self._flush_value_mutations()

    def handle_commands(self) -> str:
        """Process pending commands. Returns 'stop' if recording should end."""
        pending = self.wait_for_command()
        for cmd in pending:
            if cmd == "STOP":
                return "stop"
            elif cmd == "TOGGLE_PAUSE":
                self._paused = not self._paused
        return "continue" if not self._paused else "paused"

    def stop(self) -> RecordingSession:
        self._capture_final_state_snapshot("recording_stopped")
        self.flush_events()
        try:
            self._page.remove_listener("request", self._on_request)
        except Exception:
            pass
        try:
            self._page.remove_listener("response", self._on_response)
        except Exception:
            pass
        session = self._session_manager.stop()
        self._store.save_network_log(self._network_entries)
        if self._sensitive_alerts:
            self._store.save_sensitive_data_alert(self._sensitive_alerts)
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

    def _flush_field_snapshots(self):
        """Read pending field snapshot batches from JS and persist."""
        try:
            batches = self._page.evaluate("""() => {
                const q = window.__tfFieldSnapshotQueue || [];
                window.__tfFieldSnapshotQueue = [];
                return q;
            }""")
            for batch in (batches or []):
                self._save_field_snapshot(batch)
        except Exception:
            pass

    def _flush_value_mutations(self):
        """Read pending value mutations from JS and persist."""
        try:
            mutations = self._page.evaluate("""() => {
                const q = window.__tfValueMutationQueue || [];
                window.__tfValueMutationQueue = [];
                return q;
            }""")
            for mut in (mutations or []):
                self._save_value_mutation(mut)
        except Exception:
            pass

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

    # --- Overlay JS (injected into page) ---
    _OVERLAY_JS = r"""
        window.__tfEventQueue = [];
        window.__tfStepQueue = [];
        window.__tfCommandQueue = [];
        window.__tfFieldSnapshotQueue = [];
        window.__tfValueMutationQueue = [];
        window.__tfEventCounter = window.__tfEventCounter || 0;
        window.__tfAssertWaiting = false;
        window.__tfDragMode  = false;
        window.__tfDragState = null;
        window.__tfPendingSubmit = null;  // { url, method, timestamp } or null — restored from sessionStorage

        // Restore pending submit flag from sessionStorage (survives page navigation).
        // This tells us the page load is a form postback (ASP classic / ASP.NET).
        try {
            var _storedPending = sessionStorage.getItem('__tfPendingSubmit');
            if (_storedPending) {
                window.__tfPendingSubmit = JSON.parse(_storedPending);
                sessionStorage.removeItem('__tfPendingSubmit');
            }
        } catch(_e) { /* sessionStorage unavailable (e.g. file://) */ }

        // Restore unflushed events from previous page (saved by beforeunload handler).
        // The submit event that triggered navigation is in here with full target info.
        try {
            var _unflushedEvents = sessionStorage.getItem('__tfUnflushedEvents');
            if (_unflushedEvents) {
                var _evts = JSON.parse(_unflushedEvents);
                // Merge postback metadata into restored submit events.
                // This avoids page reload flicker: the submit event appears on the
                // new page with postback context, not as a separate postback event.
                if (window.__tfPendingSubmit) {
                    for (var i = 0; i < _evts.length; i++) {
                        if (_evts[i].type === 'submit') {
                            _evts[i].is_postback = true;
                            _evts[i].submit_method = _evts[i].submit_method || window.__tfPendingSubmit.method;
                            _evts[i].postback_url = window.__tfPendingSubmit.url;
                        }
                    }
                }
                window.__tfEventQueue = _evts;
                sessionStorage.removeItem('__tfUnflushedEvents');
                console.log('[TestForge] restored ' + _evts.length + ' unflushed event(s) from previous page');
            }
            var _unflushedSteps = sessionStorage.getItem('__tfUnflushedSteps');
            if (_unflushedSteps) {
                window.__tfStepQueue = JSON.parse(_unflushedSteps);
                sessionStorage.removeItem('__tfUnflushedSteps');
            }
        } catch(_e) { /* ignore */ }

        window._tf_getSelector = function(el) {
            try {
                if (!el || !el.tagName) return 'unknown';
                if (el.id && typeof CSS !== 'undefined' && CSS.escape) return '#' + CSS.escape(el.id);
                if (el.id) return '#' + el.id;
                var parts = [];
                var current = el;
                while (current && current !== document.body && current !== document.documentElement) {
                    var tag = current.tagName.toLowerCase();
                    var selector = tag;
                    if (current.id) {
                        var escaped = (typeof CSS !== 'undefined' && CSS.escape) ? CSS.escape(current.id) : current.id;
                        return '#' + escaped + ' ' + parts.join(' > ');
                    }
                    if (current.className && typeof current.className === 'string') {
                        var cls = current.className.trim().split(/\\s+/)[0];
                        if (cls && !cls.startsWith('tf-')) selector += '.' + (typeof CSS !== 'undefined' && CSS.escape ? CSS.escape(cls) : cls);
                    }
                    parts.unshift(selector);
                    current = current.parentElement;
                }
                return parts.join(' > ') || el.tagName.toLowerCase();
            } catch(e) {
                return (el.tagName || 'unknown').toLowerCase();
            }
        }

        window._tf_extractTarget = function(el) {
            if (!el || el === document.body || el === document.documentElement) return null;
            var rect = el.getBoundingClientRect ? el.getBoundingClientRect() : {};
            var labelEl = el.id ? document.querySelector('label[for="' + el.id + '"]') : null;

            // Collect ALL attributes inline (don't depend on function order)
            var allAttrs = {};
            if (el && el.attributes) {
                for (var ai = 0; ai < el.attributes.length; ai++) {
                    var attr = el.attributes[ai];
                    allAttrs[attr.name] = attr.value;
                }
            }

            // Collect aria-* attributes
            var ariaAttrs = {};
            for (var key in allAttrs) {
                if (key.startsWith('aria-')) ariaAttrs[key] = allAttrs[key];
            }

            // Collect data-* attributes
            var dataAttrs = {};
            for (var key in allAttrs) {
                if (key.startsWith('data-')) dataAttrs[key] = allAttrs[key];
            }

            // Collect CSS classes as array
            var classList = [];
            if (typeof el.className === 'string' && el.className.trim()) {
                classList = el.className.trim().split(/\\s+/).filter(function(c) { return c && !c.startsWith('tf-'); });
            }

            // Parent text for context (when element has no text itself)
            var parentText = null;
            var elText = (el.textContent||'').trim().substring(0,200) || null;
            if (!elText && el.parentElement && el.parentElement !== document.body) {
                parentText = (el.parentElement.textContent||'').trim().substring(0,200) || null;
            }

            // CSS path: walk up DOM to <body>
            var cssPath = '';
            try {
                var parts = [];
                var current = el;
                while (current && current !== document.body && current !== document.documentElement) {
                    var sel = (current.tagName||'').toLowerCase();
                    if (current.id) { sel += '#' + current.id; }
                    else if (current.className && typeof current.className === 'string') {
                        var cls = current.className.trim().split(/\\s+/)[0];
                        if (cls && !cls.startsWith('tf-')) sel += '.' + cls;
                    }
                    parts.unshift(sel);
                    current = current.parentElement;
                }
                cssPath = parts.join(' > ') || '';
            } catch(_e) { cssPath = ''; }

            // XPath (use built-in _tf_domPath if available, fallback to empty)
            var xpath = '';
            try { if (typeof window._tf_domPath === 'function') xpath = window._tf_domPath(el); } catch(_e2) { xpath = ''; }

            // nth-child position among same-tag siblings
            var nthChild = 0;
            try {
                var tag = (el.tagName||'').toLowerCase();
                var parent = el.parentElement;
                if (parent) {
                    var siblings = parent.children;
                    var count = 0;
                    for (var i = 0; i < siblings.length; i++) {
                        if ((siblings[i].tagName||'').toLowerCase() === tag) {
                            count++;
                            if (siblings[i] === el) { nthChild = count; break; }
                        }
                    }
                }
            } catch(_e) { nthChild = 0; }

            // Sibling summary (prev + next)
            var siblingSummary = [];
            try {
                var prev = el.previousElementSibling;
                var next = el.nextElementSibling;
                var sumSib = function(sib) {
                    if (!sib) return null;
                    return {
                        tag: (sib.tagName||'').toLowerCase(),
                        text: (sib.textContent||'').trim().substring(0,60) || null,
                        id: sib.id || null
                    };
                };
                if (prev) siblingSummary.push(sumSib(prev));
                if (next) siblingSummary.push(sumSib(next));
            } catch(_e) { siblingSummary = []; }

            // Inner HTML summary
            var innerHtml = (el.innerHTML||'').substring(0,200) || null;

            return {
                tag: (el.tagName||'').toLowerCase(),
                text: elText,
                role: el.getAttribute('role') || null,
                accessible_name: el.getAttribute('aria-label') || el.getAttribute('title') || (allAttrs['aria-label'] || null),
                id: el.id || null,
                name: el.getAttribute('name') || null,
                test_id: el.getAttribute('data-testid') || el.getAttribute('data-test-id') || null,
                placeholder: el.getAttribute('placeholder') || null,
                label: labelEl ? labelEl.textContent.trim() : null,
                className: (typeof el.className === 'string') ? el.className : null,
                class_list: classList,
                aria_attrs: ariaAttrs,
                data_attrs: dataAttrs,
                all_attributes: allAttrs,
                parent_text: parentText,
                css_path: cssPath,
                xpath: xpath,
                nth_child: nthChild,
                sibling_summary: siblingSummary,
                inner_html: innerHtml,
                type: el.getAttribute('type') || null,
                value: (el.value||'').substring(0,100) || null,
                onclick: el.getAttribute('onclick') || null,
                href: el.getAttribute('href') || null,
                bounding_box: {x:Math.round(rect.x||0), y:Math.round(rect.y||0), width:Math.round(rect.width||0), height:Math.round(rect.height||0)}
            };
        }

        window._tf_captureAttr = function(el) {
            var attrs = {};
            if (el && el.attributes) {
                for (var i = 0; i < el.attributes.length; i++) {
                    var a = el.attributes[i];
                    attrs[a.name] = a.value;
                }
            }
            return attrs;
        }

        window._tf_isSubmitTrigger = function(el) {
            // Check if element triggers form submission (submit button, or link with postback)
            if (!el) return false;
            var tag = (el.tagName || '').toLowerCase();
            // Native submit elements
            if (tag === 'input' && (el.type === 'submit' || el.type === 'image')) return true;
            if (tag === 'button' && (!el.type || el.type === 'submit')) return true;
            if (tag !== 'a') return false;

            // Collect href + onclick for postback detection
            var href = (el.href || el.getAttribute('href') || '').toLowerCase();
            var onclick = (el.getAttribute('onclick') || '').toLowerCase();

            // ASP.NET __doPostBack — href or onclick
            if (href.indexOf('__dopostback') !== -1) return true;
            if (onclick.indexOf('__dopostback') !== -1) return true;
            // ASP.NET WebForm_DoPostBackWithOptions — href or onclick
            if (href.indexOf('webform_dopostbackwithoptions') !== -1) return true;
            if (onclick.indexOf('webform_dopostbackwithoptions') !== -1) return true;
            // ASP classic document.forms[...].submit() — href or onclick
            if (href.indexOf('document.forms') !== -1) return true;
            if (onclick.indexOf('document.forms') !== -1) return true;

            return false;
        }

        window._tf_pushEvent = function(type, el) {
            var target = _tf_extractTarget(el || document.activeElement);
            window.__tfEventQueue.push({
                event_id: 'evt_' + String(++window.__tfEventCounter).padStart(5,'0'),
                type: type,
                timestamp: new Date().toISOString(),
                url: window.location.href,
                page_title: document.title,
                target: target,
                value: (el && el.value) ? el.value.substring(0,200) : null
            });
        }

        // ---- Field snapshot (Sprint 3) ----
        window._tf_snapshotFields = function() {
            var snapshots = [];
            // Input, textarea, select
            document.querySelectorAll('input, textarea, select').forEach(function(el) {
                var tag = el.tagName.toLowerCase();
                var rect = el.getBoundingClientRect();
                var key = el.name || el.getAttribute('aria-label') || el.placeholder || el.id;
                if (!key) key = tag + '_' + (el.className || '').substring(0,20);
                snapshots.push({
                    timestamp: new Date().toISOString(),
                    fingerprint: tag + '#' + (el.id||'') + '[name=' + (el.name||'') + ']',
                    identifiers: {
                        id: el.id || null,
                        name: el.name || null,
                        label: el.labels && el.labels[0] ? el.labels[0].textContent.trim() : null,
                        placeholder: el.placeholder || null,
                        'aria-label': el.getAttribute('aria-label') || null,
                        css_path: window._tf_getSelector ? window._tf_getSelector(el) : null
                    },
                    tag: tag,
                    type: el.getAttribute('type') || null,
                    value: (el.value || '').substring(0, 200),
                    checked: (el.type === 'checkbox' || el.type === 'radio') ? el.checked : null,
                    visibility: (rect.width > 0 && rect.height > 0) ? 'visible' : 'hidden',
                    enabled: !el.disabled,
                    focused: el === document.activeElement,
                    bounding_box: {x: Math.round(rect.x||0), y: Math.round(rect.y||0), width: Math.round(rect.width||0), height: Math.round(rect.height||0)}
                });
            });
            // contenteditable
            document.querySelectorAll('[contenteditable="true"], [contenteditable=""]').forEach(function(el) {
                var rect = el.getBoundingClientRect();
                snapshots.push({
                    timestamp: new Date().toISOString(),
                    fingerprint: 'contenteditable#' + (el.id||'') + (el.className ? '.' + el.className.substring(0,20) : ''),
                    identifiers: {
                        id: el.id || null,
                        role: el.getAttribute('role') || null,
                        'aria-label': el.getAttribute('aria-label') || null,
                        css_path: window._tf_getSelector ? window._tf_getSelector(el) : null
                    },
                    tag: el.tagName.toLowerCase(),
                    type: 'contenteditable',
                    value: (el.textContent || '').substring(0, 200),
                    checked: null,
                    visibility: (rect.width > 0 && rect.height > 0) ? 'visible' : 'hidden',
                    enabled: !el.disabled,
                    focused: el === document.activeElement,
                    bounding_box: {x: Math.round(rect.x||0), y: Math.round(rect.y||0), width: Math.round(rect.width||0), height: Math.round(rect.height||0)}
                });
            });
            // ARIA widgets: combobox, listbox, slider, spinbutton, searchbox, textbox
            document.querySelectorAll('[role="combobox"], [role="listbox"], [role="slider"], [role="spinbutton"], [role="searchbox"], [role="textbox"]').forEach(function(el) {
                if (el.isContentEditable) return;
                if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') return;
                var rect = el.getBoundingClientRect();
                var ariaVal = el.getAttribute('aria-valuenow') || el.getAttribute('aria-valuetext') || null;
                snapshots.push({
                    timestamp: new Date().toISOString(),
                    fingerprint: 'aria-' + (el.getAttribute('role')||'widget') + '#' + (el.id||''),
                    identifiers: {
                        id: el.id || null,
                        role: el.getAttribute('role') || null,
                        'aria-label': el.getAttribute('aria-label') || null,
                        'aria-labelledby': el.getAttribute('aria-labelledby') || null,
                        css_path: window._tf_getSelector ? window._tf_getSelector(el) : null
                    },
                    tag: el.tagName.toLowerCase(),
                    type: 'aria-' + (el.getAttribute('role') || 'widget'),
                    value: ariaVal || (el.textContent || '').substring(0, 200),
                    checked: null,
                    visibility: (rect.width > 0 && rect.height > 0) ? 'visible' : 'hidden',
                    enabled: !el.disabled && el.getAttribute('aria-disabled') !== 'true',
                    focused: el === document.activeElement || el.contains(document.activeElement),
                    bounding_box: {x: Math.round(rect.x||0), y: Math.round(rect.y||0), width: Math.round(rect.width||0), height: Math.round(rect.height||0)}
                });
            });
            return snapshots;
        };

        window._tf_captureFinalState = function(reason) {
            var snapshots = window._tf_snapshotFields();
            try {
                sessionStorage.setItem('__tfFinalState', JSON.stringify({
                    reason: reason || 'unknown',
                    timestamp: new Date().toISOString(),
                    url: window.location.href,
                    page_title: document.title,
                    fields: snapshots
                }));
            } catch(_e) { /* ignore oversized */ }
            return snapshots;
        };

        // ---- Setter hooks for programmatic value changes (Sprint 3) ----
        (function() {
            var _hookValue = function(proto, tag) {
                var desc = Object.getOwnPropertyDescriptor(proto, 'value');
                if (!desc || !desc.set) return;
                Object.defineProperty(proto, 'value', {
                    configurable: true,
                    enumerable: desc.enumerable,
                    get: function() { return desc.get.call(this); },
                    set: function(val) {
                        var oldVal = desc.get.call(this);
                        desc.set.call(this, val);
                        if (oldVal !== val) {
                            window.__tfValueMutationQueue.push({
                                type: 'value_mutation',
                                timestamp: new Date().toISOString(),
                                tag: tag,
                                name: this.name || null,
                                id: this.id || null,
                                old_value: (oldVal||'').substring(0,200),
                                new_value: (val||'').substring(0,200),
                                fingerprint: tag + '#' + (this.id||'') + '[name=' + (this.name||'') + ']'
                            });
                        }
                    }
                });
            };
            try { _hookValue(HTMLInputElement.prototype, 'input'); } catch(_e) {}
            try { _hookValue(HTMLTextAreaElement.prototype, 'textarea'); } catch(_e) {}
            try { _hookValue(HTMLSelectElement.prototype, 'select'); } catch(_e) {}
        })();

        // ---- MutationObserver for contenteditable and ARIA widgets (Sprint 3) ----
        window.__tfMutationObserver = null;
        (function() {
            try {
                var _observer = new MutationObserver(function(mutations) {
                    mutations.forEach(function(mut) {
                        var el = mut.target;
                        if (!el || el === document.body || el === document.documentElement) return;
                        // contenteditable changes
                        if (el.isContentEditable) {
                            window.__tfFieldSnapshotQueue.push({
                                type: 'content_edit',
                                timestamp: new Date().toISOString(),
                                fingerprint: 'contenteditable#' + (el.id||'') + (el.className ? '.' + el.className.substring(0,20) : ''),
                                value: (el.textContent || '').substring(0, 200),
                                tag: el.tagName.toLowerCase()
                            });
                            return;
                        }
                        // ARIA attribute changes
                        if (mut.type === 'attributes' && mut.attributeName) {
                            var attrRole = mut.target.getAttribute && mut.target.getAttribute('role');
                            if (attrRole && ['combobox', 'listbox', 'slider', 'spinbutton', 'searchbox', 'textbox'].indexOf(attrRole) !== -1) {
                                if (mut.attributeName === 'aria-valuenow' || mut.attributeName === 'aria-valuetext' || mut.attributeName === 'aria-label') {
                                    window.__tfFieldSnapshotQueue.push({
                                        type: 'aria_mutation',
                                        timestamp: new Date().toISOString(),
                                        fingerprint: 'aria-' + attrRole + '#' + (mut.target.id||''),
                                        value: mut.target.getAttribute('aria-valuenow') || mut.target.getAttribute('aria-valuetext') || (mut.target.textContent || '').substring(0,200),
                                        tag: mut.target.tagName.toLowerCase(),
                                        role: attrRole,
                                        attribute: mut.attributeName
                                    });
                                }
                            }
                        }
                    });
                });
                _observer.observe(document.documentElement, {
                    childList: true,
                    subtree: true,
                    characterData: true,
                    attributes: true,
                    attributeFilter: ['aria-valuenow', 'aria-valuetext', 'aria-label', 'contenteditable']
                });
                window.__tfMutationObserver = _observer;
            } catch(_e) { /* MutationObserver not available */ }
        })();

        window._tf_detectState = function(el) {
            var tag = (el.tagName||'').toLowerCase();
            if ((tag === 'input' && (el.type === 'checkbox' || el.type === 'radio')) || tag === 'option') {
                return el.checked ? 'checked' : 'unchecked';
            }
            return el.disabled ? 'disabled' : 'enabled';
        }

        window._tf_getExpectedValue = function(el, assertType) {
            switch(assertType) {
                case 'textual':
                case 'automatico':
                    return (el.textContent||'').trim().substring(0,200);
                case 'estado':
                    return _tf_detectState(el);
                case 'visivel':
                    var rect = el.getBoundingClientRect();
                    return (rect.width > 0 && rect.height > 0) ? 'visible' : 'hidden';
            }
            return '';
        }

        window._tf_addStep = function(action, el, assertType) {
            try {
                if (!el || el === document.body || el === document.documentElement ||
                        (el.tagName && (el.tagName === 'BODY' || el.tagName === 'HTML'))) {
                    _tf_showToast('⚠ Selecione um elemento específico, não a página inteira');
                    window.__tfAssertWaiting = false;
                    var dot = document.getElementById('tf-rec-dot');
                    var status = document.getElementById('tf-status');
                    if (dot) dot.style.color = '#e94560';
                    if (status) status.textContent = 'Gravando...';
                    return false;
                }
                var selector = '';
                try { selector = _tf_getSelector(el); } catch(e) { selector = el.tagName || 'unknown'; }
                var step = {
                    action: action,
                    selector: selector,
                    tagName: (el.tagName||'').toLowerCase(),
                    text: (el.textContent||'').trim().substring(0,200),
                    value: (el.value||'').substring(0,200),
                    attrs: {},
                    timestamp: new Date().toISOString()
                };
                try { step.attrs = _tf_captureAttr(el); } catch(e) {}
                if (assertType) {
                    step.assert_type = assertType;
                    step.assert_state = assertType === 'estado' ? _tf_detectState(el) : '';
                    step.expected_value = _tf_getExpectedValue(el, assertType);
                }
                window.__tfStepQueue.push(step);
                console.log('[TestForge] _tf_addStep OK:', step.step_id || 'step', assertType, step.expected_value);
                return true;
            } catch(e) {
                console.error('[TestForge] _tf_addStep ERRO:', e.message);
                return false;
            }
        }

        // ---- Event listeners (capture phase) ----
        window.addEventListener('pointerdown', function(e) {
            if (window.__tfAssertWaiting) {
                if (e.target && e.target.closest && e.target.closest('#tf-assert-menu, #tf-assert-confirm, #tf-overlay, #tf-stop-confirm')) return;
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                console.log('[TestForge] pointerdown em modo assert, target:', e.target.tagName, e.target.className);
            }
        }, true);

        window.addEventListener('mousedown', function(e) {
            if (window.__tfAssertWaiting) {
                if (e.target && e.target.closest && e.target.closest('#tf-assert-menu, #tf-assert-confirm, #tf-overlay, #tf-stop-confirm')) return;
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
            }
        }, true);

        window.addEventListener('click', function(e) {
            var el = e.target;
            if (el && el.closest) {
                var interactive = el.closest('button, a, input, select, textarea, [role="button"], [role="listitem"], [role="option"], [role="menuitem"], mat-icon, .mat-icon, [class*="mat-"]');
                if (interactive) el = interactive;
            }
            if (window.__tfAssertWaiting) {
                if (e.target && e.target.closest && e.target.closest('#tf-assert-menu, #tf-assert-confirm, #tf-overlay, #tf-stop-confirm')) return;
                console.log('[TestForge] click em modo assert, el:', el.tagName, el.className, 'text:', (el.textContent||'').substring(0,30));
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                window.__tfAssertElement = el;
                _tf_highlight(el);
                _tf_showAssertConfirm(el, e.clientX, e.clientY);
                return;
            }
            // Detect submit triggers: record as "submit" with postback flag.
            // Only elements that actually trigger form submission qualify.
            // Regular clicks inside forms (links, divs, spans, type=button) stay as "click".
            if (_tf_isSubmitTrigger(el)) {
                var form = null;
                if (el && el.form) {
                    form = el.form;
                } else if (el && el.closest) {
                    form = el.closest('form');
                }
                // Mark pending submit for postback detection on next page load.
                // Persist to sessionStorage so it survives page navigation.
                // The actual submit event is saved via beforeunload → __tfUnflushedEvents.
                // This flag tells the next page that the load is a postback (not navigation).
                var _pending = {
                    url: form ? (form.action || window.location.href) : window.location.href,
                    method: (form && form.method) ? form.method.toUpperCase() : 'POST',
                    timestamp: Date.now()
                };
                window.__tfPendingSubmit = _pending;
                try { sessionStorage.setItem('__tfPendingSubmit', JSON.stringify(_pending)); } catch(_e) {}
                window._tf_captureFinalState('form_submit');
                _tf_pushEvent('submit', el);
                var _sc2 = document.getElementById('tf-step-count');
                if (_sc2) {
                    var _n2 = parseInt(_sc2.textContent||0) + 1;
                    _sc2.textContent = _n2;
                    try { sessionStorage.setItem('__tfStepCount', _n2); } catch(_e){}
                }
                // Capture form field values at submit time (currency-masked inputs
                // prevent native input events, so this is the only point we can read them).
                try {
                    var _formInputs = (form || document).querySelectorAll('input, textarea, select');
                    var _formValues = {};
                    _formInputs.forEach(function(_inp) {
                        var _name = _inp.name || _inp.getAttribute('aria-label') || _inp.placeholder || _inp.id || '';
                        if (_name && _inp.value && _inp.value.trim()) {
                            _formValues[_name] = _inp.value.trim().substring(0, 200);
                        }
                    });
                    if (Object.keys(_formValues).length) {
                        if (!window.__tfEventQueue.length) return;
                        var _last = window.__tfEventQueue[window.__tfEventQueue.length - 1];
                        if (_last && _last.type === 'submit') _last.form_values = _formValues;
                    }
                } catch(_ignore) {}
                return;
            }
            _tf_pushEvent('click', el);
            var _sc = document.getElementById('tf-step-count');
            if (_sc) {
                var _n = parseInt(_sc.textContent||0) + 1;
                _sc.textContent = _n;
                try { sessionStorage.setItem('__tfStepCount', _n); } catch(_e){}
            }
        }, true);

        window.addEventListener('input', function(e) {
            if (window.__tfAssertWaiting) return;
            _tf_pushEvent('fill', e.target);
        }, true);

        window.addEventListener('change', function(e) {
            if (window.__tfAssertWaiting) return;
            var el = e.target;
            if (el && (el.tagName === 'INPUT' || el.tagName === 'SELECT' || el.tagName === 'TEXTAREA')) {
                _tf_pushEvent('fill', el);
            }
        }, true);

        // ---- Polling safety net ----
        // Frameworks (Angular currencymask, React controlled inputs) can
        // prevent native 'input' events. Polling catches ALL value changes
        // regardless of mechanism: keyboard, paste, autofill, setAttribute.
        window.__tfLastValues = {};
        window.__tfPollInterval = setInterval(function() {
            if (window.__tfAssertWaiting) return;
            try {
                document.querySelectorAll('input, textarea, select').forEach(function(el) {
                    var key = el.name || el.getAttribute('aria-label') || el.placeholder || el.id;
                    if (!key) return;
                    var val = (el.value || '').trim();
                    if (val && val !== window.__tfLastValues[key]) {
                        window.__tfLastValues[key] = val;
                        _tf_pushEvent('fill', el);
                    }
                });
            } catch(_e) {}
        }, 300);

        // ---- Field snapshot polling (Sprint 3) ----
        window.__tfLastSnapshotKey = {};
        window.__tfFieldSnapshotInterval = setInterval(function() {
            if (window.__tfAssertWaiting) return;
            try {
                var snaps = window._tf_snapshotFields();
                var changed = [];
                snaps.forEach(function(s) {
                    var key = s.fingerprint;
                    var prev = window.__tfLastSnapshotKey[key] || '';
                    var curr = s.value || '';
                    if (curr !== prev) {
                        window.__tfLastSnapshotKey[key] = curr;
                        changed.push(s);
                    }
                });
                if (changed.length > 0) {
                    window.__tfFieldSnapshotQueue.push({
                        timestamp: new Date().toISOString(),
                        snapshots: changed,
                        count: changed.length
                    });
                }
            } catch(_e) {}
        }, 1000);

        window.addEventListener('beforeunload', function() {
            clearInterval(window.__tfPollInterval);
            clearInterval(window.__tfFieldSnapshotInterval);
            window._tf_captureFinalState('beforeunload');
        });

        // ---- Keyboard shortcuts ----
        window.addEventListener('keydown', function(e) {
            if (!e.shiftKey) return;
            switch(e.key.toUpperCase()) {
                case 'P':
                    window.__tfCommandQueue.push('TOGGLE_PAUSE');
                    console.log('[TestForge] Shift+P: toggle pause');
                    break;
                case 'S':
                    window._tf_confirmStop();
                    console.log('[TestForge] Shift+S: stop');
                    break;
                case 'A':
                    window.__tfCommandQueue.push('ASSERT');
                    window.__tfAssertWaiting = true;
                    console.log('[TestForge] Shift+A: modo assert ATIVADO');
                    _tf_showToast('🟡 Modo Assert — clique no elemento');
                    var dot = document.getElementById('tf-rec-dot');
                    var status = document.getElementById('tf-status');
                    if (dot) dot.style.color = '#f59e0b';
                    if (status) status.textContent = 'Modo Assert — clique no elemento';
                    break;
                case 'M':
                    window.__tfDragMode = !window.__tfDragMode;
                    var _panel = document.getElementById('tf-panel');
                    if (_panel) {
                        _panel.style.cursor  = window.__tfDragMode ? 'grab' : '';
                        _panel.style.outline = window.__tfDragMode ? '2px dashed #f59e0b' : '';
                    }
                    _tf_showToast(window.__tfDragMode ? '↕ Arrastar ativo — solte para fixar' : '📌 Overlay fixado');
                    break;
            }
        }, true);

        // ---- Overlay UI ----
        window._tf_showOverlay = function() {
            var _initSteps = 0, _initAsserts = 0;
            try {
                _initSteps   = parseInt(sessionStorage.getItem('__tfStepCount')   || 0);
                _initAsserts = parseInt(sessionStorage.getItem('__tfAssertCount') || 0);
            } catch(_e) {}
            var ov = document.createElement('div');
            ov.id = 'tf-overlay';
            ov.innerHTML = '<div id="tf-panel" style="position:fixed;top:8px;right:8px;background:#1a1a2e;color:#fff;padding:8px 14px;border-radius:8px;font:14px monospace;z-index:99999;display:flex;gap:12px;align-items:center;box-shadow:0 4px 16px rgba(0,0,0,0.3)">' +
                '<span id="tf-rec-dot" style="color:#e94560;font-size:18px">●</span>' +
                '<span id="tf-status">Gravando...</span>' +
                '<span style="color:#aaa">|</span>' +
                '<button id="tf-btn-pause" style="background:#334155;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font:12px monospace" title="Shift+P">⏸</button>' +
                '<button id="tf-btn-stop" style="background:#991b1b;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font:12px monospace" title="Shift+S">■</button>' +
                '<button id="tf-btn-assert" style="background:#6366f1;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font:12px monospace" title="Shift+A">Assert</button>' +
                '<span style="color:#aaa">|</span>' +
                '<span>Passos: <strong id="tf-step-count">' + _initSteps + '</strong></span>' +
                ' <span>|</span>' +
                '<span>Asserts: <strong id="tf-assert-count">' + _initAsserts + '</strong></span>' +
                '</div>' +
                '<div id="tf-toast" style="display:none;position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#10b981;color:#fff;padding:10px 24px;border-radius:8px;font:14px sans-serif;z-index:99999;box-shadow:0 4px 16px rgba(0,0,0,0.3)"></div>';
            document.body.appendChild(ov);
            document.getElementById('tf-btn-pause').onclick = function() { window.__tfCommandQueue.push('TOGGLE_PAUSE'); };
            document.getElementById('tf-btn-stop').onclick = function() { window._tf_confirmStop(); };
            document.getElementById('tf-btn-assert').onclick = function() {
                window.__tfAssertWaiting = true;
                window.__tfCommandQueue.push('ASSERT');
                var dot = document.getElementById('tf-rec-dot');
                var status = document.getElementById('tf-status');
                if (dot) dot.style.color = '#f59e0b';
                if (status) status.textContent = 'Modo Assert — clique no elemento';
            };
        }

        window._tf_showToast = function(msg) {
            var toast = document.getElementById('tf-toast');
            if (!toast) return;
            toast.textContent = msg;
            toast.style.display = 'block';
            setTimeout(function() { toast.style.display = 'none'; }, 2000);
        }

        window._tf_showAssertMenu = function(x, y) {
            var el = document.getElementById('tf-assert-menu');
            if (!el) {
                el = document.createElement('div');
                el.id = 'tf-assert-menu';
                el.innerHTML = [
                    '<button data-type="textual" style="background:#10b981">📝 Texto</button>',
                    '<button data-type="estado" style="background:#f59e0b">🔘 Estado</button>',
                    '<button data-type="visivel" style="background:#3b82f6">👁 Visivel</button>',
                    '<button data-type="automatico" style="background:#8b5cf6">🤖 Auto</button>'
                ].join('');
                el.style.cssText = 'position:fixed;z-index:99999;background:#1e293b;padding:6px;border-radius:8px;display:flex;gap:4px;box-shadow:0 4px 20px rgba(0,0,0,0.4)';
                el.querySelectorAll('button').forEach(function(btn) {
                    btn.style.cssText = 'color:#fff;border:none;padding:8px 14px;border-radius:6px;cursor:pointer;font:13px sans-serif;font-weight:600';
                    btn.onclick = function(e) {
                        e.stopPropagation();
                        e.preventDefault();
                        var assertType = btn.dataset.type;
                        var targetEl = window.__tfAssertElement;
                        if (targetEl) {
                            _tf_addStep('assert', targetEl, assertType);
                            var assertCount = document.getElementById('tf-assert-count');
                            if (assertCount) {
                                var _an = parseInt(assertCount.textContent||0) + 1;
                                assertCount.textContent = _an;
                                try { sessionStorage.setItem('__tfAssertCount', _an); } catch(_e){}
                            }
                            var stepCount = document.getElementById('tf-step-count');
                            if (stepCount) {
                                var _sn = parseInt(stepCount.textContent||0) + 1;
                                stepCount.textContent = _sn;
                                try { sessionStorage.setItem('__tfStepCount', _sn); } catch(_e){}
                            }
                            var expected = _tf_getExpectedValue(targetEl, assertType);
                            _tf_showToast('✓ Assert ' + assertType + ': \"' + (expected||'').substring(0,40) + '\"');
                        }
                        el.style.display = 'none';
                        window.__tfAssertWaiting = false;
                        window.__tfAssertElement = null;
                        var dot = document.getElementById('tf-rec-dot');
                        var status = document.getElementById('tf-status');
                        if (dot) dot.style.color = '#e94560';
                        if (status) status.textContent = 'Gravando...';
                    };
                });
                document.body.appendChild(el);
            }
            el.style.display = 'flex';
            el.style.left = Math.min(x, window.innerWidth - 320) + 'px';
            el.style.top = Math.min(y + 10, window.innerHeight - 60) + 'px';
        }

        window._tf_showAssertConfirm = function(el, x, y) {
            var existing = document.getElementById('tf-assert-confirm');
            if (existing) existing.remove();
            var desc = (el.textContent || '').trim().replace(/\s+/g, ' ').substring(0, 60) ||
                       el.getAttribute('aria-label') || el.getAttribute('placeholder') ||
                       el.getAttribute('name') || el.tagName.toLowerCase();
            var dlg = document.createElement('div');
            dlg.id = 'tf-assert-confirm';
            dlg.style.cssText = 'position:fixed;z-index:999999;background:#1e293b;color:#fff;' +
                'padding:14px;border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,0.5);' +
                'max-width:340px;font:13px sans-serif';
            dlg.style.left = Math.min(x, window.innerWidth - 360) + 'px';
            dlg.style.top  = Math.min(y + 10, window.innerHeight - 130) + 'px';
            dlg.innerHTML =
                '<div style="color:#94a3b8;font-size:11px;margin-bottom:8px">CONFIRMAR ASSERT</div>' +
                '<div style="margin-bottom:12px;word-break:break-word">' +
                    '<span style="color:#f59e0b">Elemento:</span> “' + desc + '” ' +
                    '<span style="color:#64748b;font-size:11px">(&lt;' + el.tagName.toLowerCase() + '&gt;)</span>' +
                '</div>' +
                '<div style="display:flex;gap:8px">' +
                    '<button id="tf-confirm-yes" style="background:#10b981;color:#fff;border:none;' +
                        'padding:7px 16px;border-radius:6px;cursor:pointer;font:13px sans-serif;font-weight:600">✓ Sim</button>' +
                    '<button id="tf-confirm-no" style="background:#64748b;color:#fff;border:none;' +
                        'padding:7px 16px;border-radius:6px;cursor:pointer;font:13px sans-serif;font-weight:600">✗ Não</button>' +
                '</div>';
            document.body.appendChild(dlg);
            document.getElementById('tf-confirm-yes').onclick = function(ev) {
                ev.stopPropagation(); ev.preventDefault();
                dlg.remove();
                _tf_showAssertMenu(x, y);
            };
            document.getElementById('tf-confirm-no').onclick = function(ev) {
                ev.stopPropagation(); ev.preventDefault();
                dlg.remove();
                window.__tfAssertWaiting = false;
                window.__tfAssertElement = null;
                var dot = document.getElementById('tf-rec-dot');
                var status = document.getElementById('tf-status');
                if (dot) dot.style.color = '#e94560';
                if (status) status.textContent = 'Gravando...';
            };
        };

        window._tf_confirmStop = function() {
            var assertCount = parseInt((document.getElementById('tf-assert-count') || {}).textContent || 0);
            if (assertCount === 0) {
                var existing = document.getElementById('tf-stop-confirm');
                if (existing) existing.remove();
                var dlg = document.createElement('div');
                dlg.id = 'tf-stop-confirm';
                dlg.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);' +
                    'z-index:999999;background:#1e293b;color:#fff;padding:20px 24px;border-radius:12px;' +
                    'box-shadow:0 8px 32px rgba(0,0,0,0.6);font:14px sans-serif;text-align:center;max-width:360px';
                dlg.innerHTML =
                    '<div style="font-size:24px;margin-bottom:12px">⚠️</div>' +
                    '<div style="margin-bottom:16px">O teste gravado <strong>não terá nenhum assert</strong>.<br>' +
                    '<span style="color:#94a3b8;font-size:12px">Sem assert, o TestForge não verifica resultado esperado.</span></div>' +
                    '<div style="display:flex;gap:10px;justify-content:center">' +
                        '<button id="tf-stop-yes" style="background:#991b1b;color:#fff;border:none;' +
                            'padding:9px 20px;border-radius:6px;cursor:pointer;font:13px sans-serif;font-weight:600">Sair mesmo assim</button>' +
                        '<button id="tf-stop-no" style="background:#334155;color:#fff;border:none;' +
                            'padding:9px 20px;border-radius:6px;cursor:pointer;font:13px sans-serif;font-weight:600">Voltar</button>' +
                    '</div>';
                document.body.appendChild(dlg);
                document.getElementById('tf-stop-yes').onclick = function() {
                    dlg.remove();
                    window._tf_captureFinalState('user_stop');
                    window.__tfCommandQueue.push('STOP');
                };
                document.getElementById('tf-stop-no').onclick = function() { dlg.remove(); };
                return;
            }
            window._tf_captureFinalState('user_stop');
            window.__tfCommandQueue.push('STOP');
        };

        document.addEventListener('mousedown', function(e) {
            if (!window.__tfDragMode) return;
            var panel = document.getElementById('tf-panel');
            if (!panel || !panel.contains(e.target)) return;
            var rect = panel.getBoundingClientRect();
            window.__tfDragState = { dx: e.clientX - rect.left, dy: e.clientY - rect.top };
            panel.style.cursor = 'grabbing';
            e.preventDefault();
        }, true);

        document.addEventListener('mousemove', function(e) {
            if (!window.__tfDragState || !window.__tfDragMode) return;
            var panel = document.getElementById('tf-panel');
            if (!panel) return;
            var x = Math.max(0, Math.min(e.clientX - window.__tfDragState.dx, window.innerWidth  - panel.offsetWidth));
            var y = Math.max(0, Math.min(e.clientY - window.__tfDragState.dy, window.innerHeight - panel.offsetHeight));
            panel.style.right = 'auto';
            panel.style.left  = x + 'px';
            panel.style.top   = y + 'px';
        });

        document.addEventListener('mouseup', function() {
            if (!window.__tfDragState) return;
            window.__tfDragState = null;
            var panel = document.getElementById('tf-panel');
            if (panel && window.__tfDragMode) panel.style.cursor = 'grab';
        });

        window._tf_highlight = function(el) {
            var orig = el.style.outline;
            el.style.outline = '2px solid #e94560';
            el.style.outlineOffset = '2px';
            setTimeout(function() { el.style.outline = orig; }, 1500);
        }

        window.addEventListener('load', function() {
            // Check if this page load is a form postback (ASP classic / ASP.NET pattern).
            // If the submit event was already restored from sessionStorage (see init block),
            // we do NOT push a duplicate postback — the submit event already carries
            // is_postback:true and submit_method. Only push a standalone postback if
            // the pending flag is set but no submit event was restored (legacy path).
            if (window.__tfPendingSubmit) {
                var _alreadyRestored = false;
                for (var i = 0; i < window.__tfEventQueue.length; i++) {
                    if (window.__tfEventQueue[i].type === 'submit' && window.__tfEventQueue[i].is_postback) {
                        _alreadyRestored = true;
                        break;
                    }
                }
                if (!_alreadyRestored) {
                    var pending = window.__tfPendingSubmit;
                    var eventData = {
                        event_id: 'evt_' + String(++window.__tfEventCounter).padStart(5,'0'),
                        type: 'postback',
                        timestamp: new Date().toISOString(),
                        url: window.location.href,
                        page_title: document.title,
                        target: null,
                        value: null,
                        is_postback: true,
                        submit_method: pending.method
                    };
                    window.__tfEventQueue.push(eventData);
                    console.log('[TestForge] postback detected (legacy) — method:', pending.method, 'url:', window.location.href);
                } else {
                    console.log('[TestForge] postback already captured via restored submit event');
                }
                window.__tfPendingSubmit = null;
            } else {
                setTimeout(function() { _tf_pushEvent('navigation'); }, 0);
            }
            setTimeout(function() { _tf_showOverlay(); }, 100);
        });

        // Persist unflushed events to sessionStorage before navigation.
        // When the page navigates (form submit, link click), in-flight events
        // that haven't been flushed by the Python side are lost. This handler
        // saves them so they can be restored on the next page.
        window.addEventListener('beforeunload', function() {
            try {
                if (window.__tfEventQueue && window.__tfEventQueue.length > 0) {
                    sessionStorage.setItem('__tfUnflushedEvents', JSON.stringify(window.__tfEventQueue));
                }
                if (window.__tfStepQueue && window.__tfStepQueue.length > 0) {
                    sessionStorage.setItem('__tfUnflushedSteps', JSON.stringify(window.__tfStepQueue));
                }
            } catch(_e) { /* ignore */ }
        });
    """
