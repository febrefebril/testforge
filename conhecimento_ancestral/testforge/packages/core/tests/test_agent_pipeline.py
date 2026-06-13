from __future__ import annotations

import pytest

from testforge.core.healing.agents import (
    FAMILY_AGENT_MAP,
    SpecialistAgent,
    route_to_agent,
)
from testforge.core.healing.agents.selector_agent import SelectorAgent
from testforge.core.healing.agents.timing_agent import TimingAgent
from testforge.core.healing.agents.input_agent import InputAgent
from testforge.core.healing.agents.context_agent import ContextAgent
from testforge.core.healing.agents.state_agent import StateAgent
from testforge.core.healing.agents.dynamic_dom_agent import DynamicDOMAgent
from testforge.core.healing.collector import EvidencePayload
from testforge.core.healing.curator import CuradorAutomatico, ProgressResult


def make_payload(**overrides) -> EvidencePayload:
    return EvidencePayload(
        dom_snapshot=overrides.get("dom", "<html><body><button>OK</button></body></html>"),
        step_context={
            "action": overrides.get("action", "click"),
            "selector": overrides.get("selector", "#btn"),
            "value": overrides.get("value", ""),
            "tag_name": overrides.get("tag", "button"),
            "text": overrides.get("text", "OK"),
            "url": "http://example.com",
            "page_title": "Test",
        },
        console_errors=overrides.get("console", []),
        network_state=overrides.get("network", []),
        page_url="http://example.com",
        failure_signature="test",
        collected_at="2026-01-01T00:00:00",
    )


class TestRouteToAgent:
    def test_selector_agent(self):
        agent = route_to_agent("FAM-01")
        assert isinstance(agent, SelectorAgent)

    def test_timing_agent(self):
        agent = route_to_agent("FAM-02")
        assert isinstance(agent, TimingAgent)

    def test_dynamic_dom_agent(self):
        agent = route_to_agent("FAM-05")
        assert isinstance(agent, DynamicDOMAgent)

    def test_input_agent(self):
        agent = route_to_agent("FAM-06")
        assert isinstance(agent, InputAgent)

    def test_input_agent_for_file(self):
        agent = route_to_agent("FAM-07")
        assert isinstance(agent, InputAgent)

    def test_context_agent(self):
        agent = route_to_agent("FAM-03")
        assert isinstance(agent, ContextAgent)

    def test_state_agent(self):
        agent = route_to_agent("FAM-04")
        assert isinstance(agent, StateAgent)

    def test_unknown_family(self):
        assert route_to_agent("FAM-99") is None
        assert route_to_agent("") is None

    def test_all_families_mapped(self):
        from testforge.core.healing.models import FAMILIES
        for fam in FAMILIES:
            if fam in ("FAM-08", "FAM-09", "FAM-10", "FAM-11"):
                assert route_to_agent(fam) is None
            elif fam == "FAM-05":
                assert isinstance(route_to_agent(fam), DynamicDOMAgent)
            else:
                assert route_to_agent(fam) is not None, f"{fam} not mapped"


class MockCatalog:
    def __init__(self):
        self.entries = []
        self._failure_counts: dict[str, int] = {}

    def add(self, entry):
        self.entries.append(entry)
        return entry.id

    def match(self, family, symptom):
        return None

    def get(self, entry_id):
        for e in self.entries:
            if e.id == entry_id:
                return e
        return None

    def get_failure_count(self, taxonomy_id: str) -> int:
        return self._failure_counts.get(taxonomy_id, 0)

    def increment_failure_count(self, taxonomy_id: str) -> int:
        current = self._failure_counts.get(taxonomy_id, 0)
        self._failure_counts[taxonomy_id] = current + 1
        return self._failure_counts[taxonomy_id]

    def reset_failure_count(self, taxonomy_id: str) -> None:
        self._failure_counts.pop(taxonomy_id, None)

    def list(self, **kwargs):
        return self.entries

    def update(self, entry_id, **kwargs):
        for e in self.entries:
            if e.id == entry_id:
                for k, v in kwargs.items():
                    setattr(e, k, v)
                return True
        return False


