"""RC-12: evento postback deve gerar wait_for_navigation, não ser descartado."""
import pytest
from testforge.semantic.recording_normalizer import RecordingNormalizer


@pytest.fixture
def norm():
    return RecordingNormalizer()


@pytest.mark.unit
class TestPostbackWhenDetectedThenWaitForNavigation:

    def test_postback_action_is_wait_for_navigation(self, norm):
        raw = {"type": "postback", "event_id": "e1", "url": "http://x/sso",
               "postback_url": "http://x/home", "page_title": "SSO",
               "timestamp": "2026-07-07T00:00:00Z", "target": {}}
        action = norm._convert_event(raw)
        assert action is not None
        assert action.action == "wait_for_navigation"

    def test_postback_value_is_url(self, norm):
        raw = {"type": "postback", "event_id": "e2", "url": "http://x/sso",
               "postback_url": "http://x/home", "page_title": "T",
               "timestamp": "2026-07-07T00:00:00Z", "target": {}}
        action = norm._convert_event(raw)
        assert "x/home" in (action.value or "")

    def test_postback_context_has_flag(self, norm):
        raw = {"type": "postback", "event_id": "e3", "url": "http://x",
               "timestamp": "2026-07-07T00:00:00Z", "target": {}}
        action = norm._convert_event(raw)
        assert action.context.get("postback") is True
