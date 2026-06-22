from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Callable
import re


class LocatorStrategy(str, Enum):
    ROLE = "role"
    LABEL = "label"
    PLACEHOLDER = "placeholder"
    TEST_ID = "test_id"
    TEXT = "text"
    CSS = "css"
    XPATH = "xpath"
    CONTEXTUAL = "contextual"


@dataclass
class SemanticTarget:
    role: Optional[str] = None
    accessible_name: Optional[str] = None
    label: Optional[str] = None
    placeholder: Optional[str] = None
    visible_text: Optional[str] = None
    test_id: Optional[str] = None
    attributes: dict[str, Any] = field(default_factory=dict)
    tag: Optional[str] = None


@dataclass
class ActionContext:
    page_url_pattern: Optional[str] = None
    page_title: Optional[str] = None
    nearby_texts: list[str] = field(default_factory=list)
    frame: Optional[str] = None
    shadow_dom: bool = False


@dataclass
class LocatorCandidate:
    strategy: LocatorStrategy
    value: str
    playwright_expr: str
    score: float = 0.0
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class LocatorCandidateGenerator:
    """Gera candidatos a partir de sinais semânticos e estruturais."""

    def generate(self, target: SemanticTarget, context: ActionContext) -> list[LocatorCandidate]:
        candidates: list[LocatorCandidate] = []

        if target.role and target.accessible_name:
            candidates.append(LocatorCandidate(
                strategy=LocatorStrategy.ROLE,
                value=f"{target.role}[name={target.accessible_name!r}]",
                playwright_expr=f"page.get_by_role({target.role!r}, name={target.accessible_name!r})",
                reason="Role + accessible name representam o elemento como o usuário o percebe.",
            ))

        if target.label:
            candidates.append(LocatorCandidate(
                strategy=LocatorStrategy.LABEL,
                value=target.label,
                playwright_expr=f"page.get_by_label({target.label!r})",
                reason="Label é forte para campos de formulário.",
            ))

        if target.placeholder:
            candidates.append(LocatorCandidate(
                strategy=LocatorStrategy.PLACEHOLDER,
                value=target.placeholder,
                playwright_expr=f"page.get_by_placeholder({target.placeholder!r})",
                reason="Placeholder é útil quando não há label adequada.",
            ))

        if target.test_id:
            candidates.append(LocatorCandidate(
                strategy=LocatorStrategy.TEST_ID,
                value=target.test_id,
                playwright_expr=f"page.get_by_test_id({target.test_id!r})",
                reason="Test id é forte quando definido como contrato estável de automação.",
            ))

        if target.visible_text:
            candidates.append(LocatorCandidate(
                strategy=LocatorStrategy.TEXT,
                value=target.visible_text,
                playwright_expr=f"page.get_by_text({target.visible_text!r})",
                reason="Texto visível é útil, mas pode ser ambíguo.",
            ))

        candidates.extend(self._attribute_candidates(target))
        candidates.extend(self._contextual_candidates(target, context))

        return candidates

    def _attribute_candidates(self, target: SemanticTarget) -> list[LocatorCandidate]:
        candidates: list[LocatorCandidate] = []
        tag = target.tag or "*"
        attrs = target.attributes or {}

        for attr in ["name", "aria-label", "title", "type"]:
            value = attrs.get(attr)
            if value and self._is_stable_value(str(value)):
                css = f'{tag}[{attr}="{value}"]'
                candidates.append(LocatorCandidate(
                    strategy=LocatorStrategy.CSS,
                    value=css,
                    playwright_expr=f"page.locator({css!r})",
                    reason=f"Atributo {attr} parece estável.",
                ))

        element_id = attrs.get("id")
        if element_id and self._is_stable_value(str(element_id)):
            css = f"#{element_id}"
            candidates.append(LocatorCandidate(
                strategy=LocatorStrategy.CSS,
                value=css,
                playwright_expr=f"page.locator({css!r})",
                reason="ID parece estável.",
            ))

        return candidates

    def _contextual_candidates(self, target: SemanticTarget, context: ActionContext) -> list[LocatorCandidate]:
        candidates: list[LocatorCandidate] = []
        if target.role and target.accessible_name and context.nearby_texts:
            anchor = context.nearby_texts[0]
            expr = (
                f"page.get_by_text({anchor!r})"
                f".locator('xpath=ancestor::*[self::form or self::section or self::div][1]')"
                f".get_by_role({target.role!r}, name={target.accessible_name!r})"
            )
            candidates.append(LocatorCandidate(
                strategy=LocatorStrategy.CONTEXTUAL,
                value=f"within_near_text:{anchor}:{target.role}:{target.accessible_name}",
                playwright_expr=expr,
                reason="Locator contextual restringe a busca a uma região próxima esperada.",
            ))
        return candidates

    def _is_stable_value(self, value: str) -> bool:
        unstable_patterns = [
            r"^[0-9a-f]{8,}$",        # hashes
            r"\d{4,}",              # números longos
            r"react-select-",         # exemplos comuns de ids gerados
            r"ember\d+",
            r"^ng-",
        ]
        return not any(re.search(pattern, value, re.IGNORECASE) for pattern in unstable_patterns)


