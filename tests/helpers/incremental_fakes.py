"""TestForge — Fakes para testes do IncrementalRunner."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FakeCandidate:
    selector: str
    score: float = 1.0


@dataclass
class FakeTarget:
    candidates: list = field(default_factory=list)
    text: str = ""
    label: str = ""
    accessible_name: str = ""
    tag: str = ""
    name: str = ""
    placeholder: str = ""


@dataclass
class FakeStep:
    action: str
    value: str = ""
    target: Optional[FakeTarget] = None
    context: dict = field(default_factory=dict)
    depends_on: str = ""
    blocking: bool = False
    skip_reason: str = ""
    url: str = ""


def make_fake_step(action="click", selector="#btn", text="", value="",
                   tag="", context=None, blocking=False, depends_on=""):
    cands = [FakeCandidate(selector=selector)] if selector else []
    target = FakeTarget(candidates=cands, text=text, label=text, tag=tag)
    return FakeStep(
        action=action, value=value, target=target,
        context=context or {}, blocking=blocking, depends_on=depends_on,
    )


@dataclass
class FakePostconditionResult:
    passed: bool
    message: str = ""
    failures: list = field(default_factory=list)
    oracle_results: list = field(default_factory=list)
    checks: dict = field(default_factory=dict)


class FakePostconditionValidator:
    def __init__(self, passed: bool, message: str = "", failures=None):
        self._passed = passed
        self._message = message
        self._failures = failures or []

    def validate(self, step, page=None, next_step=None, url_before=""):
        return FakePostconditionResult(
            passed=self._passed,
            message=self._message,
            failures=list(self._failures),
        )


@dataclass
class FakeProposal:
    new_locator: str = ""
    strategy: str = ""
    confidence: float = 0.0
    family: str = ""
    taxonomy_id: str = ""
    rationale: str = ""
    raw_response: str = ""


@dataclass
class FakeOutcome:
    status: str = ""
    layer_used: str = ""
    family: str = ""
    taxonomy_id: str = ""
    error_message: str = ""
    proposal: Optional[FakeProposal] = None
    entry_id: str = ""


def make_fake_outcome(status="PASSED_STEP", layer_used="L2", strategy="has_text_fallback",
                     new_locator="text=Pesquisar", confidence=0.85,
                     family="FAM-01", taxonomy_id="SEL-004"):
    proposal = FakeProposal(
        new_locator=new_locator, strategy=strategy, confidence=confidence,
        family=family, taxonomy_id=taxonomy_id,
    )
    return FakeOutcome(
        status=status, layer_used=layer_used, family=family,
        taxonomy_id=taxonomy_id, proposal=proposal,
    )