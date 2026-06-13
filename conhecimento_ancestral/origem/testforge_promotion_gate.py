from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PromotionState(str, Enum):
    EXPERIMENTAL = "experimental"
    SHADOW_VALIDATED = "shadow_validated"
    CANARY = "canary"
    TRUSTED = "trusted"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"


@dataclass
class EvidenceCompleteness:
    screenshot_before: bool = False
    screenshot_after: bool = False
    dom_before: bool = False
    dom_after: bool = False
    accessibility_tree_before: bool = False
    accessibility_tree_after: bool = False
    score_breakdown: bool = False
    taxonomy_code: bool = False
    technology_profile: bool = False
    post_action_oracle: bool = False

    def is_complete(self) -> bool:
        return all(vars(self).values())


@dataclass
class PromotionMetrics:
    reviewed_observations: int = 0
    oracle_precision: float = 0.0
    false_acceptance_rate: float = 1.0
    false_heal_rate: float = 1.0
    llm_escalation_rate: float = 1.0
    semantic_gap: float = 0.0
    uniqueness_score: float = 0.0
    actionability_score: float = 0.0
    runtime_overhead_percent: float = 0.0
    false_heal_last_n: int = 999


@dataclass
class PromotionContext:
    current_state: PromotionState
    metrics: PromotionMetrics
    evidence: EvidenceCompleteness
    has_oracle_conflict: bool = False
    has_false_heal_reviewed: bool = False
    has_taxonomy_wrong_unresolved: bool = False
    has_technology_profile_wrong_unresolved: bool = False
    critical_action_without_business_or_network_oracle: bool = False
    synthetic_lab_passed: bool = False
    rollback_plan_exists: bool = False
    human_review_sample_done: bool = False


@dataclass
class PromotionDecision:
    allowed: bool
    from_state: PromotionState
    to_state: PromotionState
    reasons: list[str] = field(default_factory=list)


class PromotionGate:
    def decide(self, ctx: PromotionContext, target: PromotionState) -> PromotionDecision:
        reasons: list[str] = []

        self._check_global_blocks(ctx, reasons)

        if target == PromotionState.SHADOW_VALIDATED:
            self._check_shadow_validated(ctx, reasons)
        elif target == PromotionState.CANARY:
            self._check_canary(ctx, reasons)
        elif target == PromotionState.TRUSTED:
            self._check_trusted(ctx, reasons)
        else:
            reasons.append(f"Promoção para {target.value} não é suportada por este gate.")

        return PromotionDecision(
            allowed=len(reasons) == 0,
            from_state=ctx.current_state,
            to_state=target,
            reasons=reasons,
        )

    def _check_global_blocks(self, ctx: PromotionContext, reasons: list[str]) -> None:
        if not ctx.evidence.is_complete():
            reasons.append("Evidence package incompleto.")
        if ctx.has_oracle_conflict:
            reasons.append("Conflito entre oracles.")
        if ctx.has_false_heal_reviewed:
            reasons.append("Existe falso healing revisado.")
        if ctx.has_taxonomy_wrong_unresolved:
            reasons.append("Taxonomia incorreta ainda não resolvida.")
        if ctx.has_technology_profile_wrong_unresolved:
            reasons.append("Perfil tecnológico incorreto ainda não resolvido.")
        if ctx.critical_action_without_business_or_network_oracle:
            reasons.append("Ação crítica sem oracle de negócio ou rede.")
        if ctx.metrics.semantic_gap < 0.15:
            reasons.append("Semantic gap abaixo do mínimo.")
        if ctx.metrics.uniqueness_score < 0.85:
            reasons.append("Uniqueness score abaixo do mínimo.")
        if ctx.metrics.actionability_score < 0.95:
            reasons.append("Actionability score abaixo do mínimo.")

    def _check_shadow_validated(self, ctx: PromotionContext, reasons: list[str]) -> None:
        if ctx.metrics.reviewed_observations < 30:
            reasons.append("Menos de 30 observações revisadas.")
        if ctx.metrics.oracle_precision < 0.95:
            reasons.append("Precisão do oracle abaixo de 95%.")
        if ctx.metrics.false_acceptance_rate >= 0.02:
            reasons.append("False acceptance rate >= 2%.")
        if ctx.metrics.false_heal_rate >= 0.02:
            reasons.append("False heal rate >= 2%.")
        if not ctx.synthetic_lab_passed:
            reasons.append("Synthetic Lab obrigatório ainda não passou.")

    def _check_canary(self, ctx: PromotionContext, reasons: list[str]) -> None:
        if ctx.current_state != PromotionState.SHADOW_VALIDATED:
            reasons.append("Canary exige estado anterior shadow_validated.")
        if not ctx.human_review_sample_done:
            reasons.append("Amostra de revisão humana não concluída.")
        if not ctx.rollback_plan_exists:
            reasons.append("Plano de rollback inexistente.")

    def _check_trusted(self, ctx: PromotionContext, reasons: list[str]) -> None:
        if ctx.current_state != PromotionState.CANARY:
            reasons.append("Trusted exige estado anterior canary.")
        if ctx.metrics.reviewed_observations < 100:
            reasons.append("Menos de 100 observações revisadas.")
        if ctx.metrics.false_heal_last_n > 0:
            reasons.append("Houve falso healing nos últimos N casos.")
        if ctx.metrics.runtime_overhead_percent > 20:
            reasons.append("Overhead de execução acima de 20%.")
        if ctx.metrics.llm_escalation_rate >= 0.10:
            reasons.append("Taxa de acionamento de LLM >= 10%.")
