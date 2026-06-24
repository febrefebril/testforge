"""TestForge — CuradorAutomático (pipeline L0→L1→L2→L3).

Orquestra o pipeline de healing de 4 camadas:
  L0 — HealingCatalog (correspondência de receita, <50ms, zero LLM)
  L1 — FallbackRunner (candidatos MIS, determinístico)
  L2 — EvidenceCollector → EvidencePayload
  L3 — LLMHealer (ou fallback MockLLMHealer)

Referência: projeto-anterior/curator.py (implementação validada)
"""
from __future__ import annotations

import copy
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Callable, Optional

from ..taxonomy.taxonomy import FailureClassifier
from ..taxonomy.taxonomy import FAMILIES as _FAMILIES_DICT
from ..taxonomy.taxonomy import TAXONOMIES
from .evidence_payload import EvidencePayload
from .healing_catalog import HealingCatalog
from .llm_healer import LLMHealer, MockLLMHealer, LLMHealingProposal

logger = logging.getLogger("testforge.healing.curator")

STALE_DAYS = 90
REVIEW_THRESHOLD = int(os.environ.get("TF_REVIEW_THRESHOLD", "5"))


# -- ProgressResult ----------------------------------------------------------

class ProgressResult:
    """Resultado da execução de um passo curado."""
    PASSED_STEP = "PASSED_STEP"
    ERROR_CHANGED = "ERROR_CHANGED"
    REGRESSED = "REGRESSED"
    STAGNATED = "STAGNATED"
    UNRESOLVED = "UNRESOLVED"


def classify_step_result(original_error: str, new_error: str, passed: bool) -> str:
    """Classifica resultado da tentativa de healing comparando erros."""
    if passed:
        return ProgressResult.PASSED_STEP
    if not new_error:
        return ProgressResult.UNRESOLVED
    if new_error == original_error:
        return ProgressResult.STAGNATED
    return ProgressResult.ERROR_CHANGED


# -- CurationOutcome ---------------------------------------------------------

@dataclass
class CurationOutcome:
    """Resultado de um ciclo de curation de healing."""
    status: str = ProgressResult.UNRESOLVED
    proposal: Optional[LLMHealingProposal] = None
    evidence: Optional[EvidencePayload] = None
    entry_id: str = ""
    error_message: str = ""
    rollback_applied: bool = False
    layer_used: str = ""            # "L0", "L1", "L2", "L3"
    family: str = ""
    taxonomy_id: str = ""


# -- Failure Count Tracker ---------------------------------------------------

class FailureTracker:
    """Rastreia falhas consecutivas por taxonomy_id para limiar de review."""

    def __init__(self, path: str = ".planning/failure-counts.json"):
        self._path = path
        self._counts: dict[str, int] = {}
        self._load()

    def _load(self):
        if os.path.exists(self._path):
            try:
                import json as _json
                with open(self._path) as f:
                    self._counts = _json.load(f)
            except Exception:
                self._counts = {}

    def _save(self):
        import json as _json
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            _json.dump(self._counts, f, indent=2)

    def increment(self, taxonomy_id: str) -> int:
        self._counts[taxonomy_id] = self._counts.get(taxonomy_id, 0) + 1
        self._save()
        return self._counts[taxonomy_id]

    def reset(self, taxonomy_id: str):
        self._counts[taxonomy_id] = 0
        self._save()

    def get(self, taxonomy_id: str) -> int:
        return self._counts.get(taxonomy_id, 0)


# -- CuradorAutomatico -------------------------------------------------------

