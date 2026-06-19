"""TestForge — DynamicDOMAgent (FAM-05).

Manipula falhas de DOM dinâmico: elemento obsoleto, reordenação, carregamento lento.
Estratégias: dom_stabilization, reacquire, scroll_controlled.
"""
from __future__ import annotations

from typing import Optional

from ..evidence_payload import EvidencePayload
from ..llm_healer import LLMHealer, LLMHealingProposal, MockLLMHealer


class DynamicDOMAgent:
    """Especialista em falhas de DOM dinâmico (FAM-05)."""

    def __init__(self, llm_healer: Optional[LLMHealer] = None):
        self._llm = llm_healer or MockLLMHealer()

    def heal(
        self,
        payload: EvidencePayload,
        error_message: str = "",
    ) -> Optional[LLMHealingProposal]:
        ctx = payload.step_context
        sel = ctx.get("selector", "")
        text_val = ctx.get("text", "")
        error_lower = error_message.lower()

        # 1. Stale element / detached
        if "stale" in error_lower or "detached" in error_lower:
            if text_val:
                return LLMHealingProposal(
                    taxonomy_id="DOM-001", family="FAM-05",
                    strategy="has_text_fallback",
                    new_locator=f"text={text_val[:80]}",
                    confidence=0.78,
                    rationale="Stale element — relocate by stable text instead of DOM position",
                )
            return LLMHealingProposal(
                taxonomy_id="DOM-001", family="FAM-05",
                strategy="dom_stabilization",
                new_locator=sel,
                confidence=0.60,
                rationale="Stale element — wait for DOM stabilization before re-acquire",
            )

        # 2. Not visible / viewport
        if "not visible" in error_lower or "viewport" in error_lower:
            return LLMHealingProposal(
                taxonomy_id="DOM-005", family="FAM-05",
                strategy="visibility_wait",
                new_locator=sel,
                confidence=0.72,
                rationale="Element not visible — scroll into view and wait for visibility",
            )

        # 3. Reorder / nth-child
        if "nth" in error_lower or "reorder" in error_lower:
            if text_val:
                return LLMHealingProposal(
                    taxonomy_id="DOM-002", family="FAM-05",
                    strategy="has_text_fallback",
                    new_locator=f"text={text_val[:80]}",
                    confidence=0.70,
                    rationale="List reordered — select by text content instead of position",
                )
            return LLMHealingProposal(
                taxonomy_id="DOM-002", family="FAM-05",
                strategy="semantic_locator_conversion",
                new_locator=sel.replace(":nth-child", ""),
                confidence=0.45,
                rationale="Positional selector unstable — use semantic locator",
            )

        # 4. Lazy loading
        if "lazy" in error_lower or "loading" in error_lower:
            return LLMHealingProposal(
                taxonomy_id="DOM-005", family="FAM-05",
                strategy="visibility_wait",
                new_locator=sel,
                confidence=0.65,
                rationale="Lazy loading — wait for content to appear before interaction",
            )

        # 5. LLM fallback
        return self._llm.heal_or_unresolved(payload, error_message, family="FAM-05")
