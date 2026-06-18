"""TestForge — Intent Completeness Checker.

Validates that all necessary fields in a recording have reliable values.
Produces structured reports and classifies each field's completeness status.
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class FieldCompleteness(str, Enum):
    """Classification for each field's completeness state."""
    resolved = "resolved"
    resolved_with_warning = "resolved_with_warning"
    review_required = "review_required"
    missing = "missing"


@dataclass
class FieldStatus:
    """Completeness status for a single field."""
    field_key: str
    label: str
    placeholder: str = ""
    element_id: str = ""
    name: str = ""
    selector: str = ""
    step_index: int = -1
    value: str = ""
    source: str = ""
    completeness: FieldCompleteness = FieldCompleteness.missing
    reason: str = ""
    identifiers: dict = field(default_factory=dict)


@dataclass
class CompletenessReport:
    """Full completeness report for a recording."""
    recording_id: str = ""
    application: str = ""
    base_url: str = ""
    fields: list = field(default_factory=list)
    total_fields: int = 0
    resolved_count: int = 0
    resolved_with_warning_count: int = 0
    review_required_count: int = 0
    missing_count: int = 0
    is_complete: bool = False
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

    @property
    def pending_fields(self) -> list:
        """Fields that need user attention (missing or review_required)."""
        return [f for f in self.fields
                if f.completeness in (FieldCompleteness.missing,
                                      FieldCompleteness.review_required)]

    @property
    def captured_fields(self) -> list:
        """Fields that were successfully resolved."""
        return [f for f in self.fields
                if f.completeness == FieldCompleteness.resolved]

    @property
    def synthesized_fields(self) -> list:
        """Fields resolved through synthesis (not direct capture)."""
        return [f for f in self.fields
                if f.completeness == FieldCompleteness.resolved_with_warning]

    def to_dict(self) -> dict:
        """Serialize report to dictionary."""
        return {
            "recording_id": self.recording_id,
            "application": self.application,
            "base_url": self.base_url,
            "generated_at": self.generated_at,
            "summary": {
                "total_fields": self.total_fields,
                "resolved": self.resolved_count,
                "resolved_with_warning": self.resolved_with_warning_count,
                "review_required": self.review_required_count,
                "missing": self.missing_count,
                "is_complete": self.is_complete,
                "pending": len(self.pending_fields),
            },
            "fields": [
                {
                    "field_key": f.field_key,
                    "label": f.label,
                    "placeholder": f.placeholder,
                    "element_id": f.element_id,
                    "name": f.name,
                    "selector": f.selector,
                    "step_index": f.step_index,
                    "value": f.value,
                    "source": f.source,
                    "completeness": f.completeness.value,
                    "reason": f.reason,
                    "identifiers": f.identifiers,
                }
                for f in self.fields
            ],
        }

    def to_markdown(self) -> str:
        """Generate human-readable markdown report."""
        lines = [
            f"# Intent Completeness Report",
            f"",
            f"**Recording:** {self.recording_id}",
            f"**Application:** {self.application or 'N/A'}",
            f"**Generated:** {self.generated_at}",
            f"",
            f"## Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Fields | {self.total_fields} |",
            f"| ✅ Resolved | {self.resolved_count} |",
            f"| ⚠ Resolved (Warning) | {self.resolved_with_warning_count} |",
            f"| 🔍 Review Required | {self.review_required_count} |",
            f"| ❌ Missing | {self.missing_count} |",
            f"| **Complete** | **{'✅ Yes' if self.is_complete else '❌ No'}** |",
            f"",
        ]

        if self.captured_fields:
            lines.extend([
                f"## ✅ Captured Fields",
                f"",
                f"| Field | Value | Source | Step |",
                f"|-------|-------|--------|------|",
            ])
            for f in self.captured_fields:
                lines.append(
                    f"| {f.label or f.field_key} | {f.value or '(empty)'} "
                    f"| {f.source} | {f.step_index} |"
                )
            lines.append("")

        if self.synthesized_fields:
            lines.extend([
                f"## ⚠ Synthesized Fields",
                f"",
                f"| Field | Value | Source | Reason | Step |",
                f"|-------|-------|--------|--------|------|",
            ])
            for f in self.synthesized_fields:
                lines.append(
                    f"| {f.label or f.field_key} | {f.value or '(empty)'} "
                    f"| {f.source} | {f.reason} | {f.step_index} |"
                )
            lines.append("")

        if self.pending_fields:
            lines.extend([
                f"## ❌ Pending Fields",
                f"",
                f"| Field | Status | Label | ID | Selector | Reason | Step |",
                f"|-------|--------|-------|----|----------|--------|------|",
            ])
            for f in self.pending_fields:
                lines.append(
                    f"| {f.field_key} | {f.completeness.value} "
                    f"| {f.label or '-'} | {f.element_id or '-'} "
                    f"| `{f.selector or '-'}` | {f.reason} | {f.step_index} |"
                )
            lines.append("")

        if not self.is_complete:
            lines.extend([
                f"## Next Steps",
                f"",
                f"1. Review pending fields above.",
                f"2. Provide missing values via `--data` flag or CLI prompt.",
                f"3. Re-run completeness check after providing values.",
                f"",
            ])

        return "\n".join(lines)


