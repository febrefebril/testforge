"""TestForge — SelectorAgent (FAM-01).

Cadeia de fallback de seletor determinístico:
  data-testid > id > name > aria-label > placeholder > has-text > href > alt > class > xpath

Fallback LLM quando confiança determinística < 0.7.
"""
from __future__ import annotations

import re
from typing import Optional

from ..evidence_payload import EvidencePayload
from ..llm_healer import LLMHealer, LLMHealingProposal, MockLLMHealer


class SelectorAgent:
    """Especialista em falhas de resolução de seletor (FAM-01)."""

    def __init__(self, llm_healer: Optional[LLMHealer] = None):
        self._llm = llm_healer or MockLLMHealer()

    # -- CSS attribute selector escaping ---------------------------------------

    @staticmethod
    def _build_css_attr_selector(attr_name: str, value: str) -> str:
        """Constrói seletor de atributo CSS com escape de aspas adequado.

        Estratégia:
        - Se valor sem aspas simples, usa delimitador de aspas simples
        - Se valor com aspas simples mas sem duplas, usa delimitador de aspas duplas
        - Se ambas, usa delimitador de aspas simples com escape de barra invertida
        """
        if "'" not in value:
            return f"[{attr_name}='{value}']"
        if '"' not in value:
            return f'[{attr_name}="{value}"]'
        # Both quote types: escape single quotes with backslash
        escaped = value.replace("'", "\\'")
        return f"[{attr_name}='{escaped}']"

    # -- Attribute value extraction (handles quotes in values) -----------------

    @staticmethod
    def _extract_attr_value(dom: str, attr_name: str) -> Optional[str]:
        """Extrai valor de atributo completo do snapshot DOM, incluindo conteúdo citado.

        Tenta delimitador de aspas duplas primeiro, depois aspas simples.
        Diferente de regex simples [^"'], captura o valor completo
        mesmo quando contém o caractere de aspa oposta.
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

        # 5. Try href (stable for <a> navigation links)
        proposal = self._try_href(payload)
        if proposal and proposal.confidence >= 0.7:
            return proposal

        # 6. Try text-based
        proposal = self._try_text(text_val)
        if proposal and proposal.confidence >= 0.7:
            return proposal

        # 7. Fallback to LLM
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
                rationale=f"data-testid encontrado no DOM: {testid}",
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
                    rationale=f"ID '{old_id}' encontrado no DOM atual — pode ainda ser valido",
                )
        return None

    def _try_aria(self, payload: EvidencePayload) -> Optional[LLMHealingProposal]:
        dom = payload.dom_snapshot
        label = self._extract_attr_value(dom, "aria-label")
        if label:
            # Skip generic navigation labels — too broad for step-specific healing
            _skip_labels = {'página inicial', 'pagina inicial', 'home', 'voltar', 'fechar',
                          'close', 'menu', 'abrir menu', 'open menu'}
            if label.strip().lower() in _skip_labels:
                return None
            selector = self._build_css_attr_selector("aria-label", label)
            return LLMHealingProposal(
                taxonomy_id="SEL-006", family="FAM-01",
                strategy="aria_role_strategy",
                new_locator=selector,
                confidence=0.45,  # Lower: aria-label alone is weak without role context
                rationale=f"aria-label encontrado no DOM: {label}",
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
                rationale=f"placeholder encontrado no DOM: {ph}",
            )
        return None

    def _try_href(self, payload: EvidencePayload) -> Optional[LLMHealingProposal]:
        """Extract href from <a> in DOM snapshot — stable across Tailwind
        class changes.

        B18 (2026-06-27): the previous version grepped the FIRST `<a href>`
        in the DOM, which on SIOPI was the logo link (`<a href="/">`).
        Every step that failed got the same cure, oracle approved because
        the home link existed on every page, and `run` shipped 26
        consecutive false-positive heals. Now we:
        - skip site-root / fragment / javascript hrefs (dangerous);
        - require the anchor's text to contain the original target text
          (semantic match) — without it, an anchor cure is a guess.
        - drop confidence to a level the dangerous-locator filter would
          still reject if the match is shallow.
        """
        ctx = payload.step_context
        target_text = (ctx.get("text") or "").strip().lower()
        if not target_text or len(target_text) < 3:
            # Without a target text to match, we cannot tell a meaningful
            # anchor from the logo. Refuse to propose.
            return None
        dom = payload.dom_snapshot
        # Match anchors with their inner text so we can require a
        # textual overlap with the original target.
        candidates = re.findall(
            r'<a\b[^>]+\bhref\s*=\s*["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',
            dom, re.IGNORECASE,
        )
        for href, inner in candidates:
            href = (href or "").strip()
            if not href or href in {"/", "#", ""}:
                continue
            if href.startswith("javascript:") or href.startswith("#"):
                continue
            if href.startswith("/home"):
                continue
            # Inner text — strip HTML tags + collapse whitespace.
            inner_text = re.sub(r"<[^>]+>", " ", inner)
            inner_text = re.sub(r"\s+", " ", inner_text).strip().lower()
            if not inner_text:
                continue
            overlap = target_text in inner_text or inner_text in target_text
            if not overlap:
                continue
            # Confidence reflects depth of match: very short text overlap
            # is suspicious.
            score = 0.82 if len(inner_text) >= 6 else 0.65
            return LLMHealingProposal(
                taxonomy_id="SEL-004", family="FAM-01",
                strategy="semantic_locator_conversion",
                new_locator=f'a[href="{href}"]',
                confidence=score,
                rationale=(
                    f"href '{href}' com texto que casa com alvo "
                    f"'{target_text[:40]}'"
                ),
            )
        return None

    # B24/B25: minimum length for a text= fallback to be considered
    # semantically meaningful. "JAN", "1992", "1" all match calendar
    # widgets in unpredictable spots; raise the bar so we do not propose
    # them as cures. 6 characters covers most month names, button
    # labels, and labels like "Calcular" / "Confirmar".
    _MIN_TEXT_FALLBACK_LEN = 6

    # Very common UI words that are not specific enough to identify a
    # control even at meaningful length. Reject them outright.
    _GENERIC_TEXT_BLOCKLIST = frozenset({
        "ok", "cancelar", "fechar", "voltar", "continuar", "salvar",
        "confirmar", "enviar", "home", "menu", "sim", "nao", "não",
        "selecione", "calcular", "calculate",
    })

    def _try_text(self, text_val: str) -> Optional[LLMHealingProposal]:
        if not text_val:
            return None
        cleaned = text_val.strip()
        if len(cleaned) < self._MIN_TEXT_FALLBACK_LEN:
            return None
        # Reject text matches that are entirely numeric — calendar
        # cells, year labels, page numbers are all ambiguous targets.
        if cleaned.replace(",", "").replace(".", "").replace("/", "").isdigit():
            return None
        # Reject the generic UI vocabulary even at meaningful length.
        if cleaned.lower() in self._GENERIC_TEXT_BLOCKLIST:
            return None
        # Use exact text match (quoted) to avoid matching parent
        # elements that contain the same text (e.g. <p> wrapping a
        # <button>).
        escaped = cleaned[:80].replace('"', '\\"')
        return LLMHealingProposal(
            taxonomy_id="SEL-004", family="FAM-01",
            strategy="has_text_fallback",
            new_locator=f'text="{escaped}"',
            confidence=0.70,
            rationale=f"Fallback por texto visivel (exato): '{cleaned[:80]}'",
        )

    def _llm_fallback(
        self, payload: EvidencePayload, error_message: str,
    ) -> Optional[LLMHealingProposal]:
        """Last resort: invoke LLM."""
        proposal = self._llm.heal_or_unresolved(payload, error_message, family="FAM-01")
        if proposal.confidence >= 0.5:
            return proposal
        return None
