"""TestForge — StateAgent (FAM-04).

Handles application state failures: overlay, dialog, disabled, session expired.
Strategies: overlay_dismiss, dialog_handler, re_auth_hook.
"""
from __future__ import annotations

from typing import Optional

from ..evidence_payload import EvidencePayload
from ..llm_healer import LLMHealer, LLMHealingProposal, MockLLMHealer


class StateAgent:
    """Specialist for application state failures (FAM-04)."""

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

        # 1. Alert/Confirm/Dialog
        if "dialog" in error_lower or "alert" in error_lower or "confirm" in error_lower:
            return LLMHealingProposal(
                taxonomy_id="STA-004", family="FAM-04",
                strategy="dialog_handler",
                new_locator=sel,
                confidence=0.85,
                rationale="Dialog detected — register page.on('dialog') handler before interaction",
            )

        # 2. Overlay / obscured
        if "overlay" in error_lower or "obscured" in error_lower or "intercept" in error_lower:
            return LLMHealingProposal(
                taxonomy_id="STA-002", family="FAM-04",
                strategy="overlay_dismiss",
                new_locator=sel,
                confidence=0.75,
                rationale="Overlay detected — dismiss overlay or wait for it to disappear",
            )

        # 3. Session expired
        if "session" in error_lower or "expired" in error_lower or "401" in error_lower or "unauthorized" in error_lower:
            return LLMHealingProposal(
                taxonomy_id="STA-001", family="FAM-04",
                strategy="re_auth_hook",
                new_locator=sel,
                confidence=0.60,
                rationale="Session may be expired — re-authenticate before retry",
            )

        # 4. Disabled element
        if "disabled" in error_lower or "not enabled" in error_lower:
            return LLMHealingProposal(
                taxonomy_id="INP-007", family="FAM-04",
                strategy="label_click",
                new_locator=sel,
                confidence=0.45,
                rationale="Element disabled — wait for enable or click label instead",
            )

        # 5. LLM fallback
        return self._llm.heal_or_unresolved(payload, error_message, family="FAM-04")
