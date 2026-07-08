"""REC-28: aggregate assert(visible/enabled) + click same target into wait_and_click."""
from dataclasses import dataclass, field
from typing import Optional

import pytest


@dataclass
class FakeAction:
    action: str
    target: dict = field(default_factory=dict)
    context: Optional[dict] = None
    notes: str = ""


@pytest.mark.unit
class TestCheckThenActWhenAssertThenClickSameTargetThenMerges:
    def test_assert_visible_then_click_merges(self):
        """assert(visivel) + click same target → 1 step with preceded_by_assert."""
        # Arrange
        from testforge.semantic.recording_normalizer import _aggregate_check_then_act
        steps = [
            FakeAction(action="assert", target={"element_id": "btn"},
                       context={"assert_type": "visivel"}),
            FakeAction(action="click", target={"element_id": "btn"}),
        ]
        # Act
        _aggregate_check_then_act(steps)
        # Assert
        assert len(steps) == 1
        assert steps[0].action == "click"
        assert steps[0].context["preceded_by_assert"] == "visivel"

    def test_different_targets_not_merged(self):
        """Different targets must stay separate."""
        # Arrange
        from testforge.semantic.recording_normalizer import _aggregate_check_then_act
        steps = [
            FakeAction(action="assert", target={"element_id": "btn_a"},
                       context={"assert_type": "visivel"}),
            FakeAction(action="click", target={"element_id": "btn_b"}),
        ]
        # Act
        _aggregate_check_then_act(steps)
        # Assert
        assert len(steps) == 2

    def test_textual_assert_not_merged(self):
        """Only visible/enabled assert merges. Textual assert is separate intent."""
        # Arrange
        from testforge.semantic.recording_normalizer import _aggregate_check_then_act
        steps = [
            FakeAction(action="assert", target={"element_id": "btn"},
                       context={"assert_type": "textual"}),
            FakeAction(action="click", target={"element_id": "btn"}),
        ]
        # Act
        _aggregate_check_then_act(steps)
        # Assert
        assert len(steps) == 2

    def test_assert_enabled_then_submit_merges(self):
        """assert(enabled) + submit same target → 1 step."""
        # Arrange
        from testforge.semantic.recording_normalizer import _aggregate_check_then_act
        steps = [
            FakeAction(action="assert", target={"element_id": "submit_btn"},
                       context={"assert_type": "enabled"}),
            FakeAction(action="submit", target={"element_id": "submit_btn"}),
        ]
        # Act
        _aggregate_check_then_act(steps)
        # Assert
        assert len(steps) == 1
        assert steps[0].action == "submit"
        assert steps[0].context["preceded_by_assert"] == "enabled"

    def test_empty_list_unchanged(self):
        """Empty input returns empty."""
        # Arrange
        from testforge.semantic.recording_normalizer import _aggregate_check_then_act
        steps = []
        # Act
        _aggregate_check_then_act(steps)
        # Assert
        assert steps == []
