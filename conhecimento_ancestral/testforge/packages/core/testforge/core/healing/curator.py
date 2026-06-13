from __future__ import annotations

import copy
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Optional

from testforge.core.config.loader import load_llm_config
from testforge.core.healing.classifier import FailureClassifier
from testforge.core.healing.collector import EvidenceCollector, EvidencePayload
from testforge.core.healing.llm.healer import LLMHealer, LLMHealingProposal, MockLLMHealer
from testforge.core.healing.models import FAMILIES, TAXONOMIES, HealingEntry, migrate_family, migrate_taxonomy
from testforge.core.healing.storage import HealingCatalog

logger = logging.getLogger("testforge.healing.curator")

STALE_DAYS = 90
REVIEW_THRESHOLD = int(os.environ.get("TF_REVIEW_THRESHOLD", "5"))


class ProgressResult:
    PASSED_STEP = "PASSED_STEP"
    REGRESSED = "REGRESSED"
    ERROR_CHANGED = "ERROR_CHANGED"
    STAGNATED = "STAGNATED"
    UNRESOLVED = "UNRESOLVED"


@dataclass
class CurationOutcome:
    status: str = ProgressResult.UNRESOLVED
    proposal: Optional[LLMHealingProposal] = None
    evidence: Optional[EvidencePayload] = None
    entry_id: str = ""
    error_message: str = ""
    rollback_applied: bool = False
    reclassification_used: bool = False
    layer_used: str = ""
    family: str = ""
    taxonomy_id: str = ""
    classification_layer: str = ""
    classification_confidence: float = 0.0


def classify_step_result(
    original_error: str,
    new_error: str,
    passed: bool,
) -> str:
    if passed:
        return ProgressResult.PASSED_STEP
    if not new_error:
        return ProgressResult.UNRESOLVED
    if new_error == original_error:
        return ProgressResult.STAGNATED
    return ProgressResult.ERROR_CHANGED


