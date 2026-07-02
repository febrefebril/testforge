from testforge.semantic.model import LocatorCandidate


def make_candidate(strategy: str = "role", selector: str = 'role=button[name="Salvar"]', score: float = 0.9, reason: str = "factory") -> dict:
    """Factory returning candidate dict compatible with runtime resolver."""
    call = selector
    if selector.startswith("role="):
        call = 'get_by_role("button", name="Salvar")'
    return {
        "strategy": strategy,
        "selector": selector,
        "score": score,
        "reason": reason,
        "playwright_call": call,
    }


def make_candidate_obj(strategy: str = "role", selector: str = 'role=button[name="Salvar"]', score: float = 0.9, reason: str = "factory") -> LocatorCandidate:
    return LocatorCandidate(strategy=strategy, selector=selector, score=score, reason=reason)
