"""TestForge — Metrics Repository."""
from dataclasses import dataclass, field


@dataclass
class MetricsSnapshot:
    total_runs: int = 0
    total_healings: int = 0
    false_heals: int = 0
    true_heals: int = 0
    llm_escalations: int = 0
    oracle_passed: int = 0
    oracle_failed: int = 0

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
        }


class MetricsRepository:
    """Coleta e agrega metricas de execucao e healing."""

    def __init__(self):
        self._snapshot = MetricsSnapshot()
        self._history: list[dict] = []

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

    @property
    def snapshot(self) -> MetricsSnapshot:
        return self._snapshot

    def summary(self) -> str:
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
        return "\n".join(lines)
