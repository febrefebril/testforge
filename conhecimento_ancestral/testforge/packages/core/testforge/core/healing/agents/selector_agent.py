from __future__ import annotations

import json
from typing import Optional

from testforge.core.healing.agents import SpecialistAgent
from testforge.core.healing.collector import EvidencePayload
from testforge.core.healing.llm.healer import LLMHealingProposal


ARIA_ROLE_MAP: dict[str, str] = {
    "button": "button",
    "a": "link",
    "select": "combobox",
    "input": "textbox",
    "input_checkbox": "checkbox",
    "input_radio": "radio",
    "input_range": "slider",
}


def _safe(val: str) -> str:
    val = val.replace("\\", "\\\\")
    return val.replace("'", "\\'")


class SelectorAgent(SpecialistAgent):
    def _build_context(self, payload: EvidencePayload) -> dict:
        ctx = payload.step_context
        parents = []
        dom = payload.dom_snapshot or ""
        lines = dom.split("\n")
        depth = 0
        for line in lines:
            if depth >= 3:
                break
            stripped = line.strip()
            if stripped.startswith("<") and not stripped.startswith("</"):
                parents.append(stripped[:120])
                depth += 1
        return {
            "tag": ctx.get("tag_name", ""),
            "id": ctx.get("id", ""),
            "class": ctx.get("class_name", ""),
            "name": ctx.get("name", ""),
            "data_testid": ctx.get("data_testid", ""),
            "aria_label": ctx.get("aria_label", ""),
            "placeholder": ctx.get("placeholder", ""),
            "href": ctx.get("href", ""),
            "text": ctx.get("text", ""),
            "attributes": {
                k: v for k, v in ctx.items()
                if k.startswith("attr_")
            },
            "parents": parents,
            "selector": ctx.get("selector", ""),
            "action": ctx.get("action", ""),
            "input_type": ctx.get("input_type", ""),
        }

    def _build_prompt(self, payload: EvidencePayload, error_message: str) -> str:
        ctx = payload.step_context
        context = self._build_context(payload)
        return (
            f"Analyze selector failure. Error: {error_message[:300]}\n"
            f"Original selector: {ctx.get('selector', '')}\n"
            f"Tag: {context['tag']} ID: {context['id']} Class: {context['class']}\n"
            f"Name: {context['name']} data-testid: {context['data_testid']}\n"
            f"aria-label: {context['aria_label']} placeholder: {context['placeholder']}\n"
            f"href: {context['href']} Text: {context['text']}\n"
            f"Parents: {' > '.join(context['parents'])}\n"
            f"Action: {context['action']}\n"
            f"DOM snippet: {payload.dom_snapshot[:600]}\n"
            f"Propose new locator (priority: data-testid > id > name > aria-label > placeholder > has-text > href > alt > class > XPath).\n"
            + self._response_format()
        )

    def heal(
        self,
        payload: EvidencePayload,
        error_message: str = "",
    ) -> LLMHealingProposal:
        context = self._build_context(payload)
        sel = context["selector"]
        text = context["text"]
        tag = context["tag"]
        data_testid = context["data_testid"]
        elem_id = context["id"]
        name = context["name"]
        aria_label = context["aria_label"]
        placeholder = context["placeholder"]
        href = context["href"]
        input_type = context["input_type"]

        safe_text = _safe(text) if text else ""
        safe_sel = _safe(sel) if sel else ""

        if data_testid:
            return LLMHealingProposal(
                taxonomy_id="SEL-003",
                family="FAM-01",
                strategy="semantic_locator_conversion",
                new_locator=f"[data-testid='{_safe(data_testid)}']",
                confidence=0.9,
                rationale=f"Usar data-testid: '{data_testid}'",
                raw_response=json.dumps({
                    "taxonomy_id": "SEL-003",
                    "family": "FAM-01",
                    "strategy": "semantic_locator_conversion",
                    "new_locator": f"[data-testid='{data_testid}']",
                    "confidence": 0.9,
                    "rationale": "Usar data-testid",
                }),
            )

        if elem_id:
            return LLMHealingProposal(
                taxonomy_id="SEL-002",
                family="FAM-01",
                strategy="semantic_locator_conversion",
                new_locator=f"#{_safe(elem_id)}",
                confidence=0.85,
                rationale=f"Usar ID do elemento: '{elem_id}'",
            )

        if name:
            return LLMHealingProposal(
                taxonomy_id="SEL-005",
                family="FAM-01",
                strategy="semantic_locator_conversion",
                new_locator=f"[name='{_safe(name)}']",
                confidence=0.8,
                rationale=f"Usar atributo name: '{name}'",
            )

        if aria_label:
            return LLMHealingProposal(
                taxonomy_id="SEL-006",
                family="FAM-01",
                strategy="semantic_locator_conversion",
                new_locator=f"[aria-label='{_safe(aria_label)}']",
                confidence=0.8,
                rationale=f"Usar aria-label: '{aria_label}'",
            )

        if placeholder:
            return LLMHealingProposal(
                taxonomy_id="SEL-007",
                family="FAM-01",
                strategy="semantic_locator_conversion",
                new_locator=f"[placeholder='{_safe(placeholder)}']",
                confidence=0.8,
                rationale=f"Usar placeholder: '{placeholder}'",
            )

        if sel.startswith("/") or sel.startswith("("):
            strat = "has_text_fallback" if text else "xpath_fallback"
            locator = f"text={safe_text}" if text else f"//{safe_sel.lstrip('/')}"
            return LLMHealingProposal(
                taxonomy_id="SEL-009",
                family="FAM-01",
                strategy=strat,
                new_locator=locator,
                confidence=0.75,
                rationale=f"XPath substituido por {'has-text' if text else 'locator'}",
                raw_response=json.dumps({
                    "taxonomy_id": "SEL-009",
                    "family": "FAM-01",
                    "strategy": strat,
                    "new_locator": locator,
                    "confidence": 0.75,
                    "rationale": "XPath substituido",
                }),
            )

        if text:
            return LLMHealingProposal(
                taxonomy_id="SEL-004",
                family="FAM-01",
                strategy="semantic_locator_conversion",
                new_locator=f"text={safe_text}",
                confidence=0.85,
                rationale=f"Fallback para has-text com '{text}'",
                raw_response=json.dumps({
                    "taxonomy_id": "SEL-004",
                    "family": "FAM-01",
                    "strategy": "semantic_locator_conversion",
                    "new_locator": f"text={safe_text}",
                    "confidence": 0.85,
                    "rationale": "Fallback has-text",
                }),
            )

        if href:
            return LLMHealingProposal(
                taxonomy_id="SEL-008",
                family="FAM-01",
                strategy="semantic_locator_conversion",
                new_locator=f"[href='{_safe(href)}']",
                confidence=0.75,
                rationale=f"Usar href: '{href}'",
            )

        if tag in ("button", "a", "input", "select"):
            role_key = f"{tag}_{input_type}" if tag == "input" and input_type else tag
            role = ARIA_ROLE_MAP.get(role_key) or ARIA_ROLE_MAP.get(tag, "generic")
            if safe_text:
                new_locator = f"{tag}:has-text('{safe_text}')" if tag in ("button", "a") else f"[role='{role}']"
            else:
                new_locator = tag
            return LLMHealingProposal(
                taxonomy_id="SEL-001",
                family="FAM-01",
                strategy="semantic_locator_conversion",
                new_locator=new_locator,
                confidence=0.7,
                rationale=f"Fallback para tag '{tag}' role '{role}'",
            )

        fb = self._llm_fallback(payload, error_message)
        if fb and fb.confidence >= 0.5:
            return fb
        return LLMHealingProposal(
            taxonomy_id="SEL-001",
            family="FAM-01",
            strategy="semantic_locator_conversion",
            new_locator=safe_sel if safe_sel.startswith(".") or safe_sel.startswith("#") else f".{safe_sel}",
            confidence=0.6,
            rationale=f"Tentativa com locator padrao: {sel}",
        )

    def _response_format(self) -> str:
        return (
            "Respond JSON: "
            '{"taxonomy_id":"SEL-00X","family":"FAM-01","strategy":"semantic_locator_conversion|has_text_fallback|xpath_fallback",'
            '"new_locator":"...","confidence":0.0-1.0,"rationale":"..."}'
        )
