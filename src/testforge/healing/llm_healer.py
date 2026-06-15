"""TestForge — LLM Healer (L3).

LLMHealer: calls Azure OpenAI / OpenAI with family-specific prompts.
MockLLMHealer: deterministic fallback when no API key configured.
LLMHealingProposal: structured output from LLM.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Optional

from ..taxonomy.taxonomy import FAMILIES, TAXONOMIES
from .evidence_payload import EvidencePayload
from .llm_prompts import CURATION_PROMPT_TEMPLATE, FAMILY_PROMPTS


# ── Allowed Strategies ──────────────────────────────────────────────────────

ALLOWED_STRATEGIES = {
    "semantic_locator_conversion",
    "has_text_fallback",
    "masked_input_detection",
    "press_sequentially",
    "dialog_handler",
    "visibility_wait",
    "iframe_switch",
    "label_click",
    "synthetic_click",
    "xpath_fallback",
}


# ── LLMHealingProposal ──────────────────────────────────────────────────────

@dataclass
class LLMHealingProposal:
    """Structured healing proposal from LLM (or MockLLMHealer)."""
    taxonomy_id: str = ""
    family: str = ""
    strategy: str = ""
    new_locator: str = ""
    confidence: float = 0.0
    rationale: str = ""
    raw_response: str = ""


# ── Prompt Builder ──────────────────────────────────────────────────────────

def _build_taxonomy_hint() -> str:
    """Build condensed taxonomy reference for LLM prompt context."""
    lines: list[str] = []
    for fam_code, fam_name in FAMILIES.items():
        tax_list = TAXONOMIES.get(fam_code, [])
        lines.append(f"  {fam_code} ({fam_name}): {', '.join(tax_list[:5])}")
    return "\n".join(lines)


def _truncate_text(text: str, max_chars: int) -> str:
    """Truncate text to max_chars with marker."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "...[truncated]"


MAX_PROMPT_CHARS = 2400


def _build_prompt(payload: EvidencePayload, error_message: str, family: str = "") -> str:
    """Build LLM prompt from evidence payload and error context."""
    dom_snippet = _truncate_text(payload.dom_snapshot, 3000)
    console_lines = [c.get("text", "") for c in payload.console_errors[-5:]]
    console_str = "\n".join(console_lines) if console_lines else "(nenhum)"

    net_lines = [
        f"{r.get('method', '?')} {r.get('url', '')[:100]} -> {r.get('status', '?')}"
        for r in payload.network_state[-3:]
    ]
    net_str = "\n".join(net_lines) if net_lines else "(nenhum)"

    ctx = payload.step_context
    taxonomy_hint = _build_taxonomy_hint()

    template = CURATION_PROMPT_TEMPLATE
    if family and family in FAMILY_PROMPTS:
        template = FAMILY_PROMPTS[family]

    prompt = template.format(
        action=ctx.get("action", ""),
        selector=ctx.get("selector", ""),
        value=str(ctx.get("value", ""))[:200],
        intention=ctx.get("intention", ""),
        error_message=error_message[:500],
        dom_snippet=dom_snippet[:3000],
        console_errors=console_str[:500],
        network_summary=net_str[:300],
        taxonomy_hint=taxonomy_hint,
    )

    if len(prompt) > MAX_PROMPT_CHARS:
        prompt = prompt[:MAX_PROMPT_CHARS] + "\n[TRUNCATED]"

    return prompt


# ── JSON Parser ─────────────────────────────────────────────────────────────

def _extract_json(text: str) -> Optional[str]:
    """Extract first complete JSON object from LLM response using bracket matching."""
    stack = []
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if not stack:
                start = i
            stack.append(i)
        elif ch == "}":
            if stack:
                stack.pop()
                if not stack and start >= 0:
                    return text[start:i + 1]
    return None


def _parse_response(text: str) -> Optional[LLMHealingProposal]:
    """Parse LLM response into LLMHealingProposal. Returns None if invalid."""
    json_str = _extract_json(text)
    if not json_str:
        return None
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        return None

    required = {"taxonomy_id", "family", "strategy", "new_locator", "confidence", "rationale"}
    if not required.issubset(data.keys()):
        return None

    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        return None
    confidence = max(0.0, min(1.0, confidence))

    taxonomy_id = str(data.get("taxonomy_id", ""))
    family = str(data.get("family", ""))
    strategy = str(data.get("strategy", ""))

    proposal = LLMHealingProposal(
        taxonomy_id=taxonomy_id,
        family=family,
        strategy=strategy,
        new_locator=str(data.get("new_locator", "")),
        confidence=confidence,
        rationale=str(data.get("rationale", ""))[:300],
        raw_response=text,
    )

    # Validate against allowed strategies
    if proposal.strategy not in ALLOWED_STRATEGIES:
        proposal.confidence = 0.0

    # Validate taxonomy
    if family not in FAMILIES or taxonomy_id not in TAXONOMIES.get(family, []):
        proposal.confidence = 0.0

    return proposal


