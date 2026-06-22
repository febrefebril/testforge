from __future__ import annotations

import base64
import json
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from playwright.sync_api import Page


SANITIZE_RE = re.compile(r'<(script|style)\b[^>]*>.*?</\1>', re.IGNORECASE | re.DOTALL)
SENSITIVE_ATTRS_RE = re.compile(r'\s(data-(?:cpf|password|credit.card|ssn)=["\'][^"\']*["\'])', re.IGNORECASE)
INPUT_VALUE_RE = re.compile(r'(?:^|\s)value=(["\'])(?!password|hidden|file\b)[^"\']*?\1', re.IGNORECASE)


@dataclass
class EvidencePayload:
    dom_snapshot: str = ""
    screenshot_base64: str = ""
    console_errors: list[dict] = field(default_factory=list)
    network_state: list[dict] = field(default_factory=list)
    step_context: dict = field(default_factory=dict)
    failure_signature: str = ""
    collected_at: str = ""
    page_url: str = ""
    step_index: int = -1
    is_sufficient: bool = True
    insufficiency_reason: str = ""
    metadata: dict = field(default_factory=dict)


def sanitize_dom(html: str, sanitize_all_values: bool = False) -> str:
    cleaned = SANITIZE_RE.sub("", html)
    cleaned = SENSITIVE_ATTRS_RE.sub("", cleaned)
    if sanitize_all_values:
        cleaned = re.sub(r'\svalue=(["\'])[^"\']*?\1', '', cleaned)
    else:
        cleaned = INPUT_VALUE_RE.sub("", cleaned)
    if len(cleaned) > 50000:
        cleaned = cleaned[:50000] + "\n<!-- TRUNCATED 50000 chars -->"
    return cleaned


class EvidenceCollector:
    def __init__(self, page: Page):
        self._page = page
        self._console_logs: list[dict] = []
        self._network_requests: dict[str, dict] = {}
        self._request_order: list[str] = []
        self._listeners_attached = False
        self._lock = threading.Lock()

    def attach_listeners(self) -> None:
        if self._listeners_attached:
            return
        self._listeners_attached = True
        self._page.on("console", self._on_console)
        self._page.on("request", self._on_request)
        self._page.on("response", self._on_response)

    def detach_listeners(self) -> None:
        if not self._listeners_attached:
            return
        self._listeners_attached = False
        try:
            self._page.remove_listener("console", self._on_console)
            self._page.remove_listener("request", self._on_request)
            self._page.remove_listener("response", self._on_response)
        except Exception:
            pass

    def _on_console(self, msg) -> None:
        if msg.type != "error":
            return
        with self._lock:
            self._console_logs.append({
                "type": msg.type,
                "text": msg.text[:500],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            if len(self._console_logs) > 50:
                self._console_logs.pop(0)

    def _on_request(self, request) -> None:
        key = f"{request.method}:{request.url}"
        with self._lock:
            if key not in self._network_requests:
                self._network_requests[key] = {
                    "url": request.url,
                    "method": request.method,
                    "status": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                self._request_order.append(key)
                if len(self._request_order) > 100:
                    old_key = self._request_order.pop(0)
                    self._network_requests.pop(old_key, None)

    def _on_response(self, response) -> None:
        key = f"{response.request.method}:{response.url}"
        with self._lock:
            if key in self._network_requests:
                self._network_requests[key]["status"] = response.status

    def collect(
        self,
        step_data: dict,
        step_index: int,
        all_steps: Optional[list[dict]] = None,
    ) -> EvidencePayload:
        try:
            dom = self._page.evaluate("() => document.documentElement.outerHTML")
        except Exception:
            dom = ""
        dom_snapshot = sanitize_dom(dom)

        try:
            screenshot_bytes = self._page.screenshot(type="png")
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("ascii")
        except Exception:
            screenshot_b64 = ""

        try:
            page_url = self._page.url
        except Exception:
            page_url = step_data.get("url", "")

        step_context = {
            "step_index": step_index,
            "action": step_data.get("action", ""),
            "selector": step_data.get("selector", ""),
            "value": step_data.get("value", ""),
            "url": step_data.get("url", ""),
            "page_title": step_data.get("page_title", ""),
            "tag_name": step_data.get("tag_name", ""),
            "text": step_data.get("text", ""),
            "intention": step_data.get("intention", ""),
        }

        if all_steps:
            step_context["total_steps"] = len(all_steps)
            step_context["prior_actions"] = [
                {
                    "action": s.get("action", ""),
                    "selector": s.get("selector", ""),
                    "value": str(s.get("value", ""))[:100],
                    "url": s.get("url", ""),
                    "error": str(s.get("_error", ""))[:200],
                }
                for s in all_steps[:step_index]
            ]

        with self._lock:
            console_errors = list(self._console_logs)
            if len(console_errors) > 50:
                console_errors = console_errors[-50:]

            network_last_20_keys = self._request_order[-20:]
            network_last_20 = [self._network_requests[k] for k in network_last_20_keys if k in self._network_requests]

        try:
            failure_context = json.dumps({
                "error": str(step_data.get("_error", "")),
                "console": [str(c.get("text", "")) for c in console_errors[-5:]],
                "page_url": page_url,
                "step_selector": str(step_data.get("selector", "")),
            }, ensure_ascii=False)
        except (TypeError, ValueError):
            failure_context = json.dumps({"error": "serialization_failed"})
        failure_signature = _hash_str(failure_context)

        payload = EvidencePayload(
            dom_snapshot=dom_snapshot,
            screenshot_base64=screenshot_b64,
            console_errors=console_errors,
            network_state=network_last_20,
            step_context=step_context,
            failure_signature=failure_signature,
            collected_at=datetime.now(timezone.utc).isoformat(),
            page_url=page_url,
            step_index=step_index,
            is_sufficient=True,
            metadata={
                "all_steps_count": len(all_steps) if all_steps else 0,
                "console_errors_count": len(console_errors),
                "network_requests_count": len(network_last_20),
            },
        )

        if not dom_snapshot and not screenshot_b64:
            payload.is_sufficient = False
            payload.insufficiency_reason = "DOM vazio e screenshot indisponível"

        return payload


def _hash_str(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]
