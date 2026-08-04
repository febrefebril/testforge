
from testforge.runner.step_executor import StepExecutor
from testforge.semantic.model import SemanticAction
from testforge.semantic.recording_normalizer import RecordingNormalizer
from testforge.semantic.specialized_actions import SpecializedAction


def test_normalizer_promotes_file_upload_before_generic_fill():
    action = RecordingNormalizer()._convert_event({
        "event_id": "upload-1", "type": "fill",
        "target": {"element_id": "arquivo"},
        "file_upload": [{"name": "massa.csv", "path": "fixtures/massa.csv"}],
    })
    assert action.action == "file_upload"
    assert action.specialized_action["kind"] == "file_upload"
    assert action.specialized_action["selector"] == "#arquivo"


def test_specialized_contract_round_trip():
    data = {"kind": "authentication_redirect", "event_id": "auth-1",
            "url": "**/home", "payload": {"url_pattern": "**/home"}}
    assert SpecializedAction.from_dict(data).as_dict()["kind"] == "authentication_redirect"


class _RedirectPage:
    def __init__(self):
        self.url = "https://example.test/login"
        self.waited = []
    def wait_for_url(self, pattern):
        self.waited.append(pattern)
        self.url = "https://example.test/home"
    def wait_for_load_state(self, state):
        self.waited.append(state)


def test_step_executor_routes_specialized_action_through_registry():
    page = _RedirectPage()
    executor = StepExecutor(page)
    step = SemanticAction(action="authentication_redirect", url="**/home",
        specialized_action={"kind": "authentication_redirect", "url": "**/home",
                            "payload": {"url_pattern": "**/home"}})
    executor.execute(step)
    assert page.waited == ["**/home", "domcontentloaded"]
    assert executor._specialized_state["url"].endswith("/home")