class TestSelectorAgent:
    def test_heal_with_text_returns_text_selector(self):
        agent = SelectorAgent()
        payload = make_payload(selector="#btn-salvar", text="Salvar")
        proposal = agent.heal(payload, "Timeout: strict locator")
        assert proposal.confidence >= 0.5
        assert proposal.new_locator == "text=Salvar"
        assert proposal.family == "FAM-01"
        assert proposal.strategy == "semantic_locator_conversion"

    def test_heal_with_xpath(self):
        agent = SelectorAgent()
        payload = make_payload(selector="//*[@id='x']", text="OK")
        proposal = agent.heal(payload, "multiple elements")
        assert proposal.confidence >= 0.5
        assert proposal.strategy == "has_text_fallback"

    def test_heal_without_text(self):
        agent = SelectorAgent()
        payload = make_payload(selector="#btn", text="", tag="div")
        proposal = agent.heal(payload, "erro seletor")
        assert proposal.confidence >= 0.5
        assert proposal.taxonomy_id == "SEL-001"


class TestTimingAgent:
    def test_heal_network_error(self):
        agent = TimingAgent()
        payload = make_payload(console=[{"text": "net::ERR_CONNECTION_REFUSED"}])
        proposal = agent.heal(payload, "net::ERR_CONNECTION_REFUSED")
        assert proposal.confidence >= 0.5
        assert proposal.strategy == "network_idle"

    def test_heal_stale_element(self):
        agent = TimingAgent()
        payload = make_payload()
        proposal = agent.heal(payload, "stale element reference")
        assert proposal.confidence >= 0.5
        assert proposal.strategy == "visibility_wait"

    def test_heal_loading(self):
        agent = TimingAgent()
        payload = make_payload()
        proposal = agent.heal(payload, "still loading")
        assert proposal.confidence >= 0.5
        assert proposal.strategy == "dom_content_loaded"

    def test_heal_generic(self):
        agent = TimingAgent()
        payload = make_payload()
        proposal = agent.heal(payload, "timeout")
        assert proposal.confidence >= 0.5


class TestInputAgent:
    def test_heal_fill_error(self):
        agent = InputAgent()
        payload = make_payload(value="joao@email.com")
        proposal = agent.heal(payload, "Element not editable")
        assert proposal.confidence >= 0.5
        assert proposal.strategy == "press_sequentially"

    def test_heal_file(self):
        agent = InputAgent()
        payload = make_payload(action="upload")
        proposal = agent.heal(payload, "file input error")
        assert proposal.confidence >= 0.5
        assert proposal.strategy == "file_chooser"

    def test_heal_masked(self):
        agent = InputAgent()
        payload = make_payload(value="123.456.789-00")
        proposal = agent.heal(payload, "masked input detection")
        assert proposal.confidence >= 0.5
        assert proposal.strategy == "masked_input_detection"


class TestContextAgent:
    def test_heal_iframe(self):
        agent = ContextAgent()
        payload = make_payload()
        proposal = agent.heal(payload, "iframe not found")
        assert proposal.confidence >= 0.5
        assert proposal.strategy == "iframe_switch"

    def test_heal_shadow_dom(self):
        agent = ContextAgent()
        payload = make_payload()
        proposal = agent.heal(payload, "shadow DOM access")
        assert proposal.confidence >= 0.5
        assert proposal.strategy == "shadow_dom_query"

    def test_heal_popup(self):
        agent = ContextAgent()
        payload = make_payload()
        proposal = agent.heal(payload, "cross-origin popup")
        assert proposal.confidence >= 0.5
        assert proposal.strategy == "popup_handler"


