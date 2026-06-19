"""TestForge — EvidencePayload para LLM Healer (L3).

Payload estruturado: snippet DOM, erros de console, estado de rede, screenshot opcional.
Sanitizado — nunca expõe PII bruto ou DOM não sanitizado para LLM.
"""
import base64
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EvidencePayload:
    """Payload de evidência estruturado para consumo do LLM Healer.

    Construído por EvidenceCollector.build_llm_payload().
    Consumido por LLMHealer.heal(payload, error_message, family).
    """

    step_context: dict = field(default_factory=dict)
    dom_snapshot: str = ""
    console_errors: list[dict] = field(default_factory=list)
    network_state: list[dict] = field(default_factory=list)
    screenshot_b64: str = ""
    is_sufficient: bool = False
    insufficiency_reason: str = ""

    def validate(self) -> None:
        """Define is_sufficient baseado na qualidade de evidência.

        Suficiente quando: snapshot DOM existe (>=100 chars).
        Erros de console, estado de rede, e screenshot são contexto bônus.
        """
        has_dom = len(self.dom_snapshot) >= 100
        has_console = len(self.console_errors) > 0
        has_network = len(self.network_state) > 0
        has_screenshot = len(self.screenshot_b64) > 0

        if not has_dom:
            self.is_sufficient = False
            self.insufficiency_reason = "DOM snapshot missing or too small (<100 chars)"
        else:
            self.is_sufficient = True
            self.insufficiency_reason = ""
            # Note: console/network/screenshot absence is tolerated
            # — they provide bonus context but are not required
            if not (has_console or has_network or has_screenshot):
                self.insufficiency_reason = (
                    "Note: no console errors, network state, or screenshot available "
                    "(bonus context missing but DOM sufficient)"
                )

    @staticmethod
    def sanitize_dom(html: str, max_chars: int = 3000) -> str:
        """Sanitize HTML for LLM consumption.

        - Remove <script> and <style> tags with content
        - Remove inline event handlers (onclick, onload, etc.)
        - Truncate to max_chars keeping head+tail
        """
        if not html:
            return ""

        # Remove script and style tags with content
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Remove inline event handlers
        html = re.sub(r'\s+on\w+\s*=\s*"[^"]*"', '', html, flags=re.IGNORECASE)
        html = re.sub(r"\s+on\w+\s*=\s*'[^']*'", '', html, flags=re.IGNORECASE)

        # Collapse whitespace (preserve single spaces)
        html = re.sub(r'\s+', ' ', html).strip()

        if len(html) <= max_chars:
            return html

        marker = "\n... [TRUNCATED] ...\n"
        half = (max_chars - len(marker)) // 2
        return html[:half] + marker + html[-half:]

    @staticmethod
    def truncate_url(url: str, max_chars: int = 120) -> str:
        """Truncate URL to max_chars, keeping scheme+host intact."""
        if len(url) <= max_chars:
            return url
        return url[:max_chars - 3] + "..."

    @staticmethod
    def screenshot_to_b64(raw_bytes: bytes) -> str:
        """Convert raw PNG bytes to base64 string for LLM payload."""
        if not raw_bytes:
            return ""
        return base64.b64encode(raw_bytes).decode("ascii")

    @classmethod
    def from_collector(
        cls,
        step_context: dict,
        dom_html: str = "",
        console_entries: Optional[list[dict]] = None,
        network_entries: Optional[list[dict]] = None,
        screenshot_bytes: Optional[bytes] = None,
    ) -> "EvidencePayload":
        """Factory: build EvidencePayload from collector artifacts."""
        payload = cls(
            step_context=step_context,
            dom_snapshot=cls.sanitize_dom(dom_html),
            console_errors=console_entries or [],
            network_state=network_entries or [],
            screenshot_b64=cls.screenshot_to_b64(screenshot_bytes or b""),
        )
        payload.validate()
        return payload
