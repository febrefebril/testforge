"""B26/B31 — completeness check no longer double-reports already-covered fields.

In test-pos-hotfix10 three SIOPI fields ended up in the `--complete`
retroactive prompt despite final_state having captured their values.
Root cause: the path-2 fallback of IntentCompletenessChecker only
skipped a step when its element_id was already covered. Material
mat-input-N counters reset between the focus event and the
final_state snapshot, so the click step's id differed from the
final_state entry's id even though they referred to the same physical
input.

Fix: also skip when the step's accessible_name / label / name /
placeholder / canonical field_key matches an already-covered entry by
any of those identifiers.

This file pins:
1. A field already in field_values via final_state (or any source) by
   label is NOT re-emitted as missing through path 2.
2. A step with no real identifiers and an element_id mismatch still
   gets reported when nothing else covers it (regression guard).
3. Normalising "Quanto vale seu imóvel hoje?*" -> canonical key works
   end-to-end.
"""
from __future__ import annotations

from testforge.semantic.model import (
    LocatorCandidate,
    SemanticAction,
    SemanticTarget,
)
from testforge.validation.intent_completeness import (
    FieldCompleteness,
    IntentCompletenessChecker,
)
from testforge.semantic.recording_normalizer import RecordingNormalizer


def _stc_with_final_state_field(label: str,
                                final_state_el_id: str,
                                step_el_id: str = ""):
    """Build a tiny STC where final_state captured the value under one
    element_id and the click step carries a different element_id —
    the exact Material counter-drift situation."""
    from testforge.semantic.model import FieldValueMap, SemanticTestCase
    # final_state entry — id mat-input-5 (from session-end snapshot)
    canonical = RecordingNormalizer()._canonical_field_key(label)
    fvm = FieldValueMap(
        field_key=canonical,
        value="1.000.000,00",
        intention=f"fill {label} (from final_state)",
        identifiers={
            "id": final_state_el_id,
            "label": label,
            "aria-label": label,
        },
        source="final_state",
        step_index=0,
    )

    # Click step — id mat-input-2 (recorded at click time, before mask
    # re-assigned the counter)
    target = SemanticTarget(
        accessible_name=label,
        label=label,
        placeholder="0,00",
        element_id=step_el_id,
        tag="input",
        candidates=[LocatorCandidate(
            "aria_label",
            f'input[aria-label="{label}"]',
            0.9, "aria_label",
        )],
    )
    step = SemanticAction(action="click", target=target)

    stc = SemanticTestCase(test_id="X", source_recording_id="X")
    stc.steps = [step]
    stc.field_values = {canonical: fvm}
    return stc


class TestCoveredByLabelNotReReported:
    def test_final_state_label_match_skips_path2(self):
        """The exact failure mode from test-pos-hotfix10."""
        stc = _stc_with_final_state_field(
            label="Quanto vale seu imóvel hoje?*",
            final_state_el_id="mat-input-5",
            step_el_id="mat-input-2",  # different id, same field
        )
        checker = IntentCompletenessChecker()
        report = checker.check_steps(stc.steps, stc.field_values)
        labels = [f.label for f in report.fields]
        # Path 2 must NOT re-emit the same field as "typing_not_captured".
        missing = [
            f for f in report.fields
            if f.completeness == FieldCompleteness.missing
            and f.reason == "typing_not_captured"
        ]
        assert not missing, (
            f"Field already covered by final_state was re-reported via "
            f"path 2: labels={labels}, missing={[f.label for f in missing]}"
        )

    def test_final_state_aria_label_match_also_skips(self):
        stc = _stc_with_final_state_field(
            label="Renda mensal *",
            final_state_el_id="",          # final_state with no id
            step_el_id="mat-input-7",      # step has id; final_state has none
        )
        checker = IntentCompletenessChecker()
        report = checker.check_steps(stc.steps, stc.field_values)
        missing = [
            f for f in report.fields
            if f.completeness == FieldCompleteness.missing
        ]
        assert not missing


class TestRegressionGuard:
    def test_truly_uncovered_field_still_reported(self):
        """A step with no matching entry in field_values must still be
        flagged. Otherwise B26/B31 silently masks real gaps."""
        target = SemanticTarget(
            accessible_name="CEP",
            label="CEP",
            placeholder="00000-000",
            element_id="cep-input",
            tag="input",
            candidates=[LocatorCandidate(
                "aria_label", 'input[aria-label="CEP"]', 0.9, "aria_label",
            )],
        )
        step = SemanticAction(action="click", target=target,
                              context={"missing_fill": True})
        checker = IntentCompletenessChecker()
        report = checker.check_steps([step], {})
        # CEP should appear and be flagged as missing.
        assert any(
            f.label == "CEP"
            and f.completeness == FieldCompleteness.missing
            for f in report.fields
        )
