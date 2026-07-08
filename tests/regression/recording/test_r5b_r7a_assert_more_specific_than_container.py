"""RC-14 regression: assert em .container-fluid deve emitir warning; assert em h1
específico não deve emitir warning. Também cobre mat-button-wrapper promotion."""
import pytest
from unittest.mock import patch
from testforge.semantic.recording_normalizer import RecordingNormalizer


@pytest.fixture
def normalizer():
    return RecordingNormalizer()


@pytest.mark.regression
@pytest.mark.unit
class TestR5bR7aAssertMoreSpecificThanContainer:

    def test_assert_on_h1_no_warning(self, normalizer):
        # Arrange — R5b: assert em h1 específico (resultado de simulação)
        step = {
            "action": "assert",
            "assert_type": "textual",
            "expected_value": "Simulação aprovada",
            "css_path": "h1.resultado-titulo",
            "tag_name": "h1",
            "element_id": "",
            "role": "heading",
            "accessible_name": "Simulação aprovada",
            "text": "Simulação aprovada",
            "timestamp": "2026-07-07T00:00:00.000Z",
        }

        # Act
        with patch("testforge.semantic.recording_normalizer.logger") as mock_log:
            action = normalizer._convert_step(step)

        # Assert — no warning logged
        mock_log.warning.assert_not_called()
        assert not action.skip_reason

    def test_assert_on_container_fluid_warns(self, normalizer):
        # Arrange — R5b: assert acidentalmente em .container-fluid (wrapper do resultado)
        step = {
            "action": "assert",
            "assert_type": "textual",
            "expected_value": "Simulação aprovada",
            "css_path": "div.container-fluid",
            "tag_name": "div",
            "element_id": "",
            "role": "",
            "accessible_name": "",
            "text": "",
            "timestamp": "2026-07-07T00:00:00.000Z",
        }

        # Act
        with patch("testforge.semantic.recording_normalizer.logger") as mock_log:
            action = normalizer._convert_step(step)

        # Assert — warning logged but assert not skipped
        mock_log.warning.assert_called()
        assert not action.skip_reason

    def test_mat_button_wrapper_promotes_to_button(self, normalizer):
        # Arrange — R7a: click em .mat-button-wrapper (Angular Material button ripple)
        target_data = {
            "tag": "span",
            "css_path": "button.mat-button > span.mat-button-wrapper",
            "text": "Calcular EGI",
            "accessible_name": "Calcular EGI",
        }

        # Act
        target = normalizer._build_target(target_data)

        # Assert — promoted to button:has-text(), not the span css_path
        css_cands = [c for c in target.candidates if c.strategy == "css_path"]
        assert css_cands, "should have css candidate"
        top_css = css_cands[0]
        assert "button:has-text" in top_css.selector, (
            f"mat-button-wrapper should promote to button:has-text, got: {top_css.selector}"
        )
        assert "mat-button-wrapper" not in top_css.selector

    def test_nth_of_type_css_gets_has_text_variant(self, normalizer):
        # Arrange — R7b: seletor posicional tr:nth-of-type(3) deve ganhar variante has_text
        target_data = {
            "tag": "tr",
            "css_path": "table.resultados > tbody > tr:nth-of-type(3)",
            "text": "R$ 1.500,00",
        }

        # Act
        target = normalizer._build_target(target_data)

        # Assert — has_text variant added alongside positional selector
        css_cands = [c for c in target.candidates if c.strategy == "css_path"]
        has_text_cands = [c for c in css_cands if "has-text" in c.selector]
        assert has_text_cands, "nth-of-type css_path should have a has_text variant"
