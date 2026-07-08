"""Hotfix 1 — candidatos heuristicos + cache de deteccao."""
from __future__ import annotations

from unittest.mock import MagicMock

from testforge.diagnostic.framework_detector import FrameworkDetector
from testforge.diagnostic.heuristic_candidates import build_quick_candidates


class TestQuickCandidates:
    def test_empty_target(self):
        assert build_quick_candidates(None) == []
        assert build_quick_candidates({}) == []

    def test_test_id_first(self):
        out = build_quick_candidates({"test_id": "save-btn", "tag": "button"})
        assert out[0]["strategy"] == "test_id_css"
        assert out[0]["selector"] == '[data-testid="save-btn"]'
        assert "test_id" in out[0]["playwright_call"]

    def test_role_plus_name_native(self):
        out = build_quick_candidates({
            "role": "button", "accessible_name": "Salvar", "tag": "button",
        })
        assert any(c["strategy"] == "playwright_native" for c in out)
        native = next(c for c in out if c["strategy"] == "playwright_native")
        assert 'get_by_role("button", name="Salvar")' in native["playwright_call"]

    def test_aria_label_emits_with_tag_prefix(self):
        out = build_quick_candidates({
            "accessible_name": "Email", "tag": "input",
        })
        sel = next(c for c in out if c["strategy"] == "aria_label_css")
        assert sel["selector"] == 'input[aria-label="Email"]'

    def test_placeholder_with_input_tag(self):
        out = build_quick_candidates({
            "placeholder": "R$0,00", "tag": "input",
        })
        ph = next(c for c in out if c["strategy"] == "placeholder_css")
        assert ph["selector"] == 'input[placeholder="R$0,00"]'

    def test_auto_id_skipped(self):
        out = build_quick_candidates({"element_id": "mat-input-42", "tag": "input"})
        assert all(c["strategy"] != "id_css" for c in out)

    def test_semantic_id_kept(self):
        out = build_quick_candidates({"element_id": "user-email", "tag": "input"})
        assert any(c["strategy"] == "id_css" for c in out)

    def test_quotes_escaped_in_name(self):
        out = build_quick_candidates({
            "role": "button", "accessible_name": 'Click "now"',
        })
        native = next(c for c in out if c["strategy"] == "playwright_native")
        assert '\\"' in native["selector"]

    def test_all_strategies_typical_input(self):
        out = build_quick_candidates({
            "tag": "input", "role": "textbox",
            "accessible_name": "Email", "placeholder": "you@x.com",
            "element_id": "user-email",
        })
        strategies = {c["strategy"] for c in out}
        # nativo role+nome, aria_label_css, placeholder_css, id_css
        assert "playwright_native" in strategies
        assert "aria_label_css" in strategies
        assert "placeholder_css" in strategies
        assert "id_css" in strategies


class TestDetectionCache:
    def _page_eval_result(self, primary_signals: dict):
        page = MagicMock()
        page.evaluate = MagicMock(return_value=primary_signals)
        page.url = "http://x/"
        return page

    def test_successful_detection_cached(self):
        page = self._page_eval_result({
            "angular": True, "angular_material": True,
            "custom_components": ["dsc-input"],
            "shadow_dom_count": 0, "iframe_count": 0,
            "dom_size": 10, "max_depth": 3,
            "interactive_elements": 0, "form_count": 0,
            "evidence": ["[ng-version=16]"],
        })
        det = FrameworkDetector(page, cdp_session=None)
        result1 = det.detect()
        assert result1["primary"] == "angular-material"
        assert det._last_detection is not None
        assert det._last_detection["primary"] == "angular-material"

    def test_page_eval_failed_uses_cache(self):
        # Primeira deteccao bem-sucedida
        page = self._page_eval_result({
            "angular_material": True, "custom_components": [],
            "shadow_dom_count": 0, "iframe_count": 0, "dom_size": 10,
            "max_depth": 3, "interactive_elements": 0, "form_count": 0,
            "evidence": [],
        })
        det = FrameworkDetector(page, cdp_session=None)
        det.detect()  # preenche cache
        # Agora o page eval falha (navegador fechado)
        page.evaluate.side_effect = Exception("Target closed")
        result = det.detect()
        # cache servido, primary preservado
        assert result["primary"] == "angular-material"
        assert any("page_eval_failed_at_finalize: served from cache" in e
                    for e in result["evidence"])

    def test_no_cache_when_first_call_already_unknown(self):
        page = self._page_eval_result({
            "custom_components": [], "evidence": [],
            "shadow_dom_count": 0, "iframe_count": 0, "dom_size": 10,
            "max_depth": 3, "interactive_elements": 0, "form_count": 0,
        })
        det = FrameworkDetector(page, cdp_session=None)
        det.detect()
        assert det._last_detection is None
        # segunda chamada ainda desconhecida
        page.evaluate.side_effect = Exception("closed")
        result = det.detect()
        assert result["primary"] == "unknown"
