
from testforge.semantic.model import SemanticAction, SemanticTarget
from testforge.semantic.recording_normalizer import _same_target


class _LegacyStep:
    def __init__(self, target):
        self.target = target


def test_same_target_accepts_semantic_target_by_element_id():
    current = SemanticAction(action="assert", target=SemanticTarget(element_id="campo-simulador"))
    next_step = SemanticAction(action="click", target=SemanticTarget(element_id="campo-simulador"))
    assert _same_target(current, next_step) is True


def test_same_target_accepts_legacy_dict_target_by_css_path():
    current = _LegacyStep({"css_path": "body main form input:nth-child(1)"})
    next_step = _LegacyStep({"css_path": "body main form input:nth-child(1)"})
    assert _same_target(current, next_step) is True


def test_same_target_returns_false_for_different_semantic_targets():
    current = SemanticAction(action="assert", target=SemanticTarget(element_id="campo-a"))
    next_step = SemanticAction(action="click", target=SemanticTarget(element_id="campo-b"))
    assert _same_target(current, next_step) is False

