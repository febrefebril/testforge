"""TestForge — Incremental step result models.

Dataclasses serializáveis para o IncrementalRunner. Cada step carrega:
pré-condição, execução, pós-condição, healing, evidências, métricas.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class PreconditionResult:
    passed: bool = False
    checks: dict = field(default_factory=dict)
    failures: list = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PostconditionResult:
    passed: bool = False
    checks: dict = field(default_factory=dict)
    oracle_results: list = field(default_factory=list)
    failures: list = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "checks": dict(self.checks),
            "oracle_results": [str(o) for o in self.oracle_results],
            "failures": list(self.failures),
            "message": self.message,
        }


@dataclass
class HealingAttempt:
    attempted: bool = False
    status: str = ""
    layer: str = ""
    family: str = ""
    taxonomy_id: str = ""
    strategy: str = ""
    original_locator: str = ""
    proposed_locator: str = ""
    confidence: float = 0.0
    validated: bool = False
    oracle_passed: bool = False
    rejection_reason: list = field(default_factory=list)
    rationale: str = ""
    raw_response: str = ""
    failure_phase: str = ""
    original_error: str = ""
    entry_id: str = ""
    promotion_state: str = ""
    promotion_allowed: bool = False
    promotion_blocks: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class IncrementalStepResult:
    step_num: int
    action: str
    status: str = "unknown"
    original_locator: str = ""
    selected_locator: str = ""
    value: str = ""
    precondition: Optional[PreconditionResult] = None
    postcondition: Optional[PostconditionResult] = None
    healing: Optional[HealingAttempt] = None
    error_message: str = ""
    evidence_before: dict = field(default_factory=dict)
    evidence_after: dict = field(default_factory=dict)
    duration_ms: int = 0
    skip_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "step_num": self.step_num,
            "action": self.action,
            "status": self.status,
            "original_locator": self.original_locator,
            "selected_locator": self.selected_locator,
            "value": self.value,
            "precondition": self.precondition.to_dict() if self.precondition else None,
            "postcondition": self.postcondition.to_dict() if self.postcondition else None,
            "healing": self.healing.to_dict() if self.healing else None,
            "error_message": self.error_message,
            "evidence_before": self.evidence_before,
            "evidence_after": self.evidence_after,
            "duration_ms": self.duration_ms,
            "skip_reason": self.skip_reason,
        }