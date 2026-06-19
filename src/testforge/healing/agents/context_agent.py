"""TestForge — ContextAgent (FAM-03).

Manipula falhas de escopo/contexto: iframe, shadow DOM, popup, cross-origin.
Estratégias: iframe_switch, shadow_pierce, capture_popup.
"""
from __future__ import annotations

from typing import Optional

from ..evidence_payload import EvidencePayload
from ..llm_healer import LLMHealer, LLMHealingProposal, MockLLMHealer


class ContextAgent:
    """Especialista em falhas de contexto/escopo (FAM-03)."""

    def __init__(self, llm_healer: Optional[LLMHealer] = None):
        self._llm = llm_healer or MockLLMHealer()

    def heal(
        self,
        payload: EvidencePayload,
        error_message: str = "",
    ) -> Optional[LLMHealingProposal]:
        ctx = payload.step_context
        sel = ctx.get("selector", "")
        error_lower = error_message.lower()

        # 1. Cross-origin — unrecoverable (manual checkpoint)
        if "cross-origin" in error_lower or "cross origin" in error_lower:
            return LLMHealingProposal(
                taxonomy_id="CTX-002", family="FAM-03",
                strategy="manual_checkpoint",
                new_locator=sel,
                confidence=0.30,  # Low — needs human review
                rationale="Cross-origin iframe — cannot access DOM. Manual intervention required.",
            )

        # 2. Iframe
        if "iframe" in error_lower or "frame" in error_lower:
            return LLMHealingProposal(
                taxonomy_id="CTX-001", family="FAM-03",
                strategy="iframe_switch",
                new_locator=sel,
                confidence=0.65,
                rationale="Element may be inside iframe — switch context before interaction",
            )

        # 3. Shadow DOM
        if "shadow" in error_lower:
            return LLMHealingProposal(
                taxonomy_id="CTX-003", family="FAM-03",
                strategy="shadow_pierce",
                new_locator=sel,
                confidence=0.55,
                rationale="Shadow DOM detected — pierce shadow root or use text fallback",
            )

        # 4. Popup / new tab
        if "popup" in error_lower or "new tab" in error_lower or "new page" in error_lower:
            return LLMHealingProposal(
                taxonomy_id="CTX-005", family="FAM-03",
                strategy="capture_popup",
                new_locator=sel,
                confidence=0.70,
                rationale="Popup detected — capture new page context before interaction",
            )

        # 5. LLM fallback
        return self._llm.heal_or_unresolved(payload, error_message, family="FAM-03")