class CuradorAutomatico:
    MAX_RETRY_DEPTH = 1

    def __init__(
        self,
        catalog: HealingCatalog,
        healer: Optional[LLMHealer] = None,
        step_runner: Optional[Callable] = None,
        classifier: Optional[FailureClassifier] = None,
    ):
        self._catalog = catalog
        if healer is None:
            config = load_llm_config()
            if config is not None:
                healer = LLMHealer(config=config)
                logger.info("LLM Healer real ativado (Azure OpenAI)")
            else:
                healer = MockLLMHealer()
                logger.info("MockLLMHealer: set AZURE_OPENAI_KEY para ativar LLM real")
        self._healer = healer
        self._step_runner = step_runner
        self._classifier = classifier or FailureClassifier()

    def _build_step_copy(self, step_data: dict, new_locator: str) -> dict:
        patched = copy.deepcopy(step_data)
        patched["selector"] = new_locator
        return patched

    def _should_rollback(self, outcome: ProgressResult) -> bool:
        return outcome in (ProgressResult.REGRESSED, ProgressResult.STAGNATED)

    def _safe_format(self, template: str, **kwargs) -> str:
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError):
            return template

    def _register_learned(
        self,
        step_data: dict,
        proposal: LLMHealingProposal,
        evidence: EvidencePayload,
    ) -> str:
        ctx = evidence.step_context
        entry = HealingEntry(
            system="learned",
            symptom=f"Falha: {proposal.rationale}",
            root_cause=f"Taxonomia {proposal.taxonomy_id} / {proposal.family}",
            fix=f"Novo locator: {proposal.new_locator}",
            family=migrate_family(proposal.family),
            taxonomy=migrate_taxonomy(proposal.taxonomy_id),
            fix_type="learned",
            confidence=proposal.confidence,
            url=ctx.get("url", ""),
            action=ctx.get("action", ""),
            selector=step_data.get("selector", ""),
            tag=ctx.get("tag_name", ""),
            notes=f"Curador Automatico: {proposal.strategy} - {proposal.rationale}",
        )
        try:
            return self._catalog.add(entry)
        except (OSError, PermissionError) as e:
            return f"error:{e}"

    def _register_unresolved(
        self,
        step_data: dict,
        reason: str,
        evidence: Optional[EvidencePayload] = None,
        family: str = "",
        taxonomy: str = "",
    ) -> str:
        if not family and evidence:
            family = evidence.step_context.get("family", "")
        if not taxonomy and evidence:
            taxonomy = evidence.step_context.get("taxonomy", "")
        entry = HealingEntry(
            system="unresolved",
            symptom=f"Nao resolvido: {reason}",
            root_cause=reason,
            fix="Revisao manual necessaria",
            fix_type="unresolved",
            family=migrate_family(family),
            taxonomy=migrate_taxonomy(taxonomy),
            url=step_data.get("url", ""),
            action=step_data.get("action", ""),
            selector=step_data.get("selector", ""),
        )
        try:
            return self._catalog.add(entry)
        except (OSError, PermissionError) as e:
            return f"error:{e}"

    def _try_execute_step(self, step_data: dict) -> tuple[bool, str]:
        if not self._step_runner:
            return False, "Nenhum step_runner configurado para reexecucao"
        try:
            self._step_runner(step_data)
            return True, ""
        except Exception as e:
            return False, str(e)

    def _mark_stale_entries(self, limit: int = 500) -> int:
        marked = 0
        now = datetime.now(timezone.utc)
        for entry in self._catalog.list(fix_type="learned", limit=limit):
            if not entry.last_used_at:
                continue
            try:
                last = datetime.fromisoformat(entry.last_used_at)
            except (ValueError, TypeError):
                continue
            if (now - last) > timedelta(days=STALE_DAYS):
                notes = (entry.notes or "") + " [stale]"
                self._catalog.update(entry.id, notes=notes)
                marked += 1
        return marked

    def _run_healing_cycle(
        self,
        step_data: dict,
        evidence: EvidencePayload,
        error_message: str,
        is_retry: bool = False,
        depth: int = 0,
        family: str = "",
    ) -> CurationOutcome:
        if depth >= self.MAX_RETRY_DEPTH:
            return CurationOutcome(
                status=ProgressResult.UNRESOLVED,
                error_message=f"Depth limit ({self.MAX_RETRY_DEPTH}) excedido",
            )

        if not self._step_runner:
            return CurationOutcome(
                status=ProgressResult.UNRESOLVED,
                error_message="Nenhum step_runner configurado para validacao",
            )

        proposal = self._healer.heal_or_unresolved(evidence, error_message, family=family)
        outcome = CurationOutcome(proposal=proposal, evidence=evidence, layer_used="L3")

        if proposal.confidence < 0.5:
            outcome.status = ProgressResult.UNRESOLVED
            outcome.error_message = f"Confianca baixa ({proposal.confidence})"
            return outcome

        if proposal.family not in FAMILIES or proposal.taxonomy_id not in TAXONOMIES.get(proposal.family, []):
            outcome.status = ProgressResult.UNRESOLVED
            outcome.error_message = f"Taxonomia invalida: {proposal.taxonomy_id}/{proposal.family}"
            return outcome

        patched_step = self._build_step_copy(step_data, proposal.new_locator)
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
            retry_outcome.reclassification_used = True
            return retry_outcome

        if self._should_rollback(result):
            outcome.rollback_applied = True
            outcome.status = ProgressResult.UNRESOLVED
            outcome.error_message = new_error or error_message
            return outcome

        outcome.status = ProgressResult.UNRESOLVED
        return outcome

    def _try_layer1_catalog(
        self,
        family: str,
        step_data: dict,
        evidence: EvidencePayload,
        error_message: str,
    ) -> Optional[CurationOutcome]:
        entry = self._catalog.match(family, error_message)
        if not entry or entry.fix_type not in ("pre_populated", "reviewed", "learned"):
            return None

        if not self._step_runner:
            return CurationOutcome(
                status=ProgressResult.PASSED_STEP,
                entry_id=entry.id,
                layer_used="L1",
                family=family,
                error_message="",
            )

        try:
            self._step_runner(step_data)
            return CurationOutcome(
                status=ProgressResult.PASSED_STEP,
                entry_id=entry.id,
                layer_used="L1",
                family=family,
                error_message="",
            )
        except Exception:
            return None

    def _try_layer2_agents(
        self,
        family: str,
        step_data: dict,
        evidence: EvidencePayload,
        error_message: str,
    ) -> Optional[CurationOutcome]:
        try:
            from testforge.core.healing.agents import route_to_agent
        except ImportError:
            return None

        if not family:
            return None

        agent = route_to_agent(family, self._catalog, llm_healer=self._healer)
        if agent is None:
            return None

        if not self._step_runner:
            return None

        proposal = agent.heal(evidence, error_message)
        if not proposal or proposal.confidence < 0.5:
            return None

        if proposal.family not in FAMILIES or proposal.taxonomy_id not in TAXONOMIES.get(proposal.family, []):
            return None

        patched_step = self._build_step_copy(step_data, proposal.new_locator)
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

        return None

    def cure(
        self,
        step_data: dict,
        error_message: str,
        evidence: EvidencePayload,
    ) -> CurationOutcome:
        if not evidence.is_sufficient:
            return CurationOutcome(
                status=ProgressResult.UNRESOLVED,
                error_message=f"Evidencia insuficiente: {evidence.insufficiency_reason}",
                evidence=evidence,
            )

        classification = self._classifier.classify(error_message, evidence)
        family = classification.family
        taxonomy_id = classification.taxonomy_id

        outcome: Optional[CurationOutcome] = None
        if family:
            outcome = self._try_layer1_catalog(family, step_data, evidence, error_message)
        if outcome is None:
            outcome = self._try_layer2_agents(family, step_data, evidence, error_message)
        if outcome is None:
            outcome = self._run_healing_cycle(step_data, evidence, error_message, family=family)
            outcome.family = family or (outcome.proposal.family if outcome.proposal else "")
            outcome.taxonomy_id = taxonomy_id or (outcome.proposal.taxonomy_id if outcome.proposal else "")

        outcome.classification_layer = classification.matched_by
        outcome.classification_confidence = classification.confidence

        if outcome.status == ProgressResult.UNRESOLVED:
            self._register_unresolved(
                step_data=step_data,
                reason=outcome.error_message or error_message,
                evidence=evidence,
                family=outcome.family,
                taxonomy=outcome.taxonomy_id,
            )
            if taxonomy_id:
                self._catalog.increment_failure_count(taxonomy_id)
                count = self._catalog.get_failure_count(taxonomy_id)
                if count >= REVIEW_THRESHOLD:
                    self._notify_review_needed(taxonomy_id, family, count, error_message)
        else:
            if taxonomy_id:
                self._catalog.reset_failure_count(taxonomy_id)

        return outcome

    def _notify_review_needed(
        self,
        taxonomy_id: str,
        family: str,
        count: int,
        error_message: str,
    ) -> None:
        msg = (
            f"[REVIEW NEEDED] Taxonomy {taxonomy_id} ({family}) "
            f"falhou {count} vezes consecutivas.\n"
            f"Ultimo erro: {error_message[:200]}"
        )
        email_configured = all(os.environ.get(k) for k in (
            "TF_NOTIFY_EMAIL_SMTP_HOST", "TF_NOTIFY_EMAIL_FROM", "TF_NOTIFY_EMAIL_TO"
        ))
        teams_configured = bool(os.environ.get("TF_NOTIFY_TEAMS_WEBHOOK"))

        if email_configured or teams_configured:
            try:
                from testforge.core.notification import notify_all
                from testforge.core.models.report import Report, ExecutionSummary
                dummy_report = Report(
                    test_name=f"Review: {taxonomy_id}",
                    status="failed",
                    summary=ExecutionSummary(
                        executive=msg,
                        failed=count,
                    ),
                )
                notify_all(dummy_report)
            except Exception as e:
                logger.warning("Review notification failed: %s", e)
        else:
            logger.warning("Review needed: %s", msg)

    def stale_detection(self) -> int:
        return self._mark_stale_entries()
