from testforge.healing.agents.input_agent import InputAgent
from testforge.healing.agents.state_agent import StateAgent
from testforge.healing.evidence_payload import EvidencePayload


def _payload(dom_snapshot: str = "", has_dialog_handler: bool = False) -> EvidencePayload:
    return EvidencePayload(
        step_context={"selector": "#target", "action": "click", "value": ""},
        page_state={"has_dialog_handler": has_dialog_handler},
        dom_snapshot=dom_snapshot,
    )


def test_state_agent_requires_dom_evidence_for_dialog_strategy():
    agent = StateAgent()

    cases = [
        ("dialog blocked", "", False, 0.4),
        ("dialog is open", '<div role="dialog">modal</div>', False, 0.85),
        ("network dialog broken", "", False, 0.4),
        ("confirm required", "", True, 0.85),
    ]

    for error_msg, dom_snapshot, has_handler, expected_confidence in cases:
        payload = _payload(dom_snapshot=dom_snapshot, has_dialog_handler=has_handler)
        proposal = agent.heal(payload, error_msg)
        assert proposal is not None
        assert proposal.strategy == "dialog_handler"
        assert proposal.confidence == expected_confidence


def test_input_agent_requires_mask_attrs_for_mask_strategy():
    agent = InputAgent()

    cases = [
        ("fill failed", "<input type='text' />", 0.35),
        ("masked input rejected", "<input currencymask='true' />", 0.82),
        ("not editable", "<input data-mask='##/##/####' />", 0.82),
        ("fill error", "<div></div>", 0.35),
    ]

    for error_msg, dom_snapshot, expected_confidence in cases:
        payload = _payload(dom_snapshot=dom_snapshot)
        proposal = agent.heal(payload, error_msg)
        assert proposal is not None
        assert proposal.strategy == "press_sequentially"
        assert proposal.confidence == expected_confidence


def test_dom_introspection_helpers_support_payload_page_state():
    payload = _payload(dom_snapshot="", has_dialog_handler=True)
    proposal = StateAgent().heal(payload, "dialog is open")
    assert proposal is not None
    assert proposal.confidence == 0.85
