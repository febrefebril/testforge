"""TestForge — L2 Specialist Agents.

Family-specific deterministic healers with LLM fallback.
Each agent handles one taxonomy family with rule-based strategies.
When deterministic confidence < 0.7, falls back to LLMHealer.

Agent routing:
  FAM-01 → SelectorAgent   (selector fallback chain)
  FAM-02 → TimingAgent     (network idle, visibility wait)
  FAM-03 → ContextAgent    (iframe, shadow DOM, popup)
  FAM-04 → StateAgent      (dialog, overlay, session)
  FAM-05 → DynamicDOMAgent (stale element, reorder, lazy load)
  FAM-06 → InputAgent      (pressSequentially, native setter)
  FAM-07 → InputAgent      (file upload/download)
"""
from __future__ import annotations

from typing import Optional

from ..evidence_payload import EvidencePayload
from ..llm_healer import LLMHealer, LLMHealingProposal, MockLLMHealer
from .selector_agent import SelectorAgent
from .timing_agent import TimingAgent
from .context_agent import ContextAgent
from .state_agent import StateAgent
from .dynamic_dom_agent import DynamicDOMAgent
from .input_agent import InputAgent

FAMILY_AGENT_MAP: dict[str, type] = {
    "FAM-01": SelectorAgent,
    "FAM-02": TimingAgent,
    "FAM-03": ContextAgent,
    "FAM-04": StateAgent,
    "FAM-05": DynamicDOMAgent,
    "FAM-06": InputAgent,
    "FAM-07": InputAgent,
}


def route_to_agent(
    family: str,
    llm_healer: Optional[LLMHealer] = None,
) -> Optional[object]:
    """Route failure family to appropriate specialist agent.

    Returns None for families without agents (FAM-08 asserts, FAM-09 recorder,
    FAM-10 execution, FAM-11 browser limits — fall through to L3).
    """
    agent_cls = FAMILY_AGENT_MAP.get(family)
    if agent_cls is None:
        return None
    healer = llm_healer or MockLLMHealer()
    return agent_cls(llm_healer=healer)


__all__ = [
    "SelectorAgent", "TimingAgent", "ContextAgent",
    "StateAgent", "DynamicDOMAgent", "InputAgent",
    "FAMILY_AGENT_MAP", "route_to_agent",
]