class LocatorScorer:
    """Aplica ranking determinístico aos candidatos."""

    BASE_BY_STRATEGY = {
        LocatorStrategy.ROLE: 0.88,
        LocatorStrategy.LABEL: 0.90,
        LocatorStrategy.PLACEHOLDER: 0.78,
        LocatorStrategy.TEST_ID: 0.92,
        LocatorStrategy.TEXT: 0.72,
        LocatorStrategy.CSS: 0.58,
        LocatorStrategy.XPATH: 0.40,
        LocatorStrategy.CONTEXTUAL: 0.82,
    }

    def score(self, candidate: LocatorCandidate, runtime_probe: Optional[dict[str, Any]] = None) -> LocatorCandidate:
        runtime_probe = runtime_probe or {}
        score = self.BASE_BY_STRATEGY.get(candidate.strategy, 0.50)

        if runtime_probe.get("unique") is True:
            score += 0.08
        elif runtime_probe.get("match_count", 0) > 1:
            score -= 0.15

        if runtime_probe.get("actionable") is True:
            score += 0.05

        if runtime_probe.get("historical_success") is True:
            score += 0.05

        if self._looks_brittle(candidate.value):
            score -= 0.15

        candidate.score = round(max(0.0, min(1.0, score)), 4)
        return candidate

    def rank(self, candidates: list[LocatorCandidate], probe_fn: Optional[Callable[[LocatorCandidate], dict[str, Any]]] = None) -> list[LocatorCandidate]:
        scored = []
        for c in candidates:
            probe = probe_fn(c) if probe_fn else None
            scored.append(self.score(c, probe))
        return sorted(scored, key=lambda c: c.score, reverse=True)

    def _looks_brittle(self, value: str) -> bool:
        return any(token in value.lower() for token in ["nth-child", "/html/body", "//div[", "css-"])


class DeterministicFallbackRunner:
    """Executor conceitual. Integre os métodos _resolve, _action e _assertion com Playwright real."""

    def __init__(self, auto_threshold: float = 0.90, fallback_threshold: float = 0.75, weak_threshold: float = 0.60):
        self.auto_threshold = auto_threshold
        self.fallback_threshold = fallback_threshold
        self.weak_threshold = weak_threshold

    async def execute_with_fallback(self, action_name: str, candidates: list[LocatorCandidate], post_assertion: Optional[Callable[[], Any]] = None):
        failures = []
        usable = [c for c in candidates if c.score >= self.weak_threshold]

        for candidate in sorted(usable, key=lambda c: c.score, reverse=True):
            try:
                locator = await self._resolve(candidate)
                await self._check_unique(locator, candidate)
                await self._check_actionable(locator, candidate)
                await self._perform_action(locator, action_name)

                if post_assertion:
                    await post_assertion()

                await self._persist_success(candidate)
                return candidate

            except Exception as exc:
                failures.append({
                    "candidate": candidate,
                    "error": repr(exc),
                })
                await self._persist_failure(candidate, exc)

        raise RuntimeError(f"Todos os candidatos falharam: {failures}")

    async def _resolve(self, candidate: LocatorCandidate):
        raise NotImplementedError("Integre com Playwright: eval(candidate.playwright_expr) não é recomendado; use factory segura.")

    async def _check_unique(self, locator, candidate: LocatorCandidate):
        # Exemplo real em Playwright: count = await locator.count()
        # Se count != 1, rejeitar ou refinar contexto.
        return None

    async def _check_actionable(self, locator, candidate: LocatorCandidate):
        # Exemplo real: await expect(locator).to_be_visible(); await expect(locator).to_be_enabled()
        return None

    async def _perform_action(self, locator, action_name: str):
        # Exemplo real: click, fill, check etc.
        return None

    async def _persist_success(self, candidate: LocatorCandidate):
        return None

    async def _persist_failure(self, candidate: LocatorCandidate, exc: Exception):
        return None
