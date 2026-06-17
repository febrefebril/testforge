"""TestForge — SelectorAgent (FAM-01).

Deterministic selector fallback chain:
  data-testid > id > name > aria-label > placeholder > has-text > href > alt > class > xpath

LLM fallback when deterministic confidence < 0.7.
"""
from __future__ import annotations

import re
from typing import Optional

from ..evidence_payload import EvidencePayload
from ..llm_healer import LLMHealer, LLMHealingProposal, MockLLMHealer


class SelectorAgent:
    """Specialist for selector resolution failures (FAM-01)."""

    def __init__(self, llm_healer: Optional[LLMHealer] = None):
        self._llm = llm_healer or MockLLMHealer()

    # ── CSS attribute selector escaping ───────────────────────────────────────

    @staticmethod
    def _build_css_attr_selector(attr_name: str, value: str) -> str:
        """Build CSS attribute selector with proper quote escaping.

        Strategy:
        - If value has no single-quote, use single-quote delimiter
        - If value has single-quote but no double-quote, use double-quote delimiter
        - If value has both, use single-quote delimiter with backslash escaping
        """
        if "'" not in value:
            return f"[{attr_name}='{value}']"
        if '"' not in value:
            return f'[{attr_name}="{value}"]'
        # Both quote types: escape single quotes with backslash
        escaped = value.replace("'", "\\'")
        return f"[{attr_name}='{escaped}']"

    # ── Attribute value extraction (handles quotes in values) ─────────────────

    @staticmethod
    def _extract_attr_value(dom: str, attr_name: str) -> Optional[str]:
        """Extract full attribute value from DOM snapshot, including quoted content.

        Tries double-quote delimiter first, then single-quote.
        Unlike simple [^"'] regex, this captures the complete value
        even when it contains the opposite quote character.
        """
        # Try double-quoted: attr="value with ' inside"
        m = re.search(rf'{attr_name}\s*=\s*"([^"]{{2,80}})"', dom)
        if m:
            return m.group(1)
        # Try single-quoted: attr='value with " inside'
        m = re.search(rf"{attr_name}\s*=\s*'([^']{{2,80}})'", dom)
        if m:
            return m.group(1)
        return None

    def heal(
        self,
        payload: EvidencePayload,
        error_message: str = "",
    ) -> Optional[LLMHealingProposal]:
        """Try deterministic selector fallbacks, then LLM if needed."""
        ctx = payload.step_context
        old_sel = ctx.get("selector", "")
        text_val = ctx.get("text", "") or ""

        # 1. Try data-testid (most stable)
        proposal = self._try_testid(payload)
        if proposal and proposal.confidence >= 0.7:
            return proposal

        # 2. Try id
        proposal = self._try_id(old_sel, payload)
        if proposal and proposal.confidence >= 0.7:
            return proposal

        # 3. Try accessible name / aria-label
        proposal = self._try_aria(payload)
        if proposal and proposal.confidence >= 0.7:
            return proposal

        # 4. Try placeholder
        proposal = self._try_placeholder(payload)
        if proposal and proposal.confidence >= 0.7:
            return proposal

        # 5. Try text-based
        proposal = self._try_text(text_val)
        if proposal and proposal.confidence >= 0.7:
            return proposal

        # 6. Fallback to LLM
        return self._llm_fallback(payload, error_message)

    def _try_testid(self, payload: EvidencePayload) -> Optional[LLMHealingProposal]:
        dom = payload.dom_snapshot
        testid = self._extract_attr_value(dom, "data-testid")
        if testid:
            selector = self._build_css_attr_selector("data-testid", testid)
            return LLMHealingProposal(
                taxonomy_id="SEL-006", family="FAM-01",
                strategy="semantic_locator_conversion",
                new_locator=selector,
                confidence=0.85,
                rationale=f"Found data-testid attribute in DOM: {testid}",
            )
        return None

    def _try_id(self, old_sel: str, payload: EvidencePayload) -> Optional[LLMHealingProposal]:
        # Extract id from old selector pattern
        import re
        match = re.search(r'#([a-zA-Z][\w-]*)', old_sel)
        if match:
            old_id = match.group(1)
            # Check if the id appears in current DOM
            if old_id in payload.dom_snapshot:
                return LLMHealingProposal(
                    taxonomy_id="SEL-001", family="FAM-01",
                    strategy="semantic_locator_conversion",
                    new_locator=f"#{old_id}",
                    confidence=0.60,
                    rationale=f"ID '{old_id}' found in current DOM — may still be valid",
                )
        return None

    def _try_aria(self, payload: EvidencePayload) -> Optional[LLMHealingProposal]:
        dom = payload.dom_snapshot
        label = self._extract_attr_value(dom, "aria-label")
        if label:
            selector = self._build_css_attr_selector("aria-label", label)
            return LLMHealingProposal(
                taxonomy_id="SEL-006", family="FAM-01",
                strategy="aria_role_strategy",
                new_locator=selector,
                confidence=0.75,
                rationale=f"Found aria-label in DOM: {label}",
            )
        return None

    def _try_placeholder(self, payload: EvidencePayload) -> Optional[LLMHealingProposal]:
        dom = payload.dom_snapshot
        ph = self._extract_attr_value(dom, "placeholder")
        if ph:
            selector = self._build_css_attr_selector("placeholder", ph)
            return LLMHealingProposal(
                taxonomy_id="SEL-006", family="FAM-01",
                strategy="semantic_locator_conversion",
                new_locator=selector,
                confidence=0.80,
                rationale=f"Found placeholder in DOM: {ph}",
            )
        return None

    def _try_text(self, text_val: str) -> Optional[LLMHealingProposal]:
        if text_val and len(text_val) >= 2:
            # Use exact text match (quoted) to avoid matching parent elements
            # that contain the same text (e.g. <p> wrapping a <button>)
            escaped = text_val[:80].replace('"', '\\"')
            return LLMHealingProposal(
                taxonomy_id="SEL-004", family="FAM-01",
                strategy="has_text_fallback",
                new_locator=f'text="{escaped}"',
                confidence=0.70,
                rationale=f"Fallback to visible text (exact): '{text_val[:80]}'",
            )
        return None

    def _llm_fallback(
        self, payload: EvidencePayload, error_message: str,
    ) -> Optional[LLMHealingProposal]:
        """Last resort: invoke LLM."""
        proposal = self._llm.heal_or_unresolved(payload, error_message, family="FAM-01")
        if proposal.confidence >= 0.5:
            return proposal
        return None
