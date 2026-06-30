"""TestForge — Sprint M (2026-06-30): runtime resolver Material anchor.

Sprint J (commit 6981c6d) emitiu candidate `mat-form-field:has(mat-label)`
no compiler legacy + raw event. Sprint M conclui o wire-up:

- semantic/locator/extractor.py: STRATEGY_WEIGHTS[material_form_field]=0.99
  + extract() emite candidate quando target_data tem material_field_label
- runtime/resolver.py: itera candidates por score, prefix L1_ aplicado
  automaticamente — entao agora replay_check loga
  attempted=['L1_material_form_field'] PRIMEIRO antes de aria_label_css

Sem isso Sprint J ficava latente — runtime tentava L1_aria_label_css
direto e ignorava o anchor estrutural mais estavel.
"""
from __future__ import annotations
import pytest


class TestExtractorEmitsMaterialCandidate:
    def _build_target_data(self, material_label):
        return {
            "tag": "input",
            "role": "textbox",
            "accessible_name": "Renda mensal *",
            "placeholder": "R$0,00",
            "material_field_label": material_label,
        }

    def test_material_candidate_first_when_label_present(self):
        from testforge.semantic.locator.extractor import LocatorExtractor
        ex = LocatorExtractor()
        cands = ex.extract(self._build_target_data("Renda mensal *"))
        assert cands, "expected at least one candidate"
        first = cands[0]
        assert first.strategy == "material_form_field"
        assert "mat-form-field" in first.selector
        assert 'has-text("Renda mensal *")' in first.selector

    def test_no_material_when_label_absent(self):
        from testforge.semantic.locator.extractor import LocatorExtractor
        ex = LocatorExtractor()
        cands = ex.extract(self._build_target_data(None))
        for c in cands:
            assert c.strategy != "material_form_field"

    def test_material_textarea_tag_preserved(self):
        from testforge.semantic.locator.extractor import LocatorExtractor
        ex = LocatorExtractor()
        td = self._build_target_data("Observacoes")
        td["tag"] = "textarea"
        cands = ex.extract(td)
        first = cands[0]
        assert first.strategy == "material_form_field"
        assert " textarea" in first.selector

    def test_material_label_quotes_escaped(self):
        from testforge.semantic.locator.extractor import LocatorExtractor
        ex = LocatorExtractor()
        td = self._build_target_data('Label "with" quotes')
        cands = ex.extract(td)
        first = cands[0]
        assert '\\"with\\"' in first.selector


class TestStrategyWeightsContainsMaterial:
    def test_material_weight_above_aria(self):
        from testforge.semantic.locator.extractor import STRATEGY_WEIGHTS
        assert STRATEGY_WEIGHTS["material_form_field"] > STRATEGY_WEIGHTS["aria_label_css"]
        assert STRATEGY_WEIGHTS["material_form_field"] >= 0.99