# ── LLMHealer ───────────────────────────────────────────────────────────────

class LLMHealer:
    """Healer that calls LLM API with family-specific prompts.

    Auto-activates when AZURE_OPENAI_KEY or OPENAI_API_KEY env vars are set.
    Falls back to MockLLMHealer when no keys configured.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        max_retries: int = 3,
    ):
        self._model = model
        self._temperature = temperature
        self._max_retries = max_retries

    def heal(
        self,
        payload: EvidencePayload,
        error_message: str = "",
        family: str = "",
    ) -> LLMHealingProposal:
        """Call LLM and parse healing proposal."""
        from .llm_client import chat, is_available

        if not is_available():
            return LLMHealingProposal(
                confidence=0.0,
                rationale="LLM unavailable — no API key configured",
            )

        prompt = _build_prompt(payload, error_message, family=family)

        last_error: Optional[Exception] = None
        for attempt in range(self._max_retries):
            try:
                # System prompt is empty — all context is in user message
                text = chat(
                    system="",
                    user=prompt,
                    temperature=self._temperature,
                    max_tokens=500,
                )
                proposal = _parse_response(text)
                if proposal is None:
                    return LLMHealingProposal(
                        confidence=0.0,
                        rationale="Failed to parse LLM response",
                        raw_response=text,
                    )
                return proposal

            except Exception as e:
                last_error = e
                status_code = None
                if hasattr(e, 'status_code'):
                    status_code = e.status_code
                elif hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                    status_code = e.response.status_code

                if status_code == 429 and attempt < self._max_retries - 1:
                    wait = 2 ** attempt
                    time.sleep(wait)
                    continue

                if attempt < self._max_retries - 1:
                    time.sleep(2 ** attempt)

        raise RuntimeError(f"LLM failed after {self._max_retries} attempts: {last_error}")

    def heal_or_unresolved(
        self,
        payload: EvidencePayload,
        error_message: str = "",
        family: str = "",
    ) -> LLMHealingProposal:
        """Safe wrapper — never raises. Returns confidence=0.0 on failure."""
        try:
            return self.heal(payload, error_message, family=family)
        except Exception as e:
            return LLMHealingProposal(
                confidence=0.0,
                rationale=f"LLM error: {str(e)[:200]}",
            )


# ── MockLLMHealer ───────────────────────────────────────────────────────────

class MockLLMHealer(LLMHealer):
    """Deterministic healer — no API call, always returns a generic proposal.

    Used when AZURE_OPENAI_KEY and OPENAI_API_KEY are not configured.
    Provides feature parity without external dependencies.
    """

    def heal(
        self,
        payload: EvidencePayload,
        error_message: str = "",
        family: str = "",
    ) -> LLMHealingProposal:
        """Generate deterministic proposal from step context."""
        ctx = payload.step_context
        sel = ctx.get("selector", "")
        text_val = ctx.get("text", "")
        action = ctx.get("action", "")

        # Build a reasonable fallback locator
        if text_val:
            new_locator = f"page.get_by_text('{text_val[:50]}')"
        elif sel and "#" in sel:
            # Try to use the ID part
            new_locator = sel
        else:
            new_locator = f"page.get_by_text('click target')"

        # Map family to appropriate strategy
        strategy_map = {
            "FAM-01": "has_text_fallback",
            "FAM-02": "visibility_wait",
            "FAM-03": "iframe_switch",
            "FAM-04": "dialog_handler",
            "FAM-05": "has_text_fallback",
            "FAM-06": "press_sequentially",
            "FAM-07": "label_click",
            "FAM-08": "visibility_wait",
            "FAM-09": "synthetic_click",
            "FAM-10": "visibility_wait",
            "FAM-11": "synthetic_click",
        }
        strategy = strategy_map.get(family, "has_text_fallback")

        # Default taxonomy per family
        tax_map = {
            "FAM-01": ("SEL-004", "FAM-01"),
            "FAM-02": ("TIM-005", "FAM-02"),
            "FAM-03": ("CTX-001", "FAM-03"),
            "FAM-04": ("STA-002", "FAM-04"),
            "FAM-05": ("DOM-001", "FAM-05"),
            "FAM-06": ("INP-007", "FAM-06"),
            "FAM-07": ("FILE-001", "FAM-07"),
            "FAM-08": ("AST-001", "FAM-08"),
            "FAM-09": ("REC-002", "FAM-09"),
            "FAM-10": ("OBS-001", "FAM-10"),
            "FAM-11": ("LIM-001", "FAM-11"),
        }
        tax_id, tax_family = tax_map.get(family, ("SEL-004", "FAM-01"))

        return LLMHealingProposal(
            taxonomy_id=tax_id,
            family=tax_family,
            strategy=strategy,
            new_locator=new_locator,
            confidence=0.85,
            rationale=f"Mock: deterministic fallback using {strategy} for {action}",
            raw_response="",
        )
