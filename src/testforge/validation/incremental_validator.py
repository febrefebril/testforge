"""TestForge — IncrementalRecordingValidator.

Orchestrates the validation pipeline for a complete recording:
1. Normalize raw events → SemanticTestCase
2. Check completeness (IntentCompletenessChecker)
3. Re-execute steps incrementally (IncrementalRunner)
4. Evaluate readiness gate (RecordingReadinessGate)
5. Save reports

The validator is the bridge between Sprint 1-4 (completeness + reconstruction)
and Sprint 5+ (incremental validation + readiness gate).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from testforge.recorder.recording_status import (
    RecordingStatus,
    RecordingStatusHistory,
    RecordingStatusEntry,
)
from testforge.validation.intent_completeness import (
    IntentCompletenessChecker,
    CompletenessReport,
    save_completeness_report,
)
from testforge.validation.readiness_gate import (
    RecordingReadinessGate,
    ReadinessReport,
    ReadinessVerdict,
    save_readiness_report,
)


class IncrementalRecordingValidator:
    """Validates a recording by normalizing, checking completeness, and
    running incremental execution before evaluating readiness."""

    def __init__(
        self,
        recording_dir: str,
        output_dir: str = "",
        headless: bool = True,
        timeout: int = 60,
        browser: str = "chromium",
        interactive: bool = False,
        no_healing: bool = False,
    ):
        self.recording_dir = recording_dir
        self.output_dir = output_dir or recording_dir
        self.headless = headless
        self.timeout = timeout
        self.browser_type = browser
        self.interactive = interactive
        self.no_healing = no_healing

        self.application = ""
        self.base_url = ""
        self.recording_id = ""

        self.status_history = RecordingStatusHistory()
        self.semantic_test_case = None
        self.completeness_report: Optional[CompletenessReport] = None
        self.readiness_report: Optional[ReadinessReport] = None
        self.step_results: list = []

    def _get_recording_metadata(self) -> dict:
        """Load recording metadata from recording.json if it exists."""
        meta_path = os.path.join(self.recording_dir, "recording.json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                return json.load(f)
        return {}

    def _normalize(self) -> bool:
        """Normalize raw events into SemanticTestCase.

        Returns:
            True if normalization succeeded.
        """
        from testforge.semantic.recording_normalizer import RecordingNormalizer

        try:
            normalizer = RecordingNormalizer()
            self.semantic_test_case = normalizer.normalize(
                self.recording_dir,
                test_id=f"ST-{self.recording_id}",
                application=self.application,
                base_url=self.base_url,
            )
            self.status_history.record(
                RecordingStatus.intent_reconstructed,
                reason="Normalization completed successfully",
            )
            return True
        except Exception as exc:
            import sys
            print(f"[TestForge] Normalization failed: {exc}", file=sys.stderr)
            self.status_history.record(
                RecordingStatus.incomplete_intent,
                reason=f"Normalization failed: {exc}",
            )
            return False

    def _check_completeness(self) -> CompletenessReport:
        """Check completeness of the normalized recording.

        Returns:
            CompletenessReport with per-field status.
        """
        checker = IntentCompletenessChecker()
        report = checker.check_steps(
            steps=self.semantic_test_case.steps if self.semantic_test_case else [],
            field_values=(
                self.semantic_test_case.field_values
                if self.semantic_test_case
                else None
            ),
        )
        report.recording_id = self.recording_id
        report.application = self.application
        report.base_url = self.base_url

        if report.is_complete:
            self.status_history.record(
                RecordingStatus.intent_complete,
                reason="All fields resolved",
                metadata={
                    "total_fields": report.total_fields,
                    "resolved": report.resolved_count,
                    "resolved_with_warning": report.resolved_with_warning_count,
                },
            )
        elif report.missing_count > 0:
            self.status_history.record(
                RecordingStatus.incomplete_intent,
                reason=f"{report.missing_count} field(s) missing",
                metadata={
                    "missing": report.missing_count,
                    "review_required": report.review_required_count,
                },
            )
        elif report.review_required_count > 0:
            self.status_history.record(
                RecordingStatus.needs_user_input,
                reason=f"{report.review_required_count} field(s) require review",
            )

        self.completeness_report = report
        return report

    def _run_incremental(self) -> list:
        """Run incremental execution on the normalized steps.

        This wraps IncrementalRunner to validate that steps execute
        correctly with the resolved field values.

        Returns:
            List of IncrementalStepResult objects.
        """
        from testforge.runner.incremental_runner import IncrementalRunner

        if not self.semantic_test_case or not self.semantic_test_case.steps:
            return []

        # Find the compiled script path if it exists
        script_path = self._find_compiled_script()

        self.status_history.record(
            RecordingStatus.incremental_validation_running,
            reason=f"Starting incremental validation of {len(self.semantic_test_case.steps)} steps",
        )

        if script_path and os.path.exists(script_path):
            # Use compiled script for playback
            runner = IncrementalRunner(
                script_path=script_path,
                headless=self.headless,
                timeout=self.timeout,
                verbose=not self.headless,
                browser=self.browser_type,
                stop_on_failure=False,
                interactive=self.interactive,
                no_healing=self.no_healing,
                output_root=os.path.join(self.output_dir, "validation_run"),
            )
        else:
            # Run from semantic steps directly — create a minimal script
            # that IncrementalRunner can load
            runner = self._make_runner_from_steps()

        try:
            report = runner.run()
            self.step_results = report.get("steps", []) if isinstance(report, dict) else []
        except Exception as exc:
            import sys
            print(f"[TestForge] Incremental validation error: {exc}", file=sys.stderr)
            self.step_results = []

        return self.step_results

    def _find_compiled_script(self) -> str:
        """Find compiled test script in recording directory."""
        for entry in os.listdir(self.recording_dir):
            if entry.startswith("test_") and entry.endswith(".py"):
                return os.path.join(self.recording_dir, entry)
        return ""

    def _make_runner_from_steps(self):
        """Create IncrementalRunner configured to run from semantic steps directly.

        Since IncrementalRunner expects a script path, we create a runner
        configured with just the base URL and steps.
        """
        from testforge.runner.incremental_runner import IncrementalRunner

        runner = IncrementalRunner(
            script_path="",
            headless=self.headless,
            timeout=self.timeout,
            verbose=not self.headless,
            browser=self.browser_type,
            stop_on_failure=False,
            interactive=self.interactive,
            no_healing=self.no_healing,
            output_root=os.path.join(self.output_dir, "validation_run"),
        )
        runner.recording_id = self.recording_id
        runner.base_url = self.base_url or ""
        runner.steps = self.semantic_test_case.steps if self.semantic_test_case else []
        runner._field_value_map = (
            self.semantic_test_case.field_values if self.semantic_test_case else {}
        )
        return runner

    def _evaluate_gate(self) -> ReadinessReport:
        """Evaluate readiness gate with current results.

        Returns:
            ReadinessReport with final verdict.
        """
        gate = RecordingReadinessGate()
        report = gate.evaluate(
            recording_id=self.recording_id,
            application=self.application,
            base_url=self.base_url,
            completeness_report=self.completeness_report,
            step_results=self.step_results,
            field_values=(
                self.semantic_test_case.field_values
                if self.semantic_test_case
                else None
            ),
        )

        self.readiness_report = report

        # Record final status
        if report.verdict == ReadinessVerdict.PASS:
            self.status_history.record(
                RecordingStatus.ready_for_team,
                reason="All readiness criteria passed",
                metadata={"verdict": "pass"},
            )
        elif report.verdict == ReadinessVerdict.NEEDS_REVIEW:
            self.status_history.record(
                RecordingStatus.needs_review,
                reason=f"{len(report.failures)} failure(s) need review",
                metadata={
                    "failures": report.failures,
                    "verdict": "needs_review",
                },
            )
        else:
            self.status_history.record(
                RecordingStatus.incomplete_intent,
                reason=f"{len(report.failures)} blocking failure(s)",
                metadata={
                    "failures": report.failures,
                    "verdict": "fail",
                },
            )

        return report

    def _save_status_history(self):
        """Save status history to recording directory."""
        history_path = os.path.join(self.output_dir, "status_history.json")
        with open(history_path, "w") as f:
            json.dump(
                {
                    "recording_id": self.recording_id,
                    "entries": self.status_history.to_dict(),
                    "current_status": (
                        self.status_history.current.value
                        if self.status_history.current
                        else None
                    ),
                },
                f,
                indent=2,
                default=str,
            )

    def validate(self) -> ReadinessReport:
        """Run the full validation pipeline.

        Steps:
        1. Load recording metadata
        2. Normalize raw events → SemanticTestCase
        3. Check completeness → CompletenessReport
        4. Run incremental execution → step results
        5. Evaluate readiness gate → ReadinessReport
        6. Save all reports

        Returns:
            ReadinessReport with final verdict.
        """
        import sys

        # 1. Load metadata
        meta = self._get_recording_metadata()
        self.recording_id = meta.get("recording_id", os.path.basename(self.recording_dir))
        self.application = meta.get("application", "")
        self.base_url = meta.get("base_url", "")

        print(f"[TestForge] 🔍 Validating recording: {self.recording_id}", file=sys.stderr)

        # 2. Normalize
        if not self._normalize():
            print("[TestForge] ❌ Normalization failed — cannot validate", file=sys.stderr)
            return self._make_failed_report("Normalization failed")

        # 3. Check completeness
        completeness = self._check_completeness()
        save_completeness_report(
            completeness,
            self.output_dir,
            recording_id=self.recording_id,
        )
        total = completeness.total_fields
        missing = completeness.missing_count
        print(
            f"[TestForge] 📋 Completeness: {total} fields, "
            f"{'✅ complete' if completeness.is_complete else f'❌ {missing} missing'}",
            file=sys.stderr,
        )

        # 4. Run incremental validation
        self._run_incremental()
        step_count = len(self.step_results)
        print(
            f"[TestForge] 🔄 Incremental validation: {step_count} steps executed",
            file=sys.stderr,
        )

        # 5. Evaluate gate
        report = self._evaluate_gate()

        # 6. Save reports
        self._save_status_history()
        save_readiness_report(report, self.output_dir)

        return report

    def _make_failed_report(self, reason: str) -> ReadinessReport:
        """Create a failed readiness report when validation cannot run."""
        from datetime import datetime, timezone
        report = ReadinessReport(
            recording_id=self.recording_id,
            application=self.application,
            base_url=self.base_url,
            status=RecordingStatus.incomplete_intent,
            verdict=ReadinessVerdict.FAIL,
            failures=[reason],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        self.readiness_report = report
        save_readiness_report(report, self.output_dir)
        self._save_status_history()
        return report