class TestStateAgent:
    def test_heal_dialog(self):
        agent = StateAgent()
        payload = make_payload()
        proposal = agent.heal(payload, "alert dialog detected")
        assert proposal.confidence >= 0.5
        assert proposal.strategy == "dialog_handler"

    def test_heal_overlay(self):
        agent = StateAgent()
        payload = make_payload()
        proposal = agent.heal(payload, "blocking overlay")
        assert proposal.confidence >= 0.5
        assert proposal.strategy == "overlay_wait"

    def test_heal_session(self):
        agent = StateAgent()
        payload = make_payload()
        proposal = agent.heal(payload, "session expired")
        assert proposal.confidence >= 0.5
        assert proposal.strategy == "state_restore"

    def test_heal_navigation(self):
        agent = StateAgent()
        payload = make_payload()
        proposal = agent.heal(payload, "navigation timeout")
        assert proposal.confidence >= 0.5
        assert proposal.strategy == "navigation_retry"


class TestLayer2Integration:
    def test_agent_called_when_family_known(self):
        catalog = MockCatalog()
        def step_runner(sd):
            pass
        curador = CuradorAutomatico(catalog=catalog, step_runner=step_runner)
        payload = make_payload(selector="#btn-salvar", text="Salvar")
        outcome = curador.cure(
            {"action": "click", "selector": "#btn-salvar", "text": "Salvar"},
            "strict locator timeout",
            payload,
        )
        assert outcome.status == ProgressResult.PASSED_STEP
        assert outcome.layer_used == "L2"

    def test_l2_skipped_when_no_family(self):
        catalog = MockCatalog()
        curador = CuradorAutomatico(catalog=catalog)
        payload = make_payload()
        outcome = curador.cure(
            {"action": "click", "selector": "#x"},
            "unknown error that doesn't match any pattern",
            payload,
        )
        assert outcome.status == ProgressResult.UNRESOLVED

    def test_l2_skipped_for_unmapped_family(self):
        catalog = MockCatalog()
        curador = CuradorAutomatico(catalog=catalog)
        payload = make_payload()
        outcome = curador.cure(
            {"action": "click", "selector": "#x"},
            "AssertionError: expected true but got false",
            payload,
        )
        assert outcome.status == ProgressResult.UNRESOLVED

    def test_all_agents_are_specialist_agent_subclass(self):
        for fam, key in FAMILY_AGENT_MAP.items():
            agent = route_to_agent(fam)
            assert isinstance(agent, SpecialistAgent), f"{fam} -> {key} not a SpecialistAgent"

    def test_route_to_agent_returns_none_for_non_agent_families(self):
        for fam in ("FAM-08", "FAM-09", "FAM-10", "FAM-11"):
            assert route_to_agent(fam) is None


class TestMockAgents:
    def test_mock_selector_agent(self):
        from testforge.core.healing.agents import MockSelectorAgent
        agent = MockSelectorAgent()
        payload = make_payload(text="Salvar")
        proposal = agent.heal(payload)
        assert proposal.confidence == 0.85
        assert "Salvar" in proposal.new_locator

    def test_mock_timing_agent(self):
        from testforge.core.healing.agents import MockTimingAgent
        agent = MockTimingAgent()
        payload = make_payload(console=[{"text": "net::ERR_TIMED_OUT"}])
        proposal = agent.heal(payload)
        assert proposal.confidence >= 0.5
        assert proposal.strategy == "network_idle"

    def test_mock_input_agent(self):
        from testforge.core.healing.agents import MockInputAgent
        agent = MockInputAgent()
        proposal = agent.heal(make_payload())
        assert proposal.confidence == 0.85
        assert proposal.strategy == "press_sequentially"

    def test_mock_context_agent(self):
        from testforge.core.healing.agents import MockContextAgent
        agent = MockContextAgent()
        proposal = agent.heal(make_payload())
        assert proposal.confidence == 0.85
        assert proposal.strategy == "iframe_switch"

    def test_mock_state_agent(self):
        from testforge.core.healing.agents import MockStateAgent
        agent = MockStateAgent()
        proposal = agent.heal(make_payload())
        assert proposal.confidence == 0.9
        assert proposal.strategy == "dialog_handler"

    def test_mock_agents_return_valid_proposal(self):
        from testforge.core.healing.agents import (
            MockSelectorAgent, MockTimingAgent, MockInputAgent,
            MockContextAgent, MockStateAgent,
        )
        payload = make_payload()
        for cls in (MockSelectorAgent, MockTimingAgent, MockInputAgent, MockContextAgent, MockStateAgent):
            proposal = cls().heal(payload)
            assert proposal.confidence >= 0.5
            assert proposal.family
            assert proposal.taxonomy_id
            assert proposal.new_locator


