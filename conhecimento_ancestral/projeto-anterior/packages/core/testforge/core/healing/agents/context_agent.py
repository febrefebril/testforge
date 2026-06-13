from __future__ import annotations

import re
from typing import Optional

from testforge.core.healing.agents import SpecialistAgent
from testforge.core.healing.collector import EvidencePayload
from testforge.core.healing.llm.healer import LLMHealingProposal


class ContextAgent(SpecialistAgent):
    def _build_prompt(self, payload: EvidencePayload, error_message: str) -> str:
        ctx = payload.step_context
        return (
            f"Analyze context failure (iframe, shadow DOM, modal, popup). Error: {error_message[:300]}\n"
            f"Action: {ctx.get('action', '')} Selector: {ctx.get('selector', '')}\n"
            f"URL: {ctx.get('url', '')}\n"
            f"Frame URL: {ctx.get('frame_url', '')}\n"
            f"Shadow root: {ctx.get('has_shadow', False)}\n"
            f"DOM: {payload.dom_snapshot[:600]}\n"
            f"Check if element is inside iframe or shadow root. Propose context switch.\n"
            + self._response_format()
        )

    def heal(
        self,
        payload: EvidencePayload,
        error_message: str = "",
    ) -> LLMHealingProposal:
        ctx = payload.step_context
        err_lower = error_message.lower()

        in_iframe = bool(ctx.get("frame_url")) or bool(re.search(r'\biframe\b', error_message, re.IGNORECASE))
        in_shadow = bool(ctx.get("has_shadow")) or bool(re.search(r'\bshadow\b', error_message, re.IGNORECASE))
        has_popup = "popup" in err_lower or "cross-origin" in err_lower

        if in_iframe:
            return LLMHealingProposal(
                taxonomy_id="CTX-001",
                family="FAM-03",
                strategy="iframe_switch",
                new_locator=f"frame_url='{ctx.get('frame_url', 'iframe')}'",
                confidence=0.85,
                rationale="Elemento dentro de iframe, usar frame_locator",
            )
        if in_shadow:
            return LLMHealingProposal(
                taxonomy_id="CTX-002",
                family="FAM-03",
                strategy="shadow_dom_query",
                new_locator=":host-context(...)",
                confidence=0.8,
                rationale="Elemento dentro de Shadow DOM, navegar pelo shadow root",
            )
        if has_popup:
            return LLMHealingProposal(
                taxonomy_id="CTX-006",
                family="FAM-03",
                strategy="popup_handler",
                new_locator="page.wait_for_popup()",
                confidence=0.75,
                rationale="Popup/cross-origin detectado, aguardar popup",
            )
        fb = self._llm_fallback(payload, error_message)
        if fb and fb.confidence >= 0.5:
            return fb
        return LLMHealingProposal(
            taxonomy_id="CTX-003",
            family="FAM-03",
            strategy="iframe_switch",
            new_locator="iframe",
            confidence=0.5,
            rationale="Possivel problema de contexto generico",
        )

    def _response_format(self) -> str:
        return (
            'Respond JSON: {"taxonomy_id":"CTX-00X","family":"FAM-03","strategy":"iframe_switch|shadow_dom_query|popup_handler",'
            '"new_locator":"...","confidence":0.0-1.0,"rationale":"..."}'
        )
