from __future__ import annotations

from typing import Optional

from testforge.core.healing.agents import SpecialistAgent
from testforge.core.healing.collector import EvidencePayload
from testforge.core.healing.llm.healer import LLMHealingProposal


class DynamicDOMAgent(SpecialistAgent):
    def _build_prompt(self, payload: EvidencePayload, error_message: str) -> str:
        ctx = payload.step_context
        console = "; ".join(c.get("text", "") for c in payload.console_errors[-3:])
        return (
            f"Analyze dynamic DOM failure. Error: {error_message[:300]}\n"
            f"Action: {ctx.get('action', '')} Selector: {ctx.get('selector', '')}\n"
            f"Console: {console[:300]}\n"
            f"DOM: {payload.dom_snapshot[:600]}\n"
            f"Check for stale elements, reordered lists, lazy content. Propose wait strategy.\n"
            + self._response_format()
        )

    def heal(
        self,
        payload: EvidencePayload,
        error_message: str = "",
    ) -> LLMHealingProposal:
        has_stale = "stale" in error_message.lower()
        has_reorder = "reorder" in error_message.lower() or "multiple" in error_message.lower()
        has_lazy = "lazy" in error_message.lower() or "loading" in error_message.lower()

        if has_stale:
            return LLMHealingProposal(
                taxonomy_id="DOM-001",
                family="FAM-05",
                strategy="visibility_wait",
                new_locator="wait_for_selector(state='visible')",
                confidence=0.85,
                rationale="Elemento stale, aguardar visibilidade",
            )
        if has_reorder:
            return LLMHealingProposal(
                taxonomy_id="DOM-002",
                family="FAM-05",
                strategy="semantic_locator_conversion",
                new_locator="has_text('...')",
                confidence=0.8,
                rationale="Lista reordenada, usar has-text",
            )
        if has_lazy:
            return LLMHealingProposal(
                taxonomy_id="DOM-005",
                family="FAM-05",
                strategy="wait_for_function",
                new_locator="wait_for_function('document.querySelector(\"...\")')",
                confidence=0.75,
                rationale="Conteudo lazy, aguardar elemento aparecer",
            )
        fb = self._llm_fallback(payload, error_message)
        if fb and fb.confidence >= 0.5:
            return fb
        return LLMHealingProposal(
            taxonomy_id="DOM-003",
            family="FAM-05",
            strategy="visibility_wait",
            new_locator="wait_for_selector(state='attached')",
            confidence=0.6,
            rationale="Problema de DOM dinamico generico",
        )

    def _response_format(self) -> str:
        return (
            'Respond JSON: {"taxonomy_id":"DOM-00X","family":"FAM-05","strategy":"visibility_wait|semantic_locator_conversion|wait_for_function",'
            '"new_locator":"...","confidence":0.0-1.0,"rationale":"..."}'
        )
