from __future__ import annotations

from typing import Optional

from testforge.core.healing.agents import SpecialistAgent
from testforge.core.healing.collector import EvidencePayload
from testforge.core.healing.llm.healer import LLMHealingProposal


class InputAgent(SpecialistAgent):
    def _build_prompt(self, payload: EvidencePayload, error_message: str) -> str:
        ctx = payload.step_context
        return (
            f"Analyze input failure. Error: {error_message[:300]}\n"
            f"Action: {ctx.get('action', '')}\n"
            f"Selector: {ctx.get('selector', '')}\n"
            f"Value: {str(ctx.get('value', ''))[:200]}\n"
            f"Tag: {ctx.get('tag_name', '')} Input type: {ctx.get('input_type', '')}\n"
            f"Has mask: {ctx.get('has_mask', False)}\n"
            f"Text: {ctx.get('text', '')}\n"
            f"DOM: {payload.dom_snapshot[:600]}\n"
            f"Propose alternative interaction (pressSequentially, label click, synthetic click, file chooser).\n"
            + self._response_format()
        )

    def heal(
        self,
        payload: EvidencePayload,
        error_message: str = "",
    ) -> LLMHealingProposal:
        ctx = payload.step_context
        err_lower = error_message.lower()
        action = ctx.get("action", "")
        value = str(ctx.get("value", ""))
        safe_value = value.replace("\\", "\\\\").replace("'", "\\'")
        safe_text = str(ctx.get("text", "")).replace("\\", "\\\\").replace("'", "\\'")
        has_mask = ctx.get("has_mask", False)
        input_type = ctx.get("input_type", "")

        if "fill" in err_lower or "editable" in err_lower:
            sel = ctx.get("selector", "")
            safe_sel = sel.replace("\\", "\\\\").replace("'", "\\'") if sel else ""
            return LLMHealingProposal(
                taxonomy_id="INP-001",
                family="FAM-06",
                strategy="press_sequentially",
                new_locator=safe_sel or "[contenteditable='true']",
                confidence=0.85,
                rationale=f"page.fill falhou, tentar pressSequentially",
            )
        if "upload" in action.lower() or "file" in err_lower:
            return LLMHealingProposal(
                taxonomy_id="FILE-001",
                family="FAM-07",
                strategy="file_chooser",
                new_locator="input[type='file']",
                confidence=0.8,
                rationale="Upload falhou, tentar set_input_files",
            )
        if has_mask or "masked" in err_lower or "mask" in err_lower:
            return LLMHealingProposal(
                taxonomy_id="INP-007",
                family="FAM-06",
                strategy="masked_input_detection",
                new_locator=value,
                confidence=0.75,
                rationale="Input com mascara JS, usar pressSequentially com delay",
            )
        if input_type in ("date", "datetime-local"):
            return LLMHealingProposal(
                taxonomy_id="INP-008",
                family="FAM-06",
                strategy="label_click",
                new_locator=f"[type='{input_type}']",
                confidence=0.7,
                rationale=f"Date picker detectado, tentar label click",
            )
        fb = self._llm_fallback(payload, error_message)
        if fb and fb.confidence >= 0.5:
            return fb
        return LLMHealingProposal(
            taxonomy_id="INP-005",
            family="FAM-06",
            strategy="label_click",
            new_locator=safe_text if safe_text else "label",
            confidence=0.7,
            rationale="Input generico, tentar label click",
        )

    def _response_format(self) -> str:
        return (
            'Respond JSON: {"taxonomy_id":"INP-00X","family":"FAM-06","strategy":"press_sequentially|masked_input_detection|label_click|file_chooser",'
            '"new_locator":"...","confidence":0.0-1.0,"rationale":"..."}'
        )
