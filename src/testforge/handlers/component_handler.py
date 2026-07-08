"""TestForge — ComponentHandler abstract base.

Framework-agnostic interface for component-specific recording, execution, and healing.
Each UI framework (Angular Material, PrimeFaces, React MUI) implements this.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from playwright.sync_api import Page
    from testforge.healing.llm_healer import LLMHealingProposal
    from testforge.healing.evidence_payload import EvidencePayload


class ComponentHandler(ABC):
    """Abstract base for component-specific handlers.

    Implementation contract:
    - detect(): pure, no side effects, called on every step
    - normalize(): mutates steps list in-place (dedup/collapse)
    - execute(): performs Playwright action, returns selector used
    - heal(): returns proposal or None to fall through to L3 LLM
    """

    @abstractmethod
    def detect(self, candidates: list[str], element_id: str, tag: str) -> bool:
        """Return True if this handler owns the step's target element."""

    @property
    @abstractmethod
    def component_type(self) -> str:
        """Human-readable name, e.g. 'angular-material'."""

    def normalize(self, steps: list) -> None:
        """Collapse/dedup component-specific step sequences in-place.

        Default: no-op. Override for components with multi-step interaction
        patterns (e.g. datepicker open+nav+close → single fill).
        """

    def execute(self, page: "Page", step) -> str:
        """Execute step action using component-specific Playwright strategy.

        Returns selector string used (for reporting).
        Raises exception on failure (caller handles healing escalation).
        """
        raise NotImplementedError(f"{self.component_type} execute() not implemented")

    def heal(
        self,
        evidence: "EvidencePayload",
        error: str,
    ) -> Optional["LLMHealingProposal"]:
        """Return component-specific healing proposal or None to escalate."""
        return None
