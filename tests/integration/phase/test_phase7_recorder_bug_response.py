
import json
from pathlib import Path
from unittest.mock import MagicMock

from testforge.recorder.recorder_controller import RecorderController


def test_when_application_bug_response_then_writes_bug_report_jsonl(tmp_path):
    page = MagicMock()
    recorder = RecorderController(page, recordings_root=str(tmp_path))
    recorder.start(recording_id="REC-BUG-1", bug_detection_enabled=False)

    response = {
        "verdict": "application_bug",
        "timestamp": "2026-07-01T12:00:00Z",
        "user_expected_behavior": "Should show success",
        "signals": [
            {
                "type": "network_5xx",
                "timestamp": "2026-07-01T12:00:01Z",
                "payload": {"status": 500, "url": "http://localhost/api"},
            }
        ],
    }

    recorder._process_bug_response(response)

    bug_path = Path(recorder._store._session_dir) / "bug_report.jsonl"
    assert bug_path.exists()
    lines = bug_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["source"] == "application_under_test"
    assert payload["severity"] == "critical"
    assert payload["recording_id"] == "REC-BUG-1"

