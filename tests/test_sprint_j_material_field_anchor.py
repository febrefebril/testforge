"""TestForge — Sprint J: Material form-field structural anchor.

SIOPI Material calculadora reusa aria-label "Renda mensal *", "Valor do
imovel *" mas o aria-label volatiliza apos blur — runtime `[aria-label="X"]`
falha embora o input continue na tela. mat-input-N IDs renumera entre
sessoes, tambem nao serve. **mat-label dentro do mat-form-field eh estavel
e semantico**.

Sprint J:
- overlay_inject.js::_extractMaterialFieldLabel: walk ancestor ate
  mat-form-field, le mat-label / .mat-form-field-label / .mat-mdc-form-field-label
- target.material_field_label persistido em raw_events
- SemanticTarget.material_field_label novo campo
- normalizer emite candidate top-priority `mat-form-field:has(mat-label:has-text("X")) input`
  com score 0.99 (acima de aria-label 0.95)
"""
from __future__ import annotations
from pathlib import Path

import pytest


OVERLAY = Path(__file__).parent.parent / "src" / "testforge" / "recorder" / "overlay_inject.js"


class TestOverlayExtractsMaterialLabel:
    def test_extract_function_present(self):
        src = OVERLAY.read_text(encoding="utf-8")
        assert "function _extractMaterialFieldLabel(" in src

    def test_walks_ancestor_for_mat_form_field(self):
        src = OVERLAY.read_text(encoding="utf-8")
        body = src.split("function _extractMaterialFieldLabel(")[1].split("\n  }\n")[0]
        assert "mat-form-field" in body
        assert "parentElement" in body
        assert "mat-label" in body

    def test_extract_target_calls_helper(self):
        src = OVERLAY.read_text(encoding="utf-8")
        assert "_extractMaterialFieldLabel(el)" in src

    def test_target_object_emits_material_field_label(self):
        src = OVERLAY.read_text(encoding="utf-8")
        assert "material_field_label: materialLabel" in src

    def test_hop_limit_bounded(self):
        """Don't walk infinitely — bounded ancestor walk to prevent perf issues."""
        src = OVERLAY.read_text(encoding="utf-8")
        body = src.split("function _extractMaterialFieldLabel(")[1].split("\n  }\n")[0]
        # Hop limit (8 or similar number) to avoid walking too far up
        assert "hops" in body or "depth" in body


class TestSemanticTargetCarriesMaterialLabel:
    def test_field_present_in_dataclass(self):
        from testforge.semantic.model import SemanticTarget
        t = SemanticTarget(material_field_label="Renda mensal")
        assert t.material_field_label == "Renda mensal"

    def test_default_none(self):
        from testforge.semantic.model import SemanticTarget
        t = SemanticTarget()
        assert t.material_field_label is None


class TestNormalizerEmitsMaterialAnchorCandidate:
    def _build_target_data(self, material_label, tag="input"):
        return {
            "tag": tag,
            "role": "textbox",
            "accessible_name": "Renda mensal *",
            "placeholder": "R$0,00",
            "material_field_label": material_label,
            "candidates": [],
        }

    def test_material_anchor_inserted_at_top_when_label_present(self):
        from testforge.semantic.recording_normalizer import RecordingNormalizer
        norm = RecordingNormalizer()
        target_data = self._build_target_data("Renda mensal")
        target = norm._build_target(target_data)
        # First candidate must be the material anchor
        assert target.candidates, "no candidates emitted"
        top = target.candidates[0]
        assert top.strategy == "material_form_field"
        assert 'mat-form-field' in top.selector
        assert 'mat-label' in top.selector
        assert 'has-text("Renda mensal")' in top.selector
        assert top.score >= 0.99

    def test_no_material_candidate_when_label_absent(self):
        from testforge.semantic.recording_normalizer import RecordingNormalizer
        norm = RecordingNormalizer()
        target_data = self._build_target_data(None)
        target = norm._build_target(target_data)
        for c in target.candidates:
            assert c.strategy != "material_form_field"

    def test_material_field_label_propagated_to_target(self):
        from testforge.semantic.recording_normalizer import RecordingNormalizer
        norm = RecordingNormalizer()
        target_data = self._build_target_data("Valor do imovel")
        target = norm._build_target(target_data)
        assert target.material_field_label == "Valor do imovel"

    def test_special_chars_escaped_in_selector(self):
        from testforge.semantic.recording_normalizer import RecordingNormalizer
        norm = RecordingNormalizer()
        target_data = self._build_target_data('Quote " inside label')
        target = norm._build_target(target_data)
        top = target.candidates[0]
        # double-quote inside has-text() must be backslash-escaped
        assert '\\"' in top.selector

    def test_textarea_tag_preserved(self):
        from testforge.semantic.recording_normalizer import RecordingNormalizer
        norm = RecordingNormalizer()
        target_data = self._build_target_data("Comentario", tag="textarea")
        target = norm._build_target(target_data)
        top = target.candidates[0]
        assert ' textarea' in top.selector


class TestSelectorShapeMatchesPlaywrightSyntax:
    """Sanity: the emitted selector must be valid Playwright CSS engine."""

    def test_selector_uses_has_not_inner(self):
        from testforge.semantic.recording_normalizer import RecordingNormalizer
        norm = RecordingNormalizer()
        target_data = {
            "tag": "input",
            "material_field_label": "X",
            "candidates": [],
        }
        target = norm._build_target(target_data)
        top = target.candidates[0]
        # Playwright supports `:has()`, not deprecated `:contains`
        assert ":has(" in top.selector
        assert ":contains" not in top.selector