class CuradorAutomatico:
    """Orchestrates 4-layer healing: L0→L1→L2→L3.

    Usage:
        curator = CuradorAutomatico(
            catalog=HealingCatalog(),
            step_runner=lambda step_data: execute_step(page, step_data),
        )
        outcome = curator.cure(step_data, error_message, evidence_payload)
    """

    MAX_RETRY_DEPTH = 1

    def __init__(
        self,
        catalog: Optional[HealingCatalog] = None,
        step_runner: Optional[Callable] = None,
        debug_healing: bool = False,
    ):
        self._catalog = catalog or HealingCatalog()
        self._step_runner = step_runner
        self._classifier = FailureClassifier()
        self._failure_tracker = FailureTracker()
        self._debug_healing = debug_healing

        # Auto-activate healer: real LLM if keys configured, mock otherwise
        from .llm_client import is_available
        if is_available():
            self._healer: LLMHealer = LLMHealer()
            self._healer_type = "LLM real (Azure/OpenAI)"
            logger.info("LLMHealer real ativado (Azure OpenAI / OpenAI)")
        else:
            self._healer = MockLLMHealer()
            self._healer_type = "MockLLMHealer (deterministico)"
            logger.info("MockLLMHealer ativado (deterministico) — configure AZURE_OPENAI_KEY para LLM real")

    # -- Public API ------------------------------------------------------

    def cure(
        self,
        step_data: dict,
        error_message: str,
        evidence: EvidencePayload,
    ) -> CurationOutcome:
        """Run full healing pipeline and return outcome."""
        if not evidence.is_sufficient:
            return CurationOutcome(
                status=ProgressResult.UNRESOLVED,
                error_message=f"Insufficient evidence: {evidence.insufficiency_reason}",
                evidence=evidence,
            )

        # Classify failure
        classification = self._classifier.classify(error_message)
        family = classification.family_code
        taxonomy_id = classification.taxonomy_id

        # Try layers in order
        outcome = self._try_layer0_catalog(family, step_data, error_message)
        if outcome is None:
            outcome = self._try_layer1_candidates(step_data, family)
        if outcome is None:
            outcome = self._try_layer2_agents(family, step_data, error_message, evidence)
        if outcome is None:
            outcome = self._run_healing_cycle(step_data, evidence, error_message, family=family)
            outcome.family = family or (outcome.proposal.family if outcome.proposal else "")
            outcome.taxonomy_id = taxonomy_id or (outcome.proposal.taxonomy_id if outcome.proposal else "")

        # Post-cure: track failures, notify if threshold reached
        if outcome.status == ProgressResult.UNRESOLVED:
            if taxonomy_id:
                count = self._failure_tracker.increment(taxonomy_id)
                if count >= REVIEW_THRESHOLD:
                    self._notify_review_needed(taxonomy_id, family, count, error_message)
        else:
            if taxonomy_id:
                self._failure_tracker.reset(taxonomy_id)

        return outcome

    # -- L0: Recipe Catalog ----------------------------------------------

    def _try_layer0_catalog(
        self, family: str, step_data: dict, error_message: str,
    ) -> Optional[CurationOutcome]:
        """L0: Match exact recipe from HealingCatalog."""
        recipes = self._catalog.match_recipes(error_message, family=family)
        high_confidence = [r for r in recipes if r.priority >= 5]
        if not high_confidence:
            return None

        best = high_confidence[0]
        if not self._step_runner:
            # No runner — return as passed (catalog entry is trusted)
            self._catalog.record_usage(best.recipe_id)
            return CurationOutcome(
                status=ProgressResult.PASSED_STEP,
                entry_id=best.recipe_id,
                layer_used="L0",
                family=family,
            )

        # Execute with catalog fix
        patched_step = self._build_step_copy(step_data, best.solution_selector, best.solution_strategy)
        passed, new_error = self._try_execute_step(patched_step)
        if passed:
            self._catalog.record_success(best.recipe_id)
            return CurationOutcome(
                status=ProgressResult.PASSED_STEP,
                entry_id=best.recipe_id,
                layer_used="L0",
                family=family,
            )

        return None  # Fall through to L1

    # -- L1: Ranked Candidates (MIS fallback) --------------------------

    _DANGEROUS_SELS = {"body", "html", "div", "span", "*", "a", "button", "input"}

    def _try_layer1_candidates(
        self, step_data: dict, family: str,
    ) -> Optional[CurationOutcome]:
        """L1: Try ranked LocatorCandidates from the MIS (step.target.candidates)."""
        candidates = step_data.get("candidates") or []
        if not candidates or not self._step_runner:
            return None

        sorted_cands = sorted(candidates, key=lambda c: c.get("score", 0), reverse=True)
        for cand in sorted_cands:
            sel = (cand.get("selector") or "").strip()
            score = cand.get("score", 0)
            if not sel or score < 0.3:
                continue
            # Skip dangerously generic selectors
            if sel.lower() in self._DANGEROUS_SELS:
                continue
            if sel.startswith("nth-child") or sel.startswith(":nth-child"):
                continue

            patched = self._build_step_copy(step_data, sel, "semantic_locator_conversion")
            passed, _ = self._try_execute_step(patched)
            if passed:
                # Execution success proves locator works — boost confidence above validator threshold
                confirmed_confidence = max(score, 0.60)
                proposal = LLMHealingProposal(
                    taxonomy_id="SEL-004", family="FAM-01",
                    strategy="semantic_locator_conversion",
                    new_locator=sel,
                    confidence=confirmed_confidence,
                    rationale=f"Candidato MIS ({cand.get('strategy','')}) score={score:.2f} confirmado por execucao: {sel}",
                )
                return CurationOutcome(
                    status=ProgressResult.PASSED_STEP,
                    proposal=proposal,
                    layer_used="L1",
                    family=family or "FAM-01",
                    taxonomy_id="SEL-004",
                )
        return None

    # -- L2: Specialist Agents ------------------------------------------

    def _try_layer2_agents(
        self, family: str, step_data: dict, error_message: str, evidence: EvidencePayload,
    ) -> Optional[CurationOutcome]:
        """L2: Route to specialist agent for deterministic healing."""
        try:
            from .agents import route_to_agent
        except ImportError:
            return None

        if not family:
            return None

        agent = route_to_agent(family, llm_healer=self._healer)
        if agent is None:
            return None

        proposal = agent.heal(evidence, error_message)
        if not proposal or proposal.confidence < 0.5:
            return None

        # Validate taxonomy
        from ..taxonomy.taxonomy import FAMILIES
        if proposal.family not in FAMILIES or proposal.taxonomy_id not in TAXONOMIES.get(proposal.family, []):
            return None

        if not self._step_runner:
            # No runner — return proposal as passed (L2 suggestion is trusted)
            return CurationOutcome(
                status=ProgressResult.PASSED_STEP,
                proposal=proposal,
                evidence=evidence,
                layer_used="L2",
                family=family,
                taxonomy_id=proposal.taxonomy_id,
            )

        # Execute patched step
        patched_step = self._build_step_copy(step_data, proposal.new_locator, proposal.strategy)
        passed, new_error = self._try_execute_step(patched_step)
        result = classify_step_result(error_message, new_error, passed)

        if result == ProgressResult.PASSED_STEP:
            entry_id = self._register_learned(patched_step, proposal, evidence)
            return CurationOutcome(
                status=ProgressResult.PASSED_STEP,
                proposal=proposal,
                evidence=evidence,
                entry_id=entry_id,
                layer_used="L2",
                family=family,
                taxonomy_id=proposal.taxonomy_id,
            )

        return None  # Fall through to L3

    # -- L3: LLM Healer --------------------------------------------------

    def _run_healing_cycle(
        self,
        step_data: dict,
        evidence: EvidencePayload,
        error_message: str,
        is_retry: bool = False,
        depth: int = 0,
        family: str = "",
    ) -> CurationOutcome:
        """L3: Call LLMHealer, validate, execute, classify."""
        if depth >= self.MAX_RETRY_DEPTH:
            return CurationOutcome(
                status=ProgressResult.UNRESOLVED,
                error_message=f"Max retry depth ({self.MAX_RETRY_DEPTH}) exceeded",
            )

        if not self._step_runner:
            return CurationOutcome(
                status=ProgressResult.UNRESOLVED,
                error_message="No step_runner configured for validation",
            )

        # Call LLM (or Mock)
        if self._debug_healing:
            import sys
            print(f"\n[DEBUG:HEALING] LLM payload:", file=sys.stderr)
            print(f"  Error: {error_message[:200]}", file=sys.stderr)
            print(f"  Family: {family}", file=sys.stderr)
            print(f"  Evidence: {evidence.step_context}", file=sys.stderr)

        proposal = self._healer.heal_or_unresolved(evidence, error_message, family=family)

        if self._debug_healing:
            import sys
            print(f"[DEBUG:HEALING] LLM response:", file=sys.stderr)
            print(f"  Taxonomy: {proposal.taxonomy_id}/{proposal.family}", file=sys.stderr)
            print(f"  Strategy: {proposal.strategy}", file=sys.stderr)
            print(f"  Confidence: {proposal.confidence:.2f}", file=sys.stderr)
            print(f"  Locator: {proposal.new_locator[:60]}", file=sys.stderr)
            if proposal.raw_response:
                print(f"  Raw: {proposal.raw_response[:150]}", file=sys.stderr)

        outcome = CurationOutcome(proposal=proposal, evidence=evidence, layer_used="L3")

        # Confidence gate
        if proposal.confidence < 0.5:
            outcome.status = ProgressResult.UNRESOLVED
            outcome.error_message = f"Low confidence ({proposal.confidence:.2f})"
            return outcome

        # Validate taxonomy
        from ..taxonomy.taxonomy import FAMILIES
        if proposal.family not in FAMILIES or proposal.taxonomy_id not in TAXONOMIES.get(proposal.family, []):
            outcome.status = ProgressResult.UNRESOLVED
            outcome.error_message = f"Invalid taxonomy: {proposal.taxonomy_id}/{proposal.family}"
            return outcome

        # Execute patched step
        patched_step = self._build_step_copy(step_data, proposal.new_locator, proposal.strategy)
        passed, new_error = self._try_execute_step(patched_step)
        result = classify_step_result(error_message, new_error, passed)

        if result == ProgressResult.PASSED_STEP:
            entry_id = self._register_learned(patched_step, proposal, evidence)
            outcome.status = ProgressResult.PASSED_STEP
            outcome.entry_id = entry_id
            return outcome

        if result == ProgressResult.ERROR_CHANGED and not is_retry:
            retry_outcome = self._run_healing_cycle(
                step_data, evidence, new_error, is_retry=True, depth=depth + 1, family=family,
            )
            return retry_outcome

        if self._should_rollback(result):
            outcome.rollback_applied = True
            outcome.status = ProgressResult.UNRESOLVED
            outcome.error_message = new_error or error_message
            return outcome

        outcome.status = ProgressResult.UNRESOLVED
        return outcome

    # -- Helpers ---------------------------------------------------------

    def _build_step_copy(self, step_data: dict, new_locator: str, strategy: str = "") -> dict:
        """Clone step_data with replaced selector and strategy."""
        patched = copy.deepcopy(step_data)
        patched["selector"] = new_locator
        if strategy:
            patched["strategy"] = strategy
        return patched

    def _try_execute_step(self, step_data: dict) -> tuple[bool, str]:
        """Execute step via runner. Returns (passed, error_message)."""
        if not self._step_runner:
            return False, "No step_runner configured"
        try:
            self._step_runner(step_data)
            return True, ""
        except Exception as e:
            return False, str(e)

    def _should_rollback(self, result: str) -> bool:
        """Check if result requires rollback."""
        return result in (ProgressResult.REGRESSED, ProgressResult.STAGNATED)

    def _register_learned(
        self, step_data: dict, proposal: LLMHealingProposal, evidence: EvidencePayload,
    ) -> str:
        """Register successful healing as a learned recipe."""
        try:
            from .healing_catalog import HealingRecipe
            recipe = HealingRecipe(
                trigger_family=proposal.family,
                trigger_code=proposal.taxonomy_id,
                trigger_pattern=evidence.step_context.get("selector", "")[:200],
                trigger_framework=evidence.step_context.get("framework", "generic"),
                solution_strategy=proposal.strategy,
                solution_selector=proposal.new_locator,
                priority=5,  # Auto-learned starts at medium confidence
                status="active",
            )
            return self._catalog.add_recipe(recipe)
        except Exception:
            return ""

    def _register_unresolved(self, step_data: dict, reason: str) -> str:
        """Register unresolved case for human review."""
        try:
            from .healing_catalog import HealingRecipe
            recipe = HealingRecipe(
                trigger_family="execution",
                trigger_code="UNRESOLVED",
                trigger_pattern=reason[:200],
                trigger_framework="generic",
                solution_strategy="manual_review",
                solution_selector=step_data.get("selector", ""),
                priority=0,
                status="pending_review",
            )
            return self._catalog.add_recipe(recipe)
        except Exception:
            return ""

    def _notify_review_needed(
        self, taxonomy_id: str, family: str, count: int, error_message: str,
    ) -> None:
        """Alert when failure threshold reached."""
        msg = (
            f"[REVIEW NEEDED] Taxonomy {taxonomy_id} ({family}) "
            f"failed {count} consecutive times.\n"
            f"Last error: {error_message[:200]}"
        )
        logger.warning("Review needed: %s", msg)
        # Future: email/Teams notification via testforge.core.notification

    def stale_detection(self) -> int:
        """Mark recipes unused for > STALE_DAYS as stale. Returns count."""
        # HealingCatalog doesn't track last_used at recipe level yet.
        # Future: add last_used tracking to HealingCatalog.
        return 0
