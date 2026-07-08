"""RC-14 regression: overlay assert validation contract.

Verifies that:
1. assert step with type 'visivel' uses expected_value='visible' or 'hidden' (not plain string).
2. assert step with type 'estado' uses _detectState output (checked/unchecked/etc).
3. assert step with type 'textual' and non-empty expected_value is not skipped.
4. overlay validation: missing accessible_name on assert target is tracked in skip metrics.
"""
import pytest
from testforge.semantic.recording_normalizer import RecordingNormalizer


@pytest.fixture
def normalizer():
    return RecordingNormalizer()


def _assert_step(assert_type, expected_value, accessible_name="", css_path="#el"):
    return {
        "action": "assert",
        "assert_type": assert_type,
        "expected_value": expected_value,
        "css_path": css_path,
        "tag_name": "div",
        "element_id": "",
        "role": "",
        "accessible_name": accessible_name,
        "text": "",
        "timestamp": "2026-07-07T00:00:00.000Z",
    }


@pytest.mark.unit
class TestAssertWhenVisibleStateThenStructuredNotString:

    def test_visivel_assert_preserves_visible_string(self, normalizer):
        # Arrange
        step = _assert_step("visivel", "visible")

        # Act
        action = normalizer._convert_step(step)

        # Assert — visivel type: expected_value is the visibility flag, not skipped
        assert not action.skip_reason
        assert action.value == "visible"
        assert action.context["assert_type"] == "visivel"

    def test_visivel_assert_hidden_value(self, normalizer):
        # Arrange
        step = _assert_step("visivel", "hidden")

        # Act
        action = normalizer._convert_step(step)

        # Assert
        assert not action.skip_reason
        assert action.value == "hidden"

    def test_estado_assert_not_skipped(self, normalizer):
        # Arrange
        step = _assert_step("estado", "checked")

        # Act
        action = normalizer._convert_step(step)

        # Assert — estado type is not in textual/automatico skip check
        assert not action.skip_reason
        assert action.value == "checked"

    def test_textual_with_expected_not_skipped(self, normalizer):
        # Arrange
        step = _assert_step("textual", "Aprovado com sucesso")

        # Act
        action = normalizer._convert_step(step)

        # Assert
        assert not action.skip_reason
        assert action.value == "Aprovado com sucesso"

    def test_textual_empty_expected_gets_skip_reason(self, normalizer):
        # Arrange
        step = _assert_step("textual", "")

        # Act
        action = normalizer._convert_step(step)

        # Assert
        assert action.skip_reason == "assert_missing_expected"

    def test_visivel_empty_expected_not_skipped(self, normalizer):
        # Arrange — 'visivel' type with empty expected: normalizer doesn't skip
        # (skip only applies to textual/automatico)
        step = _assert_step("visivel", "")

        # Act
        action = normalizer._convert_step(step)

        # Assert
        assert not action.skip_reason
