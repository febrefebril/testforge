"""TestForge — TimingAgent (FAM-02).

Manipula falhas de sincronização: timeout, elemento obsoleto, erros de rede.
Estratégias: visibility_wait, network_idle_wait, response_intercept.
"""
from __future__ import annotations

from typing import Optional

from ..evidence_payload import EvidencePayload
from ..llm_healer import LLMHealer, LLMHealingProposal, MockLLMHealer


class TimingAgent:
    """Especialista em falhas de timing/sincronização (FAM-02)."""

    def __init__(self, llm_healer: Optional[LLMHealer] = None):
        self._llm = llm_healer or MockLLMHealer()

    def heal(
        self,
        payload: EvidencePayload,
        error_message: str = "",
    ) -> Optional[LLMHealingProposal]:
        ctx = payload.step_context
        sel = ctx.get("selector", "")

        # 1. Check for network errors → networkidle
        if "net::err_" in error_message.lower() or "connection" in error_message.lower():
            return LLMHealingProposal(
                taxonomy_id="TIM-003", family="FAM-02",
                strategy="visibility_wait",
                new_locator=sel,
                confidence=0.75,
                rationale="Network error detected — wait for networkidle before retry",
            )

        # 2. Check for timeout → increase wait
        if "timeout" in error_message.lower():
            return LLMHealingProposal(
                taxonomy_id="TIM-005", family="FAM-02",
                strategy="visibility_wait",
                new_locator=sel,
                confidence=0.80,
                rationale="Timeout detected — increase wait with visibility check",
            )

        # 3. Check for stale element
        if "stale" in error_message.lower() or "detached" in error_message.lower():
            return LLMHealingProposal(
                taxonomy_id="DOM-001", family="FAM-02",
                strategy="visibility_wait",
                new_locator=sel,
                confidence=0.70,
                rationale="Stale/detached element — re-acquire after DOM stabilization",
            )

        # 4. LLM fallback
        return self._llm.heal_or_unresolved(payload, error_message, family="FAM-02")
