"""TestForge — Repositório de Métricas."""
from dataclasses import dataclass, field
from enum import Enum


class StepOutcome(str, Enum):
    """Resultado de um step individual apos execucao e healing."""
    FAILURE_DETECTED = "falha_detectada"    # Step falhou (erro lancado)
    HEALING_ATTEMPTED = "healing_tentado"   # Curador foi invocado
    HEALING_APPLIED = "aplicado"             # Healing aplicado com sucesso
    ORACLE_VALIDATED = "validado"            # Oracle confirmou o fix
    HEALING_REJECTED = "rejeitado"           # Healing falhou ou nao promovido


@dataclass
class MetricsSnapshot:
    total_runs: int = 0
    total_healings: int = 0
    false_heals: int = 0
    true_heals: int = 0
    llm_escalations: int = 0
    oracle_passed: int = 0
    oracle_failed: int = 0
    # Per-step counters (BUG-011)
    falhas_detectadas: int = 0
    healings_tentados: int = 0
    aplicados: int = 0
    validados: int = 0
    rejeitados: int = 0

    @property
    def false_heal_rate(self) -> float:
        if self.total_healings == 0:
            return 0.0
        return self.false_heals / self.total_healings

    @property
    def precision(self) -> float:
        if self.total_healings == 0:
            return 1.0
        return self.true_heals / self.total_healings

    @property
    def llm_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return self.llm_escalations / self.total_runs

    @property
    def healing_success_rate(self) -> float:
        """Taxa de healings que resultaram em aplicados/validados vs rejeitados."""
        total_outcomes = self.aplicados + self.validados + self.rejeitados
        if total_outcomes == 0:
            return 0.0
        return (self.aplicados + self.validados) / total_outcomes

    def to_dict(self) -> dict:
        return {
            "total_runs": self.total_runs,
            "total_healings": self.total_healings,
            "false_heals": self.false_heals,
            "true_heals": self.true_heals,
            "llm_escalations": self.llm_escalations,
            "oracle_passed": self.oracle_passed,
            "oracle_failed": self.oracle_failed,
            "false_heal_rate": round(self.false_heal_rate, 4),
            "precision": round(self.precision, 4),
            "llm_rate": round(self.llm_rate, 4),
            # Per-step (BUG-011)
            "falhas_detectadas": self.falhas_detectadas,
            "healings_tentados": self.healings_tentados,
            "aplicados": self.aplicados,
            "validados": self.validados,
            "rejeitados": self.rejeitados,
            "healing_success_rate": round(self.healing_success_rate, 4),
        }


class MetricsRepository:
    """Coleta e agrega metricas de execucao e healing."""

    def __init__(self):
        self._snapshot = MetricsSnapshot()
        self._history: list[dict] = []
        self._step_history: list[dict] = []

    def record_run(self, healed: bool = False, false_heal: bool = False,
                   llm_used: bool = False, oracle_passed: int = 0, oracle_failed: int = 0):
        self._snapshot.total_runs += 1
        self._snapshot.oracle_passed += oracle_passed
        self._snapshot.oracle_failed += oracle_failed

        if llm_used:
            self._snapshot.llm_escalations += 1

        if healed:
            self._snapshot.total_healings += 1
            if false_heal:
                self._snapshot.false_heals += 1
            else:
                self._snapshot.true_heals += 1

        self._history.append(self._snapshot.to_dict())

    def record_step(self, outcome: StepOutcome, step_num: int = 0,
                    action: str = "", family_code: str = "",
                    healing_layer: str = "", selector: str = "") -> None:
        """Registra metrica individual de step (BUG-011)."""
        if outcome == StepOutcome.FAILURE_DETECTED:
            self._snapshot.falhas_detectadas += 1
        elif outcome == StepOutcome.HEALING_ATTEMPTED:
            self._snapshot.healings_tentados += 1
        elif outcome == StepOutcome.HEALING_APPLIED:
            self._snapshot.aplicados += 1
        elif outcome == StepOutcome.ORACLE_VALIDATED:
            self._snapshot.validados += 1
        elif outcome == StepOutcome.HEALING_REJECTED:
            self._snapshot.rejeitados += 1

        self._step_history.append({
            "step_num": step_num,
            "action": action,
            "outcome": outcome.value,
            "family_code": family_code,
            "healing_layer": healing_layer,
            "selector": selector[:80] if selector else "",
        })

    @property
    def snapshot(self) -> MetricsSnapshot:
        return self._snapshot

    @property
    def step_history(self) -> list[dict]:
        """Historico detalhado dos steps (BUG-011)."""
        return list(self._step_history)

    def summary(self, show_per_step: bool = True) -> str:
        s = self._snapshot
        lines = [
            f"Total runs:      {s.total_runs}",
            f"Total healings:  {s.total_healings}",
            f"True heals:      {s.true_heals}",
            f"False heals:     {s.false_heals}",
            f"LLM escalations: {s.llm_escalations}",
            f"Oracle passed:   {s.oracle_passed}",
            f"Oracle failed:   {s.oracle_failed}",
            f"",
            f"False heal rate: {s.false_heal_rate:.2%}",
            f"Precision:       {s.precision:.2%}",
            f"LLM rate:        {s.llm_rate:.2%}",
        ]
        if show_per_step:
            lines.extend([
                f"",
                f"--- Per-Step Metrics (BUG-011) ---",
                f"Falhas detectadas:  {s.falhas_detectadas}",
                f"Healings tentados:  {s.healings_tentados}",
                f"Aplicados:          {s.aplicados}",
                f"Validados:          {s.validados}",
                f"Rejeitados:         {s.rejeitados}",
                f"Healing success:    {s.healing_success_rate:.2%}",
            ])
        return "\n".join(lines)
