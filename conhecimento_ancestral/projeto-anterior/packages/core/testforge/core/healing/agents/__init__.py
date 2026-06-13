from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from testforge.core.healing.collector import EvidencePayload
from testforge.core.healing.llm.healer import LLMHealer, LLMHealingProposal, MockLLMHealer
from testforge.core.healing.storage import HealingCatalog


FAMILY_AGENT_MAP: dict[str, str] = {
    "FAM-01": "selector",
    "FAM-02": "timing",
    "FAM-03": "context",
    "FAM-04": "state",
    "FAM-05": "dynamic_dom",
    "FAM-06": "input",
    "FAM-07": "input",
}


class SpecialistAgent(ABC):
    def __init__(
        self,
        catalog: Optional[HealingCatalog] = None,
        llm_config: Optional[Any] = None,
        llm_healer: Optional[LLMHealer] = None,
    ):
        self._catalog = catalog
        self._llm_config = llm_config
        self._llm_healer = llm_healer

    @abstractmethod
    def heal(
        self,
        payload: EvidencePayload,
        error_message: str = "",
    ) -> LLMHealingProposal:
        ...

    def _llm_fallback(
        self,
        payload: EvidencePayload,
        error_message: str,
    ) -> Optional[LLMHealingProposal]:
        if not self._llm_healer:
            return None
        prompt = self._build_prompt(payload, error_message)
        return self._llm_healer.heal_or_unresolved(payload, error_message)

    def _validate_proposal(
        self,
        proposal: LLMHealingProposal,
        page=None,
    ) -> bool:
        if page is None:
            return proposal.confidence >= 0.5 and bool(proposal.new_locator)
        try:
            count = page.locator(proposal.new_locator).count()
            return count > 0
        except Exception:
            return False


class MockSelectorAgent(SpecialistAgent):
    def heal(
        self,
        payload: EvidencePayload,
        error_message: str = "",
    ) -> LLMHealingProposal:
        return LLMHealingProposal(
            taxonomy_id="SEL-004",
            family="FAM-01",
            strategy="semantic_locator_conversion",
            new_locator="get_by_text('Salvar')",
            confidence=0.85,
            rationale="Mock: has-text fallback para seletor fragil",
        )


class MockTimingAgent(SpecialistAgent):
    def heal(
        self,
        payload: EvidencePayload,
        error_message: str = "",
    ) -> LLMHealingProposal:
        has_network = any("ERR_" in c.get("text", "") for c in payload.console_errors)
        if has_network:
            return LLMHealingProposal(
                taxonomy_id="TIM-003",
                family="FAM-02",
                strategy="network_idle",
                new_locator="wait_for_load_state('networkidle')",
                confidence=0.8,
                rationale="Mock: network idle apos erro de rede",
            )
        return LLMHealingProposal(
            taxonomy_id="TIM-001",
            family="FAM-02",
            strategy="visibility_wait",
            new_locator="wait_for_selector(state='visible')",
            confidence=0.85,
            rationale="Mock: aguardar visibilidade",
        )


class MockInputAgent(SpecialistAgent):
    def heal(
        self,
        payload: EvidencePayload,
        error_message: str = "",
    ) -> LLMHealingProposal:
        return LLMHealingProposal(
            taxonomy_id="INP-001",
            family="FAM-06",
            strategy="press_sequentially",
            new_locator="press_sequentially('valor')",
            confidence=0.85,
            rationale="Mock: pressSequentially apos fill falhar",
        )


class MockContextAgent(SpecialistAgent):
    def heal(
        self,
        payload: EvidencePayload,
        error_message: str = "",
    ) -> LLMHealingProposal:
        return LLMHealingProposal(
            taxonomy_id="CTX-001",
            family="FAM-03",
            strategy="iframe_switch",
            new_locator="frame_locator('iframe').locator(...)",
            confidence=0.85,
            rationale="Mock: iframe switch",
        )


class MockStateAgent(SpecialistAgent):
    def heal(
        self,
        payload: EvidencePayload,
        error_message: str = "",
    ) -> LLMHealingProposal:
        return LLMHealingProposal(
            taxonomy_id="STA-004",
            family="FAM-04",
            strategy="dialog_handler",
            new_locator="page.on('dialog', lambda d: d.accept())",
            confidence=0.9,
            rationale="Mock: dialog auto-accept",
        )


def route_to_agent(
    family: str,
    catalog: Optional[HealingCatalog] = None,
    llm_healer: Optional[LLMHealer] = None,
) -> Optional[SpecialistAgent]:
    agent_key = FAMILY_AGENT_MAP.get(family)
    if agent_key is None:
        return None
    if agent_key == "selector":
        from testforge.core.healing.agents.selector_agent import SelectorAgent
        return SelectorAgent(catalog, llm_healer=llm_healer)
    if agent_key == "timing":
        from testforge.core.healing.agents.timing_agent import TimingAgent
        return TimingAgent(catalog, llm_healer=llm_healer)
    if agent_key == "input":
        from testforge.core.healing.agents.input_agent import InputAgent
        return InputAgent(catalog, llm_healer=llm_healer)
    if agent_key == "context":
        from testforge.core.healing.agents.context_agent import ContextAgent
        return ContextAgent(catalog, llm_healer=llm_healer)
    if agent_key == "state":
        from testforge.core.healing.agents.state_agent import StateAgent
        return StateAgent(catalog, llm_healer=llm_healer)
    if agent_key == "dynamic_dom":
        from testforge.core.healing.agents.dynamic_dom_agent import DynamicDOMAgent
        return DynamicDOMAgent(catalog, llm_healer=llm_healer)
    return None


__all__ = [
    "SpecialistAgent",
    "MockSelectorAgent",
    "MockTimingAgent",
    "MockInputAgent",
    "MockContextAgent",
    "MockStateAgent",
    "route_to_agent",
    "FAMILY_AGENT_MAP",
]
