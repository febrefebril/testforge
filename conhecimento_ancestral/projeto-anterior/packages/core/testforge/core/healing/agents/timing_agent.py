from __future__ import annotations

from typing import Optional

from testforge.core.healing.agents import SpecialistAgent
from testforge.core.healing.collector import EvidencePayload
from testforge.core.healing.llm.healer import LLMHealingProposal


class TimingAgent(SpecialistAgent):
    def _build_prompt(self, payload: EvidencePayload, error_message: str) -> str:
        ctx = payload.step_context
        console = "; ".join(c.get("text", "") for c in payload.console_errors[-3:])
        net = "; ".join(
            f"{r.get('method','?')} {r.get('status','?')}"
            for r in payload.network_state[-3:]
        )
        return (
            f"Analyze timing/DOM failure. Error: {error_message[:300]}\n"
            f"Action: {ctx.get('action', '')} Selector: {ctx.get('selector', '')}\n"
            f"Console errors: {console[:300]}\n"
            f"Network: {net[:300]}\n"
            f"DOM: {payload.dom_snapshot[:600]}\n"
            f"Propose semantic wait (no fixed timeout).\n"
            + self._response_format()
        )

    def heal(
        self,
        payload: EvidencePayload,
        error_message: str = "",
    ) -> LLMHealingProposal:
        has_network_error = any("net::ERR_" in c.get("text", "") for c in payload.console_errors)
        has_stale = "stale" in error_message.lower()
        has_loading = "loading" in error_message.lower()
        has_mutation = "mutation" in error_message.lower() or "reorder" in error_message.lower()
        has_xhr = any(
            kw in error_message.lower()
            for kw in ["xhr", "fetch", "ajax", "async"]
        )

        if has_network_error:
            return LLMHealingProposal(
                taxonomy_id="TIM-003",
                family="FAM-02",
                strategy="network_idle",
                new_locator="wait_for_load_state('networkidle')",
                confidence=0.8,
                rationale="Aguardar network idle apos erro de rede",
            )
        if has_stale:
            return LLMHealingProposal(
                taxonomy_id="TIM-001",
                family="FAM-02",
                strategy="visibility_wait",
                new_locator="wait_for_selector(state='visible')",
                confidence=0.85,
                rationale="Elemento stale, aguardar visibilidade",
            )
        if has_loading:
            return LLMHealingProposal(
                taxonomy_id="TIM-002",
                family="FAM-02",
                strategy="dom_content_loaded",
                new_locator="wait_for_load_state('domcontentloaded')",
                confidence=0.75,
                rationale="Pagina ainda carregando",
            )
        if has_mutation or has_xhr:
            return LLMHealingProposal(
                taxonomy_id="TIM-004",
                family="FAM-02",
                strategy="wait_for_function",
                new_locator="wait_for_function('document.querySelector(\"...\")')",
                confidence=0.7,
                rationale="Conteudo assincrono, usar wait_for_function",
            )
        fb = self._llm_fallback(payload, error_message)
        if fb and fb.confidence >= 0.5:
            return fb
        return LLMHealingProposal(
            taxonomy_id="TIM-005",
            family="FAM-02",
            strategy="visibility_wait",
            new_locator="wait_for_selector(state='attached')",
            confidence=0.6,
            rationale="Timing generico, aguardar attached",
        )

    def _response_format(self) -> str:
        return (
            'Respond JSON: {"taxonomy_id":"TIM-00X","family":"FAM-02","strategy":"visibility_wait|network_idle|dom_content_loaded|wait_for_function",'
            '"new_locator":"...","confidence":0.0-1.0,"rationale":"..."}'
        )
