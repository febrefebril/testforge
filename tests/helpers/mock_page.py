from dataclasses import dataclass, field
from enum import Enum
from unittest.mock import MagicMock


class CandidateState(Enum):
    EXISTS_AND_ACCEPTS = "exists_ok"
    EXISTS_BUT_REJECTS_FILL = "exists_reject_fill"
    EXISTS_BUT_REJECTS_CLICK = "exists_reject_click"
    EXISTS_BUT_INTERCEPTED = "exists_intercepted"
    NOT_EXISTS = "absent"


@dataclass
class MockPageBuilder:
    _candidates: dict = field(default_factory=dict)

    def with_candidate(self, strategy: str, state: CandidateState):
        self._candidates[strategy] = state
        return self

    def build(self):
        page = MagicMock()
        for strategy, state in self._candidates.items():
            locator = self._make_locator(state)
            if strategy == "role":
                page.get_by_role.return_value = locator
            elif strategy == "label":
                page.get_by_label.return_value = locator
            elif strategy == "placeholder":
                page.get_by_placeholder.return_value = locator
            elif strategy == "test_id":
                page.get_by_test_id.return_value = locator
            elif strategy == "text":
                page.get_by_text.return_value = locator
            else:
                page.locator.return_value = locator
        return page

    def _make_locator(self, state: CandidateState):
        locator = MagicMock()
        locator.count.return_value = 0 if state == CandidateState.NOT_EXISTS else 1
        if state == CandidateState.EXISTS_BUT_REJECTS_FILL:
            locator.fill.side_effect = RuntimeError("fill timeout - mock")
        if state in (CandidateState.EXISTS_BUT_REJECTS_CLICK, CandidateState.EXISTS_BUT_INTERCEPTED):
            locator.click.side_effect = RuntimeError("click rejected - mock")
        return locator
