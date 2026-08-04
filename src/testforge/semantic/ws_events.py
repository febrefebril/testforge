
"""TestForge — Captura de WebSocket/eventos e waits semanticos.

Cobre: captura CDP/network (WebSocket frames + requests); deteccao de
evento assincrono relevante (padrao de URL/payload); waits semanticos por
mudanca de DOM/estado (MutationObserver + wait_for_function).
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from playwright.sync_api import Page

logger = logging.getLogger(__name__)


@dataclass
class NetworkEvent:
    kind: str
    url: str = ""
    payload: str = ""
    status: int = 0
    ts: float = field(default_factory=time.time)


def _as_text(payload) -> str:
    try:
        if isinstance(payload, (bytes, bytearray)):
            return payload.decode("utf-8", "replace")
        return str(payload)
    except Exception:
        return ""


class NetworkCapture:
    """Captura trafego de rede e WebSocket via API Playwright + CDP."""

    def __init__(self, page: Page, *, url_filter: str = "") -> None:
        self._page = page
        self._url_re = re.compile(url_filter) if url_filter else None
        self.events = []
        self._cdp = None

    def _match(self, url: str) -> bool:
        return True if self._url_re is None else bool(self._url_re.search(url or ""))

    def start(self) -> "NetworkCapture":
        page = self._page

        def _on_ws(ws):
            if not self._match(ws.url):
                return
            ws.on("framereceived", lambda p: self.events.append(
                NetworkEvent("ws_frame", ws.url, _as_text(p))))
            ws.on("framesent", lambda p: self.events.append(
                NetworkEvent("ws_frame", ws.url, _as_text(p))))

        page.on("websocket", _on_ws)
        page.on("response", lambda r: self._match(r.url) and self.events.append(
            NetworkEvent("response", r.url, "", r.status)))
        try:
            self._cdp = page.context.new_cdp_session(page)
            self._cdp.send("Network.enable")

            def _on_req(e):
                req = e.get("request", {}) or {}
                url = req.get("url", "")
                if self._match(url):
                    self.events.append(NetworkEvent("request", url, req.get("postData", "") or ""))

            self._cdp.on("Network.requestWillBeSent", _on_req)
        except Exception as exc:
            logger.debug("CDP indisponivel (%s); usando apenas API publica.", exc)
        return self

    def wait_for(self, *, url_contains: str = "", payload_contains: str = "",
                 kind: str = "", timeout_ms: int = 20_000) -> "NetworkEvent":
        """Aguarda evento assincrono relevante (ja capturado ou futuro)."""
        deadline = time.time() + timeout_ms / 1000.0
        while time.time() < deadline:
            for ev in list(self.events):
                if kind and ev.kind != kind:
                    continue
                if url_contains and url_contains not in ev.url:
                    continue
                if payload_contains and payload_contains not in ev.payload:
                    continue
                return ev
            self._page.wait_for_timeout(150)
        raise TimeoutError(
            f"Evento assincrono nao capturado (url~{url_contains!r}, kind={kind!r})."
        )

    def stop(self) -> None:
        try:
            if self._cdp:
                self._cdp.detach()
        except Exception:
            pass


def wait_dom_change(page: Page, selector: str, *, attribute: str = "",
                    timeout_ms: int = 15_000) -> None:
    """Wait semantico: resolve quando o DOM sob selector muda (MutationObserver)."""
    js = """
    ([selector, attribute, timeout]) => new Promise((resolve, reject) => {
      const root = document.querySelector(selector);
      if (!root) { reject('root nao encontrado: ' + selector); return; }
      const obs = new MutationObserver(() => { obs.disconnect(); resolve(true); });
      obs.observe(root, {
        childList: true, subtree: true,
        attributes: !!attribute,
        attributeFilter: attribute ? [attribute] : undefined,
      });
      setTimeout(() => { obs.disconnect(); reject('timeout'); }, timeout);
    })
    """
    try:
        page.evaluate(js, [selector, attribute, timeout_ms])
    except Exception as exc:
        raise TimeoutError(f"Sem mudanca de DOM em {selector!r}: {exc}") from exc


def wait_state(page: Page, js_expression: str, *, timeout_ms: int = 15_000,
               poll_ms: int = 200) -> None:
    """Wait semantico por estado de app: aguarda expressao JS truthy."""
    page.wait_for_function(f"() => ({js_expression})", timeout=timeout_ms, polling=poll_ms)

