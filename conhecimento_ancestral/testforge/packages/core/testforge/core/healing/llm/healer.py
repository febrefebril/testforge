from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from testforge.core.config.schema import LLMConfig
from testforge.core.errors.hierarchy import LLMUnavailableError
from testforge.core.healing.collector import EvidencePayload
from testforge.core.healing.llm.prompts import CURATION_PROMPT_TEMPLATE, FAMILY_PROMPTS
from testforge.core.healing.models import FAMILIES, TAXONOMIES


@dataclass
class LLMHealingProposal:
    taxonomy_id: str = ""
    family: str = ""
    strategy: str = ""
    new_locator: str = ""
    confidence: float = 0.0
    rationale: str = ""
    raw_response: str = ""


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


def _build_taxonomy_hint() -> str:
    lines: list[str] = []
    for fam_code, fam_name in FAMILIES.items():
        tax_list = TAXONOMIES.get(fam_code, [])
        lines.append(f"  {fam_code} ({fam_name}): {', '.join(tax_list[:5])}")
    return "\n".join(lines)


def _truncate_dom(dom: str, max_chars: int = 3000) -> str:
    if len(dom) <= max_chars:
        return dom
    half = max_chars // 2
    return dom[:half] + "\n... [TRUNCATED] ...\n" + dom[-half:]


MAX_PROMPT_CHARS = 2400


def _build_prompt(payload: EvidencePayload, error_message: str, family: str = "") -> str:
    dom_snippet = _truncate_dom(payload.dom_snapshot)
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


def _extract_json(text: str) -> Optional[str]:
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

    proposal = LLMHealingProposal(
        taxonomy_id=taxonomy_id,
        family=family,
        strategy=str(data.get("strategy", "")),
        new_locator=str(data.get("new_locator", "")),
        confidence=confidence,
        rationale=str(data.get("rationale", ""))[:300],
        raw_response=text,
    )

    if proposal.strategy not in ALLOWED_STRATEGIES:
        proposal.confidence = 0.0

    if family not in FAMILIES or taxonomy_id not in TAXONOMIES.get(family, []):
        proposal.confidence = 0.0

    return proposal


class LLMHealer:
    def __init__(
        self,
        api_key: str = "",
        azure_endpoint: str = "",
        model: str = "gpt-4.1-mini",
        temperature: float = 0.3,
        max_retries: int = 3,
        config: Optional[LLMConfig] = None,
    ):
        if config is not None:
            api_key = config.api_key
            azure_endpoint = config.azure_endpoint
            model = config.model
            temperature = config.temperature
            max_retries = config.max_retries
        self._api_key = api_key
        self._azure_endpoint = azure_endpoint
        self._model = model
        self._temperature = temperature
        self._max_retries = max_retries
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AzureOpenAI
                self._client = AzureOpenAI(
                    api_key=self._api_key,
                    api_version="2024-08-01-preview",
                    azure_endpoint=self._azure_endpoint,
                )
            except ImportError:
                raise LLMUnavailableError("openai SDK não instalado. pip install openai>=1.0.0")
            except Exception as e:
                raise LLMUnavailableError(f"Falha ao criar AzureOpenAI client: {e}")
        return self._client

    def heal(
        self,
        payload: EvidencePayload,
        error_message: str = "",
        family: str = "",
    ) -> LLMHealingProposal:
        prompt = _build_prompt(payload, error_message, family=family)

        last_error: Optional[Exception] = None
        for attempt in range(self._max_retries):
            try:
                client = self._get_client()
                response = client.chat.completions.create(
                    model=self._model,
                    temperature=self._temperature,
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = response.choices[0].message.content or ""
                proposal = _parse_response(text)
                if proposal is None:
                    return LLMHealingProposal(
                        confidence=0.0,
                        rationale="Falha ao parsear resposta do LLM",
                        raw_response=text,
                    )
                return proposal

            except LLMUnavailableError:
                raise
            except Exception as e:
                status_code = getattr(e, 'status_code', None) or getattr(e, 'http_status', None)
                if status_code == 429 and attempt < self._max_retries - 1:
                    wait = 2 ** attempt
                    time.sleep(wait)
                    last_error = e
                    continue
                last_error = e
                if attempt < self._max_retries - 1:
                    time.sleep(2 ** attempt)

        raise LLMUnavailableError(f"LLM falhou apos {self._max_retries} tentativas: {last_error}")

    def heal_or_unresolved(
        self,
        payload: EvidencePayload,
        error_message: str = "",
        family: str = "",
    ) -> LLMHealingProposal:
        try:
            return self.heal(payload, error_message, family=family)
        except LLMUnavailableError:
            return LLMHealingProposal(
                confidence=0.0,
                rationale="LLM unavailable",
            )
        except Exception as e:
            return LLMHealingProposal(
                confidence=0.0,
                rationale=f"Erro inesperado no healer: {e}",
            )


class MockLLMHealer(LLMHealer):
    def heal(
        self,
        payload: EvidencePayload,
        error_message: str = "",
        family: str = "",
    ) -> LLMHealingProposal:
        ctx = payload.step_context
        sel = ctx.get("selector", "")
        return LLMHealingProposal(
            taxonomy_id="SEL-004",
            family="FAM-01",
            strategy="semantic_locator_conversion",
            new_locator=f"page.get_by_text('{ctx.get('text', 'example')}')",
            confidence=0.85,
            rationale="Mock: fallback para has-text",
            raw_response='{"taxonomy_id":"SEL-004","family":"FAM-01","strategy":"semantic_locator_conversion","new_locator":"page.get_by_text(\'example\')","confidence":0.85,"rationale":"Mock"}',
        )
