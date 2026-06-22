"""TestForge — InputAgent (FAM-06 + FAM-07).

Manipula falhas de entrada/interação: campos mascarados, upload/download de arquivo.
Estratégias: press_sequentially, masked_input_detection, label_click, file_fixture.
"""
from __future__ import annotations

from typing import Optional

from ..evidence_payload import EvidencePayload
from ..llm_healer import LLMHealer, LLMHealingProposal, MockLLMHealer


class InputAgent:
    """Especialista em falhas de entrada/interação (FAM-06, FAM-07)."""

    def __init__(self, llm_healer: Optional[LLMHealer] = None):
        self._llm = llm_healer or MockLLMHealer()

    def heal(
        self,
        payload: EvidencePayload,
        error_message: str = "",
    ) -> Optional[LLMHealingProposal]:
        ctx = payload.step_context
        sel = ctx.get("selector", "")
        action = ctx.get("action", "")
        value = ctx.get("value", "")
        error_lower = error_message.lower()

        # 1. Masked input / fill failure
        if "fill" in error_lower or "masked" in error_lower or "not editable" in error_lower:
            return LLMHealingProposal(
                taxonomy_id="INP-007", family="FAM-06",
                strategy="press_sequentially",
                new_locator=sel,
                confidence=0.82,
                rationale="Campo com mascara JS — use press_sequentially em vez de fill",
            )

        # 2. Clear failure
        if "clear" in error_lower:
            return LLMHealingProposal(
                taxonomy_id="INP-007", family="FAM-06",
                strategy="masked_input_detection",
                new_locator=sel,
                confidence=0.70,
                rationale="Limpeza falhou — use JS native setter como fallback",
            )

        # 3. File upload
        if "file" in error_lower or "upload" in error_lower:
            return LLMHealingProposal(
                taxonomy_id="FILE-001", family="FAM-07",
                strategy="label_click",
                new_locator="input[type=file]",
                confidence=0.68,
                rationale="Input de arquivo pode estar oculto — acione via label ou input[type=file] direto",
            )

        # 4. Download
        if "download" in error_lower:
            return LLMHealingProposal(
                taxonomy_id="FILE-005", family="FAM-07",
                strategy="semantic_locator_conversion",
                new_locator=sel,
                confidence=0.55,
                rationale="Download pode precisar de contexto de sessao — capture dentro do fluxo autenticado",
            )

        # 5. Drag and drop
        if "drag" in error_lower or "drop" in error_lower:
            return LLMHealingProposal(
                taxonomy_id="INP-005", family="FAM-06",
                strategy="synthetic_click",
                new_locator=sel,
                confidence=0.50,
                rationale="Drag-and-drop nao reproduzivel — simule via eventos de mouse controlados ou clique sintetico",
            )

        # 6. CAPTCHA — unrecoverable
        if "captcha" in error_lower:
            return LLMHealingProposal(
                taxonomy_id="INP-008", family="FAM-06",
                strategy="manual_checkpoint",
                new_locator=sel,
                confidence=0.10,
                rationale="CAPTCHA detectado — intervencao manual necessaria. Nao tente contornar.",
            )

        # 7. LLM fallback
        return self._llm.heal_or_unresolved(payload, error_message, family="FAM-06")
