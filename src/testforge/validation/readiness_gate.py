"""TestForge — Portão de Prontidão de Gravação.

Decide se uma gravação está pronta para uso do time baseado em critérios objetivos:
1. Completude: todos campos resolvidos (sem missing/review_required)
2. Execução de passo: todos passos executáveis passaram ou healed_validated
3. Passos bloqueantes: resolvidos (passaram ou healed_validated)
4. Valores fornecidos pelo usuário: validados por execução incremental
5. Healing: rejeitado sem oracle positivo

Produz readiness_report.json e readiness_report.md.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from testforge.recorder.recording_status import RecordingStatus


class ReadinessVerdict(str, Enum):
    """Veredicto final para prontidão de gravação."""
    PASS = "pass"
    FAIL = "fail"
    NEEDS_REVIEW = "needs_review"
    # H16: criteria pass but zero executable steps ran — gate-only signal.
    # Prevents dashboard false-greens when nothing was actually exercised.
    GATED_ONLY = "gated_only"


@dataclass
class ReadinessReport:
    """Avaliação compreensiva de prontidão para uma gravação única."""

    recording_id: str = ""
    application: str = ""
    base_url: str = ""
    status: RecordingStatus = RecordingStatus.incomplete_intent
    verdict: ReadinessVerdict = ReadinessVerdict.FAIL

    # Criteria results
    completeness_passed: bool = False
    all_steps_passed: bool = False
    blocking_steps_resolved: bool = False
    user_supplied_values_validated: bool = False
    healing_oracles_passed: bool = False

    # Details
    total_steps: int = 0
    passed_steps: int = 0
    healed_steps: int = 0
    failed_steps: int = 0
    blocked_steps: int = 0
    skipped_steps: int = 0
    missing_fields: list = field(default_factory=list)
    review_required_fields: list = field(default_factory=list)
    failures: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "readiness_report": {
                "metadata": {
                    "recording_id": self.recording_id,
                    "application": self.application,
                    "base_url": self.base_url,
                    "generated_at": self.generated_at,
                },
                "status": self.status.value,
                "verdict": self.verdict.value,
                "criteria": {
                    "completeness_passed": self.completeness_passed,
                    "all_steps_passed": self.all_steps_passed,
                    "blocking_steps_resolved": self.blocking_steps_resolved,
                    "user_supplied_values_validated": self.user_supplied_values_validated,
                    "healing_oracles_passed": self.healing_oracles_passed,
                },
                "steps": {
                    "total": self.total_steps,
                    "passed": self.passed_steps,
                    "healed": self.healed_steps,
                    "failed": self.failed_steps,
                    "blocked": self.blocked_steps,
                    "skipped": self.skipped_steps,
                },
                "missing_fields": self.missing_fields,
                "review_required_fields": self.review_required_fields,
                "failures": self.failures,
                "warnings": self.warnings,
            }
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Recording Readiness Report",
            f"",
            f"**Recording:** {self.recording_id}",
            f"**Application:** {self.application or 'N/A'}",
            f"**Generated:** {self.generated_at}",
            f"",
            f"## Status",
            f"",
            f"| Criteria | Result |",
            f"|----------|--------|",
            f"| Verdict | **{self.verdict.value.upper()}** |",
            f"| Recording Status | `{self.status.value}` |",
            f"| Completeness Passed | {'[OK]' if self.completeness_passed else '[FAIL]'} |",
            f"| All Steps Passed | {'[OK]' if self.all_steps_passed else '[FAIL]'} |",
            f"| Blocking Steps Resolved | {'[OK]' if self.blocking_steps_resolved else '[FAIL]'} |",
            f"| User-Supplied Values Validated | {'[OK]' if self.user_supplied_values_validated else '[FAIL]'} |",
            f"| Healing Oracles Passed | {'[OK]' if self.healing_oracles_passed else '[FAIL]'} |",
            f"",
            f"## Step Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total | {self.total_steps} |",
            f"| [OK] Passed | {self.passed_steps} |",
            f"| 🔧 Healed | {self.healed_steps} |",
            f"| [FAIL] Failed | {self.failed_steps} |",
            f"| [BLOCK] Blocked | {self.blocked_steps} |",
            f"| [SKIP] Skipped | {self.skipped_steps} |",
            f"",
        ]

        if self.missing_fields:
            lines.extend([
                f"## [FAIL] Missing Fields",
                f"",
                f"| Field | Label | Reason |",
                f"|-------|-------|--------|",
            ])
            for f in self.missing_fields:
                lines.append(f"| {f.get('field_key', '?')} | {f.get('label', '-')} | {f.get('reason', '')} |")
            lines.append("")

        if self.review_required_fields:
            lines.extend([
                f"## [WARN] Review Required Fields",
                f"",
                f"| Field | Label | Reason |",
                f"|-------|-------|--------|",
            ])
            for f in self.review_required_fields:
                lines.append(f"| {f.get('field_key', '?')} | {f.get('label', '-')} | {f.get('reason', '')} |")
            lines.append("")

        if self.failures:
            lines.extend([
                f"## Failures",
            ])
            for f in self.failures:
                lines.append(f"- [FAIL] {f}")
            lines.append("")

        if self.warnings:
            lines.extend([
                f"## Warnings",
            ])
            for w in self.warnings:
                lines.append(f"- [WARN] {w}")
            lines.append("")

        if self.verdict == ReadinessVerdict.PASS:
            lines.extend([
                f"## [OK] Ready for Team",
                f"",
                f"This recording passed all readiness criteria and can be used by the team.",
            ])
        elif self.verdict == ReadinessVerdict.GATED_ONLY:
            lines.extend([
                f"## [GATED] Gate Passed — No Execution Evidence",
                f"",
                f"Criteria green but zero executable steps ran. Run 'testforge run-incremental' "
                f"before marking ready for team.",
            ])
        elif self.verdict == ReadinessVerdict.NEEDS_REVIEW:
            lines.extend([
                f"## 🔍 Needs Review",
                f"",
                f"This recording requires human review before it can be marked as ready.",
                f"Review the failures above, fix the issues, and re-run validation.",
            ])
        else:
            lines.extend([
                f"## [FAIL] Not Ready",
                f"",
                f"This recording did not pass readiness criteria.",
                f"Address the failures above before attempting validation again.",
            ])

        return "\n".join(lines)


class RecordingReadinessGate:
    """Objective readiness gate for recording validation.

    Evaluates multiple criteria to decide if a recording is ready_for_team.
    """

    # Step statuses that count as 'passed' for readiness
    PASSING_STATUSES = {"passed", "healed_validated"}
    # Step statuses that count as 'failed' for readiness
    FAILING_STATUSES = {"failed", "healing_rejected"}

    @staticmethod
    def _is_passing_status(status: str) -> bool:
        return status in RecordingReadinessGate.PASSING_STATUSES

    @staticmethod
    def _is_failing_status(status: str) -> bool:
        return status in RecordingReadinessGate.FAILING_STATUSES

    def evaluate(
        self,
        recording_id: str,
        application: str,
        base_url: str,
        completeness_report,  # CompletenessReport from intent_completeness
        step_results: list,  # List of IncrementalStepResult from incremental runner
        field_values: Optional[dict] = None,
    ) -> ReadinessReport:
        """Evaluate all readiness criteria and produce a report.

        Args:
            recording_id: ID of the recording being evaluated.
            application: Application name.
            base_url: Base URL of the application.
            completeness_report: CompletenessReport from check_steps().
            step_results: List of IncrementalStepResult from incremental run.
            field_values: Optional field_value_map dict.

        Returns:
            ReadinessReport with verdict and detailed breakdown.
        """
        report = ReadinessReport(
            recording_id=recording_id,
            application=application,
            base_url=base_url,
        )

        # ---------- Criterion 1: Completeness ----------
        completeness_ok = (
            completeness_report is not None
            and completeness_report.is_complete
        )
        report.completeness_passed = completeness_ok
        if not completeness_ok:
            report.failures.append("Completeness check failed: missing or unresolved fields exist")
            missing = []
            review_req = []
            if completeness_report:
                for f in completeness_report.fields:
                    from testforge.validation.intent_completeness import FieldCompleteness
                    field_info = {
                        "field_key": f.field_key,
                        "label": f.label,
                        "reason": f.reason,
                        "source": f.source,
                    }
                    if f.completeness == FieldCompleteness.missing:
                        missing.append(field_info)
                    elif f.completeness == FieldCompleteness.review_required:
                        review_req.append(field_info)
            report.missing_fields = missing
            report.review_required_fields = review_req

        # ---------- Criterion 2: Step execution ----------
        if step_results:
            report.total_steps = len(step_results)
            report.passed_steps = sum(
                1 for r in step_results if r.status == "passed"
            )
            report.healed_steps = sum(
                1 for r in step_results if r.status == "healed_validated"
            )
            report.failed_steps = sum(
                1 for r in step_results if self._is_failing_status(getattr(r, "status", ""))
            )
            report.blocked_steps = sum(
                1 for r in step_results if r.status == "blocked"
            )
            report.skipped_steps = sum(
                1 for r in step_results if r.status == "skipped"
            )

            # Consider a step 'passed' if it passed or healed_validated
            executable = [r for r in step_results if r.status not in ("blocked", "skipped")]
            all_passed = all(
                self._is_passing_status(getattr(r, "status", ""))
                for r in executable
            ) if executable else True
            report.all_steps_passed = all_passed
            if not all_passed:
                failed_steps_detail = [
                    f"Step {r.step_num} ({r.action}): {r.status} — {r.error_message or 'no details'}"
                    for r in step_results
                    if self._is_failing_status(getattr(r, "status", ""))
                ]
                report.failures.extend(failed_steps_detail)
        else:
            report.all_steps_passed = True
            report.warnings.append(
                "Step validation skipped at record time — run 'testforge run-incremental' to validate execution"
            )

        # ---------- Criterion 3: Blocking steps resolved ----------
        if step_results:
            blocking = [r for r in step_results if getattr(r, "blocking", False)]
            if blocking:
                all_blocking_ok = all(
                    self._is_passing_status(getattr(r, "status", ""))
                    for r in blocking
                )
                report.blocking_steps_resolved = all_blocking_ok
                if not all_blocking_ok:
                    report.failures.append(
                        "Blocking step(s) failed or unresolved — dependent steps may be affected"
                    )
            else:
                report.blocking_steps_resolved = True  # No blocking steps == trivially resolved
        else:
            report.blocking_steps_resolved = True

        # ---------- Criterion 4: User-supplied values validated ----------
        # Check if field_values has user_supplied_cli sources
        user_supplied_count = 0
        if field_values:
            for key, fvm in field_values.items():
                source = ""
                if hasattr(fvm, "source"):
                    source = fvm.source
                elif isinstance(fvm, dict):
                    source = fvm.get("source", "")
                if source == "user_supplied_cli":
                    user_supplied_count += 1

        if user_supplied_count > 0:
            # User-supplied values exist — check if they were validated via step execution
            if step_results and report.all_steps_passed:
                report.user_supplied_values_validated = True
            else:
                report.user_supplied_values_validated = False
                report.warnings.append(
                    f"{user_supplied_count} user-supplied value(s) present but not fully validated "
                    f"by incremental execution"
                )
        else:
            report.user_supplied_values_validated = True  # No user values == trivially validated

        # ---------- Criterion 5: Healing oracles ----------
        if step_results:
            healed = [r for r in step_results if r.status == "healed_validated"]
            oracles_failed = False
            for r in healed:
                healing = getattr(r, "healing", None)
                if healing and not getattr(healing, "oracle_passed", False):
                    oracles_failed = True
                    break
            report.healing_oracles_passed = not oracles_failed
            if oracles_failed:
                report.failures.append(
                    "Healing was applied but oracle validation failed — healing may be unreliable"
                )
        else:
            report.healing_oracles_passed = True  # No healing == trivially passed

        # ---------- Final verdict ----------
        # H16: verdict=pass requires ALL of:
        #   1. every criterion green
        #   2. at least one executable step succeeded (passed or healed_validated)
        #   3. zero failed or healing_rejected steps
        # Otherwise: gated_only (criteria green, nothing executed), fail (failures),
        # or needs_review (criteria green but no execution evidence).
        all_criteria = [
            report.completeness_passed,
            report.all_steps_passed,
            report.blocking_steps_resolved,
            report.user_supplied_values_validated,
            report.healing_oracles_passed,
        ]
        criteria_green = all(all_criteria)
        successful_steps = report.passed_steps + report.healed_steps
        any_failed = report.failed_steps > 0

        if criteria_green and successful_steps > 0 and not any_failed:
            report.verdict = ReadinessVerdict.PASS
            report.status = RecordingStatus.ready_for_team
        elif criteria_green and successful_steps == 0 and not any_failed:
            report.verdict = ReadinessVerdict.GATED_ONLY
            report.status = RecordingStatus.needs_review
            report.warnings.append(
                "Gate passed but no executable step ran — dashboard cannot claim end-to-end success"
            )
        elif any_failed or report.failures:
            has_blocking_failures = any(
                "blocking" in f.lower() or "completeness" in f.lower()
                for f in report.failures
            )
            if has_blocking_failures or any_failed:
                report.verdict = ReadinessVerdict.FAIL
                report.status = RecordingStatus.incomplete_intent
            else:
                report.verdict = ReadinessVerdict.NEEDS_REVIEW
                report.status = RecordingStatus.needs_review
        else:
            report.verdict = ReadinessVerdict.NEEDS_REVIEW
            report.status = RecordingStatus.needs_review

        return report


def save_readiness_report(
    report: ReadinessReport,
    output_dir: str,
) -> tuple[str, str]:
    """Save readiness report to JSON and Markdown files.

    Args:
        report: ReadinessReport to save.
        output_dir: Directory to save files in.

    Returns:
        Tuple of (json_path, md_path).
    """
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, "readiness_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, default=str)

    md_path = os.path.join(output_dir, "readiness_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report.to_markdown())

    return json_path, md_path
