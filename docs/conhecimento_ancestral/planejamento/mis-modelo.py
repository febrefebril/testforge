from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ActionType(str, Enum):
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    CHECK = "check"
    ASSERT = "assert"


class LocatorStrategy(str, Enum):
    ROLE = "role"
    LABEL = "label"
    PLACEHOLDER = "placeholder"
    TEST_ID = "test_id"
    TEXT = "text"
    CSS = "css"
    XPATH = "xpath"


@dataclass
class DomFingerprint:
    tag: Optional[str] = None
    normalized_path_hash: Optional[str] = None
    sibling_index: Optional[int] = None
    bounding_box: dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticTarget:
    role: Optional[str] = None
    accessible_name: Optional[str] = None
    label: Optional[str] = None
    placeholder: Optional[str] = None
    visible_text: Optional[str] = None
    test_id: Optional[str] = None
    attributes: dict[str, Any] = field(default_factory=dict)
    dom_fingerprint: DomFingerprint = field(default_factory=DomFingerprint)


@dataclass
class ActionContext:
    page_url_pattern: Optional[str] = None
    page_title: Optional[str] = None
    frame: Optional[str] = None
    shadow_dom: bool = False
    nearby_texts: list[str] = field(default_factory=list)


@dataclass
class LocatorCandidate:
    strategy: LocatorStrategy
    value: str
    playwright: str
    score: float
    reason: str


@dataclass
class SemanticAction:
    action_id: str
    intent: str
    action: ActionType
    target: SemanticTarget
    context: ActionContext
    locator_candidates: list[LocatorCandidate] = field(default_factory=list)
    input_value: Optional[str] = None
    expected_after_action: list[dict[str, Any]] = field(default_factory=list)

    def best_candidate(self) -> LocatorCandidate:
        if not self.locator_candidates:
            raise ValueError(f"Ação {self.action_id} não possui candidatos de locator.")
        return sorted(self.locator_candidates, key=lambda c: c.score, reverse=True)[0]


class LocatorCandidateGenerator:
    def generate(self, target: SemanticTarget) -> list[LocatorCandidate]:
        candidates: list[LocatorCandidate] = []

        if target.role and target.accessible_name:
            candidates.append(
                LocatorCandidate(
                    strategy=LocatorStrategy.ROLE,
                    value=f"{target.role}[name='{target.accessible_name}']",
                    playwright=f"page.get_by_role('{target.role}', name='{target.accessible_name}')",
                    score=0.95,
                    reason="Role e accessible name são sinais semânticos fortes.",
                )
            )

        if target.label:
            candidates.append(
                LocatorCandidate(
                    strategy=LocatorStrategy.LABEL,
                    value=target.label,
                    playwright=f"page.get_by_label('{target.label}')",
                    score=0.94,
                    reason="Label é um contrato próximo da percepção do usuário.",
                )
            )

        if target.test_id:
            candidates.append(
                LocatorCandidate(
                    strategy=LocatorStrategy.TEST_ID,
                    value=target.test_id,
                    playwright=f"page.get_by_test_id('{target.test_id}')",
                    score=0.90,
                    reason="Test id é estável quando definido como contrato de automação.",
                )
            )

        if target.visible_text:
            candidates.append(
                LocatorCandidate(
                    strategy=LocatorStrategy.TEXT,
                    value=target.visible_text,
                    playwright=f"page.get_by_text('{target.visible_text}')",
                    score=0.78,
                    reason="Texto visível é útil, mas pode ser ambíguo.",
                )
            )

        return sorted(candidates, key=lambda c: c.score, reverse=True)


class PlaywrightPythonCompiler:
    def compile_action(self, action: SemanticAction) -> str:
        locator = action.best_candidate().playwright

        if action.action == ActionType.CLICK:
            return f"await {locator}.click()"

        if action.action == ActionType.FILL:
            if action.input_value is None:
                raise ValueError(f"Ação {action.action_id} é fill, mas não possui input_value.")
            return f"await {locator}.fill({action.input_value!r})"

        raise NotImplementedError(f"Ação não suportada: {action.action}")
