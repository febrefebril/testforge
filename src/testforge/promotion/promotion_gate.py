"""TestForge — Portão de Promoção."""
from dataclasses import dataclass, field
from enum import Enum


class PromotionState(str, Enum):
    EXPERIMENTAL = "experimental"
    SHADOW_VALIDATED = "shadow_validated"
    REJECTED = "rejected"


@dataclass
class PromotionDecision:
    state: PromotionState
    allowed: bool
    reasons: list = field(default_factory=list)
    blocks: list = field(default_factory=list)


class PromotionGate:
    """Decide se uma sugestao de healing pode ser promovida."""

    BLOCKERS = {
        "evidence_incomplete": "Evidencias insuficientes",
        "oracle_missing": "Nenhum oracle executado",
        "oracle_failed": "Oracle falhou",
        "oracle_conflict": "Oracles conflitantes",
        "uniqueness_low": "Score de unicidade muito baixo",
    }

    def evaluate(self, oracle_results: list, evidence: dict = None,
                 uniqueness_score: float = 1.0) -> PromotionDecision:
        evidence = evidence or {}
        blocks = []
        reasons = []

        if not evidence.get("screenshots"):
            blocks.append("evidence_incomplete")

        if not oracle_results:
            blocks.append("oracle_missing")
        else:
            statuses = [r.status for r in oracle_results]
            if all(s == "failed" for s in statuses):
                blocks.append("oracle_failed")
            elif "failed" in statuses and "passed" in statuses:
                blocks.append("oracle_conflict")

        if uniqueness_score < 0.3:
            blocks.append("uniqueness_low")

        if blocks:
            return PromotionDecision(
                state=PromotionState.REJECTED,
                allowed=False,
                blocks=blocks,
                reasons=[self.BLOCKERS.get(b, b) for b in blocks]
            )

        if all(s == "passed" for s in [r.status for r in oracle_results]):
            return PromotionDecision(
                state=PromotionState.SHADOW_VALIDATED,
                allowed=True,
                reasons=["Todos os oracles passaram"]
            )

        return PromotionDecision(
            state=PromotionState.EXPERIMENTAL,
            allowed=False,
            reasons=["Alguns oracles inconclusivos — requer revisao humana"]
        )
