from __future__ import annotations

from typing import Optional

from testforge.core.healing.agents import SpecialistAgent
from testforge.core.healing.collector import EvidencePayload
from testforge.core.healing.llm.healer import LLMHealingProposal


class StateAgent(SpecialistAgent):
    def _build_prompt(self, payload: EvidencePayload, error_message: str) -> str:
        ctx = payload.step_context
        console = "; ".join(c.get("text", "") for c in payload.console_errors[-3:])
        return (
            f"Analyze application state failure (dialog, overlay, session, navigation). Error: {error_message[:300]}\n"
            f"Action: {ctx.get('action', '')} Selector: {ctx.get('selector', '')}\n"
            f"URL: {ctx.get('url', '')}\n"
            f"Has dialog: {ctx.get('has_dialog', False)}\n"
            f"Has overlay: {ctx.get('has_overlay', False)}\n"
            f"Console: {console[:300]}\n"
            f"DOM: {payload.dom_snapshot[:600]}\n"
            f"Check for dialogs, overlays, session expiry. Propose state correction.\n"
            + self._response_format()
        )

    def heal(
        self,
        payload: EvidencePayload,
        error_message: str = "",
    ) -> LLMHealingProposal:
        ctx = payload.step_context
        err_lower = error_message.lower()

        has_dialog = (
            bool(ctx.get("has_dialog"))
            or any(kw in err_lower for kw in ["dialog", "alert", "confirm", "prompt"])
        )
        has_overlay = (
            bool(ctx.get("has_overlay"))
            or "overlay" in err_lower
            or "blocking" in err_lower
        )
        has_session = "session" in err_lower or "expir" in err_lower
        has_nav = "navigation" in err_lower or "redirect" in err_lower

        if has_dialog:
            return LLMHealingProposal(
                taxonomy_id="STA-004",
                family="FAM-04",
                strategy="dialog_handler",
                new_locator="page.on('dialog', lambda d: d.accept())",
                confidence=0.9,
                rationale="Dialog nativo bloqueando, auto-accept",
            )
        if has_overlay:
            return LLMHealingProposal(
                taxonomy_id="STA-002",
                family="FAM-04",
                strategy="overlay_wait",
                new_locator="wait_for_selector('#blocking-overlay', state='hidden')",
                confidence=0.85,
                rationale="Overlay bloqueando, aguardar desaparecer",
            )
        if has_session:
            return LLMHealingProposal(
                taxonomy_id="STA-001",
                family="FAM-04",
                strategy="state_restore",
                new_locator="page.reload()",
                confidence=0.7,
                rationale="Sessao expirada, recarregar pagina",
            )
        if has_nav:
            return LLMHealingProposal(
                taxonomy_id="STA-005",
                family="FAM-04",
                strategy="navigation_retry",
                new_locator="page.goto(url, wait_until='networkidle')",
                confidence=0.75,
                rationale="Navegacao falhou, retentar com networkidle",
            )
        fb = self._llm_fallback(payload, error_message)
        if fb and fb.confidence >= 0.5:
            return fb
        return LLMHealingProposal(
            taxonomy_id="STA-003",
            family="FAM-04",
            strategy="overlay_wait",
            new_locator="wait_for_function('document.querySelector(\"...\") === null')",
            confidence=0.5,
            rationale="Possivel estado bloqueante generico",
        )

    def _response_format(self) -> str:
        return (
            'Respond JSON: {"taxonomy_id":"STA-00X","family":"FAM-04","strategy":"dialog_handler|state_restore|navigation_retry|overlay_wait",'
            '"new_locator":"...","confidence":0.0-1.0,"rationale":"..."}'
        )