class IntentCompletenessChecker:
    """Validates completeness of test intent in a recording.

    Examines field_value_map, semantic steps, and blind spots
    to determine if all necessary fields have reliable values.
    """

    FIELD_TAGS = {"input", "textarea", "select"}

    def check_steps(self, steps: list,
                    field_values: Optional[dict] = None) -> CompletenessReport:
        """Check completeness of a recording from semantic steps.

        Args:
            steps: List of SemanticAction objects.
            field_values: Optional dict of field_key -> FieldValueMap.

        Returns:
            CompletenessReport with per-field status and summary.
        """
        report = CompletenessReport()
        fields: dict = {}  # field_key -> FieldStatus

        # 1. Examine field_value_map entries
        if field_values:
            for key, fvm in field_values.items():
                fs = FieldStatus(
                    field_key=key,
                    label=fvm.identifiers.get("label", ""),
                    placeholder=fvm.identifiers.get("placeholder", ""),
                    element_id=fvm.identifiers.get("element_id", ""),
                    name=fvm.identifiers.get("name", ""),
                    step_index=fvm.step_index,
                    value=fvm.value,
                    source=fvm.source,
                    identifiers=fvm.identifiers,
                )

                if fvm.source == "missing_fill":
                    fs.completeness = FieldCompleteness.missing
                    fs.reason = "typing_not_captured"
                elif fvm.source == "form_values":
                    fs.completeness = FieldCompleteness.resolved_with_warning
                    fs.reason = "reconstructed_from_form_values"
                elif fvm.source == "polling":
                    fs.completeness = FieldCompleteness.resolved_with_warning
                    fs.reason = "reconstructed_from_polling"
                elif fvm.source == "network_payload":
                    fs.completeness = FieldCompleteness.resolved_with_warning
                    fs.reason = "reconstructed_from_network"
                elif fvm.source == "user_supplied_cli":
                    fs.completeness = FieldCompleteness.review_required
                    fs.reason = "user_supplied_cli_not_validated"
                elif fvm.value:
                    fs.completeness = FieldCompleteness.resolved
                    fs.reason = "direct_capture"
                else:
                    fs.completeness = FieldCompleteness.missing
                    fs.reason = "empty_value"

                fields[key] = fs

        # 2. Examine steps for field interactions without field_value_map entry
        if steps:
            from testforge.semantic.model import SemanticAction
            for i, step in enumerate(steps):
                if not isinstance(step, SemanticAction):
                    continue

                ctx = step.context or {}
                tag = (step.target.tag or "").lower() if step.target else ""

                # Check clicks on input/textarea/select with missing_fill flag
                if (step.action in ("click", "fill")
                        and tag in self.FIELD_TAGS):
                    field_key = self._field_key_from_step(step)

                    # Skip if already in fields dict
                    if field_key and field_key in fields:
                        continue

                    # Detect missing fill via context flag
                    is_missing = ctx.get("missing_fill", False)
                    has_fill_value = bool(step.value)

                    fs = FieldStatus(
                        field_key=field_key or f"field_step_{i}",
                        label=(
                            getattr(step.target, "accessible_name", None)
                            or getattr(step.target, "label", None)
                            or getattr(step.target, "placeholder", None)
                            or ""
                        ),
                        placeholder=getattr(step.target, "placeholder", "") or "",
                        element_id=getattr(step.target, "element_id", "") or "",
                        name=getattr(step.target, "name", "") or "",
                        selector=self._first_selector(step),
                        step_index=i,
                        value=step.value or "",
                        source="missing_fill" if is_missing else "step_capture",
                        identifiers=self._identifiers_from_step(step),
                    )

                    if is_missing and not has_fill_value:
                        fs.completeness = FieldCompleteness.missing
                        fs.reason = "typing_not_captured"
                        if tag == "select":
                            fs.reason = "select_not_captured"
                    elif is_missing and has_fill_value:
                        fs.completeness = FieldCompleteness.resolved_with_warning
                        fs.reason = "has_value_but_missing_flag"
                    elif has_fill_value:
                        fs.completeness = FieldCompleteness.resolved
                        fs.reason = "direct_capture"
                    else:
                        fs.completeness = FieldCompleteness.missing
                        fs.reason = "no_value_captured"

                    fields[fs.field_key] = fs

                # Check selects without captured value
                elif (step.action == "click"
                      and tag == "select"
                      and not step.value):
                    ctx = step.context or {}
                    if not ctx.get("form_values"):
                        field_key = self._field_key_from_step(step) or f"select_step_{i}"
                        if field_key not in fields:
                            fs = FieldStatus(
                                field_key=field_key,
                                label=(
                                    getattr(step.target, "accessible_name", None)
                                    or getattr(step.target, "label", None)
                                    or getattr(step.target, "placeholder", None)
                                    or ""
                                ),
                                element_id=getattr(step.target, "element_id", "") or "",
                                name=getattr(step.target, "name", "") or "",
                                selector=self._first_selector(step),
                                step_index=i,
                                completeness=FieldCompleteness.missing,
                                reason="select_not_captured",
                                identifiers=self._identifiers_from_step(step),
                            )
                            fields[field_key] = fs

        # 3. Compile report
        report.fields = list(fields.values())
        report.total_fields = len(report.fields)
        report.resolved_count = sum(
            1 for f in report.fields
            if f.completeness == FieldCompleteness.resolved
        )
        report.resolved_with_warning_count = sum(
            1 for f in report.fields
            if f.completeness == FieldCompleteness.resolved_with_warning
        )
        report.review_required_count = sum(
            1 for f in report.fields
            if f.completeness == FieldCompleteness.review_required
        )
        report.missing_count = sum(
            1 for f in report.fields
            if f.completeness == FieldCompleteness.missing
        )
        report.is_complete = (
            report.missing_count == 0
            and report.review_required_count == 0
        )

        return report

    def _field_key_from_step(self, step) -> Optional[str]:
        """Extract a canonical field key from a semantic step."""
        from testforge.semantic.model import SemanticAction
        if not isinstance(step, SemanticAction):
            return None
        target = step.target
        if not target:
            return None

        # Try name first, then id, then label, then placeholder
        key = (target.name or target.element_id
               or target.label or target.placeholder
               or target.test_id or "")
        if not key:
            return None

        # Canonicalize: lowercase, replace spaces/hyphens with underscore
        import re
        key = re.sub(r'[^a-zA-Z0-9_]', '_', key.lower())
        key = re.sub(r'_+', '_', key).strip('_')
        return key or None

    def _first_selector(self, step) -> str:
        """Get first candidate selector from a step."""
        from testforge.semantic.model import SemanticAction
        if not isinstance(step, SemanticAction):
            return ""
        if step.target and step.target.candidates:
            return step.target.candidates[0].selector or ""
        return ""

    def _identifiers_from_step(self, step) -> dict:
        """Extract identifiers dict from a step."""
        from testforge.semantic.model import SemanticAction
        if not isinstance(step, SemanticAction) or not step.target:
            return {}
        t = step.target
        return {
            "name": t.name or "",
            "id": t.element_id or "",
            "label": t.label or "",
            "placeholder": t.placeholder or "",
            "role": t.role or "",
            "test_id": t.test_id or "",
        }


def save_completeness_report(report: CompletenessReport,
                               output_dir: str,
                               recording_id: str = "") -> tuple[str, str]:
    """Save completeness report to JSON and Markdown files.

    Args:
        report: CompletenessReport to save.
        output_dir: Directory to save files in.
        recording_id: Optional recording ID for filenames.

    Returns:
        Tuple of (json_path, md_path).
    """
    os.makedirs(output_dir, exist_ok=True)
    rid = recording_id or "unknown"

    json_path = os.path.join(output_dir, f"intent_completeness_report.json")
    with open(json_path, "w") as f:
        json.dump(report.to_dict(), f, indent=2, default=str)

    md_path = os.path.join(output_dir, f"intent_completeness_report.md")
    with open(md_path, "w") as f:
        f.write(report.to_markdown())

    return json_path, md_path
