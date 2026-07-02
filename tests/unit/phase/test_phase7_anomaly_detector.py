from unittest.mock import MagicMock

from testforge.recorder.anomaly_detector import AnomalyDetector


def test_when_console_error_then_emits_console_signal():
    page = MagicMock()
    captured = []

    detector = AnomalyDetector(page, on_signal=captured.append)

    msg = MagicMock()
    msg.type = "error"
    msg.text = "TypeError"
    msg.location = {"url": "http://localhost"}

    detector._on_console(msg)

    assert len(captured) == 1
    assert captured[0].type == "console_error"
    assert captured[0].payload["level"] == "error"


def test_when_response_5xx_then_emits_network_5xx_signal():
    page = MagicMock()
    captured = []

    detector = AnomalyDetector(page, on_signal=captured.append)

    response = MagicMock()
    response.status = 500
    response.url = "http://localhost/api/broken"
    response.request.method = "POST"
    response.body.return_value = b"internal error"

    detector._on_response(response)

    assert len(captured) == 1
    assert captured[0].type == "network_5xx"
    assert captured[0].payload["status"] == 500
    assert "internal error" in captured[0].payload["body_snippet"]
