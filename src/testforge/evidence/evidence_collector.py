"""TestForge — Evidence Collector."""
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from playwright.sync_api import Page

from ..healing.evidence_payload import EvidencePayload


@dataclass
class EvidencePackage:
    run_id: str
    started_at: str = ""
    finished_at: str = ""
    steps: list = field(default_factory=list)
    screenshot_paths: list = field(default_factory=list)
    dom_paths: list = field(default_factory=list)
    network_log: list = field(default_factory=list)
    sensitive_alerts: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class EvidenceCollector:
    """Coleta evidencias durante execucao/gravacao."""

    def __init__(self, page: Page, evidence_root: str = "evidence"):
        self._page = page
        self._root = evidence_root
        self._pkg: Optional[EvidencePackage] = None
        self._screenshot_dir: str = ""
        self._dom_dir: str = ""
        self._console_buffer: list[dict] = []
        self._network_buffer: list[dict] = []
        self._listeners_active: bool = False

    def start(self, run_id: str, metadata: dict = None):
        self._pkg = EvidencePackage(
            run_id=run_id,
            started_at=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )
        self._screenshot_dir = os.path.join(self._root, run_id, "screenshots")
        self._dom_dir = os.path.join(self._root, run_id, "dom")
        os.makedirs(self._screenshot_dir, exist_ok=True)
        os.makedirs(self._dom_dir, exist_ok=True)
        self._console_buffer.clear()
        self._network_buffer.clear()
        self._setup_listeners()

    def capture_screenshot(self, step_id: str, phase: str = "after") -> str:
        """Captura screenshot. phase = 'before' ou 'after'."""
        try:
            data = self._page.screenshot(type="png", full_page=False)
            filename = f"{phase}_{step_id}.png"
            path = os.path.join(self._screenshot_dir, filename)
            with open(path, "wb") as f:
                f.write(data)
            self._pkg.screenshot_paths.append(path)
            return path
        except Exception:
            return ""

    def capture_dom(self, step_id: str, phase: str = "after") -> str:
        """Captura DOM snapshot. phase = 'before' ou 'after'."""
        try:
            html = self._page.content()
            filename = f"{phase}_{step_id}.html"
            path = os.path.join(self._dom_dir, filename)
            with open(path, "w") as f:
                f.write(html)
            self._pkg.dom_paths.append(path)
            return path
        except Exception:
            return ""

    def capture_network_log(self, entries: list):
        self._pkg.network_log = entries

    def add_step_evidence(self, step: dict):
        """Adiciona step com evidencias."""
        self._pkg.steps.append(step)

    def add_sensitive_alert(self, alert: dict):
        self._pkg.sensitive_alerts.append(alert)

    def finalize(self) -> str:
        """Finaliza e salva o evidence package. Retorna o caminho."""
        if not self._pkg:
            return ""
        self._pkg.finished_at = datetime.now(timezone.utc).isoformat()

        pkg_dir = os.path.join(self._root, self._pkg.run_id)

        # manifest
        manifest = {
            "run_id": self._pkg.run_id,
            "started_at": self._pkg.started_at,
            "finished_at": self._pkg.finished_at,
            "step_count": len(self._pkg.steps),
            "screenshot_count": len(self._pkg.screenshot_paths),
            "network_entries": len(self._pkg.network_log),
            "sensitive_alerts": len(self._pkg.sensitive_alerts),
            "metadata": self._pkg.metadata,
        }
        with open(os.path.join(pkg_dir, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=2, default=str)

        # steps
        if self._pkg.steps:
            with open(os.path.join(pkg_dir, "steps.jsonl"), "w") as f:
                for step in self._pkg.steps:
                    f.write(json.dumps(step, default=str) + "\n")

        # network
        if self._pkg.network_log:
            with open(os.path.join(pkg_dir, "network_log.json"), "w") as f:
                json.dump(self._pkg.network_log, f, indent=2, default=str)

        # sensitive data
        if self._pkg.sensitive_alerts:
            data = {
                "policy": "alert_only",
                "masking_applied": False,
                "alerts": self._pkg.sensitive_alerts,
            }
            with open(os.path.join(pkg_dir, "sensitive_data_alert.json"), "w") as f:
                json.dump(data, f, indent=2, default=str)

        return pkg_dir

    def _setup_listeners(self):
        """Registra listeners de console e network no page."""
        if self._listeners_active or not self._page:
            return
        try:
            self._page.on("console", self._on_console)
            self._page.on("response", self._on_response)
            self._listeners_active = True
        except Exception:
            pass

    def _on_console(self, msg):
        """Handler: console message."""
        try:
            self._console_buffer.append({
                "text": str(msg.text)[:500],
                "level": msg.type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            pass

    def _on_response(self, response):
        """Handler: network response."""
        try:
            self._network_buffer.append({
                "method": response.request.method,
                "url": response.url[:300],
                "status": response.status,
                "timing_ms": 0,
            })
        except Exception:
            pass

    def build_llm_payload(
        self,
        step_context: dict,
        include_screenshot: bool = False,
    ) -> EvidencePayload:
        """Build structured evidence payload for LLM Healer (L3).

        Collects DOM snapshot, recent console errors, recent network requests,
        and optional screenshot. Sanitizes DOM before inclusion.
        """
        dom_html = ""
        screenshot_bytes = None

        if self._page:
            try:
                dom_html = self._page.content()
            except Exception:
                dom_html = ""

            if include_screenshot:
                try:
                    screenshot_bytes = self._page.screenshot(type="png", full_page=False)
                except Exception:
                    screenshot_bytes = None

        # Last 5 console errors (filter warnings/errors)
        recent_console = [e for e in self._console_buffer[-5:]
                         if e.get("level", "") in ("error", "warning", "info")]

        # Last 3 network requests (truncate URLs)
        recent_network = []
        for entry in self._network_buffer[-3:]:
            entry_copy = dict(entry)
            entry_copy["url"] = EvidencePayload.truncate_url(entry_copy.get("url", ""), 120)
            recent_network.append(entry_copy)

        return EvidencePayload.from_collector(
            step_context=step_context,
            dom_html=dom_html,
            console_entries=recent_console,
            network_entries=recent_network,
            screenshot_bytes=screenshot_bytes,
        )

    def clear_buffers(self):
        """Clear console and network buffers (between runs)."""
        self._console_buffer.clear()
        self._network_buffer.clear()

    @property
    def package(self) -> Optional[EvidencePackage]:
        return self._pkg
