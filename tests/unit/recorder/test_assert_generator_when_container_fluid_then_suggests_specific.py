"""RC-14 regression: assert on container-fluid / generic wrappers logs warning;
assert with no expected_value for textual type sets skip_reason."""
import pytest
from unittest.mock import patch
from testforge.semantic.recording_normalizer import RecordingNormalizer


@pytest.fixture
def normalizer():
    return RecordingNormalizer()


def _make_assert_step(assert_type="textual", expected_value="", css_path="", tag="div"):
    return {
        "action": "assert",
        "assert_type": assert_type,
        "expected_value": expected_value,
        "css_path": css_path,
        "tag_name": tag,
        "element_id": "",
        "role": "",
        "accessible_name": "",
        "text": "",
        "timestamp": "2026-07-07T00:00:00Z",
    }


@pytest.mark.unit
class TestAssertGeneratorWhenContainerFluidThenSuggestsSpecific:

    def test_textual_assert_no_expected_sets_skip_reason(self, normalizer):
        # Arrange
        step = _make_assert_step(assert_type="textual", expected_value="", css_path="#main > div")

        # Act
        action = normalizer._convert_step(step)

        # Assert
        assert action is not None, "should return action, not None"
        assert action.skip_reason == "assert_missing_expected"

    def test_automatico_assert_no_expected_sets_skip_reason(self, normalizer):
        # Arrange
        step = _make_assert_step(assert_type="automatico", expected_value="")

        # Act
        action = normalizer._convert_step(step)

        # Assert
        assert action.skip_reason == "assert_missing_expected"

    def test_textual_assert_with_expected_no_skip(self, normalizer):
        # Arrange
        step = _make_assert_step(assert_type="textual", expected_value="Aprovado", css_path="#result")

        # Act
        action = normalizer._convert_step(step)

        # Assert
        assert not action.skip_reason, f"should not skip, got: {action.skip_reason}"
        assert action.value == "Aprovado"

    def test_visivel_assert_no_expected_no_skip(self, normalizer):
        # Arrange — visivel asserts use 'visible'/'hidden' string, expected_value may be empty at skip check
        step = _make_assert_step(assert_type="visivel", expected_value="visible")

        # Act
        action = normalizer._convert_step(step)

        # Assert
        assert not action.skip_reason

    def test_container_fluid_css_logs_warning(self, normalizer):
        # Arrange
        step = _make_assert_step(
            assert_type="textual",
            expected_value="Resultado",
            css_path="div.container-fluid > span",
        )

        # Act
        with patch("testforge.semantic.recording_normalizer.logger") as mock_log:
            action = normalizer._convert_step(step)

        # Assert — warning was emitted, but assert still proceeds (not skipped)
        mock_log.warning.assert_called()
        assert not action.skip_reason

    def test_wrapper_css_logs_warning(self, normalizer):
        # Arrange
        step = _make_assert_step(
            assert_type="textual",
            expected_value="Total",
            css_path="div.wrapper > p",
        )

        # Act
        with patch("testforge.semantic.recording_normalizer.logger") as mock_log:
            action = normalizer._convert_step(step)

        # Assert
        mock_log.warning.assert_called()

    def test_specific_css_no_warning(self, normalizer):
        # Arrange
        step = _make_assert_step(
            assert_type="textual",
            expected_value="R$ 1.500,00",
            css_path="#result-value",
        )

        # Act
        with patch("testforge.semantic.recording_normalizer.logger") as mock_log:
            action = normalizer._convert_step(step)

        # Assert
        mock_log.warning.assert_not_called()
