from testforge.semantic.model import SemanticAction, SemanticTarget


def make_semantic_action(action: str = "click", target_candidates=None, value: str = "") -> SemanticAction:
    candidates = target_candidates or []
    target = SemanticTarget(candidates=candidates)
    return SemanticAction(action=action, target=target, value=value)
