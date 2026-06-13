"""TestForge — Recorder Controller (JS injection + evaluate polling).

Injeta listeners JavaScript na pagina via add_init_script.
Usa page.evaluate para ler eventos pendentes, sem expose_function.
"""
import json
import re
import os
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
        self._network_entries: list = []
        self._sensitive_alerts: list = []

    def start(self, recording_id: str, application: str = "", base_url: str = "") -> RecordingSession:
        session = self._session_manager.start(recording_id, application, base_url)
        self._store = RawRecordingStore(session.session_dir)
        self._event_counter = 0
        self._network_entries = []
        self._sensitive_alerts = []

        self._page.on("request", self._on_request)
        self._page.on("response", self._on_response)

        self._page.add_init_script("""
            window.__tf_events = [];
            window.__tf_eventCounter = 0;

            function _tf_extractTarget(el) {
                if (!el || el === document.body || el === document.documentElement) return null;
                const rect = el.getBoundingClientRect ? el.getBoundingClientRect() : {};
                const labelEl = el.id ? document.querySelector('label[for="' + el.id + '"]') : null;
                return {
                    tag: el.tagName ? el.tagName.toLowerCase() : null,
                    text: (el.textContent || '').trim().substring(0, 200) || null,
                    role: el.getAttribute('role') || null,
                    accessible_name: el.getAttribute('aria-label') || el.getAttribute('title') || null,
                    id: el.id || null,
                    name: el.getAttribute('name') || null,
                    test_id: el.getAttribute('data-testid') || el.getAttribute('data-test-id') || null,
                    placeholder: el.getAttribute('placeholder') || null,
                    label: labelEl ? labelEl.textContent.trim() : null,
                    className: el.className || null,
                    type: el.getAttribute('type') || null,
                    value: (el.value || '').substring(0, 100) || null,
                    bounding_box: { x: Math.round(rect.x||0), y: Math.round(rect.y||0), width: Math.round(rect.width||0), height: Math.round(rect.height||0) },
                };
            }

            function _tf_capture(eventType) {
                const el = document.activeElement;
                const target = _tf_extractTarget(el);
                window.__tf_events.push({
                    event_id: 'evt_' + String(++window.__tf_eventCounter).padStart(4, '0'),
                    type: eventType,
                    timestamp: new Date().toISOString(),
                    url: window.location.href,
                    page_title: document.title,
                    target: target,
                    value: (el && el.value) ? el.value.substring(0, 200) : null,
                });
            }

            window.addEventListener('load', () => setTimeout(() => _tf_capture('navigation'), 100));
            window.addEventListener('click', (e) => setTimeout(() => _tf_capture('click'), 0), true);
            window.addEventListener('input', (e) => setTimeout(() => _tf_capture('fill'), 0), true);
            window.addEventListener('change', (e) => setTimeout(() => _tf_capture('fill'), 0), true);
        """)

        return session

    def flush_events(self):
        """Read pending events from JS and persist them."""
        try:
            events = self._page.evaluate("""() => {
                const evts = window.__tf_events || [];
                window.__tf_events = [];
                return evts;
            }""")
            for data in events:
                self._persist_event(data)
        except Exception:
            pass

    def _persist_event(self, data: dict):
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
                bounding_box=target_data.get("bounding_box"),
            )

        event = RawRecordedEvent(
            event_id=data.get("event_id", f"evt_{self._event_counter:04d}"),
            event_type=data.get("type", "unknown"),
            timestamp=data.get("timestamp", ""),
            url=data.get("url"),
            page_title=data.get("page_title"),
            target=target,
            value=data.get("value"),
        )
        self._event_counter += 1
        self._capture_snapshots(event)
        self._store.append_event(event)

    def stop(self) -> RecordingSession:
        self.flush_events()
        self._page.remove_listener("request", self._on_request)
        self._page.remove_listener("response", self._on_response)
        session = self._session_manager.stop()
        self._store.save_network_log(self._network_entries)
        if self._sensitive_alerts:
            self._store.save_sensitive_data_alert(self._sensitive_alerts)
        return session

    def finalize(self) -> RecordingSession:
        self.flush_events()
        return self._session_manager.finalize()

    @property
    def active_session(self):
        return self._session_manager.active_session

    def _on_request(self, request: Request):
        self._network_entries.append({
            "type": "request",
            "method": request.method,
            "url": request.url,
            "resource_type": request.resource_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def _on_response(self, response: Response):
        self._network_entries.append({
            "type": "response",
            "url": response.url,
            "status": response.status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def _capture_snapshots(self, event: RawRecordedEvent):
        eid = event.event_id
        try:
            data = self._page.screenshot(type="png", full_page=False)
            event.screenshot_path = self._store.save_screenshot(eid, data)
        except Exception:
            pass
        try:
            dom = self._page.content()
            event.dom_snapshot_path = self._store.save_dom(eid, dom)
        except Exception:
            pass
        try:
            ax = self._page.accessibility.snapshot()
            if ax:
                event.ax_snapshot_path = self._store.save_ax_snapshot(eid, ax)
        except Exception:
            pass

    def detect_sensitive_data(self, value: str, field_name: str = ""):
        patterns = {
            "CPF": r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}",
            "CNPJ": r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}",
        }
        for label, pattern in patterns.items():
            if re.search(pattern, value):
                alert = {
                    "field": field_name,
                    "type": label,
                    "policy": "alert_only",
                    "masking_applied": False,
                }
                self._sensitive_alerts.append(alert)
                return True
        return False