class TestBuildContext:
    def test_build_context_extracts_tag_and_text(self):
        agent = SelectorAgent()
        payload = make_payload(selector="#btn", text="Salvar", tag="button")
        ctx = agent._build_context(payload)
        assert ctx["tag"] == "button"
        assert ctx["text"] == "Salvar"
        assert ctx["selector"] == "#btn"

    def test_build_context_extracts_attributes(self):
        agent = SelectorAgent()
        payload = make_payload()
        payload.step_context["attr_type"] = "submit"
        payload.step_context["attr_disabled"] = "true"
        ctx = agent._build_context(payload)
        assert "attr_type" in ctx["attributes"]
        assert "attr_disabled" in ctx["attributes"]

    def test_build_context_parents_from_dom(self):
        agent = SelectorAgent()
        dom = "<html><body><div><button>OK</button></div></body></html>"
        payload = make_payload(dom=dom)
        ctx = agent._build_context(payload)
        assert len(ctx["parents"]) >= 1

    def test_build_context_data_testid_when_present(self):
        agent = SelectorAgent()
        payload = make_payload(selector="#btn", text="Salvar")
        payload.step_context["data_testid"] = "btn-salvar"
        ctx = agent._build_context(payload)
        assert ctx["data_testid"] == "btn-salvar"


class TestValidateProposal:
    def test_validate_without_page_checks_confidence_and_locator(self):
        agent = SelectorAgent()
        payload = make_payload(text="Salvar")
        proposal = agent.heal(payload)
        assert agent._validate_proposal(proposal) is True

    def test_validate_low_confidence_returns_false(self):
        from testforge.core.healing.llm.healer import LLMHealingProposal
        agent = SelectorAgent()
        proposal = LLMHealingProposal(
            taxonomy_id="SEL-001",
            family="FAM-01",
            strategy="xpath_fallback",
            new_locator="",
            confidence=0.3,
            rationale="baixa confianca",
        )
        assert agent._validate_proposal(proposal) is False


class TestSelectorAgentFallbacks:
    def test_data_testid_priority(self):
        agent = SelectorAgent()
        payload = make_payload(selector="#btn", text="Salvar", tag="button")
        payload.step_context["data_testid"] = "btn-salvar"
        proposal = agent.heal(payload)
        assert "[data-testid=" in proposal.new_locator
        assert proposal.confidence == 0.9

    def test_tag_fallback_when_no_text(self):
        agent = SelectorAgent()
        payload = make_payload(selector="#btn", text="", tag="button")
        proposal = agent.heal(payload)
        assert proposal.new_locator == "button"

    def test_tag_fallback_for_link_when_no_text(self):
        agent = SelectorAgent()
        payload = make_payload(selector="#lnk", text="", tag="a")
        proposal = agent.heal(payload)
        assert proposal.new_locator == "a"

    def test_text_higher_priority_than_tag(self):
        agent = SelectorAgent()
        payload = make_payload(selector="#btn", text="OK", tag="button")
        proposal = agent.heal(payload)
        assert proposal.new_locator == "text=OK"

    def test_text_selector_when_text_present(self):
        agent = SelectorAgent()
        payload = make_payload(selector=".class-name", text="Continuar", tag="span")
        proposal = agent.heal(payload)
        assert proposal.new_locator == "text=Continuar"
        assert proposal.strategy == "semantic_locator_conversion"

    def test_xpath_converts_to_has_text(self):
        agent = SelectorAgent()
        payload = make_payload(selector="//div[@class='x']", text="Proximo", tag="div")
        proposal = agent.heal(payload)
        assert proposal.strategy == "has_text_fallback"
