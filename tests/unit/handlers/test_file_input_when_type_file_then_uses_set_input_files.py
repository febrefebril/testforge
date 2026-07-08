"""RC-11: fill em input[type=file] deve gerar set_input_files, não fill."""
import pytest
from testforge.semantic.recording_normalizer import RecordingNormalizer


@pytest.fixture
def norm():
    return RecordingNormalizer()


def _file_event(filename, value=None, file_upload=None):
    return {
        "type": "fill", "event_id": "e1",
        "url": "http://x", "page_title": "T",
        "timestamp": "2026-07-07T00:00:00Z",
        "target": {
            "tag": "input", "element_id": "files",
            "attributes": {"type": "file", "id": "files"},
            "all_attributes": {"type": "file", "id": "files"},
            "label": "Upload", "css_path": "#files",
        },
        "value": value or f"C:\\fakepath\\{filename}",
        "file_upload": file_upload or [{"name": filename, "size": 100, "type": ""}],
    }


@pytest.mark.unit
class TestFileInputWhenTypeFileThenUsesSetInputFiles:

    def test_action_is_set_input_files(self, norm):
        raw = _file_event("relatorio.pdf")
        action = norm._convert_event(raw)
        assert action is not None
        assert action.action == "set_input_files"

    def test_value_strips_fakepath(self, norm):
        raw = _file_event("relatorio.pdf", value="C:\\fakepath\\relatorio.pdf", file_upload=[])
        action = norm._convert_event(raw)
        assert action.value == "relatorio.pdf"

    def test_value_from_file_upload_metadata(self, norm):
        raw = _file_event("CNT.EMP.MZ.D260625.R4", file_upload=[{"name": "CNT.EMP.MZ.D260625.R4", "size": 546, "type": ""}])
        action = norm._convert_event(raw)
        assert action.value == "CNT.EMP.MZ.D260625.R4"

    def test_regular_fill_not_affected(self, norm):
        raw = {
            "type": "fill", "event_id": "e2",
            "url": "http://x", "page_title": "T",
            "timestamp": "2026-07-07T00:00:00Z",
            "target": {"tag": "input", "element_id": "nome", "attributes": {"type": "text"}, "all_attributes": {}, "css_path": "#nome"},
            "value": "João",
        }
        action = norm._convert_event(raw)
        assert action is not None
        assert action.action == "fill"
